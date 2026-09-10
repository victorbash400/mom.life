"""Registered OAuth clients with PKCE and encrypted family-bound tokens."""
import base64
import binascii
import hashlib
import json
import os
import secrets
import time
from urllib.parse import urlencode, urlsplit

import httpx
from cryptography.fernet import Fernet

from plugins.configuration import setting
from plugins.catalog import plugin_by_id


GOOGLE_WORKSPACE_SCOPES = {
    'openid',
    'email',
    'profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/calendar.calendarlist.readonly',
    'https://www.googleapis.com/auth/calendar.events.freebusy',
    'https://www.googleapis.com/auth/calendar.events',
}

GOOGLE_CLASSROOM_SCOPES = {
    'openid',
    'email',
    'profile',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
}

GOOGLE_PLUGINS = {'google-workspace', 'google-classroom'}

DYNAMIC_OAUTH_PROVIDERS = {
    'todoist': {
        'metadata_url':'https://todoist.com/.well-known/oauth-authorization-server',
        'resource':'https://ai.todoist.net/mcp',
        'scopes':'data:read_write',
        'token_endpoint_auth_method':'client_secret_post',
    },
    'notion': {
        'metadata_url':'https://mcp.notion.com/.well-known/oauth-authorization-server',
        'resource':'https://mcp.notion.com/mcp',
        'scopes':'default',
        'token_endpoint_auth_method':'none',
    },
    'canva': {
        'metadata_url':'https://mcp.canva.com/.well-known/oauth-authorization-server',
        'resource':'https://mcp.canva.com/mcp',
        'scopes':'profile:read design:meta:read design:content:read design:content:write folder:read folder:write asset:read asset:write',
        'token_endpoint_auth_method':'client_secret_post',
    },
}


