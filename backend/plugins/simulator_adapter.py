"""Agent-facing tools backed by explicit mom.life simulator data."""
import re

from plugins.api_adapters import definition, field


class SimulatorAdapter:
    def __init__(self, plugin_id, family_id, store):
        if plugin_id not in {"whatsapp", "fitbit", "withings", "instacart"}:
            raise ValueError("This plugin does not have a simulator adapter.")
        self.plugin_id = plugin_id
        self.family_id = family_id
        self.store = store

    def directory(self):
        child_date = {
            "child_id": field("child_id", "Child profile ID"),
            "date": field("date", "Date in YYYY-MM-DD format"),
        }
        if self.plugin_id == "whatsapp":
            return [definition("send_text", "Send a message to a simulated family profile.", {
                "to": field("to", "Simulated family profile ID"),
                "text": field("text", "Exact requested message"),
            }, True)]
        if self.plugin_id == "fitbit":
            return [
                definition("read_profile", "Read a simulated child activity profile.", {"child_id": field("child_id", "Child profile ID")}),
                definition("read_daily_activity", "Read simulated daily activity for one child.", child_date),
                definition("read_sleep", "Read simulated sleep for one child.", child_date),
            ]
        if self.plugin_id == "withings":
            return [
                definition("read_measurements", "Read simulated measurements for one child.", {"child_id": field("child_id", "Child profile ID")}),
                definition("read_daily_activity", "Read simulated daily activity for one child.", child_date),
                definition("read_sleep", "Read simulated sleep for one child.", child_date),
            ]
        return [
            definition("create_recipe_page", "Create a simulated Instacart recipe page.", {
                "title": field("title", "Recipe title"), "ingredients": field("ingredients", "Comma-separated ingredients"),
            }, True),
            definition("prepare_shopping_list", "Prepare a simulated Instacart shopping list.", {
                "items": field("items", "Comma-separated grocery items"),
            }, True),
        ]

    async def call(self, name, arguments):
        spec = next((item for item in self.directory() if item["name"] == name), None)
        required = set(spec["inputSchema"]["json"]["required"]) if spec else set()
        if not spec or set(arguments) != required or any(not isinstance(value, str) or not value.strip() for value in arguments.values()):
            raise ValueError("Use an exact simulator capability and its documented arguments.")
        if "date" in arguments and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", arguments["date"]):
            raise ValueError("Date must use YYYY-MM-DD.")
        if self.plugin_id == "whatsapp":
            from app.auth import families
            recipient = arguments["to"]
            if recipient != "parent" and not families.child(self.family_id, recipient):
                raise ValueError("Choose a simulated family profile.")
            message = self.store.add_simulator_message(self.family_id, recipient, "outgoing", arguments["text"].strip(), "agent")
            from app.event_stream import family_events
            family_events.publish(self.family_id, {'type':'simulator_changed'})
            return {"status": "success", "data": {**message, "reply_correlation": f"sim:{recipient}"}}
        if self.plugin_id in {"fitbit", "withings"}:
            return self._health(name, arguments)
        detail = {key: value.strip() for key, value in arguments.items()}
        return {"status": "success", "data": self.store.add_simulator_action(self.family_id, self.plugin_id, name, detail)}

    def _health(self, name, arguments):
        child_id = arguments["child_id"]
        from app.auth import families
        child = families.child(self.family_id, child_id)
        if not child:
            raise ValueError("Choose a known child profile.")
        if name in {"read_profile", "read_measurements"}:
            return {"status": "success", "data": {"id": child_id, "name": child["name"], "source": "mom.life Simulator"}}
        types = ("sleep_analysis",) if name == "read_sleep" else ("step_count", "active_energy", "walking_running_distance", "heart_rate")
        placeholders = ",".join("?" for _ in types)
        with self.store._connect() as db:
            rows = db.execute(
                f"""SELECT sample_type,start_at,end_at,value,unit,source FROM apple_health_samples
                WHERE family_id=? AND child_id=? AND substr(start_at,1,10)=? AND sample_type IN ({placeholders})
                AND source='mom.life Simulator' ORDER BY start_at""",
                (self.family_id, child_id, arguments["date"], *types),
            ).fetchall()
        return {"status": "success", "data": {"samples": [dict(row) for row in rows]}}

    async def validate(self):
        return {"status": "success", "data": {"provider": self.plugin_id, "mode": "simulated"}}
