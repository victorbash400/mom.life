"""Family ownership and child/folder records in PostgreSQL."""
from uuid import uuid4
from app.database import batch, connect


class FamilyStore:
    def __init__(self, url):
        self.url = url
        with connect(url) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS families (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL REFERENCES families(id),
                    email TEXT NOT NULL UNIQUE, name TEXT NOT NULL, password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS children (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL REFERENCES families(id),
                    name TEXT NOT NULL, birth_date DATE, avatar_seed TEXT NOT NULL,
                    photo BYTEA, photo_type TEXT,
                    email_updates BOOLEAN NOT NULL DEFAULT TRUE,
                    text_updates BOOLEAN NOT NULL DEFAULT FALSE,
                    notifications BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(family_id,id)
                );
                CREATE TABLE IF NOT EXISTS child_nodes (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL, child_id TEXT NOT NULL,
                    parent_id TEXT, name TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('folder','file')),
                    content BYTEA, media_type TEXT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    FOREIGN KEY(family_id,child_id) REFERENCES children(family_id,id) ON DELETE CASCADE,
                    UNIQUE(family_id,child_id,id),
                    FOREIGN KEY(family_id,child_id,parent_id) REFERENCES child_nodes(family_id,child_id,id) ON DELETE CASCADE,
                    CHECK(kind='file' OR content IS NULL)
                );
                ALTER TABLE children ADD COLUMN IF NOT EXISTS photo_version INTEGER NOT NULL DEFAULT 0;
                CREATE TABLE IF NOT EXISTS family_nodes (
                    id TEXT PRIMARY KEY, family_id TEXT NOT NULL REFERENCES families(id),
                    child_id TEXT NOT NULL CHECK(child_id='parent'), parent_id TEXT, name TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('folder','file')), content BYTEA, media_type TEXT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(family_id,child_id,id),
                    FOREIGN KEY(family_id,child_id,parent_id) REFERENCES family_nodes(family_id,child_id,id) ON DELETE CASCADE,
                    CHECK(kind='file' OR content IS NULL)
                );
                CREATE INDEX IF NOT EXISTS family_nodes_parent ON family_nodes(family_id,parent_id);
                CREATE UNIQUE INDEX IF NOT EXISTS family_nodes_name ON family_nodes(family_id,coalesce(parent_id,''),lower(name));
                CREATE INDEX IF NOT EXISTS children_family ON children(family_id);
                CREATE INDEX IF NOT EXISTS child_nodes_parent ON child_nodes(family_id,child_id,parent_id);
                CREATE UNIQUE INDEX IF NOT EXISTS child_nodes_unique_name ON child_nodes(child_id,coalesce(parent_id,''),lower(name));
            ''')

    def seed_demo(self):
        from datetime import date
        with connect(self.url) as db:
            db.execute('SELECT pg_advisory_xact_lock(72461904)')
            db.execute('CREATE TABLE IF NOT EXISTS family_migrations (name TEXT PRIMARY KEY)')
            if db.execute("SELECT name FROM family_migrations WHERE name='demo_children_v1'").fetchone():
                return
            db.execute("INSERT INTO families(id,name) VALUES ('sarah-family','Sarah') ON CONFLICT DO NOTHING")
            for identity,name,years in [('noah','Noah',5),('amina','Amina',8),('lila','Lila',2)]:
                today = date.today()
                born = date(today.year-years,today.month,min(today.day,28))
                db.execute('INSERT INTO children(id,family_id,name,birth_date,avatar_seed) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING',(identity,'sarah-family',name,born,identity))
                for folder in ['Profile','Health','Documents','Activities','School','Routines','Milestones']:
                    db.execute("INSERT INTO child_nodes(id,family_id,child_id,name,kind) VALUES (?,?,?,?,'folder') ON CONFLICT DO NOTHING",(str(uuid4()),'sarah-family',identity,folder))
            db.execute("INSERT INTO family_migrations VALUES ('demo_children_v1')")

    def seed_parent_folders(self):
        with connect(self.url) as db:
            db.execute('SELECT pg_advisory_xact_lock(72461905)')
            if db.execute("SELECT name FROM family_migrations WHERE name='parent_folders_v1'").fetchone():
                return
            for name in ['Profile','Health','Documents','Activities']:
                db.execute("INSERT INTO family_nodes(id,family_id,child_id,name,kind) VALUES (?,'sarah-family','parent',?,'folder') ON CONFLICT DO NOTHING",(str(uuid4()),name))
            db.execute("INSERT INTO family_migrations VALUES ('parent_folders_v1')")

    def register(self, name, email, password_hash):
        family_id, account_id = str(uuid4()), str(uuid4())
        with connect(self.url) as db:
            db.execute('INSERT INTO families(id,name) VALUES (?,?)', (family_id,name))
            db.execute('INSERT INTO accounts(id,family_id,email,name,password_hash) VALUES (?,?,?,?,?)', (account_id,family_id,email,name,password_hash))
        return family_id

    def account(self, email):
        with connect(self.url) as db:
            return db.execute('SELECT * FROM accounts WHERE email=?', (email,)).fetchone()

    def list_children(self, family_id):
        with connect(self.url) as db:
            return db.execute('SELECT id,name,birth_date,avatar_seed,photo_version,email_updates,text_updates,notifications,photo IS NOT NULL AS has_photo FROM children WHERE family_id=? ORDER BY created_at,id', (family_id,)).fetchall()

    def add_child(self, family_id, name, birth_date=None):
        identity = str(uuid4())
        with connect(self.url) as db:
            db.execute('INSERT INTO children(id,family_id,name,birth_date,avatar_seed) VALUES (?,?,?,?,?)', (identity,family_id,name,birth_date,identity))
        return identity

    def remove_child(self, family_id, identity):
        with connect(self.url) as db:
            return db.execute('DELETE FROM children WHERE family_id=? AND id=?', (family_id,identity)).rowcount > 0

    def profile(self, family_id):
        with connect(self.url) as db:
            row = db.execute('SELECT id,name,email FROM accounts WHERE family_id=? ORDER BY created_at LIMIT 1', (family_id,)).fetchone()
        return row or {'id': 'sarah', 'name': 'Sarah', 'email': 'demo@mom.life'}

    def snapshot(self, family_id):
        with connect(self.url) as db:
            with batch(db):
                parent_cursor = db.execute('SELECT id,name,email FROM accounts WHERE family_id=? ORDER BY created_at LIMIT 1', (family_id,))
                children_cursor = db.execute('SELECT id,name,birth_date,avatar_seed,photo_version,email_updates,text_updates,notifications,photo IS NOT NULL AS has_photo FROM children WHERE family_id=? ORDER BY created_at,id', (family_id,))
            parent = parent_cursor.fetchone()
            children = children_cursor.fetchall()
        return parent or {'id': 'sarah', 'name': 'Sarah', 'email': 'demo@mom.life'}, children

    def child(self, family_id, identity):
        with connect(self.url) as db:
            return db.execute('SELECT * FROM children WHERE family_id=? AND id=?', (family_id,identity)).fetchone()

    def update_child(self, family_id, identity, values):
        allowed = {'name','birth_date','email_updates','text_updates','notifications','photo','photo_type'}
        if not values or not set(values).issubset(allowed):
            raise ValueError('Invalid child settings.')
        with connect(self.url) as db:
            return db.execute('UPDATE children SET '+','.join(f'{key}=?' for key in values)+(',photo_version=photo_version+1' if 'photo' in values else '')+' WHERE family_id=? AND id=?', (*values.values(),family_id,identity)).rowcount > 0

    def nodes(self, family_id, child_id):
        table = 'family_nodes' if child_id == 'parent' else 'child_nodes'
        with connect(self.url) as db:
            return db.execute(f'SELECT id,parent_id AS "parentId",name,kind,updated_at AS "updatedAt",octet_length(content) AS size FROM {table} WHERE family_id=? AND child_id=? ORDER BY kind DESC,name', (family_id,child_id)).fetchall()

    def add_node(self, family_id, child_id, parent_id, name, content=None, media_type=None):
        identity = str(uuid4())
        table = 'family_nodes' if child_id == 'parent' else 'child_nodes'
        with connect(self.url) as db:
            if parent_id:
                parent = db.execute(f"SELECT id FROM {table} WHERE family_id=? AND child_id=? AND id=? AND kind='folder' FOR UPDATE", (family_id,child_id,parent_id)).fetchone()
                if not parent:
                    raise ValueError('Folder not found.')
            db.execute(f'INSERT INTO {table}(id,family_id,child_id,parent_id,name,kind,content,media_type) VALUES (?,?,?,?,?,?,?,?)', (identity,family_id,child_id,parent_id,name,'folder' if content is None else 'file',content,media_type))
        return identity

    def node(self, family_id, child_id, identity):
        table = 'family_nodes' if child_id == 'parent' else 'child_nodes'
        with connect(self.url) as db:
            return db.execute(f'SELECT * FROM {table} WHERE family_id=? AND child_id=? AND id=?', (family_id,child_id,identity)).fetchone()

    def remove_node(self, family_id, child_id, identity):
        table = 'family_nodes' if child_id == 'parent' else 'child_nodes'
        with connect(self.url) as db:
            return db.execute(f'DELETE FROM {table} WHERE family_id=? AND child_id=? AND id=?', (family_id,child_id,identity)).rowcount > 0