class OAuthConnections:
    def __init__(self,store,transport=None):
        self.store=store
        self.transport=transport
        key_path=store.path.parent/'connection.key'
        try:
            descriptor=os.open(key_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor,'wb') as file:
                file.write(Fernet.generate_key())
        self.cipher=Fernet(key_path.read_bytes())
        with store._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS oauth_attempts (
                    state TEXT PRIMARY KEY, family_id TEXT NOT NULL, plugin_id TEXT NOT NULL,
                    verifier TEXT NOT NULL, config TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    family_id TEXT NOT NULL, plugin_id TEXT NOT NULL, token TEXT NOT NULL,
                    PRIMARY KEY(family_id,plugin_id)
                );
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    plugin_id TEXT PRIMARY KEY, config TEXT NOT NULL
                );
            ''')

    def config(self,plugin_id):
        plugin_by_id(plugin_id)
        prefix='MOM_LIFE_PLUGIN_'+plugin_id.replace('-','_').upper()+'_OAUTH_'
        config={name.lower():setting(prefix+name) for name in ['AUTHORIZE_URL','TOKEN_URL','CLIENT_ID','CLIENT_SECRET','REDIRECT_URI','SCOPES','RESOURCE']}
        if plugin_id == 'google-classroom':
            workspace_prefix='MOM_LIFE_PLUGIN_GOOGLE_WORKSPACE_OAUTH_'
            for name in ['AUTHORIZE_URL','TOKEN_URL','CLIENT_ID','CLIENT_SECRET','REDIRECT_URI']:
                config[name.lower()] = config[name.lower()] or setting(workspace_prefix+name)
            config['scopes'] = config['scopes'] or ' '.join(sorted(GOOGLE_CLASSROOM_SCOPES))
        if not all(config[name] for name in ['authorize_url','token_url','client_id','redirect_uri','scopes']):
            with self.store._connect() as db:
                registered=db.execute('SELECT config FROM oauth_clients WHERE plugin_id=?',(plugin_id,)).fetchone()
            if registered:
                config=json.loads(self.cipher.decrypt(registered['config'].encode()))
        for name in ['authorize_url','token_url','client_id','redirect_uri','scopes']:
            if not config[name]:
                raise ValueError(f'Configure {prefix+name.upper()} for this registered OAuth client.')
        for name in ['authorize_url','token_url']:
            parsed=urlsplit(config[name])
            if parsed.scheme!='https' or not parsed.hostname or parsed.username:
                raise ValueError('OAuth provider endpoints must use HTTPS without embedded credentials.')
        redirect=urlsplit(config['redirect_uri'])
        if redirect.scheme!='https' and not (redirect.scheme=='http' and redirect.hostname in {'localhost','127.0.0.1'}):
            raise ValueError('OAuth callback must use HTTPS or local loopback HTTP.')
        if plugin_id == 'google-workspace' and not GOOGLE_WORKSPACE_SCOPES.issubset(config['scopes'].split()):
            raise ValueError('Configure every required Google Workspace OAuth scope.')
        if plugin_id == 'google-classroom' and not GOOGLE_CLASSROOM_SCOPES.issubset(config['scopes'].split()):
            raise ValueError('Configure every required Google Classroom read-only OAuth scope.')
        return config

    async def register_dynamic_client(self,plugin_id):
        provider=DYNAMIC_OAUTH_PROVIDERS.get(plugin_id)
        if not provider:
            return
        with self.store._connect() as db:
            if db.execute('SELECT plugin_id FROM oauth_clients WHERE plugin_id=?',(plugin_id,)).fetchone():
                return
        redirect_uri=setting('MOM_LIFE_PLUGIN_'+plugin_id.replace('-','_').upper()+'_OAUTH_REDIRECT_URI') or 'http://localhost:3000/api/oauth/callback'
        async with httpx.AsyncClient(timeout=20,follow_redirects=False,transport=self.transport) as client:
            metadata_response=await client.get(provider['metadata_url'])
            metadata_response.raise_for_status()
            metadata=metadata_response.json()
            registration_url=metadata.get('registration_endpoint')
            if not registration_url or urlsplit(registration_url).scheme!='https':
                raise ValueError('OAuth provider did not publish a secure client registration endpoint.')
            response=await client.post(registration_url,json={
                'client_name':'mom.life',
                'redirect_uris':[redirect_uri],
                'scope':provider['scopes'],
                'grant_types':['authorization_code','refresh_token'],
                'response_types':['code'],
                'token_endpoint_auth_method':provider['token_endpoint_auth_method'],
            })
            if response.status_code not in {200,201}:
                raise ValueError('OAuth provider rejected dynamic client registration.')
            registered=response.json()
        config={
            'authorize_url':metadata.get('authorization_endpoint'),
            'token_url':metadata.get('token_endpoint'),
            'client_id':registered.get('client_id'),
            'client_secret':registered.get('client_secret'),
            'redirect_uri':redirect_uri,
            'scopes':provider['scopes'],
            'resource':provider['resource'],
        }
        if not all(config[name] for name in ['authorize_url','token_url','client_id']):
            raise ValueError('OAuth provider returned an incomplete client registration.')
        encrypted=self.cipher.encrypt(json.dumps(config).encode()).decode()
        with self.store._connect() as db:
            db.execute('INSERT INTO oauth_clients VALUES (?,?) ON CONFLICT (plugin_id) DO NOTHING',(plugin_id,encrypted))

    def has_registered_config(self,plugin_id):
        prefix='MOM_LIFE_PLUGIN_'+plugin_id.replace('-','_').upper()+'_OAUTH_'
        if setting(prefix+'CLIENT_ID'):
            return True
        with self.store._connect() as db:
            return db.execute('SELECT plugin_id FROM oauth_clients WHERE plugin_id=?',(plugin_id,)).fetchone() is not None

    async def begin(self,family_id,plugin_id):
        if plugin_id not in self.store.installed_plugins(family_id):
            raise ValueError('Install the connection first.')
        if plugin_id in DYNAMIC_OAUTH_PROVIDERS and not self.has_registered_config(plugin_id):
            await self.register_dynamic_client(plugin_id)
        config=self.config(plugin_id)
        state=secrets.token_urlsafe(32)
        verifier=secrets.token_urlsafe(64)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        with self.store._connect() as db:
            db.execute('DELETE FROM oauth_attempts WHERE expires_at<?',(time.time(),))
            db.execute('INSERT INTO oauth_attempts VALUES (?,?,?,?,?,?)',(hashlib.sha256(state.encode()).hexdigest(),family_id,plugin_id,self.cipher.encrypt(verifier.encode()).decode(),self.cipher.encrypt(json.dumps(config).encode()).decode(),time.time()+600))
        params={'response_type':'code','client_id':config['client_id'],'redirect_uri':config['redirect_uri'],'scope':config['scopes'],'state':state,'code_challenge':challenge,'code_challenge_method':'S256'}
        if plugin_id in GOOGLE_PLUGINS:
            params.update({'access_type':'offline','include_granted_scopes':'true','prompt':'consent'})
        if config['resource']:
            params['resource']=config['resource']
        return {'authorization_url':config['authorize_url']+('&' if '?' in config['authorize_url'] else '?')+urlencode(params)}

    async def finish(self,state,code):
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            identity=hashlib.sha256(state.encode()).hexdigest()
            row=db.execute('SELECT * FROM oauth_attempts WHERE state=?',(identity,)).fetchone()
            if not row or row['expires_at']<time.time():
                raise ValueError('Authorization expired or was already used. Connect again.')
            db.execute('DELETE FROM oauth_attempts WHERE state=?',(identity,))
        if row['plugin_id'] not in self.store.installed_plugins(row['family_id']):
            raise ValueError('The connection was removed during authorization.')
        config=json.loads(self.cipher.decrypt(row['config'].encode()))
        data={'grant_type':'authorization_code','code':code,'client_id':config['client_id'],'redirect_uri':config['redirect_uri'],'code_verifier':self.cipher.decrypt(row['verifier'].encode()).decode()}
        if config['client_secret']:
            data['client_secret']=config['client_secret']
        if config['resource']:
            data['resource']=config['resource']
        async with httpx.AsyncClient(timeout=20,follow_redirects=False,transport=self.transport) as client:
            response=await client.post(config['token_url'],data=data)
            if response.status_code!=200:
                raise ValueError('Provider rejected authorization. Connect again.')
            tokens=response.json()
        if not tokens.get('access_token') or str(tokens.get('token_type','')).lower()!='bearer':
            raise ValueError('Provider did not return a bearer access token.')
        if row['plugin_id'] in GOOGLE_PLUGINS and not tokens.get('refresh_token'):
            raise ValueError('Google did not return offline access. Reconnect and approve access again.')
        tokens['expires_at']=time.time()+float(tokens.get('expires_in',3600))
        with self.store._connect() as db:
            if not db.execute('SELECT plugin_id FROM plugin_installations WHERE family_id=? AND plugin_id=?',(row['family_id'],row['plugin_id'])).fetchone():
                raise ValueError('The connection was removed during authorization.')
            db.execute('INSERT INTO oauth_tokens VALUES (?,?,?) ON CONFLICT (family_id,plugin_id) DO UPDATE SET token=excluded.token',(row['family_id'],row['plugin_id'],self.cipher.encrypt(json.dumps(tokens).encode()).decode()))
            db.execute('DELETE FROM plugin_connections WHERE family_id=? AND plugin_id=?',(row['family_id'],row['plugin_id']))
        return {'family_id':row['family_id'],'plugin_id':row['plugin_id'],'status':'authorized'}

    def token(self,family_id,plugin_id):
        with self.store._connect() as db:
            row=db.execute('SELECT token FROM oauth_tokens WHERE family_id=? AND plugin_id=?',(family_id,plugin_id)).fetchone()
        if not row:
            return None
        token=json.loads(self.cipher.decrypt(row['token'].encode()))
        if token['expires_at']<=time.time():
            raise ValueError('Provider authorization expired. Reconnect this plugin.')
        return token['access_token']

    def identity(self,family_id,plugin_id):
        with self.store._connect() as db:
            row=db.execute('SELECT token FROM oauth_tokens WHERE family_id=? AND plugin_id=?',(family_id,plugin_id)).fetchone()
        if not row:
            return None
        tokens=json.loads(self.cipher.decrypt(row['token'].encode()))
        encoded=tokens.get('id_token')
        if not encoded:
            return None
        try:
            payload=encoded.split('.')[1]
            payload += '=' * (-len(payload) % 4)
            claims=json.loads(base64.urlsafe_b64decode(payload.encode()))
        except (ValueError,IndexError,UnicodeDecodeError,binascii.Error,json.JSONDecodeError):
            return None
        return {key:claims.get(key) for key in ('email','name','picture') if claims.get(key)} or None

    def has_required_scopes(self, family_id, plugin_id):
        if plugin_id not in GOOGLE_PLUGINS:
            return True
        with self.store._connect() as db:
            row=db.execute('SELECT token FROM oauth_tokens WHERE family_id=? AND plugin_id=?',(family_id,plugin_id)).fetchone()
        if not row:
            return False
        tokens=json.loads(self.cipher.decrypt(row['token'].encode()))
        required=GOOGLE_WORKSPACE_SCOPES if plugin_id == 'google-workspace' else GOOGLE_CLASSROOM_SCOPES
        return required.issubset(set(tokens.get('scope','').split()))

    async def access_token(self,family_id,plugin_id):
        from app.runtime_lock import acquire, release
        with self.store._connect() as db:
            row=db.execute('SELECT token FROM oauth_tokens WHERE family_id=? AND plugin_id=?',(family_id,plugin_id)).fetchone()
        if not row:
            return None
        tokens=json.loads(self.cipher.decrypt(row['token'].encode()))
        if tokens['expires_at']>time.time()+30:
            return tokens['access_token']
        lease=acquire(self.store.path,f'oauth:{family_id}:{plugin_id}')
        if lease is None:
            raise ValueError('This connection is refreshing in another request. Retry after it finishes.')
        try:
            with self.store._connect() as db:
                row=db.execute('SELECT token FROM oauth_tokens WHERE family_id=? AND plugin_id=?',(family_id,plugin_id)).fetchone()
            if not row:
                raise ValueError('The connection was removed.')
            original=row['token']
            tokens=json.loads(self.cipher.decrypt(original.encode()))
            if tokens['expires_at']>time.time()+30:
                return tokens['access_token']
            if not tokens.get('refresh_token'):
                raise ValueError('Provider authorization expired. Reconnect this plugin.')
            config=self.config(plugin_id)
            data={'grant_type':'refresh_token','refresh_token':tokens['refresh_token'],'client_id':config['client_id']}
            if config['client_secret']:
                data['client_secret']=config['client_secret']
            if config['resource']:
                data['resource']=config['resource']
            async with httpx.AsyncClient(timeout=20,follow_redirects=False,transport=self.transport) as client:
                response=await client.post(config['token_url'],data=data)
                if response.status_code!=200:
                    raise ValueError('Provider rejected token refresh. Reconnect this plugin.')
                renewed=response.json()
            if not renewed.get('access_token') or str(renewed.get('token_type','')).lower()!='bearer':
                raise ValueError('Provider returned an invalid refreshed token.')
            renewed['refresh_token']=renewed.get('refresh_token') or tokens['refresh_token']
            renewed['scope']=renewed.get('scope') or tokens.get('scope','')
            renewed['expires_at']=time.time()+float(renewed.get('expires_in',3600))
            with self.store._connect() as db:
                updated=db.execute('UPDATE oauth_tokens SET token=? WHERE family_id=? AND plugin_id=? AND token=?',(self.cipher.encrypt(json.dumps(renewed).encode()).decode(),family_id,plugin_id,original))
                if updated.rowcount!=1:
                    raise ValueError('The connection changed during refresh. Its old authorization was not restored.')
            return renewed['access_token']
        finally:
            release(lease)
