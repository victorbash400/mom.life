import asyncio
import json

import httpx
import pytest

from app.task_store import TaskStore
from app.plugin_service import PluginService
from plugins.api_adapters import ApiAdapter
from plugins.runtime import PluginToolSession


def configured(monkeypatch,plugin):
    prefix='MOM_LIFE_PLUGIN_'+plugin.replace('-','_').upper()
    monkeypatch.setenv(prefix+'_FAMILY_ID','family')
    monkeypatch.setenv(prefix+'_TOKEN','test-token')
    return prefix


def test_install_is_not_a_validated_connection(tmp_path,monkeypatch):
    configured(monkeypatch,'todoist')
    store=TaskStore(tmp_path/'store.db')
    store.install_plugin('family','todoist')
    plugin=next(p for p in PluginService(store).list('family') if p['id']=='todoist')
    assert plugin['installed'] and not plugin['connected']


def test_runtime_enforces_namespace_and_revoked_permissions(tmp_path):
    store=TaskStore(tmp_path/'store.db')
    store.install_plugin('family','todoist')
    runtime=PluginToolSession(['todoist'],store,'family')
    with pytest.raises(ValueError):
        asyncio.run(runtime.load('notion'))
    store.set_permission('family','todoist','todoist.1',False)
    with pytest.raises(RuntimeError,match='disabled'):
        asyncio.run(runtime.load('todoist'))
    store.uninstall_plugin('family','todoist')
    with pytest.raises(RuntimeError,match='removed'):
        runtime.require_access('todoist')


def test_api_credentials_are_family_scoped(monkeypatch):
    configured(monkeypatch,'microsoft-family')
    with pytest.raises(RuntimeError,match='family identity'):
        ApiAdapter('microsoft-family','other')


def test_graph_draft_is_bounded_and_does_not_send(monkeypatch):
    configured(monkeypatch,'microsoft-family')
    def handler(request):
        assert request.method=='POST'
        assert request.url.path=='/v1.0/me/messages'
        assert json.loads(request.content)['body']['content']=='Please review'
        return httpx.Response(201,json={'id':'draft-123','isDraft':True})
    adapter=ApiAdapter('microsoft-family','family',httpx.MockTransport(handler))
    assert asyncio.run(adapter.call('create_draft',{'subject':'Trip','body':'Please review'}))['data']['isDraft']
    with pytest.raises(ValueError):
        asyncio.run(adapter.call('send_mail',{}))
    with pytest.raises(ValueError):
        asyncio.run(adapter.call('create_draft',{'subject':'Trip','body':'Review','url':'https://elsewhere'}))


def test_fhir_patient_scope_is_not_model_controlled(monkeypatch):
    prefix=configured(monkeypatch,'mychart')
    monkeypatch.setenv(prefix+'_URL','https://provider.example/fhir/R4')
    monkeypatch.setenv(prefix+'_PATIENT_ID','child-123')
    def handler(request):
        assert request.url.params['patient']=='child-123'
        return httpx.Response(200,json={'resourceType':'Bundle','entry':[]})
    adapter=ApiAdapter('mychart','family',httpx.MockTransport(handler))
    asyncio.run(adapter.call('read_observations',{}))
    with pytest.raises(ValueError):
        asyncio.run(adapter.call('read_observations',{'patient':'other'}))


def test_provider_errors_surface(monkeypatch):
    configured(monkeypatch,'microsoft-family')
    adapter=ApiAdapter('microsoft-family','family',httpx.MockTransport(lambda request:httpx.Response(403)))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(adapter.call('list_events',{}))


def test_browser_uses_observed_targets_and_closes_session(monkeypatch):
    from plugins import browser_adapter
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    monkeypatch.setenv('MOM_LIFE_PLUGIN_AGENTCORE_BROWSER_FAMILY_ID','family')
    monkeypatch.setattr(browser_adapter,'BrowserClient',lambda region:SimpleNamespace(stop=lambda:True))
    adapter=browser_adapter.BrowserAdapter('family')
    target=SimpleNamespace(count=AsyncMock(return_value=2),click=AsyncMock())
    page=SimpleNamespace(get_by_role=lambda *args,**kwargs:target)
    adapter.page=page
    async def run():
        with pytest.raises(ValueError,match='ambiguous'):
            await adapter.call('click',{'role':'button','name':'Submit'})
        target.click.assert_not_called()
        with pytest.raises(ValueError,match='HTTPS'):
            await adapter.call('navigate',{'url':'http://example.com'})
        adapter.session_id='session'
        adapter.playwright=SimpleNamespace(stop=AsyncMock())
        await adapter.close()
        assert adapter.session_id is None
        assert adapter.page is None
    asyncio.run(run())


def test_amazon_product_request_uses_server_marketplace(monkeypatch):
    prefix=configured(monkeypatch,'amazon-shopping')
    monkeypatch.setenv(prefix+'_PARTNER_TAG','family-20')
    monkeypatch.setenv(prefix+'_MARKETPLACE','www.amazon.com')
    def handler(request):
        assert request.url.host=='creatorsapi.amazon'
        body=json.loads(request.content)
        assert body['itemIds']==['B09B2SBHQK']
        assert body['partnerTag']=='family-20'
        return httpx.Response(200,json={'itemsResult':{'items':[]}})
    adapter=ApiAdapter('amazon-shopping','family',httpx.MockTransport(handler))
    asyncio.run(adapter.call('get_product',{'asin':'B09B2SBHQK'}))


