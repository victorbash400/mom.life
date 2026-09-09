import asyncio
import base64
import json
from urllib.parse import urlsplit,parse_qs

import httpx
import pytest

from app.task_store import TaskStore
from app.oauth_routes import Callback, callback
from app.plugin_service import PluginService
from plugins.oauth import GOOGLE_CLASSROOM_SCOPES, GOOGLE_WORKSPACE_SCOPES, OAuthConnections


def configured(tmp_path,monkeypatch,handler):
    store=TaskStore(tmp_path/'oauth.db')
    store.install_plugin('family','todoist')
    prefix='MOM_LIFE_PLUGIN_TODOIST_OAUTH_'
    values={'AUTHORIZE_URL':'https://provider.example/authorize','TOKEN_URL':'https://provider.example/token','CLIENT_ID':'registered-client','REDIRECT_URI':'http://localhost:3000/api/oauth/callback','SCOPES':'tasks:read'}
    for name,value in values.items():
        monkeypatch.setenv(prefix+name,value)
    return store,OAuthConnections(store,httpx.MockTransport(handler))


def test_pkce_callback_is_one_use_encrypted_and_family_bound(tmp_path,monkeypatch):
    def handler(request):
        fields=parse_qs(request.content.decode())
        assert fields['grant_type']==['authorization_code']
        assert len(fields['code_verifier'][0])>=43
        return httpx.Response(200,json={'access_token':'private-provider-token','token_type':'Bearer','expires_in':3600})
    store,oauth=configured(tmp_path,monkeypatch,handler)
    query=parse_qs(urlsplit(asyncio.run(oauth.begin('family','todoist'))['authorization_url']).query)
    assert query['code_challenge_method']==['S256']
    state=query['state'][0]
    result=asyncio.run(oauth.finish(state,'provider-code'))
    assert result['family_id']=='family'
    assert oauth.token('family','todoist')=='private-provider-token'
    assert oauth.token('other','todoist') is None
    assert b'private-provider-token' not in store.path.read_bytes()
    with pytest.raises(ValueError,match='already used'):
        asyncio.run(oauth.finish(state,'provider-code'))
    store.uninstall_plugin('family','todoist')
    assert oauth.token('family','todoist') is None


def test_google_workspace_requests_offline_incremental_consent(tmp_path,monkeypatch):
    store=TaskStore(tmp_path/'oauth.db')
    store.install_plugin('family','google-workspace')
    prefix='MOM_LIFE_PLUGIN_GOOGLE_WORKSPACE_OAUTH_'
    values={'AUTHORIZE_URL':'https://accounts.google.com/o/oauth2/v2/auth','TOKEN_URL':'https://oauth2.googleapis.com/token','CLIENT_ID':'registered-client','REDIRECT_URI':'http://localhost:3000/api/oauth/callback','SCOPES':' '.join(sorted(GOOGLE_WORKSPACE_SCOPES))}
    for name,value in values.items():
        monkeypatch.setenv(prefix+name,value)
    query=parse_qs(urlsplit(asyncio.run(OAuthConnections(store).begin('family','google-workspace'))['authorization_url']).query)
    assert query['access_type']==['offline']
    assert query['include_granted_scopes']==['true']
    assert query['prompt']==['consent']


def test_google_classroom_reuses_registered_google_client_with_read_only_scopes(tmp_path,monkeypatch):
    store=TaskStore(tmp_path/'oauth.db')
    store.install_plugin('family','google-classroom')
    prefix='MOM_LIFE_PLUGIN_GOOGLE_WORKSPACE_OAUTH_'
    values={'AUTHORIZE_URL':'https://accounts.google.com/o/oauth2/v2/auth','TOKEN_URL':'https://oauth2.googleapis.com/token','CLIENT_ID':'registered-client','CLIENT_SECRET':'registered-secret','REDIRECT_URI':'http://localhost:3000/api/oauth/callback','SCOPES':' '.join(sorted(GOOGLE_WORKSPACE_SCOPES))}
    for name,value in values.items():
        monkeypatch.setenv(prefix+name,value)
    query=parse_qs(urlsplit(asyncio.run(OAuthConnections(store).begin('family','google-classroom'))['authorization_url']).query)
    assert set(query['scope'][0].split()) == GOOGLE_CLASSROOM_SCOPES
    assert query['access_type']==['offline']
    assert query['include_granted_scopes']==['true']
    assert query['prompt']==['consent']


