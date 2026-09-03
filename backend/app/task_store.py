import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


class TaskStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS family_tasks (id TEXT PRIMARY KEY, family_id TEXT NOT NULL, child_id TEXT NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")

    def list(self, family_id: str) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM family_tasks WHERE family_id = ? ORDER BY created_at DESC", (family_id,)).fetchall()
        return [dict(row) for row in rows]

    def create(self, family_id: str, child_id: str, text: str) -> dict[str, str]:
        now = datetime.now(UTC).isoformat()
        task = {"id": str(uuid4()), "family_id": family_id, "child_id": child_id, "text": text, "status": "active", "created_at": now, "updated_at": now}
        with self._connect() as connection:
            connection.execute("INSERT INTO family_tasks VALUES (:id, :family_id, :child_id, :text, :status, :created_at, :updated_at)", task)
        return task

    def update(self, task_id: str, status: str) -> dict[str, str] | None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("UPDATE family_tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now, task_id))
            row = connection.execute("SELECT * FROM family_tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def delete(self, task_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute("DELETE FROM family_tasks WHERE id = ?", (task_id,))
        return result.rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection
