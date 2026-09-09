import hashlib
import hmac
import json

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import PlainTextResponse

from plugins.configuration import setting
from app.provider_events import ProviderEvents
from app.event_stream import family_events

router=APIRouter()


@router.get('/api/webhooks/whatsapp')
def verify(request: Request):
    expected=setting('MOM_LIFE_PLUGIN_WHATSAPP_VERIFY_TOKEN')
    supplied=request.query_params.get('hub.verify_token','')
    if not expected or request.query_params.get('hub.mode')!='subscribe' or not hmac.compare_digest(expected,supplied):
        raise HTTPException(403,'Invalid webhook verification.')
    return PlainTextResponse(request.query_params.get('hub.challenge',''))


@router.post('/api/webhooks/whatsapp')
async def receive(request: Request):
    secret=setting('MOM_LIFE_PLUGIN_WHATSAPP_APP_SECRET')
    if not secret:
        raise HTTPException(503,'WhatsApp webhook is not configured.')
    body=await request.body()
    if len(body)>1_000_000:
        raise HTTPException(413,'Webhook payload is too large.')
    expected='sha256='+hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,request.headers.get('x-hub-signature-256','')):
        raise HTTPException(403,'Invalid webhook signature.')
    try:
        payload=json.loads(body)
    except ValueError as error:
        raise HTTPException(400,'Invalid webhook JSON.') from error
    from app.main import intake_agent,task_store,goal_tasks
    family_id=setting('MOM_LIFE_PLUGIN_WHATSAPP_FAMILY_ID')
    phone_id=setting('MOM_LIFE_PLUGIN_WHATSAPP_PHONE_NUMBER_ID')
    if not family_id or not phone_id:
        raise HTTPException(503,'The business phone family binding is missing.')
    if 'whatsapp' not in task_store.installed_plugins(family_id):
        raise HTTPException(403,'WhatsApp is not installed for this family.')
    ledger=ProviderEvents(task_store)
    wake=[]
    for entry in payload.get('entry',[]):
        for change in entry.get('changes',[]):
            value=change.get('value',{})
            if value.get('metadata',{}).get('phone_number_id')!=phone_id:
                continue
            for message in value.get('messages',[]):
                if not message.get('id') or not message.get('from'):
                    continue
                received=ledger.receive_with_status(family_id,'whatsapp',message['id'],message['from'],message)
                wake.extend(received['goal_ids'])
                if not received['matched'] and not received['duplicate']:
                    content=message.get('text',{}).get('body','') if isinstance(message.get('text'),dict) else ''
                    await intake_agent.receive(
                        family_id,'whatsapp',message['id'],correlation=message['from'],
                        sender=message['from'],content=content,payload=message,
                    )
    for goal_id in set(wake):
        await goal_tasks.start(family_id,goal_id)
        family_events.publish(family_id,{'type':'goals_changed','goal_id':goal_id})
    return {'status':'received'}
