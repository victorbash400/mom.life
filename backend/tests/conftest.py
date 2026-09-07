import pytest
from app import auth


@pytest.fixture
def auth_headers(tmp_path, monkeypatch):
    sessions = auth.Sessions(tmp_path / 'auth.sqlite3')
    monkeypatch.setattr(auth, 'sessions', sessions)
    return lambda family: {'Authorization': f'Bearer {sessions.create(family)}'}
