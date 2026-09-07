"""Opaque, revocable demo sessions. Only token digests are persisted."""
import hashlib
import secrets
from app.database import connect
from app.config import get_settings
from app.family_store import FamilyStore
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from psycopg.errors import UniqueViolation
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

DEMO_EMAIL = 'demo@mom.life'
DEMO_PASSWORD = 'MomLifeDemo!'
SESSION_SECONDS = 60 * 60 * 24


class Sessions:
    def __init__(self, path: Path):
        self.path = path
        if isinstance(path, Path):
            path.parent.mkdir(parents=True, exist_ok=True)
        with connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS auth_sessions (digest TEXT PRIMARY KEY, family_id TEXT NOT NULL, expires_at REAL NOT NULL)')

    def create(self, family_id='sarah-family'):
        token = secrets.token_urlsafe(32)
        with connect(self.path) as db:
            db.execute('DELETE FROM auth_sessions WHERE expires_at <= ?', (time.time(),))
            db.execute('INSERT INTO auth_sessions VALUES (?,?,?)', (self.digest(token), family_id, time.time() + SESSION_SECONDS))
        return token

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def family(self, token):
        with connect(self.path) as db:
            row = db.execute('SELECT family_id FROM auth_sessions WHERE digest=? AND expires_at>?', (self.digest(token), time.time())).fetchone()
        return row[0] if row else None

    def revoke(self, token):
        with connect(self.path) as db:
            db.execute('DELETE FROM auth_sessions WHERE digest=?', (self.digest(token),))


sessions = Sessions(get_settings().database_url)
families = FamilyStore(get_settings().database_url)
families.seed_demo()
families.seed_parent_folders()
hasher = PasswordHasher()
router = APIRouter(prefix='/api/auth')


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


def bearer(request):
    scheme, _, token = request.headers.get('authorization', '').partition(' ')
    return token if scheme.lower() == 'bearer' else ''


@router.post('/login')
def login(body: Login):
    valid_email = secrets.compare_digest(body.email.strip().lower().encode(), DEMO_EMAIL.encode())
    valid_password = secrets.compare_digest(body.password.encode(), DEMO_PASSWORD.encode())
    if valid_email and valid_password:
        return {'token': sessions.create(), 'expires_in': SESSION_SECONDS}
    account = families.account(body.email.strip().lower())
    try:
        if not account or not hasher.verify(account['password_hash'], body.password):
            raise HTTPException(401, 'Email or password is incorrect.')
    except VerifyMismatchError:
        raise HTTPException(401, 'Email or password is incorrect.')
    return {'token': sessions.create(account['family_id']), 'expires_in': SESSION_SECONDS}


@router.get('/session')
def session(request: Request):
    family = sessions.family(bearer(request))
    if not family:
        raise HTTPException(401, 'Sign in to continue.')
    return {'family_id': family, **families.profile(family), 'demo': family == 'sarah-family'}


@router.post('/logout', status_code=204)
def logout(request: Request):
    sessions.revoke(bearer(request))


async def require_session(request: Request, call_next):
    path = request.url.path
    if not path.startswith('/api/') or path in {'/api/auth/login', '/api/auth/register', '/api/webhooks/whatsapp'} or request.method == 'OPTIONS':
        return await call_next(request)
    family = sessions.family(bearer(request))
    if not family:
        return JSONResponse({'detail': 'Sign in to continue.'}, status_code=401)
    supplied = request.query_params.get('family_id')
    if supplied and supplied != family:
        return JSONResponse({'detail': 'This family is not accessible.'}, status_code=403)
    if request.method in {'POST', 'PUT', 'PATCH'} and 'application/json' in request.headers.get('content-type', ''):
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({'detail': 'Invalid JSON.'}, status_code=400)
        if isinstance(body, dict) and body.get('family_id', family) != family:
            return JSONResponse({'detail': 'This family is not accessible.'}, status_code=403)
    request.state.family_id = family
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response


class Registration(Login):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=10, max_length=256)


@router.post('/register', status_code=201)
def register(body: Registration):
    email, name = body.email.strip().lower(), body.name.strip()
    if not name or email.count('@') != 1 or '.' not in email.split('@')[-1] or any(char.isspace() for char in email):
        raise HTTPException(400, 'Enter a name and valid email.')
    if email == DEMO_EMAIL:
        raise HTTPException(409, 'An account with this email already exists.')
    try:
        family_id = families.register(name, email, hasher.hash(body.password))
    except UniqueViolation:
        raise HTTPException(409, 'An account with this email already exists.')
    return {'token': sessions.create(family_id), 'expires_in': SESSION_SECONDS}
