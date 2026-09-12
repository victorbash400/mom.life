"""Opt-in integration test: MOM_LIFE_TEST_POSTGRES=1, using an isolated schema."""
import asyncio
import os
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from app import config
from app.automation_manager import AutomationManager
from app.task_store import TaskStore
from automation_lambda import handler as dispatcher
from tests.test_automations import Goals, Scheduler


@pytest.mark.skipif(os.environ.get('MOM_LIFE_TEST_POSTGRES') != '1', reason='Opt-in PostgreSQL integration')
def test_dispatcher_offline_recovery_and_live_subscription(monkeypatch):
    settings = config.get_settings()
    base = settings.database_url
    schema = 'automation_test_' + uuid4().hex
    with psycopg.connect(base, connect_timeout=10) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    parts = urlsplit(base)
    query = urlencode([*parse_qsl(parts.query), ('options', '-c search_path=' + schema)], quote_via=quote)
    database = urlunsplit(parts._replace(query=query))
    monkeypatch.setattr(config, 'get_settings', lambda: settings.model_copy(update={'database_url': database}))
    monkeypatch.setenv('DATABASE_SECRET_ARN', 'integration-test')
    monkeypatch.setenv('SECRETS_ENDPOINT_URL', 'https://integration-test')

    class Secret:
        def get_secret_value(self, **arguments):
            return {'SecretString': database}

    monkeypatch.setattr(dispatcher.boto3, 'client', lambda name, **arguments: Secret())

    async def verify():
        tasks = TaskStore(database)
        tasks.initialize()
        parent = tasks.create('fixture', 'all', 'Verify saved automation checks')
        tasks.set_goal_state(parent['id'], run_state='waiting')
        manager = AutomationManager(tasks, Goals(tasks), Scheduler())
        try:
            item = await manager.create('fixture', parent['id'], 'Check the supplied event once.', 'incoming')
            event = {'automation_id': item['id'], 'version': item['version'], 'scheduled_at': 'offline'}
            assert dispatcher.handler(event, None)['status'] == 'saved'
            assert dispatcher.handler(event, None)['status'] == 'duplicate'
            ready, completed = asyncio.Event(), asyncio.Event()
            recover = manager.recover

            async def subscribed_recovery():
                await recover()
                ready.set()

            def publish(family_id):
                with tasks._connect() as db:
                    wake = db.execute('SELECT state FROM automation_wakes WHERE id=?',
                                      (f"{item['id']}:{item['version']}:{event['scheduled_at']}",)).fetchone()
                if wake and wake['state'] == 'completed':
                    completed.set()

            manager.recover = subscribed_recovery
            manager.publish = publish
            manager.start_listener()
            await asyncio.wait_for(ready.wait(), 30)
            assert manager.events_connected
            await asyncio.wait_for(completed.wait(), 30)
            completed.clear()
            event['scheduled_at'] = 'online'
            assert await asyncio.to_thread(dispatcher.handler, event, None) == {'status': 'saved'}
            await asyncio.wait_for(completed.wait(), 30)
            assert len(manager.goals.started) == 2
            await manager.update('fixture', item['id'], enabled=False)
            assert dispatcher.handler(event, None)['status'] == 'ignored'
        finally:
            await manager.shutdown()

    try:
        asyncio.run(verify())
    finally:
        with psycopg.connect(base, connect_timeout=10) as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
