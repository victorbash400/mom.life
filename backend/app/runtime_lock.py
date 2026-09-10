import fcntl
import hashlib
from pathlib import Path


def _postgres_lock(path: Path, identity: str, *, wait: bool):
    if path.name != "postgres":
        return None
    import psycopg
    from app.config import get_settings
    key = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], "big", signed=True)
    connection = psycopg.connect(get_settings().database_url, autocommit=True)
    function = "pg_advisory_lock" if wait else "pg_try_advisory_lock"
    acquired = connection.execute(f"SELECT {function}(%s)", (key,)).fetchone()[0]
    if wait or acquired:
        return connection
    connection.close()
    return None


def _file_lock(path: Path, identity: str, *, wait: bool):
    directory = path.parent / "runtime-locks"
    directory.mkdir(parents=True, exist_ok=True)
    file = (directory / hashlib.sha256(identity.encode()).hexdigest()).open("a")
    try:
        mode = fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB
        fcntl.flock(file.fileno(), mode)
        return file
    except BlockingIOError:
        file.close()
        return None


def acquire(path: Path, identity: str):
    return _postgres_lock(path, identity, wait=False) if path.name == "postgres" else _file_lock(path, identity, wait=False)


def acquire_wait(path: Path, identity: str):
    """Wait for exclusive ownership without retry loops."""
    return _postgres_lock(path, identity, wait=True) if path.name == "postgres" else _file_lock(path, identity, wait=True)


def release(lock):
    if hasattr(lock, "execute"):
        lock.close()
        return
    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    lock.close()
