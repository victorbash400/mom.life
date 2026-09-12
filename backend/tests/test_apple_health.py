import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.task_store import TaskStore
from app.automation_store import AutomationStore
from plugins.apple_health_adapter import AppleHealthAdapter


def sample(**changes):
    values={
        'external_id':'healthkit-1',
        'child_id':'child',
        'sample_type':'step_count',
        'start_at':datetime(2026,9,9,8,tzinfo=timezone.utc),
        'end_at':datetime(2026,9,9,9,tzinfo=timezone.utc),
        'value':1200,
        'unit':'count',
        'source':'iPhone',
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_apple_health_tools_read_only_the_family_child_and_date(tmp_path):
    store=TaskStore(tmp_path/'health.db')
    adapter=AppleHealthAdapter('family',store)
    adapter.sync([sample(),sample(external_id='heart',sample_type='heart_rate',value=82,unit='count/min')],[])
    activity=asyncio.run(adapter.call('read_daily_activity',{'child_id':'child','date':'2026-09-09'}))
    assert [item['sample_type'] for item in activity['data']['samples']]==['step_count']
    assert asyncio.run(adapter.call('read_daily_activity',{'child_id':'other','date':'2026-09-09'}))['data']['samples']==[]
    assert asyncio.run(adapter.validate())['data']['sample_count']==2


def test_apple_health_sync_replaces_changes_and_applies_deletions(tmp_path):
    store=TaskStore(tmp_path/'health.db')
    adapter=AppleHealthAdapter('family',store)
    adapter.sync([sample()],[])
    adapter.sync([sample(value=2400)],[])
    result=asyncio.run(adapter.call('read_daily_activity',{'child_id':'child','date':'2026-09-09'}))
    assert result['data']['samples'][0]['value']==2400
    assert adapter.sync([],['healthkit-1'])['data']['sample_count']==0
    with pytest.raises(ValueError,match='normalized unit'):
        adapter.sync([sample(unit='steps')],[])


def test_identical_health_sync_does_not_wake_an_automation_twice(tmp_path):
    store=TaskStore(tmp_path/'health.db')
    goal=store.create('family','child','Monitor sleep.')
    automations=AutomationStore(store)
    automation=automations.create('family',goal['id'],'Check sleep.','health',enabled=True,scheduler_state='ready')
    adapter=AppleHealthAdapter('family',store)

    adapter.sync([sample()],[])
    first=automations.next_wake('family',goal['id'])
    assert first is not None
    adapter.sync([sample()],[])
    with store._connect() as db:
        wakes=db.execute('SELECT COUNT(*) AS count FROM automation_wakes WHERE automation_id=?',(automation['id'],)).fetchone()
    assert wakes['count']==1

    adapter.sync([sample(value=2400)],[])
    with store._connect() as db:
        rows=db.execute('SELECT context FROM automation_wakes WHERE automation_id=? ORDER BY created_at',(automation['id'],)).fetchall()
    assert len(rows)==2
    assert '2026-09-09' in rows[-1]['context']


def test_companion_sync_requires_session_installation_and_owned_child(tmp_path,monkeypatch,auth_headers):
    from app import auth,main
    store=TaskStore(tmp_path/'health.db')
    monkeypatch.setattr(main,'task_store',store)
    monkeypatch.setattr(auth,'families',SimpleNamespace(child=lambda family,child: {'id':child} if family=='family' and child=='child' else None))
    client=TestClient(main.app)
    payload={'samples':[{
        'external_id':'healthkit-1','child_id':'child','sample_type':'step_count',
        'start_at':'2026-09-09T08:00:00+00:00','end_at':'2026-09-09T09:00:00+00:00',
        'value':1200,'unit':'count','source':'iPhone',
    }]}
    assert client.post('/api/plugins/apple-health/sync',json=payload).status_code==401
    headers=auth_headers('family')
    assert client.post('/api/plugins/apple-health/sync',json=payload,headers=headers).status_code==409
    store.install_plugin('family','apple-health')
    assert client.post('/api/plugins/apple-health/sync',json=payload,headers=headers).json()['data']['sample_count']==1
    payload['samples'][0]['child_id']='other'
    assert client.post('/api/plugins/apple-health/sync',json=payload,headers=headers).status_code==404
