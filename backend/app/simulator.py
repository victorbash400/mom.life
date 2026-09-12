from datetime import UTC, date, datetime, time, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from plugins.apple_health_adapter import AppleHealthAdapter
from app.database import batch


SIMULATED_PLUGINS = {"whatsapp", "apple-health", "fitbit", "withings", "instacart"}
HEALTH_PLUGINS = {"apple-health", "fitbit", "withings"}


class SimulatorService:
    def __init__(self, store, families):
        self.store = store
        self.families = families

    def state(self, family_id):
        if isinstance(self.store.database, Path):
            parent = self.families.profile(family_id)
            if not parent:
                raise ValueError("Family account not found.")
            profiles = [{"id": "parent", "name": parent["name"], "role": "adult"}]
            profiles.extend({"id": child["id"], "name": child["name"], "role": "child"} for child in self.families.list_children(family_id))
            connected = self.store.simulator_plugins(family_id)
            return {
                "profiles": profiles,
                "connections": [{"id": plugin_id, "connected": plugin_id in connected} for plugin_id in sorted(SIMULATED_PLUGINS)],
                "messages": self.store.simulator_messages(family_id),
                "health": self.health_summary(family_id),
            }
        AppleHealthAdapter(family_id, self.store)
        target_date = date.today().isoformat()
        with self.store._connect() as db:
            with batch(db):
                parent_cursor = db.execute('SELECT name FROM accounts WHERE family_id=? ORDER BY created_at LIMIT 1', (family_id,))
                children_cursor = db.execute('SELECT id,name FROM children WHERE family_id=? ORDER BY created_at,id', (family_id,))
                connected_cursor = db.execute('SELECT plugin_id FROM simulator_connections WHERE family_id=?', (family_id,))
                messages_cursor = db.execute('SELECT * FROM simulator_messages WHERE family_id=? ORDER BY created_at DESC LIMIT 80', (family_id,))
                health_cursor = db.execute("""SELECT child_id,sample_type,start_at,end_at,value,unit FROM apple_health_samples
                    WHERE family_id=? AND substr(start_at,1,10)=? AND source='mom.life Simulator'""", (family_id, target_date))
            parent = parent_cursor.fetchone()
            children = children_cursor.fetchall()
            connected = {row['plugin_id'] for row in connected_cursor}
            messages = messages_cursor.fetchall()
            health = health_cursor.fetchall()
        if not parent:
            raise ValueError("Family account not found.")
        profiles = [{"id": "parent", "name": parent["name"], "role": "adult"}]
        profiles.extend({"id": child["id"], "name": child["name"], "role": "child"} for child in children)
        return {
            "profiles": profiles,
            "connections": [{"id": plugin_id, "connected": plugin_id in connected} for plugin_id in sorted(SIMULATED_PLUGINS)],
            "messages": [dict(row) for row in reversed(messages)],
            "health": self._health_summary(target_date, health),
        }

    def connect(self, family_id, plugin_id):
        self._require_supported(plugin_id)
        self.store.install_plugin(family_id, plugin_id)
        self.store.set_simulator_plugin(family_id, plugin_id, True)
        if plugin_id in HEALTH_PLUGINS:
            self.seed_health(family_id)
        return self.state(family_id)

    def disconnect(self, family_id, plugin_id):
        self._require_supported(plugin_id)
        self.store.set_simulator_plugin(family_id, plugin_id, False)
        if plugin_id in HEALTH_PLUGINS and not (self.store.simulator_plugins(family_id) & HEALTH_PLUGINS):
            with self.store._connect() as db:
                db.execute("DELETE FROM apple_health_samples WHERE family_id=? AND source='mom.life Simulator'", (family_id,))

    def seed_health(self, family_id):
        adapter = AppleHealthAdapter(family_id, self.store)
        samples = []
        for child in self.families.list_children(family_id):
            seed = int.from_bytes(sha256(str(child["id"]).encode()).digest()[:2], "big")
            for day_offset in range(0, 7):
                sample_date = date.today() - timedelta(days=day_offset)
                start = datetime.combine(sample_date, time(7, 0), UTC)
                values = {
                    "step_count": (4800 + seed % 3100 + day_offset * 113, "count", start, start + timedelta(hours=12)),
                    "active_energy": (210 + seed % 170 + day_offset * 7, "kcal", start, start + timedelta(hours=12)),
                    "walking_running_distance": (2600 + seed % 2200 + day_offset * 41, "m", start, start + timedelta(hours=12)),
                    "heart_rate": (68 + seed % 18, "count/min", start + timedelta(hours=5), start + timedelta(hours=5, minutes=1)),
                    "sleep_analysis": (1, "stage", datetime.combine(sample_date, time(0, 0), UTC), datetime.combine(sample_date, time(0, 0), UTC) + timedelta(hours=8 + (seed % 8) / 10)),
                }
                for sample_type, (value, unit, begins, ends) in values.items():
                    samples.append(SimpleNamespace(
                        external_id=f"simulator:{child['id']}:{sample_date.isoformat()}:{sample_type}", child_id=child["id"],
                        sample_type=sample_type, start_at=begins, end_at=ends, value=value, unit=unit, source="mom.life Simulator",
                    ))
        adapter.sync(samples, [])

    def update_health(self, family_id, child_id, sample_date, steps, sleep_hours, heart_rate, active_energy, distance):
        child = self.families.child(family_id, child_id)
        if not child:
            raise ValueError("Choose a known child profile.")
        if not (self.store.simulator_plugins(family_id) & HEALTH_PLUGINS):
            raise ValueError("Connect a simulated health provider first.")
        start = datetime.combine(sample_date, time(7, 0), UTC)
        values = {
            "step_count": (steps, "count", start, start + timedelta(hours=12)),
            "active_energy": (active_energy, "kcal", start, start + timedelta(hours=12)),
            "walking_running_distance": (distance, "m", start, start + timedelta(hours=12)),
            "heart_rate": (heart_rate, "count/min", start + timedelta(hours=5), start + timedelta(hours=5, minutes=1)),
            "sleep_analysis": (1, "stage", datetime.combine(sample_date, time(0, 0), UTC), datetime.combine(sample_date, time(0, 0), UTC) + timedelta(hours=sleep_hours)),
        }
        samples = [SimpleNamespace(
            external_id=f"simulator:{child_id}:{sample_date.isoformat()}:{kind}", child_id=child_id, sample_type=kind,
            start_at=begins, end_at=ends, value=value, unit=unit, source="mom.life Simulator",
        ) for kind, (value, unit, begins, ends) in values.items()]
        AppleHealthAdapter(family_id, self.store).sync(samples, [])
        return self.health_summary(family_id, child_id, sample_date)

    def health_summary(self, family_id, child_id=None, sample_date=None):
        AppleHealthAdapter(family_id, self.store)
        target_date = (sample_date or date.today()).isoformat()
        query = """SELECT child_id,sample_type,start_at,end_at,value,unit FROM apple_health_samples
            WHERE family_id=? AND substr(start_at,1,10)=? AND source='mom.life Simulator'"""
        params = [family_id, target_date]
        if child_id:
            query += " AND child_id=?"
            params.append(child_id)
        with self.store._connect() as db:
            rows = db.execute(query, tuple(params)).fetchall()
        return self._health_summary(target_date, rows)

    @staticmethod
    def _health_summary(target_date, rows):
        profiles = {}
        for row in rows:
            values = profiles.setdefault(row["child_id"], {})
            if row["sample_type"] == "sleep_analysis":
                duration = (datetime.fromisoformat(row["end_at"]) - datetime.fromisoformat(row["start_at"])).total_seconds() / 3600
                values["sleep_analysis"] = round(values.get("sleep_analysis", 0) + duration, 1)
            else:
                values[row["sample_type"]] = row["value"]
        return {"date": target_date, "profiles": profiles}

    @staticmethod
    def _require_supported(plugin_id):
        if plugin_id not in SIMULATED_PLUGINS:
            raise ValueError("This plugin does not support simulation.")
