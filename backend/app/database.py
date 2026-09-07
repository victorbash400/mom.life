"""Shared SQL connection boundary; SQLite paths are explicit test fixtures only."""
import atexit
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pools = {}


def close_pools():
    for pool in _pools.values():
        pool.close()
    _pools.clear()


atexit.register(close_pools)


class Record(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.rowcount = cursor.rowcount

    def fetchone(self):
        row = self.cursor.fetchone()
        return Record(row) if row is not None else None

    def fetchall(self):
        return [Record(row) for row in self.cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=()):
        if query == 'BEGIN IMMEDIATE':
            # Serialize legacy ledger read/modify/write transactions across hosts.
            return Cursor(self.connection.execute('SELECT pg_advisory_xact_lock(72461902)'))
        query = re.sub(r'\bREAL\b', 'DOUBLE PRECISION', query)
        query = query.replace('?', '%s')
        if isinstance(params, dict):
            query = re.sub(r':([a-z_]+)', r'%(\1)s', query)
        return Cursor(self.connection.execute(query, params))

    def executescript(self, script):
        for statement in script.split(';'):
            if statement.strip():
                self.execute(statement)


@contextmanager
def connect(target):
    if isinstance(target, Path):
        db = sqlite3.connect(target)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()
        return
    if not str(target).startswith(('postgresql://', 'postgres://')):
        raise ValueError('MOM_LIFE_DATABASE_URL must be a PostgreSQL connection URL.')
    if target not in _pools:
        _pools[target] = ConnectionPool(target, min_size=1, max_size=10, kwargs={'row_factory': dict_row}, open=True)
    with _pools[target].connection() as connection:
        yield Connection(connection)


def table_exists(db, name):
    if isinstance(db, Connection):
        return bool(db.execute('SELECT to_regclass(%s) AS name', (name,)).fetchone()['name'])
    return bool(db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())
