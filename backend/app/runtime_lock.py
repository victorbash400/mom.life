import fcntl
from pathlib import Path


def acquire(path: Path, identity: str):
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
    fcntl.flock(file.fileno(),fcntl.LOCK_UN)
    file.close()
