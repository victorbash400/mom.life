"""Opt-in real schedule and Strands check: MOM_LIFE_TEST_AWS=1."""
import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest

from app.auth import families, hasher
from app.automation_manager import AutomationManager
from app.config import get_settings
from app.goal_tasks import GoalTaskManager
from app.task_store import TaskStore


@pytest.mark.skipif(os.environ.get('MOM_LIFE_TEST_AWS') != '1', reason='Opt-in AWS integration')
def test_real_scheduler_wake_and_agent_notification():
    settings = get_settings()
    assert settings.automation_target_arn and settings.automation_role_arn
    family_id = families.register('Automation Test', f'automation-{uuid4()}@example.com', hasher.hash(str(uuid4())))
    tasks = TaskStore(settings.database_url)
    goals = GoalTaskManager(tasks)
    manager = AutomationManager(tasks, goals)
    rule = None

    async def verify():
        nonlocal rule
        parent = tasks.create(family_id, 'all', 'Verify this scheduled infrastructure check and its in-app notification once.')
        tasks.set_goal_state(parent['id'], run_state='waiting')
        async with await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True) as events:
            await events.execute('LISTEN mom_life_automations')
            when = datetime.now(UTC) + timedelta(seconds=45)
            rule = await manager.create(family_id, parent['id'],
                'This is an infrastructure test. The check is necessary when this scheduled wake arrives. '
                'Send exactly one in-app notification reading Automation test completed using notify_mom. '
                'Produce output named exactly "Notification receipt" with the observed delivery receipt. '
                'No external communication, research, health data, or family decision is needed.',
                'time', f"at({when.strftime('%Y-%m-%dT%H:%M:%S')})")
            assert rule['enabled'], rule['failure']

            async def completed():
                async for event in events.notifies():
                    if event.payload != parent['id']:
                        continue
                    await manager.recover()
                    current = manager.store.get(family_id, rule['id'])
                    if current['last_checked_at']:
                        assert not current['failure'], current['failure']
                        return current
                    with tasks._connect() as db:
                        failed = db.execute("SELECT failure FROM automation_wakes WHERE automation_id=? AND state='failed'", (rule['id'],)).fetchone()
                    assert not failed, failed['failure'] if failed else ''

            checked = await asyncio.wait_for(completed(), 240)
            assert checked['scheduler_state'] == 'completed' and not checked['enabled']
            notifications = manager.store.notifications(family_id)
            assert len(notifications) == 1
            assert notifications[0]['message'] == 'Automation test completed'
            with tasks._connect() as db:
                wakes = db.execute('SELECT state FROM automation_wakes WHERE automation_id=?', (rule['id'],)).fetchall()
            assert [wake['state'] for wake in wakes] == ['completed']

    async def cleanup():
        if rule:
            await manager.delete(family_id, rule['id'])
        await manager.shutdown()
        await goals.shutdown()

    async def exercise():
        try:
            await verify()
        finally:
            await cleanup()

    try:
        asyncio.run(exercise())
    finally:
        with tasks._connect() as db:
            for table in ('family_tasks', 'family_skills', 'plugin_permissions', 'accounts'):
                db.execute(f'DELETE FROM {table} WHERE family_id=?', (family_id,))
            db.execute('DELETE FROM families WHERE id=?', (family_id,))
