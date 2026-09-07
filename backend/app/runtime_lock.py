import fcntl
from pathlib import Path


def acquire(path: Path, identity: str):
    if path.name == 'postgres':
        import hashlib
        import psycopg
        from app.config import get_settings
        key = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], 'big', signed=True)
        connection = psycopg.connect(get_settings().database_url, autocommit=True)
        if connection.execute('SELECT pg_try_advisory_lock(%s)', (key,)).fetchone()[0]:
            return connection
        connection.close()
        return None
    directory = path.parent / 'runtime-locks'
    directory.mkdir(parents=True,exist_ok=True)
    import hashlib
    file = (directory / hashlib.sha256(identity.encode()).hexdigest()).open('a')
    try:
        fcntl.flock(file.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
        return file
    except BlockingIOError:
        file.close()
        return None


def release(file):
    if not hasattr(file, 'fileno'):
        file.close()
        return
    # psycopg connections also expose fileno; distinguish their SQL interface.
    if hasattr(file, 'execute'):
        file.close()
        return
    fcntl.flock(file.fileno(),fcntl.LOCK_UN)
    file.close()
