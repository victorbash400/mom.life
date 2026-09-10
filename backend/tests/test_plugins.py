import asyncio
import json

import httpx
import pytest

from app.task_store import TaskStore
from app.plugin_service import PluginService
from plugins.api_adapters import ApiAdapter
from plugins.google_workspace_adapter import GoogleWorkspaceAdapter
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


def test_google_maps_uses_server_key_without_family_binding(tmp_path,monkeypatch):
    monkeypatch.setenv('MOM_LIFE_PLUGIN_GOOGLE_MAPS_TOKEN','maps-key')
    store=TaskStore(tmp_path/'maps.db')
    store.install_plugin('family','google-maps')
    runtime=PluginToolSession(['google-maps'],store,'family')
    assert PluginService.setup_fields('google-maps') == [
        {'name':'MOM_LIFE_PLUGIN_GOOGLE_MAPS_TOKEN','configured':True},
    ]


def test_workspace_permissions_are_scoped_to_each_service(tmp_path):
    store=TaskStore(tmp_path/'workspace.db')
    store.install_plugin('family','google-workspace')
    store.set_permission('family','google-workspace','google-workspace.0',False)
    runtime=PluginToolSession(['google-workspace'],store,'family')
    with pytest.raises(RuntimeError,match='service is disabled'):
        runtime.require_access('workspace.gmail')
    runtime.require_access('workspace.drive')


def test_google_workspace_adapter_keeps_services_bounded():
    requests=[]
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('/profile'):
            return httpx.Response(200,json={'emailAddress':'parent@example.com'})
        if request.url.path.endswith('/drafts'):
            body=json.loads(request.content)
            assert body['message']['raw']
            return httpx.Response(200,json={'id':'draft-1'})
        return httpx.Response(200,json={'files':[]})
    transport=httpx.MockTransport(handler)
    gmail=GoogleWorkspaceAdapter('workspace.gmail','google-token',transport)
    drive=GoogleWorkspaceAdapter('workspace.drive','google-token',transport)
    assert asyncio.run(gmail.validate())['status']=='success'
    assert asyncio.run(gmail.call('create_draft',{'to':'school@example.com','subject':'Trip','body':'Please review'}))['data']['id']=='draft-1'
    assert asyncio.run(drive.call('search_files',{'query':"Noah's report"}))['data']=={'files':[]}
    assert all(request.headers['authorization']=='Bearer google-token' for request in requests)
    with pytest.raises(ValueError,match='Unknown Google Workspace'):
        asyncio.run(gmail.call('send_message',{}))


def test_google_calendar_adapter_reads_and_creates_events():
    requests=[]
    def handler(request):
        requests.append(request)
        if request.method == 'GET':
            return httpx.Response(200,json={'items':[{'id':'event-1','summary':'School trip'}]})
        body=json.loads(request.content)
        assert body['summary']=='School trip'
        assert body['start']['timeZone']=='Africa/Nairobi'
        assert body['reminders']['overrides']==[{'method':'popup','minutes':30}]
        assert 'location' not in body
        return httpx.Response(200,json={'id':'event-2'})
    calendar=GoogleWorkspaceAdapter('workspace.calendar','google-token',httpx.MockTransport(handler))
    assert asyncio.run(calendar.call('list_events',{}))['data']['items'][0]['id']=='event-1'
    result=asyncio.run(calendar.call('create_event',{
        'title':'School trip',
        'start':'2026-09-18T08:00:00+03:00',
        'end':'2026-09-18T15:00:00+03:00',
        'time_zone':'Africa/Nairobi',
        'reminder_method':'popup',
        'reminder_minutes':'30',
    }))
    assert result['data']['id']=='event-2'
    assert [request.method for request in requests]==['GET','POST']


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


def test_google_classroom_adapter_reads_courses_and_coursework(monkeypatch):
    configured(monkeypatch,'google-classroom')
    def handler(request):
        if request.url.path == '/v1/courses':
            assert request.url.params['courseStates'] == 'ACTIVE'
            return httpx.Response(200,json={'courses':[{'id':'math'}]})
        assert request.url.path == '/v1/courses/math/courseWork'
        return httpx.Response(200,json={'courseWork':[{'title':'Fractions'}]})
    adapter=ApiAdapter('google-classroom','family',httpx.MockTransport(handler))
    assert asyncio.run(adapter.validate())['data']['courses'][0]['id']=='math'
    assert asyncio.run(adapter.call('list_coursework',{'course_id':'math'}))['status']=='success'


def test_fitbit_adapter_limits_daily_reads_to_an_explicit_date(monkeypatch):
    configured(monkeypatch,'fitbit')
    def handler(request):
        assert request.url.path == '/1.2/user/-/sleep/date/2026-09-09.json'
        return httpx.Response(200,json={'sleep':[]})
    adapter=ApiAdapter('fitbit','family',httpx.MockTransport(handler))
    assert asyncio.run(adapter.call('read_sleep',{'date':'2026-09-09'}))['data']=={'sleep':[]}
    with pytest.raises(ValueError,match='YYYY-MM-DD'):
        asyncio.run(adapter.call('read_sleep',{'date':'today'}))


def test_withings_adapter_uses_authorized_health_endpoint(monkeypatch):
    configured(monkeypatch,'withings')
    def handler(request):
        assert request.method == 'POST'
        assert request.url.path == '/measure'
        assert 'action=getmeas' in request.content.decode()
        return httpx.Response(200,json={'status':0,'body':{'measuregrps':[]}})
    adapter=ApiAdapter('withings','family',httpx.MockTransport(handler))
    assert asyncio.run(adapter.validate())['data']['status']==0


def test_setup_status_never_exposes_secret_values(monkeypatch):
    configured(monkeypatch,'instacart')
    fields=PluginService.setup_fields('instacart')
    assert all(set(field)=={'name','configured'} for field in fields)
    assert 'test-token' not in json.dumps(fields)
    assert next(field for field in fields if field['name'].endswith('_TOKEN'))['configured']


def test_self_registering_oauth_plugins_do_not_report_server_secret_fields():
    assert PluginService.setup_fields('todoist') == []
    assert PluginService.setup_fields('notion') == []
    assert PluginService.setup_fields('canva') == []


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
