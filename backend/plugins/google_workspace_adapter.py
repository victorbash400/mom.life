"""Bounded Google Workspace tools backed by the official REST APIs."""
import base64
from datetime import datetime, timezone
from email.message import EmailMessage

import httpx

from .api_adapters import definition, field


WORKSPACE_NAMESPACES = {'workspace.gmail','workspace.drive','workspace.docs','workspace.calendar'}


class GoogleWorkspaceAdapter:
    def __init__(self, namespace, token, transport=None):
        if namespace not in WORKSPACE_NAMESPACES:
            raise ValueError('Unknown Google Workspace namespace.')
        if not token:
            raise RuntimeError('An authorized Google account is required.')
        self.namespace = namespace
        self.token = token
        self.transport = transport

    def directory(self):
        if self.namespace == 'workspace.gmail':
            return [
                definition('search_threads','Search Gmail threads.',{'query':field('query','Gmail search query')}),
                definition('get_message','Read one Gmail message.',{'message_id':field('message_id','Gmail message ID')}),
                definition('create_draft','Create an email draft for Mom to review.',{'to':field('to','Recipient email address'),'subject':field('subject','Subject'),'body':field('body','Plain text body')},True),
            ]
        if self.namespace == 'workspace.drive':
            return [
                definition('search_files','Search Google Drive.',{'query':field('query','Words to find in file content')}),
                definition('get_file_metadata','Read Google Drive file metadata.',{'file_id':field('file_id','Google Drive file ID')}),
            ]
        if self.namespace == 'workspace.docs':
            return [
                definition('read_doc','Read a Google document.',{'document_id':field('document_id','Google Docs document ID')}),
                definition('append_text','Append text to a Google document.',{'document_id':field('document_id','Google Docs document ID'),'text':field('text','Text to append')},True),
            ]
        return [
            definition('list_events','Read upcoming Google Calendar events.'),
            definition('get_event','Read one Google Calendar event.',{'event_id':field('event_id','Google Calendar event ID')}),
        ]

    async def call(self, name, arguments):
        specs = {item['name']:item for item in self.directory()}
        if name not in specs:
            raise ValueError('Unknown Google Workspace capability.')
        required = specs[name]['inputSchema']['json']['required']
        if set(arguments) != set(required) or any(not isinstance(value,str) or not value.strip() for value in arguments.values()):
            raise ValueError('Supply exactly the documented non-empty string arguments.')
        headers = {'Authorization':f'Bearer {self.token}'}
        method, body = 'GET', None
        if self.namespace == 'workspace.gmail':
            if name == 'search_threads':
                url = 'https://gmail.googleapis.com/gmail/v1/users/me/threads'
                params = {'q':arguments['query'],'maxResults':'20'}
            elif name == 'get_message':
                url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{arguments['message_id']}"
                params = {'format':'full'}
            else:
                message = EmailMessage()
                message['To'], message['Subject'] = arguments['to'], arguments['subject']
                message.set_content(arguments['body'])
                raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip('=')
                url, params, method, body = 'https://gmail.googleapis.com/gmail/v1/users/me/drafts', None, 'POST', {'message':{'raw':raw}}
        elif self.namespace == 'workspace.drive':
            if name == 'search_files':
                escaped = arguments['query'].replace('\\','\\\\').replace("'","\\'")
                url = 'https://www.googleapis.com/drive/v3/files'
                params = {'q':f"fullText contains '{escaped}' and trashed = false",'pageSize':'20','fields':'files(id,name,mimeType,modifiedTime,webViewLink)'}
            else:
                url = f"https://www.googleapis.com/drive/v3/files/{arguments['file_id']}"
                params = {'fields':'id,name,mimeType,modifiedTime,webViewLink,owners(displayName,emailAddress)'}
        elif self.namespace == 'workspace.docs':
            url = f"https://docs.googleapis.com/v1/documents/{arguments['document_id']}"
            params = None
            if name == 'append_text':
                async with self._client() as client:
                    document = (await client.get(url,headers=headers)).raise_for_status().json()
                    content = document.get('body',{}).get('content',[])
                    end_index = max((item.get('endIndex',1) for item in content),default=1)
                    response = await client.post(url+':batchUpdate',headers=headers,json={'requests':[{'insertText':{'location':{'index':max(1,end_index-1)},'text':arguments['text']}}]})
                    response.raise_for_status()
                    return {'status':'success','http_status':response.status_code,'data':response.json()}
        else:
            if name == 'list_events':
                url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
                params = {'maxResults':'25','singleEvents':'true','orderBy':'startTime','timeMin':datetime.now(timezone.utc).isoformat()}
            else:
                url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{arguments['event_id']}"
                params = None
        async with self._client() as client:
            response = await client.request(method,url,headers=headers,params=params,json=body)
            response.raise_for_status()
            return {'status':'success','http_status':response.status_code,'data':response.json()}

    async def validate(self):
        probes = {
            'workspace.gmail':('https://gmail.googleapis.com/gmail/v1/users/me/profile',None),
            'workspace.drive':('https://www.googleapis.com/drive/v3/files',{'pageSize':'1','fields':'files(id)'}),
            'workspace.docs':('https://www.googleapis.com/drive/v3/files',{'pageSize':'1','q':"mimeType = 'application/vnd.google-apps.document'",'fields':'files(id)'}),
            'workspace.calendar':('https://www.googleapis.com/calendar/v3/users/me/calendarList',{'maxResults':'1'}),
        }
        url, params = probes[self.namespace]
        async with self._client() as client:
            response = await client.get(url,params=params,headers={'Authorization':f'Bearer {self.token}'})
            response.raise_for_status()
            return {'status':'success','http_status':response.status_code}

    def _client(self):
        return httpx.AsyncClient(timeout=20,follow_redirects=False,transport=self.transport)
