import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def now() -> str:
    return datetime.now(UTC).isoformat()


from app.goal_ledger import GoalLedger


class TaskStore(GoalLedger):
    """Durable family goals, assignment boards, skills, plugins, and evidence."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS family_skills (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, slug TEXT NOT NULL,
                    name TEXT NOT NULL, description TEXT NOT NULL, instructions TEXT NOT NULL,
                    required_plugin_ids TEXT NOT NULL DEFAULT '[]', source TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
                    UNIQUE(family_id, slug)
                );
            """)
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS family_context (family_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS goal_questions (
                    id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES family_tasks(id) ON DELETE CASCADE,
                    assignment_id TEXT NOT NULL REFERENCES goal_assignments(id) ON DELETE CASCADE,
                    question TEXT NOT NULL, context TEXT NOT NULL, action TEXT NOT NULL,
                    state TEXT NOT NULL, answer TEXT NOT NULL, created_at TEXT NOT NULL, answered_at TEXT
                );
                CREATE TABLE IF NOT EXISTS plugin_connections (
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, validated_at TEXT NOT NULL,
                    PRIMARY KEY(family_id,plugin_id)
                );
            """)
            self._migrate_tasks(connection)

    def _migrate_tasks(self, connection: sqlite3.Connection) -> None:
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
            rows = connection.execute("SELECT * FROM family_tasks WHERE family_id=? ORDER BY created_at DESC", (family_id,)).fetchall()
            return [self._goal_snapshot(connection, row) for row in rows]

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
            row = connection.execute("SELECT * FROM family_tasks WHERE id=?", (goal["id"],)).fetchone()
            return self._goal_snapshot(connection, row)

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
                  "report": "", "evidence": "[]", "created_at": now(), "started_at": None, "finished_at": None}
        with self._connect() as connection:
            connection.execute("""INSERT INTO goal_assignments
                (id,goal_id,title,instruction,status,phase,current_step,next_step,progress,depends_on,required_inputs,expected_outputs,skill_ids,report,evidence,created_at,started_at,finished_at)
                VALUES (:id,:goal_id,:title,:instruction,:status,:phase,:current_step,:next_step,:progress,:depends_on,:required_inputs,:expected_outputs,:skill_ids,:report,:evidence,:created_at,:started_at,:finished_at)""", record)
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
        values = {key: json.dumps(value) if key in {"evidence", "skill_ids", "depends_on", "required_inputs", "expected_outputs"} and not isinstance(value, str) else value for key, value in changes.items()}
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

    def install_plugin(self, family_id: str, plugin_id: str) -> None:
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO plugin_installations VALUES (?,?,?)", (family_id, plugin_id, now()))

    def uninstall_plugin(self, family_id: str, plugin_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM plugin_installations WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))
            if connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oauth_tokens'").fetchone():
                connection.execute("DELETE FROM oauth_tokens WHERE family_id=? AND plugin_id=?",(family_id,plugin_id))
                connection.execute("DELETE FROM oauth_attempts WHERE family_id=? AND plugin_id=?",(family_id,plugin_id))
            connection.execute("DELETE FROM plugin_connections WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))
            connection.execute("DELETE FROM plugin_permissions WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))

    def installed_plugins(self, family_id: str) -> set[str]:
        with self._connect() as connection:
            return {row[0] for row in connection.execute("SELECT plugin_id FROM plugin_installations WHERE family_id=?", (family_id,))}

    def set_permission(self, family_id: str, plugin_id: str, permission_id: str, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO plugin_permissions VALUES (?,?,?,?)", (family_id, plugin_id, permission_id, int(enabled)))

    def permissions(self, family_id: str, plugin_id: str) -> dict[str, bool]:
        with self._connect() as connection:
            return {row[0]: bool(row[1]) for row in connection.execute("SELECT permission_id,enabled FROM plugin_permissions WHERE family_id=? AND plugin_id=?", (family_id, plugin_id))}

    def seed_skills(self, family_id: str, skills: tuple[dict[str, object], ...]) -> None:
        with self._connect() as connection:
            for skill in skills:
                connection.execute("""INSERT OR IGNORE INTO family_skills
                    (id,family_id,slug,name,description,instructions,required_plugin_ids,source,version,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""", (str(uuid4()), family_id, skill["slug"], skill["name"], skill["description"],
                    skill["instructions"], json.dumps(skill["required_plugin_ids"]), "builtin", 1, now()))

    def skills(self, family_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM family_skills WHERE family_id=? ORDER BY name", (family_id,)).fetchall()
            return [{**dict(row), "required_plugin_ids": json.loads(row["required_plugin_ids"])} for row in rows]

    def _goal_snapshot(self, connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, object]:
        goal = dict(row)
        goal["skill_ids"] = json.loads(goal["skill_ids"] or "[]")
        goal["plugin_ids"] = json.loads(goal["plugin_ids"] or "[]")
        assignments = connection.execute("SELECT * FROM goal_assignments WHERE goal_id=? ORDER BY created_at", (row["id"],)).fetchall()
        goal["assignments"] = [self._assignment_snapshot(item) for item in assignments]
        goal["questions"] = self.questions(str(row["id"]))
        goal["activities"] = [{**dict(item), "evidence": json.loads(item["evidence"])} for item in connection.execute("SELECT * FROM goal_activities WHERE goal_id=? ORDER BY created_at", (row["id"],))]
        return goal

    @staticmethod
    def _assignment_snapshot(row: sqlite3.Row) -> dict[str, object]:
        item = dict(row)
        for field in ("depends_on", "required_inputs", "expected_outputs", "skill_ids", "evidence"):
            item[field] = json.loads(item[field] or "[]")
        return item

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
