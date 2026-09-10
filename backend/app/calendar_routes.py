from fastapi import APIRouter, HTTPException

from app.schemas import CalendarPreferencesWrite
from plugins.google_workspace_adapter import GoogleWorkspaceAdapter
from plugins.namespaces import WORKSPACE_PERMISSION_IDS
from plugins.oauth import OAuthConnections


router = APIRouter()


def services():
    from app.main import task_store
    return task_store


@router.get('/api/calendar')
async def calendar(family_id: str):
    store = services()
    preferences = store.calendar_preferences(family_id)
    if 'google-workspace' not in store.installed_plugins(family_id):
        return {'connected': False, 'writable': False, 'events': [], 'preferences': preferences}
    permissions = store.permissions(family_id, 'google-workspace')
    if not permissions.get(WORKSPACE_PERMISSION_IDS['workspace.calendar'], True):
        return {'connected': False, 'writable': False, 'events': [], 'preferences': preferences}
    oauth = OAuthConnections(store)
    token = await oauth.access_token(family_id, 'google-workspace')
    if not token:
        return {'connected': False, 'writable': False, 'events': [], 'preferences': preferences}
    try:
        result = await GoogleWorkspaceAdapter('workspace.calendar', token).call('list_events', {})
    except Exception as error:
        raise HTTPException(400, str(error)) from error
    events = [
        {
            'id': event['id'],
            'title': event.get('summary') or 'Untitled event',
            'start': event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
            'end': event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
            'all_day': 'date' in event.get('start', {}),
            'location': event.get('location', ''),
            'url': event.get('htmlLink', ''),
        }
        for event in result['data'].get('items', [])
        if event.get('id') and (event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'))
    ]
    return {'connected': True, 'writable': oauth.has_required_scopes(family_id, 'google-workspace'), 'events': events, 'preferences': preferences}


@router.patch('/api/calendar/preferences')
def update_preferences(body: CalendarPreferencesWrite, family_id: str):
    return services().save_calendar_preferences(family_id, body.enabled, body.reminder_method, body.reminder_minutes)
