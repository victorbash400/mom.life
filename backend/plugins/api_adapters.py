"""Bounded API capabilities for providers without the required family MCP surface."""
from plugins.configuration import setting
import re

import httpx


def field(name, description):
    return {'type':'string','description':description,'minLength':1}


def definition(name, description, fields=None, write=False):
    properties = fields or {}
    return {'name':name,'description':description,'inputSchema':{'json':{'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}},'requires_approval':write}


class ApiAdapter:
    def __init__(self, plugin_id, family_id, transport=None, token=None):
        self.plugin_id = plugin_id
        self.prefix = 'MOM_LIFE_PLUGIN_' + plugin_id.replace('-','_').upper()
        self.transport = transport
        if not token and setting(self.prefix+'_FAMILY_ID') != family_id:
            raise RuntimeError('Configure the connection family identity before using these credentials.')
        self.token = token or setting(self.prefix+'_TOKEN')
        if not self.token:
            raise RuntimeError('An authorized provider access token is required.')
        if plugin_id not in {'microsoft-family','whatsapp','mychart','amazon-shopping'}:
            raise RuntimeError('This provider requires the adapter setup described in docs/family-plugins.md.')

    def directory(self):
        if self.plugin_id == 'amazon-shopping':
            if not setting(self.prefix+'_PARTNER_TAG') or not setting(self.prefix+'_MARKETPLACE'):
                raise RuntimeError('Configure the approved Associates partner tag and marketplace.')
            return [definition('get_product','Read an Amazon product and review link by known ASIN.',{'asin':field('asin','Verified product ASIN')})]
        if self.plugin_id == 'microsoft-family':
            return [definition('list_events','Read the signed-in family calendar.'),definition('list_task_lists','Read Microsoft To Do lists.'),
                    definition('list_messages','Read recent Outlook mail.'),
                    definition('create_draft','Create an Outlook draft for Mom to review.',{'subject':field('subject','Subject'),'body':field('body','Plain text body')},True)]
        if self.plugin_id == 'mychart':
            if not setting(self.prefix+'_URL') or not setting(self.prefix+'_PATIENT_ID'):
                raise RuntimeError('Configure the provider FHIR base URL and authorized patient ID.')
            return [definition('read_patient','Read the patient selected during SMART authorization.'),
                    definition('read_observations','Read observations for the authorized patient.'),
                    definition('read_care_plans','Read existing clinician care plans for the authorized patient.')]
        if not setting(self.prefix+'_PHONE_NUMBER_ID') or not setting(self.prefix+'_API_VERSION'):
            raise RuntimeError('Configure the WhatsApp business phone number ID and supported Graph API version.')
        return [definition('send_text','Send an approved WhatsApp Business reply within the permitted customer-service window.',{'to':field('to','Recipient international phone number'),'text':field('text','Exact approved message')},True)]

    async def call(self, name, arguments):
        specs = {item['name']:item for item in self.directory()}
        if name not in specs:
            raise ValueError('Unknown adapter capability.')
        required = specs[name]['inputSchema']['json']['required']
        if set(arguments) != set(required) or any(not isinstance(v,str) or not v.strip() for v in arguments.values()):
            raise ValueError('Supply exactly the documented non-empty string arguments.')
        method, body = 'GET', None
        headers = {'Authorization':f'Bearer {self.token}'}
        if self.plugin_id == 'amazon-shopping':
            if not re.fullmatch(r'[A-Z0-9]{10}',arguments['asin']):
                raise ValueError('A valid ASIN is required.')
            marketplace = setting(self.prefix+'_MARKETPLACE')
            url = 'https://creatorsapi.amazon/catalog/v1/getItems'
            method,body = 'POST',{'itemIds':[arguments['asin']],'itemIdType':'ASIN','marketplace':marketplace,'partnerTag':setting(self.prefix+'_PARTNER_TAG'),'resources':['itemInfo.title','itemInfo.features','images.primary.small']}
            headers['x-marketplace'] = marketplace
        elif self.plugin_id == 'microsoft-family':
            paths = {'list_events':'/me/events?$top=25','list_task_lists':'/me/todo/lists','list_messages':'/me/messages?$top=25','create_draft':'/me/messages'}
            url = 'https://graph.microsoft.com/v1.0'+paths[name]
            if name == 'create_draft':
                method,body = 'POST',{'subject':arguments['subject'],'body':{'contentType':'Text','content':arguments['body']}}
        elif self.plugin_id == 'mychart':
            base = setting(self.prefix+'_URL').rstrip('/')
            patient = setting(self.prefix+'_PATIENT_ID')
            if not re.fullmatch(r'[A-Za-z0-9.\-]+',patient) or not base.startswith('https://'):
                raise ValueError('Invalid FHIR patient identity or provider URL.')
            path = {'read_patient':f'/Patient/{patient}','read_observations':f'/Observation?patient={patient}&_count=25','read_care_plans':f'/CarePlan?patient={patient}&_count=25'}[name]
            url = base+path
        else:
            phone = setting(self.prefix+'_PHONE_NUMBER_ID')
            version = setting(self.prefix+'_API_VERSION')
            if not phone.isdigit() or not re.fullmatch(r'v\d+\.\d+',version):
                raise ValueError('Invalid WhatsApp API version or business phone ID.')
            url = f'https://graph.facebook.com/{version}/{phone}/messages'
            method,body = 'POST',{'messaging_product':'whatsapp','to':arguments['to'],'type':'text','text':{'body':arguments['text']}}
        async with httpx.AsyncClient(timeout=20,follow_redirects=False,transport=self.transport) as client:
            response = await client.request(method,url,headers=headers,json=body)
            response.raise_for_status()
            return {'status':'success','http_status':response.status_code,'data':response.json()}

    async def validate(self):
        """Probe access without sending a message or creating a resource."""
        self.directory()
        if self.plugin_id == 'microsoft-family':
            return await self.call('list_task_lists',{})
        if self.plugin_id == 'mychart':
            return await self.call('read_patient',{})
        if self.plugin_id == 'amazon-shopping':
            asin = setting(self.prefix+'_VALIDATION_ASIN')
            if not asin:
                raise ValueError('Set the validation ASIN to a real product you want this connection to read.')
            result = await self.call('get_product',{'asin':asin})
            if not result['data'].get('itemsResult',{}).get('items'):
                raise ValueError('The catalog returned no product. Check the ASIN and catalog permissions.')
            return result
        phone = setting(self.prefix+'_PHONE_NUMBER_ID')
        version = setting(self.prefix+'_API_VERSION')
        if not phone.isdigit() or not re.fullmatch(r'v\d+\.\d+',version):
            raise ValueError('Invalid WhatsApp API version or business phone ID.')
        async with httpx.AsyncClient(timeout=20,follow_redirects=False,transport=self.transport) as client:
            response = await client.get(f'https://graph.facebook.com/{version}/{phone}',params={'fields':'id,display_phone_number,verified_name'},headers={'Authorization':f'Bearer {self.token}'})
            response.raise_for_status()
            if response.json().get('id') != phone:
                raise ValueError('The authorized business phone does not match the configured connection.')
            return {'status':'success','data':response.json()}
