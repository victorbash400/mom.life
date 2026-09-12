import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app import main
from app.task_store import TaskStore


def test_startup_repairs_existing_schema_before_serving(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / 'existing.db')
    store.update_security_settings('family', True, 'important', 'Keep this instruction')
    with store._connect() as connection:
        connection.execute('DROP TABLE security_policy')
    monkeypatch.setattr(main, 'task_store', store)
    for name in ('automations', 'intake_agent', 'security_agent', 'education_agent', 'goal_tasks'):
        monkeypatch.setattr(main, name, SimpleNamespace(
            recover=AsyncMock(), shutdown=AsyncMock(), start_listener=Mock(),
        ))

    async def verify():
        for _ in range(2):
            async with main.lifespan(main.app):
                settings = store.security_settings('family')
                assert settings['instructions'] == 'Keep this instruction'
                assert settings['sources'] == []

    asyncio.run(verify())


def test_schema_failure_prevents_serving(monkeypatch):
    def fail():
        raise RuntimeError('Database migration failed')

    monkeypatch.setattr(main, 'task_store', SimpleNamespace(initialize=fail))

    async def verify():
        with pytest.raises(RuntimeError, match='Database migration failed'):
            async with main.lifespan(main.app):
                raise AssertionError('Startup served requests before migration succeeded')

    asyncio.run(verify())
