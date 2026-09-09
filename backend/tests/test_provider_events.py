import hashlib
import hmac
import json
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.task_store import TaskStore
from app.provider_events import ProviderEvents


def test_signed_event_wakes_only_exact_wait_and_deduplicates(tmp_path,monkeypatch):
    from app import main
    store=TaskStore(tmp_path/'events.db')
    goal=store.create('family','child','Wait for caregiver reply')
    identity=store.create_assignment(goal['id'],{'title':'Reply','instruction':'Wait','expected_outputs':['Reply']})
    store.install_plugin('family','whatsapp')
    ledger=ProviderEvents(store)
    ledger.wait('family',goal['id'],identity,'whatsapp','254700000000')
    store.set_assignment(identity,status='blocked')
    manager=AsyncMock()
    monkeypatch.setattr(main,'task_store',store)
    monkeypatch.setattr(main,'goal_tasks',manager)
    monkeypatch.setenv('MOM_LIFE_PLUGIN_WHATSAPP_APP_SECRET','secret')
    monkeypatch.setenv('MOM_LIFE_PLUGIN_WHATSAPP_FAMILY_ID','family')
    monkeypatch.setenv('MOM_LIFE_PLUGIN_WHATSAPP_PHONE_NUMBER_ID','123')
    payload={'entry':[{'changes':[{'value':{'metadata':{'phone_number_id':'123'},'messages':[{'id':'message-1','from':'254700000000','text':{'body':'Confirmed'}}]}}]}]}
    raw=json.dumps(payload).encode()
    client=TestClient(main.app)
    assert client.post('/api/webhooks/whatsapp',content=raw).status_code==403
    manager.start.assert_not_awaited()
    headers={'x-hub-signature-256':'sha256='+hmac.new(b'secret',raw,hashlib.sha256).hexdigest()}
    assert client.post('/api/webhooks/whatsapp',content=raw,headers=headers).status_code==200
    assert store.assignment(identity)['status']=='queued'
    manager.start.assert_awaited_once_with('family',goal['id'])
    assert client.post('/api/webhooks/whatsapp',content=raw,headers=headers).status_code==200
    assert manager.start.await_count==1
    assert store.get('family',goal['id'])['activities'][0]['evidence']['payload']['text']['body']=='Confirmed'


def test_paused_goal_keeps_reply_without_automatic_execution(tmp_path):
    store=TaskStore(tmp_path/'paused.db')
    goal=store.create('family','child','Wait')
    identity=store.create_assignment(goal['id'],{'title':'Reply','instruction':'Wait','expected_outputs':['Reply']})
    store.install_plugin('family','whatsapp')
    ledger=ProviderEvents(store)
    ledger.wait('family',goal['id'],identity,'whatsapp','sender')
    store.set_assignment(identity,status='blocked')
    store.update(goal['id'],'paused')
    assert ledger.receive('family','whatsapp','event','sender',{'text':'Confirmed'})==[]
    snapshot=store.get('family',goal['id'])
    assert snapshot['status']=='paused'
    assert snapshot['assignments'][0]['status']=='queued'
    assert snapshot['activities'][0]['evidence']['payload']['text']=='Confirmed'


def test_plan_revision_invalidates_old_event_wait(tmp_path):
    from agents.goal_planner import AssignmentPlan
    store=TaskStore(tmp_path/'revised.db')
    goal=store.create('family','child','Wait')
    identity=store.create_assignment(goal['id'],{'title':'Reply','instruction':'Wait','expected_outputs':['Reply']})
    store.install_plugin('family','whatsapp')
    ledger=ProviderEvents(store)
    ledger.wait('family',goal['id'],identity,'whatsapp','sender')
    store.set_assignment(identity,status='blocked')
    store.apply_plan('family',goal['id'],[AssignmentPlan(action='cancel',task_id=identity)])
    assert ledger.receive('family','whatsapp','event','sender',{'text':'Confirmed'})==[]
    assert store.assignment(identity)['status']=='cancelled'


def test_unmatched_whatsapp_message_enters_intake_once(tmp_path,monkeypatch):
    from app import main
    store=TaskStore(tmp_path/'unmatched.db')
    store.install_plugin('family','whatsapp')
    goal_manager=AsyncMock()
    intake_manager=AsyncMock()
    monkeypatch.setattr(main,'task_store',store)
    monkeypatch.setattr(main,'goal_tasks',goal_manager)
    monkeypatch.setattr(main,'intake_agent',intake_manager)
    monkeypatch.setenv('MOM_LIFE_PLUGIN_WHATSAPP_APP_SECRET','secret')
    monkeypatch.setenv('MOM_LIFE_PLUGIN_WHATSAPP_FAMILY_ID','family')
    monkeypatch.setenv('MOM_LIFE_PLUGIN_WHATSAPP_PHONE_NUMBER_ID','123')
    payload={'entry':[{'changes':[{'value':{'metadata':{'phone_number_id':'123'},'messages':[{'id':'message-new','from':'254700000000','text':{'body':'School closes early Friday'}}]}}]}]}
    raw=json.dumps(payload).encode()
    headers={'x-hub-signature-256':'sha256='+hmac.new(b'secret',raw,hashlib.sha256).hexdigest()}
    client=TestClient(main.app)
    assert client.post('/api/webhooks/whatsapp',content=raw,headers=headers).status_code==200
    assert client.post('/api/webhooks/whatsapp',content=raw,headers=headers).status_code==200
    intake_manager.receive.assert_awaited_once_with(
        'family','whatsapp','message-new',correlation='254700000000',sender='254700000000',
        content='School closes early Friday',payload=payload['entry'][0]['changes'][0]['value']['messages'][0],
    )
    goal_manager.start.assert_not_awaited()
