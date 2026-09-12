"""Family-scoped chat history backed only by Strands sessions."""
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from strands.session.file_session_manager import FileSessionManager


AGENT_ID = "mom-life"
SESSION_DIRECTORY = Path(__file__).resolve().parents[1] / ".sessions"


class ChatSessions:
    def __init__(self, root: Path = SESSION_DIRECTORY):
        self.root = root

    def create(self, family_id: str) -> dict[str, object]:
        chat_id = str(uuid4())
        FileSessionManager(session_id=chat_id, storage_dir=str(self._family_directory(family_id)))
        return {"id": chat_id, "title": "New chat", "updated_at": 0, "messages": []}

    def ensure(self, family_id: str, chat_id: str) -> FileSessionManager:
        identity = self._identity(chat_id)
        return FileSessionManager(session_id=identity, storage_dir=str(self._family_directory(family_id)))

    def exists(self, family_id: str, chat_id: str) -> bool:
        try:
            identity = self._identity(chat_id)
        except ValueError:
            return False
        return (self._family_directory(family_id) / f"session_{identity}" / "session.json").is_file()

    def list(self, family_id: str) -> list[dict[str, object]]:
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
        manager = FileSessionManager(session_id=identity, storage_dir=str(self._family_directory(family_id)))
        session = manager.read_session(identity)
        stored = manager.list_messages(identity, AGENT_ID) if manager.read_agent(identity, AGENT_ID) else []
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
        updated_at = _timestamp(stored[-1].updated_at if stored else session.updated_at if session else "")
        return {"id": identity, "title": " ".join(first_user.split())[:70] or "New chat", "updated_at": updated_at, "messages": messages}

    def delete(self, family_id: str, chat_id: str) -> bool:
        if not self.exists(family_id, chat_id):
            return False
        identity = self._identity(chat_id)
        FileSessionManager(session_id=identity, storage_dir=str(self._family_directory(family_id))).delete_session(identity)
        return True

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
