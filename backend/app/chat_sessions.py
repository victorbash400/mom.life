"""Family-scoped chat index with Strands session-backed message history."""
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from strands.session.file_session_manager import FileSessionManager

from app.database import connect


AGENT_ID = "mom-life"
SESSION_DIRECTORY = Path(__file__).resolve().parents[1] / ".sessions"


class ChatSessions:
    def __init__(self, root: Path = SESSION_DIRECTORY, *, database: str = "", memory_id: str = "", region: str = "us-east-1"):
        self.root = root
        self.database = database
        self.memory_id = memory_id
        self.region = region

    def create(self, family_id: str) -> dict[str, object]:
        chat_id = str(uuid4())
        if self.database:
            timestamp = datetime.now().astimezone().isoformat()
            with connect(self.database) as db:
                db.execute("INSERT INTO chats(id,family_id,title,created_at,updated_at) VALUES (?,?,?,?,?)", (chat_id, family_id, "New chat", timestamp, timestamp))
            return {"id": chat_id, "title": "New chat", "updated_at": datetime.fromisoformat(timestamp).timestamp(), "messages": []}
        FileSessionManager(session_id=chat_id, storage_dir=str(self._family_directory(family_id)))
        return {"id": chat_id, "title": "New chat", "updated_at": 0, "messages": []}

    def ensure(self, family_id: str, chat_id: str):
        identity = self._identity(chat_id)
        if self.database:
            timestamp = datetime.now().astimezone().isoformat()
            with connect(self.database) as db:
                db.execute("INSERT INTO chats(id,family_id,title,created_at,updated_at) VALUES (?,?,?,?,?) ON CONFLICT(id) DO NOTHING", (identity, family_id, "New chat", timestamp, timestamp))
                row = db.execute("SELECT id FROM chats WHERE id=? AND family_id=?", (identity, family_id)).fetchone()
            if not row:
                raise ValueError("Chat not found.")
            return identity
        return FileSessionManager(session_id=identity, storage_dir=str(self._family_directory(family_id)))

    def exists(self, family_id: str, chat_id: str) -> bool:
        try:
            identity = self._identity(chat_id)
        except ValueError:
            return False
        if self.database:
            with connect(self.database) as db:
                return bool(db.execute("SELECT id FROM chats WHERE id=? AND family_id=?", (identity, family_id)).fetchone())
        return (self._family_directory(family_id) / f"session_{identity}" / "session.json").is_file()

    def list(self, family_id: str) -> list[dict[str, object]]:
        if self.database:
            with connect(self.database) as db:
                rows = db.execute("SELECT id,title,updated_at FROM chats WHERE family_id=? ORDER BY updated_at DESC", (family_id,)).fetchall()
            return [{"id": row["id"], "title": row["title"], "updated_at": _timestamp(str(row["updated_at"]))} for row in rows]
        directory = self._family_directory(family_id)
        chats = []
        for path in directory.glob("session_*/session.json"):
            chat = self.get(family_id, path.parent.name.removeprefix("session_"))
            if chat:
                chats.append({key: chat[key] for key in ("id", "title", "updated_at")})
        return sorted(chats, key=lambda chat: float(chat["updated_at"]), reverse=True)

    def get(self, family_id: str, chat_id: str) -> dict[str, object] | None:
        if not self.exists(family_id, chat_id):
            return None
        identity = self._identity(chat_id)
        manager = self._memory_manager(family_id, identity) if self.database else FileSessionManager(session_id=identity, storage_dir=str(self._family_directory(family_id)))
        session = manager.read_session(identity)
        stored = manager.list_messages(identity, AGENT_ID)
        messages = []
        for item in stored:
            message = item.to_message()
            role = message.get("role")
            for index, block in enumerate(message.get("content", [])):
                if not isinstance(block, dict):
                    continue
                if "toolUse" in block:
                    call = block["toolUse"]
                    messages.append({"id": call["toolUseId"], "kind": "tool", "name": call["name"], "status": "error"})
                elif "toolResult" in block:
                    result = block["toolResult"]
                    for call in messages:
                        if call.get("kind") == "tool" and call["id"] == result["toolUseId"]:
                            call["status"] = "error" if result.get("status") == "error" else "done"
                elif block.get("text") and role in {"user", "assistant"}:
                    messages.append({"id": f"{identity}:{item.message_id}:{index}", "role": role, "content": block["text"]})
        first_user = next((message["content"] for message in messages if message.get("role") == "user"), "")
        if self.database:
            with connect(self.database) as db:
                row = db.execute("SELECT title,updated_at FROM chats WHERE id=? AND family_id=?", (identity, family_id)).fetchone()
            manager.close()
            return {"id": identity, "title": row["title"], "updated_at": _timestamp(str(row["updated_at"])), "messages": messages}
        updated_at = _timestamp(stored[-1].updated_at if stored else session.updated_at if session else "")
        return {"id": identity, "title": " ".join(first_user.split())[:70] or "New chat", "updated_at": updated_at, "messages": messages}

    def delete(self, family_id: str, chat_id: str) -> bool:
        if not self.exists(family_id, chat_id):
            return False
        identity = self._identity(chat_id)
        if self.database:
            with connect(self.database) as db:
                return db.execute("DELETE FROM chats WHERE id=? AND family_id=?", (identity, family_id)).rowcount > 0
        FileSessionManager(session_id=identity, storage_dir=str(self._family_directory(family_id))).delete_session(identity)
        return True

    def touch(self, family_id: str, chat_id: str, message: str) -> None:
        if not self.database:
            return
        identity = self._identity(chat_id)
        title = " ".join(message.split())[:70] or "New chat"
        with connect(self.database) as db:
            db.execute(
                "UPDATE chats SET title=CASE WHEN title='New chat' THEN ? ELSE title END,updated_at=? WHERE id=? AND family_id=?",
                (title, datetime.now().astimezone().isoformat(), identity, family_id),
            )

    def _memory_manager(self, family_id: str, chat_id: str):
        if not self.memory_id:
            raise RuntimeError("MOM_LIFE_AGENTCORE_MEMORY_ID is required.")
        from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
        from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
        return AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(memory_id=self.memory_id, actor_id=family_id, session_id=chat_id),
            region_name=self.region,
        )

    def _family_directory(self, family_id: str) -> Path:
        return self.root / f"family_{sha256(family_id.encode()).hexdigest()}"

    @staticmethod
    def _identity(chat_id: str) -> str:
        identity = str(UUID(chat_id))
        if identity != chat_id.lower():
            raise ValueError("Invalid chat identifier.")
        return identity


def _timestamp(value: str) -> float:
    return datetime.fromisoformat(value).timestamp() if value else 0
