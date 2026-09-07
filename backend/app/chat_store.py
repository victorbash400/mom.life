"""Family-scoped conversation history."""
import json
import time
import uuid
from app.database import connect


class ChatStore:
    def __init__(self, target):
        self.target = target
        with connect(target) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, family_id TEXT NOT NULL, title TEXT NOT NULL,
                messages TEXT NOT NULL, updated_at REAL NOT NULL)''')
            db.execute('CREATE INDEX IF NOT EXISTS conversations_family ON conversations(family_id, updated_at)')

    def list(self, family):
        with connect(self.target) as db:
            return [dict(row) for row in db.execute('SELECT id,title,updated_at FROM conversations WHERE family_id=? ORDER BY updated_at DESC', (family,)).fetchall()]

    def get(self, family, identity):
        with connect(self.target) as db:
            row = db.execute('SELECT * FROM conversations WHERE family_id=? AND id=?', (family, identity)).fetchone()
            return {**dict(row), 'messages': json.loads(row['messages'])} if row else None

    def create(self, family):
        identity = str(uuid.uuid4())
        with connect(self.target) as db:
            db.execute('INSERT INTO conversations VALUES (?,?,?,?,?)', (identity, family, 'New chat', '[]', time.time()))
        return self.get(family, identity)

    def append(self, family, identity, role, content):
        with connect(self.target) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT messages,title FROM conversations WHERE family_id=? AND id=?', (family, identity)).fetchone()
            if not row:
                raise ValueError('Chat not found.')
            messages = json.loads(row['messages'])
            title = ' '.join(content.split())[:70] if not messages and role == 'user' else row['title']
            messages.append({'id': str(uuid.uuid4()), 'role': role, 'content': content})
            db.execute('UPDATE conversations SET messages=?,title=?,updated_at=? WHERE family_id=? AND id=?', (json.dumps(messages), title, time.time(), family, identity))

    def delete(self, family, identity):
        with connect(self.target) as db:
            return db.execute('DELETE FROM conversations WHERE family_id=? AND id=?', (family, identity)).rowcount > 0
