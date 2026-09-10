from app.task_store import TaskStore


def test_calendar_preferences_are_family_scoped(tmp_path):
    store = TaskStore(tmp_path / 'calendar.db')
    assert store.calendar_preferences('family') == {
        'enabled': True,
        'reminder_method': 'popup',
        'reminder_minutes': 30,
    }
    saved = store.save_calendar_preferences('family', False, 'email', 60)
    assert saved == {'enabled': False, 'reminder_method': 'email', 'reminder_minutes': 60}
    assert store.calendar_preferences('other')['reminder_method'] == 'popup'
