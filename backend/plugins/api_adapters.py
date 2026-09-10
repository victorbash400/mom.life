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
        if plugin_id not in {'whatsapp','google-classroom','fitbit','withings'}:
            raise RuntimeError('This provider requires the adapter setup described in docs/family-plugins.md.')

    def directory(self):
        if self.plugin_id == 'google-classroom':
            course = {'course_id':field('course_id','Google Classroom course ID')}
            return [definition('list_courses','Read active courses for the signed-in student.'),
                    definition('list_coursework','Read assignments and due dates for a course.',course),
                    definition('list_announcements','Read announcements for a course.',course)]
        if self.plugin_id == 'fitbit':
            date = {'date':field('date','Date in YYYY-MM-DD format')}
            return [definition('read_profile','Read the authorized Fitbit profile.'),
                    definition('read_daily_activity','Read a daily Fitbit activity summary.',date),
                    definition('read_sleep','Read a daily Fitbit sleep summary.',date)]
        if self.plugin_id == 'withings':
            date = {'date':field('date','Date in YYYY-MM-DD format')}
            return [definition('read_measurements','Read authorized Withings body measurements.'),
                    definition('read_daily_activity','Read a daily Withings activity summary.',date),
                    definition('read_sleep','Read a daily Withings sleep summary.',date)]
        if not setting(self.prefix+'_PHONE_NUMBER_ID') or not setting(self.prefix+'_API_VERSION'):
            raise RuntimeError('Configure the WhatsApp business phone number ID and supported Graph API version.')
        return [definition('send_text','Send a requested WhatsApp Business reply within the permitted customer-service window.',{'to':field('to','Recipient international phone number'),'text':field('text','Exact requested message')},True)]

    async def call(self, name, arguments):
        specs = {item['name']:item for item in self.directory()}
        if name not in specs:
            raise ValueError('Unknown adapter capability.')
        required = specs[name]['inputSchema']['json']['required']
        if set(arguments) != set(required) or any(not isinstance(v,str) or not v.strip() for v in arguments.values()):
            raise ValueError('Supply exactly the documented non-empty string arguments.')
        method, body, form = 'GET', None, None
        headers = {'Authorization':f'Bearer {self.token}'}
        if self.plugin_id == 'google-classroom':
            paths = {'list_courses':'/v1/courses?courseStates=ACTIVE',
                     'list_coursework':f"/v1/courses/{arguments.get('course_id','')}/courseWork?courseWorkStates=PUBLISHED&orderBy=dueDate%20desc",
                     'list_announcements':f"/v1/courses/{arguments.get('course_id','')}/announcements?announcementStates=PUBLISHED&orderBy=updateTime%20desc"}
            url = 'https://classroom.googleapis.com'+paths[name]
        elif self.plugin_id == 'fitbit':
            if 'date' in arguments and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',arguments['date']):
                raise ValueError('Date must use YYYY-MM-DD.')
            paths = {'read_profile':'/1/user/-/profile.json',
                     'read_daily_activity':f"/1/user/-/activities/date/{arguments.get('date','')}.json",
                     'read_sleep':f"/1.2/user/-/sleep/date/{arguments.get('date','')}.json"}
            url = 'https://api.fitbit.com'+paths[name]
        elif self.plugin_id == 'withings':
            if 'date' in arguments and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',arguments['date']):
                raise ValueError('Date must use YYYY-MM-DD.')
            method = 'POST'
            url = 'https://wbsapi.withings.net/' + {'read_measurements':'measure','read_daily_activity':'v2/measure','read_sleep':'v2/sleep'}[name]
            form = {'action':{'read_measurements':'getmeas','read_daily_activity':'getactivity','read_sleep':'getsummary'}[name]}
            if 'date' in arguments:
                from datetime import datetime, timezone
                start = datetime.strptime(arguments['date'],'%Y-%m-%d').replace(tzinfo=timezone.utc)
                form |= {'startdateymd':arguments['date'],'enddateymd':arguments['date'],'startdate':str(int(start.timestamp())),'enddate':str(int(start.timestamp())+86399)}
        else:
            phone = setting(self.prefix+'_PHONE_NUMBER_ID')
            version = setting(self.prefix+'_API_VERSION')
            if not phone.isdigit() or not re.fullmatch(r'v\d+\.\d+',version):
                raise ValueError('Invalid WhatsApp API version or business phone ID.')
            url = f'https://graph.facebook.com/{version}/{phone}/messages'
            method,body = 'POST',{'messaging_product':'whatsapp','to':arguments['to'],'type':'text','text':{'body':arguments['text']}}
        async with httpx.AsyncClient(timeout=20,follow_redirects=False,transport=self.transport) as client:
            response = await client.request(method,url,headers=headers,json=body,data=form)
            response.raise_for_status()
            data = response.json()
            if self.plugin_id == 'withings' and data.get('status') != 0:
                raise ValueError('Withings rejected this health-data request.')
            return {'status':'success','http_status':response.status_code,'data':data}

    async def validate(self):
        """Probe access without sending a message or creating a resource."""
        self.directory()
        if self.plugin_id == 'google-classroom':
            return await self.call('list_courses',{})
        if self.plugin_id == 'fitbit':
            return await self.call('read_profile',{})
        if self.plugin_id == 'withings':
            return await self.call('read_measurements',{})
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
