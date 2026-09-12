import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4


def now() -> str:
    return datetime.now(UTC).isoformat()


from app.goal_ledger import GoalLedger
from app.database import batch, connect, table_exists


class TaskStore(GoalLedger):
    """Durable family goals, assignment boards, skills, plugins, and evidence."""

    def __init__(self, path: Path) -> None:
        self.database = path
        self.path = path if isinstance(path, Path) else Path(__file__).resolve().parents[1] / "data" / "postgres"
        if isinstance(path, Path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS family_tasks (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, child_id TEXT NOT NULL,
                    text TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, run_state TEXT NOT NULL DEFAULT 'idle',
                    current_step TEXT NOT NULL DEFAULT '', progress INTEGER NOT NULL DEFAULT 0,
                    report TEXT NOT NULL DEFAULT '', skill_ids TEXT NOT NULL DEFAULT '[]',
                    plugin_ids TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS goal_assignments (
                    id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, title TEXT NOT NULL,
                    instruction TEXT NOT NULL, status TEXT NOT NULL, phase TEXT NOT NULL,
                    current_step TEXT NOT NULL, next_step TEXT NOT NULL DEFAULT '',
                    progress INTEGER NOT NULL DEFAULT 0, depends_on TEXT NOT NULL DEFAULT '[]',
                    required_inputs TEXT NOT NULL DEFAULT '[]', expected_outputs TEXT NOT NULL DEFAULT '[]',
                    skill_ids TEXT NOT NULL DEFAULT '[]', report TEXT NOT NULL DEFAULT '',
                    evidence TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL,
                    started_at TEXT, finished_at TEXT,
                    FOREIGN KEY(goal_id) REFERENCES family_tasks(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS goal_activities (
                    id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, kind TEXT NOT NULL,
                    summary TEXT NOT NULL, evidence TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
                    FOREIGN KEY(goal_id) REFERENCES family_tasks(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS plugin_installations (
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, installed_at TEXT NOT NULL,
                    PRIMARY KEY(family_id, plugin_id)
                );
                CREATE TABLE IF NOT EXISTS plugin_permissions (
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, permission_id TEXT NOT NULL,
                    enabled INTEGER NOT NULL, PRIMARY KEY(family_id, plugin_id, permission_id)
                );
                CREATE TABLE IF NOT EXISTS profile_plugin_access (
                    family_id TEXT NOT NULL, profile_id TEXT NOT NULL, plugin_id TEXT NOT NULL,
                    enabled INTEGER NOT NULL, PRIMARY KEY(family_id, profile_id, plugin_id)
                );
                CREATE TABLE IF NOT EXISTS family_skills (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, slug TEXT NOT NULL,
                    name TEXT NOT NULL, description TEXT NOT NULL, instructions TEXT NOT NULL,
                    required_plugin_ids TEXT NOT NULL DEFAULT '[]', source TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
                    UNIQUE(family_id, slug)
                );
                CREATE TABLE IF NOT EXISTS incoming_items (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, source TEXT NOT NULL,
                    provider_event_id TEXT NOT NULL, correlation TEXT NOT NULL DEFAULT '',
                    sender TEXT NOT NULL DEFAULT '', subject TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'queued', action TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '', child_id TEXT NOT NULL DEFAULT '',
                    goal_id TEXT NOT NULL DEFAULT '', attention_required INTEGER NOT NULL DEFAULT 0,
                    failure TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, processed_at TEXT,
                    UNIQUE(family_id, source, provider_event_id)
                );
                CREATE TABLE IF NOT EXISTS intake_activities (
                    id TEXT PRIMARY KEY, incoming_id TEXT NOT NULL,
                    kind TEXT NOT NULL, summary TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
                    FOREIGN KEY(incoming_id) REFERENCES incoming_items(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS family_intake_memory (
                    family_id TEXT NOT NULL, scope_id TEXT NOT NULL,
                    summary TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(family_id, scope_id)
                );
                CREATE TABLE IF NOT EXISTS security_settings (
                    family_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1,
                    alert_level TEXT NOT NULL DEFAULT 'important',
                    instructions TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS security_policy (family_id TEXT PRIMARY KEY, policy TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS security_reviews (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, incoming_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued', action TEXT NOT NULL DEFAULT '',
                    severity TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '',
                    child_id TEXT NOT NULL DEFAULT '', dismissed INTEGER NOT NULL DEFAULT 0,
                    failure TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, processed_at TEXT,
                    UNIQUE(family_id, incoming_id)
                );
                CREATE TABLE IF NOT EXISTS security_activities (
                    id TEXT PRIMARY KEY, review_id TEXT NOT NULL,
                    kind TEXT NOT NULL, summary TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
                    FOREIGN KEY(review_id) REFERENCES security_reviews(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS family_education_snapshots (
                    family_id TEXT NOT NULL, child_id TEXT NOT NULL,
                    summary TEXT NOT NULL, source_ids TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL, PRIMARY KEY(family_id, child_id)
                );
                CREATE TABLE IF NOT EXISTS education_reviews (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, incoming_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued', action TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '', failure TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL, processed_at TEXT,
                    UNIQUE(family_id, incoming_id)
                );
                CREATE TABLE IF NOT EXISTS calendar_preferences (
                    family_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1,
                    reminder_method TEXT NOT NULL DEFAULT 'popup',
                    reminder_minutes INTEGER NOT NULL DEFAULT 30,
                    updated_at TEXT NOT NULL
                );
            """)
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS goal_questions (
                    id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES family_tasks(id) ON DELETE CASCADE,
                    assignment_id TEXT NOT NULL REFERENCES goal_assignments(id) ON DELETE CASCADE,
                    question TEXT NOT NULL, context TEXT NOT NULL, action TEXT NOT NULL,
                    state TEXT NOT NULL, answer TEXT NOT NULL, created_at TEXT NOT NULL, answered_at TEXT
                );
                CREATE TABLE IF NOT EXISTS provider_events (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, plugin_id TEXT NOT NULL,
                    correlation TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(family_id,plugin_id,id)
                );
                CREATE TABLE IF NOT EXISTS provider_waits (
                    id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES family_tasks(id) ON DELETE CASCADE,
                    assignment_id TEXT NOT NULL REFERENCES goal_assignments(id) ON DELETE CASCADE,
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, correlation TEXT NOT NULL,
                    state TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS plugin_connections (
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, validated_at TEXT NOT NULL,
                    PRIMARY KEY(family_id,plugin_id)
                );
                CREATE TABLE IF NOT EXISTS simulator_connections (
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, connected_at TEXT NOT NULL,
                    PRIMARY KEY(family_id,plugin_id)
                );
                CREATE TABLE IF NOT EXISTS simulator_messages (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                    direction TEXT NOT NULL CHECK(direction IN ('incoming','outgoing')),
                    body TEXT NOT NULL, provider_event_id TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS simulator_actions (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, plugin_id TEXT NOT NULL,
                    action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_attempts (
                    state TEXT PRIMARY KEY, family_id TEXT NOT NULL, plugin_id TEXT NOT NULL,
                    verifier TEXT NOT NULL, config TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, token TEXT NOT NULL,
                    PRIMARY KEY(family_id,plugin_id)
                );
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    plugin_id TEXT PRIMARY KEY, config TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS apple_health_samples (
                    family_id TEXT NOT NULL, external_id TEXT NOT NULL, child_id TEXT NOT NULL,
                    sample_type TEXT NOT NULL, start_at TEXT NOT NULL, end_at TEXT NOT NULL,
                    value REAL NOT NULL, unit TEXT NOT NULL, source TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY (family_id, external_id)
                );
                CREATE TABLE IF NOT EXISTS browser_sessions (
                    assignment_id TEXT PRIMARY KEY REFERENCES goal_assignments(id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL, expires_at REAL NOT NULL
                );
            """)
            self._migrate_tasks(connection)
            if isinstance(self.database, Path):
                columns = {row[1] for row in connection.execute("PRAGMA table_info(goal_assignments)")}
                if "plugin_ids" not in columns:
                    connection.execute("ALTER TABLE goal_assignments ADD COLUMN plugin_ids TEXT NOT NULL DEFAULT '[]'")
            else:
                connection.execute("ALTER TABLE goal_assignments ADD COLUMN IF NOT EXISTS plugin_ids TEXT NOT NULL DEFAULT '[]'")
        from app.automation_store import AutomationStore
        AutomationStore(self).initialize()

    def calendar_preferences(self, family_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM calendar_preferences WHERE family_id=?", (family_id,)).fetchone()
        if not row:
            return {"enabled": True, "reminder_method": "popup", "reminder_minutes": 30}
        return {
            "enabled": bool(row["enabled"]),
            "reminder_method": row["reminder_method"],
            "reminder_minutes": row["reminder_minutes"],
        }

    def save_calendar_preferences(self, family_id: str, enabled: bool, reminder_method: str, reminder_minutes: int) -> dict[str, object]:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO calendar_preferences VALUES (?,?,?,?,?)
                ON CONFLICT (family_id) DO UPDATE SET enabled=excluded.enabled,
                reminder_method=excluded.reminder_method,reminder_minutes=excluded.reminder_minutes,
                updated_at=excluded.updated_at""",
                (family_id, int(enabled), reminder_method, reminder_minutes, now()),
            )
        return self.calendar_preferences(family_id)

    def _migrate_tasks(self, connection: sqlite3.Connection) -> None:
        if not isinstance(self.database, Path):
            return
        columns = {row[1] for row in connection.execute("PRAGMA table_info(family_tasks)")}
        additions = {
            "run_state": "TEXT NOT NULL DEFAULT 'idle'", "current_step": "TEXT NOT NULL DEFAULT ''",
            "progress": "INTEGER NOT NULL DEFAULT 0", "report": "TEXT NOT NULL DEFAULT ''",
            "skill_ids": "TEXT NOT NULL DEFAULT '[]'", "plugin_ids": "TEXT NOT NULL DEFAULT '[]'",
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE family_tasks ADD COLUMN {name} {definition}")


    def list(self, family_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            with batch(connection):
                rows_cursor = connection.execute("SELECT * FROM family_tasks WHERE family_id=? AND id NOT IN (SELECT run_goal_id FROM automation_run_links) ORDER BY created_at DESC", (family_id,))
                assignments_cursor = connection.execute("""SELECT assignment.* FROM goal_assignments assignment
                JOIN family_tasks goal ON goal.id=assignment.goal_id
                WHERE goal.family_id=? ORDER BY assignment.created_at""", (family_id,))
                questions_cursor = connection.execute("""SELECT question.* FROM goal_questions question
                JOIN family_tasks goal ON goal.id=question.goal_id
                WHERE goal.family_id=? ORDER BY question.created_at""", (family_id,))
                activities_cursor = connection.execute("""SELECT activity.* FROM goal_activities activity
                JOIN family_tasks goal ON goal.id=activity.goal_id
                WHERE goal.family_id=? ORDER BY activity.created_at""", (family_id,))
                skills_cursor = connection.execute("SELECT * FROM family_skills WHERE family_id=?", (family_id,))
            rows = rows_cursor.fetchall()
            assignments = assignments_cursor.fetchall()
            questions = questions_cursor.fetchall()
            activities = activities_cursor.fetchall()
            skills = {skill["id"]: {**dict(skill), "required_plugin_ids": json.loads(skill["required_plugin_ids"])}
                      for skill in skills_cursor}
        assignments_by_goal: dict[str, list[dict[str, object]]] = {}
        from plugins.namespaces import namespaces
        for row in assignments:
            assignment = self._assignment_snapshot(row)
            assignment["skills"] = [skills[identity] for identity in assignment["skill_ids"] if identity in skills]
            assignment["permitted_namespaces"] = namespaces(list(dict.fromkeys(assignment["plugin_ids"] or [
                identity for skill in assignment["skills"] for identity in skill["required_plugin_ids"]
            ])))
            assignments_by_goal.setdefault(str(row["goal_id"]), []).append(assignment)
        questions_by_goal: dict[str, list[dict[str, object]]] = {}
        for row in questions:
            questions_by_goal.setdefault(str(row["goal_id"]), []).append(self._question_snapshot(row))
        activities_by_goal: dict[str, list[dict[str, object]]] = {}
        for row in activities:
            activities_by_goal.setdefault(str(row["goal_id"]), []).append({**dict(row), "evidence": json.loads(row["evidence"])})
        goals = []
        for row in rows:
            goal = dict(row)
            goal["skill_ids"] = json.loads(goal["skill_ids"] or "[]")
            goal["plugin_ids"] = json.loads(goal["plugin_ids"] or "[]")
            goal["assignments"] = assignments_by_goal.get(str(row["id"]), [])
            goal["questions"] = questions_by_goal.get(str(row["id"]), [])
            goal["activities"] = activities_by_goal.get(str(row["id"]), [])
            goals.append(goal)
        return goals

    def receive_incoming(
        self,
        family_id: str,
        source: str,
        provider_event_id: str,
        *,
        correlation: str = "",
        sender: str = "",
        subject: str = "",
        content: str = "",
        payload: object | None = None,
    ) -> tuple[dict[str, object], bool]:
        source = source.strip()
        provider_event_id = provider_event_id.strip()
        correlation = correlation.strip()
        sender = sender.strip()
        subject = subject.strip()
        content = content.strip()
        if not source or not provider_event_id:
            raise ValueError("Incoming information needs a source and provider event ID.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM incoming_items WHERE family_id=? AND source=? AND provider_event_id=?",
                (family_id, source, provider_event_id),
            ).fetchone()
            if existing:
                return self._incoming_snapshot(connection, existing), False
            replay = connection.execute(
                """SELECT * FROM incoming_items
                WHERE family_id=? AND source=? AND correlation=? AND sender=? AND subject=? AND content=? AND created_at>=?
                ORDER BY created_at DESC LIMIT 1""",
                (family_id, source, correlation, sender, subject, content, (datetime.now(UTC) - timedelta(minutes=5)).isoformat()),
            ).fetchone()
            if replay:
                return self._incoming_snapshot(connection, replay), False
            identity = str(uuid4())
            connection.execute(
                """INSERT INTO incoming_items
                (id,family_id,source,provider_event_id,correlation,sender,subject,content,payload,status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,'queued',?)""",
                (identity, family_id, source, provider_event_id, correlation, sender, subject, content, json.dumps(payload or {}, default=str), now()),
            )
            connection.execute(
                "INSERT INTO intake_activities VALUES (?,?,?,?,?,?)",
                (str(uuid4()), identity, "received", f"Received information from {source}.", "{}", now()),
            )
            from app.automation_store import AutomationStore
            child_id = str(payload.get('child_id') or '') if isinstance(payload,dict) else ''
            AutomationStore(self).enqueue_event(family_id,{child_id},'incoming',identity,
                {'incoming_id':identity,'source':source,'content':content},connection)
            row = connection.execute("SELECT * FROM incoming_items WHERE id=?", (identity,)).fetchone()
            return self._incoming_snapshot(connection, row), True

    def incoming(self, incoming_id: str, family_id: str | None = None) -> dict[str, object] | None:
        with self._connect() as connection:
            if family_id:
                row = connection.execute("SELECT * FROM incoming_items WHERE id=? AND family_id=?", (incoming_id, family_id)).fetchone()
            else:
                row = connection.execute("SELECT * FROM incoming_items WHERE id=?", (incoming_id,)).fetchone()
            return self._incoming_snapshot(connection, row) if row else None

    def incoming_items(self, family_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM incoming_items WHERE family_id=? ORDER BY created_at DESC", (family_id,)).fetchall()
            return [self._incoming_snapshot(connection, row) for row in rows]

    def delete_incoming(self, family_id: str, incoming_id: str) -> bool:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM security_reviews WHERE incoming_id=? AND family_id=?", (incoming_id, family_id))
            connection.execute("DELETE FROM education_reviews WHERE incoming_id=? AND family_id=?", (incoming_id, family_id))
            result = connection.execute("DELETE FROM incoming_items WHERE id=? AND family_id=?", (incoming_id, family_id))
            return result.rowcount > 0

    def set_incoming(self, incoming_id: str, **changes: object) -> None:
        allowed = {"status", "action", "reason", "child_id", "goal_id", "attention_required", "failure", "processed_at"}
        values = {key: value for key, value in changes.items() if key in allowed}
        if not values:
            return
        clause = ", ".join(f"{key}=?" for key in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE incoming_items SET {clause} WHERE id=?", (*values.values(), incoming_id))

    def add_intake_activity(self, incoming_id: str, kind: str, summary: str, detail: object | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO intake_activities VALUES (?,?,?,?,?,?)",
                (str(uuid4()), incoming_id, kind, summary.strip(), json.dumps(detail or {}, default=str), now()),
            )

    def intake_memory(self, family_id: str) -> dict[str, str]:
        with self._connect() as connection:
            return {
                str(row["scope_id"]): str(row["summary"])
                for row in connection.execute(
                    "SELECT scope_id,summary FROM family_intake_memory WHERE family_id=? ORDER BY scope_id",
                    (family_id,),
                )
            }

    def update_intake_memory(self, family_id: str, scope_id: str, summary: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO family_intake_memory VALUES (?,?,?,?)
                ON CONFLICT (family_id,scope_id) DO UPDATE SET summary=excluded.summary,updated_at=excluded.updated_at""",
                (family_id, scope_id, summary, now()),
            )

    def security_settings(self, family_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM security_settings WHERE family_id=?", (family_id,)).fetchone()
            policy = connection.execute("SELECT policy FROM security_policy WHERE family_id=?", (family_id,)).fetchone()
            item = dict(row) if row else {"family_id": family_id, "enabled": True, "alert_level": "important", "instructions": "", "updated_at": ""}
            item["enabled"] = bool(item["enabled"])
            return {**item, "sources": [], "child_ids": [], "depth": "item", "review_mode": "incoming", "channel": "in_app", **(json.loads(policy[0]) if policy else {})}

    def update_security_settings(self, family_id: str, enabled: bool, alert_level: str, instructions: str, **policy) -> dict[str, object]:
        if alert_level not in {"urgent", "important", "all"}:
            raise ValueError("Choose a valid security alert level.")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO security_settings VALUES (?,?,?,?,?)
                ON CONFLICT (family_id) DO UPDATE SET enabled=excluded.enabled,alert_level=excluded.alert_level,
                instructions=excluded.instructions,updated_at=excluded.updated_at""",
                (family_id, int(enabled), alert_level, instructions.strip(), now()),
            )
            if policy:
                connection.execute("INSERT INTO security_policy VALUES (?,?) ON CONFLICT(family_id) DO UPDATE SET policy=excluded.policy", (family_id,json.dumps(policy)))
        return self.security_settings(family_id)

    def security_scope_matches(self, settings, incoming):
        if settings['sources'] and incoming['source'] not in settings['sources']:
            return False
        payload = incoming.get('payload') or {}
        child_id = (payload.get('child_id') if isinstance(payload,dict) else None) or incoming.get('child_id')
        return not settings['child_ids'] or child_id in settings['child_ids']

    def security_context_slice(self, family_id, settings):
        if settings['depth'] == 'item':
            return []
        with self._connect() as db:
            rows = db.execute('SELECT * FROM incoming_items WHERE family_id=? ORDER BY created_at DESC LIMIT 50', (family_id,)).fetchall()
        return [{key:dict(row)[key] for key in ('id','source','subject','content','created_at')} for row in rows
                if self.security_scope_matches(settings,{**dict(row),'payload':json.loads(row['payload'])})][:10]

    def receive_security_review(self, family_id: str, incoming_id: str) -> tuple[dict[str, object], bool]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM security_reviews WHERE family_id=? AND incoming_id=?",
                (family_id, incoming_id),
            ).fetchone()
            if existing:
                return self._security_snapshot(connection, existing), False
            identity = str(uuid4())
            connection.execute(
                """INSERT INTO security_reviews
                (id,family_id,incoming_id,status,created_at) VALUES (?,?,?,'queued',?)""",
                (identity, family_id, incoming_id, now()),
            )
            connection.execute(
                "INSERT INTO security_activities VALUES (?,?,?,?,?,?)",
                (str(uuid4()), identity, "received", "Safety Agent received the item.", "{}", now()),
            )
            row = connection.execute("SELECT * FROM security_reviews WHERE id=?", (identity,)).fetchone()
            return self._security_snapshot(connection, row), True

    def security_review(self, review_id: str, family_id: str | None = None) -> dict[str, object] | None:
        with self._connect() as connection:
            if family_id:
                row = connection.execute("SELECT * FROM security_reviews WHERE id=? AND family_id=?", (review_id, family_id)).fetchone()
            else:
                row = connection.execute("SELECT * FROM security_reviews WHERE id=?", (review_id,)).fetchone()
            return self._security_snapshot(connection, row) if row else None

    def security_reviews(self, family_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM security_reviews WHERE family_id=?
                AND (action='alert' OR status IN ('queued','processing','failed'))
                ORDER BY created_at DESC""",
                (family_id,),
            ).fetchall()
            return [self._security_snapshot(connection, row) for row in rows]

    def security_alert_count(self, family_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT count(*) AS total FROM security_reviews
                WHERE family_id=? AND status='completed' AND action='alert' AND dismissed=0""",
                (family_id,),
            ).fetchone()
        return int(row["total"])

    def set_security_review(self, review_id: str, **changes: object) -> None:
        allowed = {"status", "action", "severity", "category", "summary", "reason", "child_id", "dismissed", "failure", "processed_at"}
        values = {key: value for key, value in changes.items() if key in allowed}
        if not values:
            return
        clause = ", ".join(f"{key}=?" for key in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE security_reviews SET {clause} WHERE id=?", (*values.values(), review_id))

    def add_security_activity(self, review_id: str, kind: str, summary: str, detail: object | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO security_activities VALUES (?,?,?,?,?,?)",
                (str(uuid4()), review_id, kind, summary.strip(), json.dumps(detail or {}, default=str), now()),
            )

    def dismiss_security_alert(self, family_id: str, review_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                "UPDATE security_reviews SET dismissed=1 WHERE id=? AND family_id=? AND action='alert'",
                (review_id, family_id),
            )
            return result.rowcount > 0

    def education_snapshot(self, family_id: str, child_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM family_education_snapshots WHERE family_id=? AND child_id=?",
                (family_id, child_id),
            ).fetchone()
            return self._education_snapshot(row) if row else None

    def education_snapshots(self, family_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM family_education_snapshots WHERE family_id=? ORDER BY updated_at DESC",
                (family_id,),
            ).fetchall()
            return [self._education_snapshot(row) for row in rows]

    def delete_education_snapshot(self, family_id: str, child_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM family_education_snapshots WHERE family_id=? AND child_id=?",
                (family_id, child_id),
            )

    def update_education_snapshot(self, family_id: str, child_id: str, summary: str, source_id: str) -> dict[str, object]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM family_education_snapshots WHERE family_id=? AND child_id=?",
                (family_id, child_id),
            ).fetchone()
            sources = json.loads(existing["source_ids"] or "[]") if existing else []
            if source_id not in sources:
                sources.append(source_id)
            connection.execute(
                """INSERT INTO family_education_snapshots VALUES (?,?,?,?,?)
                ON CONFLICT (family_id,child_id) DO UPDATE SET
                summary=excluded.summary,source_ids=excluded.source_ids,updated_at=excluded.updated_at""",
                (family_id, child_id, summary.strip(), json.dumps(sources), now()),
            )
            row = connection.execute(
                "SELECT * FROM family_education_snapshots WHERE family_id=? AND child_id=?",
                (family_id, child_id),
            ).fetchone()
            return self._education_snapshot(row)

    def receive_education_review(self, family_id: str, incoming_id: str) -> tuple[dict[str, object], bool]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM education_reviews WHERE family_id=? AND incoming_id=?",
                (family_id, incoming_id),
            ).fetchone()
            if existing:
                return self._education_review_snapshot(connection, existing), False
            identity = str(uuid4())
            connection.execute(
                "INSERT INTO education_reviews (id,family_id,incoming_id,status,created_at) VALUES (?,?,?,'queued',?)",
                (identity, family_id, incoming_id, now()),
            )
            row = connection.execute("SELECT * FROM education_reviews WHERE id=?", (identity,)).fetchone()
            return self._education_review_snapshot(connection, row), True

    def education_review(self, review_id: str, family_id: str | None = None) -> dict[str, object] | None:
        with self._connect() as connection:
            if family_id:
                row = connection.execute(
                    "SELECT * FROM education_reviews WHERE id=? AND family_id=?",
                    (review_id, family_id),
                ).fetchone()
            else:
                row = connection.execute("SELECT * FROM education_reviews WHERE id=?", (review_id,)).fetchone()
            return self._education_review_snapshot(connection, row) if row else None

    def set_education_review(self, review_id: str, **changes: object) -> None:
        allowed = {"status", "action", "reason", "failure", "processed_at"}
        values = {key: value for key, value in changes.items() if key in allowed}
        if not values:
            return
        clause = ", ".join(f"{key}=?" for key in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE education_reviews SET {clause} WHERE id=?", (*values.values(), review_id))

    def get(self, family_id: str, goal_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM family_tasks WHERE id=? AND family_id=?", (goal_id, family_id)).fetchone()
            return self._goal_snapshot(connection, row) if row else None

    def create(self, family_id: str, child_id: str, text: str) -> dict[str, object]:
        timestamp = now()
        goal = {"id": str(uuid4()), "family_id": family_id, "child_id": child_id, "text": text,
                "status": "active", "created_at": timestamp, "updated_at": timestamp,
                "run_state": "queued", "current_step": "Preparing the work", "progress": 0,
                "report": "", "skill_ids": "[]", "plugin_ids": "[]"}
        with self._connect() as connection:
            connection.execute("""INSERT INTO family_tasks
                (id,family_id,child_id,text,status,created_at,updated_at,run_state,current_step,progress,report,skill_ids,plugin_ids)
                VALUES (:id,:family_id,:child_id,:text,:status,:created_at,:updated_at,:run_state,:current_step,:progress,:report,:skill_ids,:plugin_ids)""", goal)
        return {**goal, "skill_ids": [], "plugin_ids": [], "assignments": [], "questions": [], "activities": []}

    def update(self, task_id: str, status: str) -> dict[str, object] | None:
        run_state = "completed" if status == "completed" else "paused" if status == "paused" else "queued"
        with self._connect() as connection:
            connection.execute("UPDATE family_tasks SET status=?,run_state=?,progress=CASE WHEN ?='completed' THEN 100 ELSE progress END,updated_at=? WHERE id=?", (status, run_state, status, now(), task_id))
            row = connection.execute("SELECT * FROM family_tasks WHERE id=?", (task_id,)).fetchone()
            return self._goal_snapshot(connection, row) if row else None

    def set_goal_state(self, goal_id: str, **changes: object) -> None:
        if not changes:
            return
        values = {key: json.dumps(value) if key in {"skill_ids", "plugin_ids"} else value for key, value in changes.items() if value is not None}
        values["updated_at"] = now()
        clause = ", ".join(f"{key}=?" for key in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE family_tasks SET {clause} WHERE id=?", (*values.values(), goal_id))

    def create_assignment(self, goal_id: str, payload: dict[str, object]) -> str:
        assignment_id = str(uuid4())
        record = {"id": assignment_id, "goal_id": goal_id, "title": str(payload["title"]), "instruction": str(payload["instruction"]),
                  "status": "queued", "phase": "queued", "current_step": str(payload["title"]), "next_step": "", "progress": 0,
                  "depends_on": json.dumps(payload.get("depends_on", [])), "required_inputs": json.dumps(payload.get("required_inputs", [])),
                  "expected_outputs": json.dumps(payload.get("expected_outputs", [])), "skill_ids": json.dumps(payload.get("skill_ids", [])),
                  "plugin_ids": json.dumps(payload.get("plugin_ids", [])),
                  "report": "", "evidence": "[]", "created_at": now(), "started_at": None, "finished_at": None}
        with self._connect() as connection:
            connection.execute("""INSERT INTO goal_assignments
                (id,goal_id,title,instruction,status,phase,current_step,next_step,progress,depends_on,required_inputs,expected_outputs,skill_ids,plugin_ids,report,evidence,created_at,started_at,finished_at)
                VALUES (:id,:goal_id,:title,:instruction,:status,:phase,:current_step,:next_step,:progress,:depends_on,:required_inputs,:expected_outputs,:skill_ids,:plugin_ids,:report,:evidence,:created_at,:started_at,:finished_at)""", record)
        return assignment_id

    def assignments(self, goal_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM goal_assignments WHERE goal_id=? ORDER BY created_at", (goal_id,)).fetchall()
            return [self._assignment_snapshot(row) for row in rows]

    def assignment(self, assignment_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM goal_assignments WHERE id=?", (assignment_id,)).fetchone()
            return self._assignment_snapshot(row) if row else None

    def set_assignment(self, assignment_id: str, **changes: object) -> None:
        values = {key: json.dumps(value) if key in {"evidence", "skill_ids", "plugin_ids", "depends_on", "required_inputs", "expected_outputs"} and not isinstance(value, str) else value for key, value in changes.items()}
        if not values:
            return
        clause = ", ".join(f"{key}=?" for key in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE goal_assignments SET {clause} WHERE id=?", (*values.values(), assignment_id))

    def add_activity(self, goal_id: str, kind: str, summary: str, evidence: object | None = None) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO goal_activities VALUES (?,?,?,?,?,?)", (str(uuid4()), goal_id, kind, summary, json.dumps(evidence or {}), now()))

    def delete(self, task_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute("DELETE FROM family_tasks WHERE id=?", (task_id,))
            return result.rowcount > 0

    def install_plugin(self, family_id: str, plugin_id: str) -> dict[str, bool]:
        with self._connect() as connection:
            with batch(connection):
                connection.execute("INSERT INTO plugin_installations VALUES (?,?,?) ON CONFLICT DO NOTHING", (family_id, plugin_id, now()))
                permissions = connection.execute(
                    "SELECT permission_id,enabled FROM plugin_permissions WHERE family_id=? AND plugin_id=?",
                    (family_id, plugin_id),
                )
            return {row[0]: bool(row[1]) for row in permissions}

    def uninstall_plugin(self, family_id: str, plugin_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM plugin_installations WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))
            if table_exists(connection, "oauth_tokens"):
                connection.execute("DELETE FROM oauth_tokens WHERE family_id=? AND plugin_id=?",(family_id,plugin_id))
                connection.execute("DELETE FROM oauth_attempts WHERE family_id=? AND plugin_id=?",(family_id,plugin_id))
            connection.execute("DELETE FROM plugin_connections WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))
            connection.execute("DELETE FROM simulator_connections WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))
            connection.execute("DELETE FROM plugin_permissions WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))
            connection.execute("DELETE FROM profile_plugin_access WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))

    def installed_plugins(self, family_id: str) -> set[str]:
        with self._connect() as connection:
            return {row[0] for row in connection.execute("SELECT plugin_id FROM plugin_installations WHERE family_id=?", (family_id,))}

    def set_permission(self, family_id: str, plugin_id: str, permission_id: str, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO plugin_permissions VALUES (?,?,?,?) ON CONFLICT (family_id,plugin_id,permission_id) DO UPDATE SET enabled=excluded.enabled", (family_id, plugin_id, permission_id, int(enabled)))

    def permissions(self, family_id: str, plugin_id: str) -> dict[str, bool]:
        with self._connect() as connection:
            return {row[0]: bool(row[1]) for row in connection.execute("SELECT permission_id,enabled FROM plugin_permissions WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))}

    def profile_plugin_access(self, family_id: str) -> tuple[list[str], dict[tuple[str, str], bool]]:
        with self._connect() as connection:
            with batch(connection):
                plugins_cursor = connection.execute(
                    """SELECT installation.plugin_id FROM plugin_installations installation
                    WHERE installation.family_id=? AND (
                        EXISTS (SELECT 1 FROM plugin_connections connection WHERE connection.family_id=installation.family_id AND connection.plugin_id=installation.plugin_id)
                        OR EXISTS (SELECT 1 FROM simulator_connections simulation WHERE simulation.family_id=installation.family_id AND simulation.plugin_id=installation.plugin_id)
                    ) ORDER BY installation.installed_at""",
                    (family_id,),
                )
                access_cursor = connection.execute(
                    "SELECT profile_id,plugin_id,enabled FROM profile_plugin_access WHERE family_id=?",
                    (family_id,),
                )
            plugin_ids = [row[0] for row in plugins_cursor]
            access = {(row[0],row[1]): bool(row[2]) for row in access_cursor}
        return plugin_ids, access

    def set_profile_plugin_access(self, family_id: str, profile_id: str, plugin_id: str, enabled: bool) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                """INSERT INTO profile_plugin_access(family_id,profile_id,plugin_id,enabled)
                SELECT ?,?,?,? WHERE EXISTS (
                    SELECT 1 FROM plugin_installations installation WHERE installation.family_id=? AND installation.plugin_id=? AND (
                        EXISTS (SELECT 1 FROM plugin_connections connection WHERE connection.family_id=installation.family_id AND connection.plugin_id=installation.plugin_id)
                        OR EXISTS (SELECT 1 FROM simulator_connections simulation WHERE simulation.family_id=installation.family_id AND simulation.plugin_id=installation.plugin_id)
                    )
                )
                ON CONFLICT (family_id,profile_id,plugin_id) DO UPDATE SET enabled=excluded.enabled""",
                (family_id,profile_id,plugin_id,int(enabled),family_id,plugin_id),
            )
            return result.rowcount > 0

    def remove_profile_plugin_access(self, family_id: str, profile_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM profile_plugin_access WHERE family_id=? AND profile_id=?", (family_id,profile_id))

    def runtime_plugin_access(self, family_id: str, plugin_id: str, profile_id: str = "") -> dict[str, object]:
        with self._connect() as connection:
            with batch(connection):
                installed_cursor = connection.execute(
                    "SELECT 1 AS installed FROM plugin_installations WHERE family_id=? AND plugin_id=?",
                    (family_id,plugin_id),
                )
                simulated_cursor = connection.execute(
                    "SELECT 1 AS simulated FROM simulator_connections WHERE family_id=? AND plugin_id=?",
                    (family_id,plugin_id),
                )
                permissions_cursor = connection.execute(
                    "SELECT permission_id,enabled FROM plugin_permissions WHERE family_id=? AND plugin_id=?",
                    (family_id,plugin_id),
                )
                access_profile = 'parent' if profile_id == 'all' else profile_id
                profile_cursor = connection.execute(
                    "SELECT enabled FROM profile_plugin_access WHERE family_id=? AND profile_id=? AND plugin_id=?",
                    (family_id,access_profile,plugin_id),
                ) if profile_id else None
            profile = profile_cursor.fetchone() if profile_cursor else None
            return {
                "installed": installed_cursor.fetchone() is not None,
                "simulated": simulated_cursor.fetchone() is not None,
                "enabled": bool(profile[0]) if profile else True,
                "permissions": {row[0]: bool(row[1]) for row in permissions_cursor},
            }

    def simulator_plugins(self, family_id: str) -> set[str]:
        with self._connect() as connection:
            return {row[0] for row in connection.execute("SELECT plugin_id FROM simulator_connections WHERE family_id=?", (family_id,))}

    def remove_simulator_profile(self, family_id: str, profile_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM simulator_messages WHERE family_id=? AND profile_id=?", (family_id, profile_id))
            if table_exists(connection, "apple_health_samples"):
                connection.execute("DELETE FROM apple_health_samples WHERE family_id=? AND child_id=? AND source='mom.life Simulator'", (family_id, profile_id))

    def set_simulator_plugin(self, family_id: str, plugin_id: str, connected: bool) -> None:
        with self._connect() as connection:
            if connected:
                connection.execute(
                    "INSERT INTO simulator_connections VALUES (?,?,?) ON CONFLICT (family_id,plugin_id) DO UPDATE SET connected_at=excluded.connected_at",
                    (family_id, plugin_id, now()),
                )
            else:
                connection.execute("DELETE FROM simulator_connections WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))

    def add_simulator_message(self, family_id: str, profile_id: str, direction: str, body: str, provider_event_id: str) -> dict[str, object]:
        identity = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO simulator_messages VALUES (?,?,?,?,?,?,?)",
                (identity, family_id, profile_id, direction, body, provider_event_id, now()),
            )
            row = connection.execute("SELECT * FROM simulator_messages WHERE id=?", (identity,)).fetchone()
        return dict(row)

    def receive_simulator_incoming(self, family_id: str, profile_id: str, sender: str, body: str, event_id: str, payload: object) -> dict[str, object]:
        """Persist one simulated provider event, message, and its review jobs atomically."""
        timestamp = now()
        message_id = str(uuid4())
        message = {"id": message_id, "family_id": family_id, "profile_id": profile_id, "direction": "incoming", "body": body, "provider_event_id": event_id, "created_at": timestamp}
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connected = connection.execute(
                "SELECT 1 AS connected FROM simulator_connections WHERE family_id=? AND plugin_id='whatsapp'", (family_id,),
            ).fetchone()
            if not connected:
                raise ValueError("Connect WhatsApp Simulator first.")
            if connection.execute("SELECT id FROM provider_events WHERE id=?", (event_id,)).fetchone():
                return {"created": False, "duplicate": True, "matched": False, "goal_ids": []}
            correlation = f"sim:{profile_id}"
            connection.execute("INSERT INTO provider_events VALUES (?,?,?,?,?,?)",
                (event_id, family_id, "whatsapp", correlation, json.dumps(payload, default=str), timestamp))
            from app.automation_store import AutomationStore
            AutomationStore(self).enqueue_event(family_id,{profile_id},'incoming',event_id,payload,connection)
            waits = connection.execute(
                """SELECT wait.*,goal.status AS goal_status FROM provider_waits wait
                JOIN family_tasks goal ON goal.id=wait.goal_id
                JOIN goal_assignments assignment ON assignment.id=wait.assignment_id
                WHERE wait.family_id=? AND wait.plugin_id='whatsapp' AND wait.correlation=?
                AND wait.state='waiting' AND goal.status IN ('active','paused')
                AND assignment.status IN ('running','blocked')""", (family_id, correlation),
            ).fetchall()
            goal_ids = []
            for wait in waits:
                connection.execute("UPDATE provider_waits SET state='received' WHERE id=?", (wait["id"],))
                connection.execute("UPDATE goal_assignments SET status='queued',phase='queued' WHERE id=? AND status='blocked'", (wait["assignment_id"],))
                if wait["goal_status"] == "active":
                    connection.execute("UPDATE family_tasks SET run_state='queued' WHERE id=?", (wait["goal_id"],))
                    goal_ids.append(wait["goal_id"])
                connection.execute("INSERT INTO goal_activities VALUES (?,?,?,?,?,?)", (
                    str(uuid4()), wait["goal_id"], "provider_event", "Received the awaited provider event",
                    json.dumps({"plugin_id": "whatsapp", "event_id": event_id, "payload": payload}, default=str), timestamp,
                ))
            connection.execute("INSERT INTO simulator_messages VALUES (?,?,?,?,?,?,?)",
                (message_id, family_id, profile_id, "incoming", body, event_id, timestamp))
            if waits:
                return {"created": False, "duplicate": False, "matched": True, "goal_ids": list(dict.fromkeys(goal_ids)), "message": message}
            replay = connection.execute(
                """SELECT id FROM incoming_items
                WHERE family_id=? AND source='whatsapp' AND correlation=? AND sender=? AND subject='' AND content=? AND created_at>=?
                ORDER BY created_at DESC LIMIT 1""",
                (family_id, f"sim:{profile_id}", sender, body, (datetime.now(UTC) - timedelta(minutes=5)).isoformat()),
            ).fetchone()
            if replay:
                return {"created": False, "duplicate": False, "matched": False, "goal_ids": [], "incoming_id": replay["id"], "message": message}
            incoming_id = str(uuid4())
            connection.execute(
                """INSERT INTO incoming_items
                (id,family_id,source,provider_event_id,correlation,sender,subject,content,payload,status,created_at)
                VALUES (?,?, 'whatsapp', ?,?,?, '',?,?,'queued',?)""",
                (incoming_id, family_id, event_id, f"sim:{profile_id}", sender, body, json.dumps(payload, default=str), timestamp),
            )
            connection.execute("INSERT INTO intake_activities VALUES (?,?,?,?,?,?)",
                (str(uuid4()), incoming_id, "received", "Received information from whatsapp.", "{}", timestamp))
            security_id = str(uuid4())
            connection.execute("INSERT INTO security_reviews (id,family_id,incoming_id,status,created_at) VALUES (?,?,?,'queued',?)",
                (security_id, family_id, incoming_id, timestamp))
            connection.execute("INSERT INTO security_activities VALUES (?,?,?,?,?,?)",
                (str(uuid4()), security_id, "received", "Safety Agent received the item.", "{}", timestamp))
            education_id = str(uuid4())
            connection.execute("INSERT INTO education_reviews (id,family_id,incoming_id,status,created_at) VALUES (?,?,?,'queued',?)",
                (education_id, family_id, incoming_id, timestamp))
            return {"created": True, "duplicate": False, "matched": False, "goal_ids": [], "message": message,
                "incoming_id": incoming_id, "security_id": security_id, "education_id": education_id}

    def simulator_messages(self, family_id: str, limit: int = 80) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM simulator_messages WHERE family_id=? ORDER BY created_at DESC LIMIT ?",
                (family_id, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def add_simulator_action(self, family_id: str, plugin_id: str, action: str, detail: object) -> dict[str, object]:
        identity = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO simulator_actions VALUES (?,?,?,?,?,?)",
                (identity, family_id, plugin_id, action, json.dumps(detail, default=str), now()),
            )
        return {"id": identity, "plugin_id": plugin_id, "action": action, "detail": detail}

    def seed_skills(self, family_id: str, skills: tuple[dict[str, object], ...]) -> None:
        with self._connect() as connection:
            for skill in skills:
                connection.execute("""INSERT INTO family_skills
                    (id,family_id,slug,name,description,instructions,required_plugin_ids,source,version,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT (family_id,slug) DO UPDATE SET
                    name=excluded.name,description=excluded.description,instructions=excluded.instructions,
                    required_plugin_ids=excluded.required_plugin_ids,version=excluded.version
                    WHERE family_skills.source='builtin'""", (str(uuid4()), family_id, skill["slug"], skill["name"], skill["description"],
                    skill["instructions"], json.dumps(skill["required_plugin_ids"]), "builtin", 1, now()))

    def skills(self, family_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM family_skills WHERE family_id=? ORDER BY name", (family_id,)).fetchall()
            return [{**dict(row), "required_plugin_ids": json.loads(row["required_plugin_ids"])} for row in rows]

    def _goal_snapshot(self, connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, object]:
        goal = dict(row)
        goal["skill_ids"] = json.loads(goal["skill_ids"] or "[]")
        goal["plugin_ids"] = json.loads(goal["plugin_ids"] or "[]")
        with batch(connection):
            assignments_cursor = connection.execute("SELECT * FROM goal_assignments WHERE goal_id=? ORDER BY created_at", (row["id"],))
            skills_cursor = connection.execute("SELECT * FROM family_skills WHERE family_id=?", (row["family_id"],))
            questions_cursor = connection.execute("SELECT * FROM goal_questions WHERE goal_id=? ORDER BY created_at", (row["id"],))
            activities_cursor = connection.execute("SELECT * FROM goal_activities WHERE goal_id=? ORDER BY created_at", (row["id"],))
        assignments = assignments_cursor.fetchall()
        goal["assignments"] = [self._assignment_snapshot(item) for item in assignments]
        skills = {skill["id"]: {**dict(skill), "required_plugin_ids": json.loads(skill["required_plugin_ids"])} for skill in skills_cursor}
        from plugins.namespaces import namespaces
        for assignment in goal["assignments"]:
            assignment["skills"] = [skills[identity] for identity in assignment["skill_ids"] if identity in skills]
            assignment["permitted_namespaces"] = namespaces(list(dict.fromkeys(assignment["plugin_ids"] or [
                identity for skill in assignment["skills"] for identity in skill["required_plugin_ids"]
            ])))
        goal["questions"] = [self._question_snapshot(question) for question in questions_cursor]
        goal["activities"] = [{**dict(item), "evidence": json.loads(item["evidence"])} for item in activities_cursor]
        return goal

    @staticmethod
    def _question_snapshot(row) -> dict[str, object]:
        question = dict(row)
        question.pop("action", None)
        return question

    @staticmethod
    def _incoming_snapshot(connection, row) -> dict[str, object]:
        item = dict(row)
        item["payload"] = json.loads(item["payload"] or "{}")
        item["attention_required"] = bool(item["attention_required"])
        item["activities"] = [
            {**dict(activity), "detail": json.loads(activity["detail"] or "{}")}
            for activity in connection.execute(
                "SELECT * FROM intake_activities WHERE incoming_id=? ORDER BY created_at",
                (item["id"],),
            )
        ]
        return item

    @staticmethod
    def _security_snapshot(connection, row) -> dict[str, object]:
        item = dict(row)
        item["dismissed"] = bool(item["dismissed"])
        incoming = connection.execute("SELECT * FROM incoming_items WHERE id=?", (item["incoming_id"],)).fetchone()
        item["incoming"] = TaskStore._incoming_snapshot(connection, incoming) if incoming else None
        item["activities"] = [
            {**dict(activity), "detail": json.loads(activity["detail"] or "{}")}
            for activity in connection.execute(
                "SELECT * FROM security_activities WHERE review_id=? ORDER BY created_at",
                (item["id"],),
            )
        ]
        return item

    @staticmethod
    def _education_snapshot(row) -> dict[str, object]:
        item = dict(row)
        item["source_ids"] = json.loads(item["source_ids"] or "[]")
        return item

    @staticmethod
    def _education_review_snapshot(connection, row) -> dict[str, object]:
        item = dict(row)
        incoming = connection.execute("SELECT * FROM incoming_items WHERE id=?", (item["incoming_id"],)).fetchone()
        item["incoming"] = TaskStore._incoming_snapshot(connection, incoming) if incoming else None
        return item

    @staticmethod
    def _assignment_snapshot(row: sqlite3.Row) -> dict[str, object]:
        item = dict(row)
        for field in ("depends_on", "required_inputs", "expected_outputs", "skill_ids", "plugin_ids", "evidence"):
            item[field] = json.loads(item[field] or "[]")
        return item

    def _connect(self):
        return connect(self.database)
