"""Registered OAuth clients with PKCE and encrypted family-bound tokens."""
import base64
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
            ''')

    @staticmethod
    def config(plugin_id):
        plugin_by_id(plugin_id)
        prefix='MOM_LIFE_PLUGIN_'+plugin_id.replace('-','_').upper()+'_OAUTH_'
        config={name.lower():setting(prefix+name) for name in ['AUTHORIZE_URL','TOKEN_URL','CLIENT_ID','CLIENT_SECRET','REDIRECT_URI','SCOPES','RESOURCE']}
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
        return config

    def begin(self,family_id,plugin_id):
        if plugin_id not in self.store.installed_plugins(family_id):
            raise ValueError('Install the connection first.')
        config=self.config(plugin_id)
        state=secrets.token_urlsafe(32)
        verifier=secrets.token_urlsafe(64)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        with self.store._connect() as db:
            db.execute('DELETE FROM oauth_attempts WHERE expires_at<?',(time.time(),))
            db.execute('INSERT INTO oauth_attempts VALUES (?,?,?,?,?,?)',(hashlib.sha256(state.encode()).hexdigest(),family_id,plugin_id,self.cipher.encrypt(verifier.encode()).decode(),self.cipher.encrypt(json.dumps(config).encode()).decode(),time.time()+600))
        params={'response_type':'code','client_id':config['client_id'],'redirect_uri':config['redirect_uri'],'scope':config['scopes'],'state':state,'code_challenge':challenge,'code_challenge_method':'S256'}
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
            renewed['expires_at']=time.time()+float(renewed.get('expires_in',3600))
            with self.store._connect() as db:
                updated=db.execute('UPDATE oauth_tokens SET token=? WHERE family_id=? AND plugin_id=? AND token=?',(self.cipher.encrypt(json.dumps(renewed).encode()).decode(),family_id,plugin_id,original))
                if updated.rowcount!=1:
                    raise ValueError('The connection changed during refresh. Its old authorization was not restored.')
            return renewed['access_token']
        finally:
            release(lease)