def test_todoist_registers_dynamic_oauth_client_and_encrypts_secret(tmp_path,monkeypatch):
    store=TaskStore(tmp_path/'oauth.db')
    store.install_plugin('family','todoist')
    def handler(request):
        if request.method == 'GET':
            return httpx.Response(200,json={
                'authorization_endpoint':'https://todoist.example/authorize',
                'token_endpoint':'https://todoist.example/token',
                'registration_endpoint':'https://todoist.example/register',
            })
        body=json.loads(request.content)
        assert body['redirect_uris']==['http://localhost:3000/api/oauth/callback']
        assert body['scope']=='data:read_write'
        return httpx.Response(201,json={'client_id':'dynamic-client','client_secret':'dynamic-secret'})
    oauth=OAuthConnections(store,httpx.MockTransport(handler))
    query=parse_qs(urlsplit(asyncio.run(oauth.begin('family','todoist'))['authorization_url']).query)
    assert query['client_id']==['dynamic-client']
    assert query['resource']==['https://ai.todoist.net/mcp']
    assert b'dynamic-secret' not in store.path.read_bytes()


def test_removed_connection_cannot_finish_callback(tmp_path,monkeypatch):
    store,oauth=configured(tmp_path,monkeypatch,lambda request:pytest.fail('Provider must not be called'))
    state=parse_qs(urlsplit(asyncio.run(oauth.begin('family','todoist'))['authorization_url']).query)['state'][0]
    store.uninstall_plugin('family','todoist')
    with pytest.raises(ValueError):
        asyncio.run(oauth.finish(state,'code'))


def test_provider_failure_does_not_store_credentials(tmp_path,monkeypatch):
    store,oauth=configured(tmp_path,monkeypatch,lambda request:httpx.Response(400,json={'error':'invalid_grant'}))
    state=parse_qs(urlsplit(asyncio.run(oauth.begin('family','todoist'))['authorization_url']).query)['state'][0]
    with pytest.raises(ValueError,match='rejected'):
        asyncio.run(oauth.finish(state,'code'))
    assert oauth.token('family','todoist') is None


def test_refresh_rotates_token_and_does_not_resurrect_removed_connection(tmp_path,monkeypatch):
    calls=[]
    def handler(request):
        fields=parse_qs(request.content.decode())
        calls.append(fields)
        return httpx.Response(200,json={'access_token':'renewed','refresh_token':'rotated','token_type':'Bearer','expires_in':3600})
    store,oauth=configured(tmp_path,monkeypatch,handler)
    def seed():
        encrypted=oauth.cipher.encrypt(json.dumps({'access_token':'old','refresh_token':'refresh-old','expires_at':0}).encode()).decode()
        with store._connect() as db:
            db.execute('INSERT OR REPLACE INTO oauth_tokens VALUES (?,?,?)',('family','todoist',encrypted))
    seed()
    assert asyncio.run(oauth.access_token('family','todoist'))=='renewed'
    assert calls[0]['grant_type']==['refresh_token']
    with store._connect() as db:
        token=db.execute('SELECT token FROM oauth_tokens').fetchone()['token']
    assert json.loads(oauth.cipher.decrypt(token.encode()))['refresh_token']=='rotated'
    seed()
    def remove_during_refresh(request):
        store.uninstall_plugin('family','todoist')
        return httpx.Response(200,json={'access_token':'must-not-save','token_type':'Bearer'})
    oauth.transport=httpx.MockTransport(remove_during_refresh)
    with pytest.raises(ValueError,match='changed during refresh'):
        asyncio.run(oauth.access_token('family','todoist'))
    assert oauth.token('family','todoist') is None


def test_connected_identity_comes_from_provider_id_token(tmp_path,monkeypatch):
    claims=base64.urlsafe_b64encode(json.dumps({'email':'sarah@example.com','name':'Sarah','picture':'https://images.example/sarah.jpg'}).encode()).decode().rstrip('=')
    def handler(request):
        return httpx.Response(200,json={'access_token':'private-provider-token','id_token':f'header.{claims}.signature','token_type':'Bearer','expires_in':3600})
    store,oauth=configured(tmp_path,monkeypatch,handler)
    state=parse_qs(urlsplit(asyncio.run(oauth.begin('family','todoist'))['authorization_url']).query)['state'][0]
    asyncio.run(oauth.finish(state,'provider-code'))
    assert oauth.identity('family','todoist') == {'email':'sarah@example.com','name':'Sarah','picture':'https://images.example/sarah.jpg'}


@pytest.mark.parametrize('plugin_id',['google-workspace','google-classroom','todoist'])
def test_oauth_callback_finishes_connection_without_second_user_action(monkeypatch,plugin_id):
    validated=[]
    async def finish(_oauth,state,code):
        return {'family_id':'family','plugin_id':plugin_id,'status':'authorized'}
    async def validate(_service,family_id,plugin_id):
        validated.append((family_id,plugin_id))
    monkeypatch.setattr(OAuthConnections,'finish',finish)
    monkeypatch.setattr(PluginService,'validate',validate)
    result=asyncio.run(callback(Callback(state='x'*20,code='google-code')))
    assert result['status']=='connected'
    assert validated==[('family',plugin_id)]
