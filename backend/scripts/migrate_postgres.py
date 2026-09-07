"""Copy existing local ledgers into an empty PostgreSQL database without deleting sources."""
import sqlite3
from pathlib import Path
from psycopg import connect, sql
from app.task_store import TaskStore


def migrate(url):
    root = Path(__file__).resolve().parents[1] / 'data'
    TaskStore(url)
    with connect(url) as destination:
        destination.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)')
        destination.execute('SELECT pg_advisory_xact_lock(72461903)')
        if destination.execute("SELECT name FROM schema_migrations WHERE name='sqlite_import_v1'").fetchone():
            return
        for filename in ['mom-life.sqlite3', 'auth.sqlite3']:
            path = root / filename
            if not path.exists():
                continue
            with sqlite3.connect(path) as source:
                source.row_factory = sqlite3.Row
                tables = source.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid").fetchall()
                for table in tables:
                    destination.execute(table['sql'].replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1).replace('REAL', 'DOUBLE PRECISION'))
                    rows = source.execute(f'SELECT * FROM "{table["name"]}"').fetchall()
                    for row in rows:
                        query = sql.SQL('INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING').format(sql.Identifier(table['name']), sql.SQL(',').join(map(sql.Identifier, row.keys())), sql.SQL(',').join(sql.Placeholder() for _ in row))
                        destination.execute(query, tuple(row))
        destination.execute("INSERT INTO schema_migrations VALUES ('sqlite_import_v1')")


if __name__ == '__main__':
    from app.config import get_settings
    migrate(get_settings().database_url)