def test_whatsapp_validation_reads_identity_without_sending(monkeypatch):
    prefix=configured(monkeypatch,'whatsapp')
    monkeypatch.setenv(prefix+'_PHONE_NUMBER_ID','123456')
    monkeypatch.setenv(prefix+'_API_VERSION','v25.0')
    def handler(request):
        assert request.method=='GET'
        assert request.url.path=='/v25.0/123456'
        return httpx.Response(200,json={'id':'123456','verified_name':'Family helper'})
    adapter=ApiAdapter('whatsapp','family',httpx.MockTransport(handler))
    assert asyncio.run(adapter.validate())['status']=='success'


def test_amazon_validation_rejects_empty_success_response(monkeypatch):
    prefix=configured(monkeypatch,'amazon-shopping')
    monkeypatch.setenv(prefix+'_PARTNER_TAG','family-20')
    monkeypatch.setenv(prefix+'_MARKETPLACE','www.amazon.com')
    monkeypatch.setenv(prefix+'_VALIDATION_ASIN','B09B2SBHQK')
    adapter=ApiAdapter('amazon-shopping','family',httpx.MockTransport(lambda request:httpx.Response(200,json={'itemsResult':{'items':[]}})))
    with pytest.raises(ValueError,match='no product'):
        asyncio.run(adapter.validate())


def test_setup_status_never_exposes_secret_values(monkeypatch):
    configured(monkeypatch,'todoist')
    fields=PluginService.setup_fields('todoist')
    assert all(set(field)=={'name','configured'} for field in fields)
    assert 'test-token' not in json.dumps(fields)
    assert next(field for field in fields if field['name'].endswith('_TOKEN'))['configured']


def test_browser_preserves_approval_session_and_reuses_it(tmp_path,monkeypatch):
    from plugins import browser_adapter
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock
    import time
    store=TaskStore(tmp_path/'browser.db')
    goal=store.create('family','child','Browser work')
    identity=store.create_assignment(goal['id'],{'title':'Form','instruction':'Prepare form','expected_outputs':['Form']})
    monkeypatch.setenv('MOM_LIFE_PLUGIN_AGENTCORE_BROWSER_FAMILY_ID','family')
    client=SimpleNamespace(stop=Mock(),start=Mock(),generate_ws_headers=lambda:('wss://browser.example',{}))
    monkeypatch.setattr(browser_adapter,'BrowserClient',lambda region:client)
    first=browser_adapter.BrowserAdapter('family',store,identity)
    with store._connect() as db:
        db.execute('INSERT INTO browser_sessions VALUES (?,?,?)',(identity,'existing-session',time.time()+600))
    first.session_id='existing-session'
    first.preserve_session=True
    asyncio.run(first.close())
    client.stop.assert_not_called()
    page=SimpleNamespace(set_default_timeout=Mock())
    playwright=SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=AsyncMock(return_value=SimpleNamespace(contexts=[SimpleNamespace(pages=[page])]))),stop=AsyncMock())
    monkeypatch.setattr(browser_adapter,'async_playwright',lambda:SimpleNamespace(start=AsyncMock(return_value=playwright)))
    resumed=browser_adapter.BrowserAdapter('family',store,identity)
    async def run():
        await resumed.start()
        assert resumed.session_id=='existing-session'
        client.start.assert_not_called()
        await resumed.close()
    asyncio.run(run())
    client.stop.assert_called_once()
    with store._connect() as db:
        assert db.execute('SELECT * FROM browser_sessions').fetchall()==[]


@pytest.mark.parametrize('fails', [False, True])
def test_browser_cleanup_retains_handle_until_stop_succeeds(tmp_path, monkeypatch, fails):
    from app import browser_cleanup
    from types import SimpleNamespace
    from unittest.mock import Mock

    store = TaskStore(tmp_path / 'cleanup.db')
    goal = store.create('family', 'child', 'Browser work')
    assignment = store.create_assignment(goal['id'], {'title': 'Form', 'instruction': 'Prepare form'})
    with store._connect() as db:
        db.execute('CREATE TABLE browser_sessions (assignment_id TEXT PRIMARY KEY, session_id TEXT, expires_at REAL)')
        db.execute('INSERT INTO browser_sessions VALUES (?, ?, ?)', (assignment, 'retained-session', 1))
    client = SimpleNamespace(
        stop_browser_session=Mock(side_effect=RuntimeError('AWS unavailable') if fails else None),
        exceptions=SimpleNamespace(ResourceNotFoundException=KeyError),
        close=Mock(),
    )
    monkeypatch.setattr(browser_cleanup.boto3, 'Session', lambda **kwargs: SimpleNamespace(client=lambda name: client))
    if fails:
        with pytest.raises(RuntimeError, match='AWS unavailable'):
            asyncio.run(browser_cleanup.discard_goal_browser_sessions(store, goal['id']))
    else:
        asyncio.run(browser_cleanup.discard_goal_browser_sessions(store, goal['id']))
    client.stop_browser_session.assert_called_once_with(browserIdentifier='aws.browser.v1', sessionId='retained-session')
    client.close.assert_called_once()
    with store._connect() as db:
        assert len(db.execute('SELECT * FROM browser_sessions').fetchall()) == int(fails)
