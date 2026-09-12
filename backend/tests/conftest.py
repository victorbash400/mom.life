import pytest
from app import auth


class MemoryFamilies:
    def __init__(self):
        self.accounts = {}

    def register(self, name, email, password_hash, family_id=None):
        family_id = family_id or f'family-{len(self.accounts) + 1}'
        self.accounts[email] = {
            'id': f'account-{len(self.accounts) + 1}',
            'family_id': family_id,
            'email': email,
            'name': name,
            'password_hash': password_hash,
            'photo_version': 0,
            'has_photo': False,
        }
        return family_id

    def account(self, email):
        return self.accounts.get(email)

    def profile(self, family_id):
        return next((account for account in self.accounts.values() if account['family_id'] == family_id), None)


@pytest.fixture
def auth_headers(tmp_path, monkeypatch):
    sessions = auth.Sessions(tmp_path / 'auth.sqlite3')
    families = MemoryFamilies()
    monkeypatch.setattr(auth, 'sessions', sessions)
    monkeypatch.setattr(auth, 'families', families)
    return lambda family: {'Authorization': f'Bearer {sessions.create(family)}'}
