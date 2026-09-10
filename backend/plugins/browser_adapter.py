"""Session-scoped AgentCore browser operations with observed DOM evidence."""
import asyncio
import base64
import datetime
import secrets
import time
from urllib.parse import urlsplit

import boto3
from bedrock_agentcore.tools.browser_client import BrowserClient
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from playwright.async_api import async_playwright

from app.config import get_settings
from plugins.configuration import setting
from plugins.api_adapters import definition, field


class BrowserAdapter:
    def __init__(self, family_id, store=None, assignment_id=None):
        if setting('MOM_LIFE_PLUGIN_AGENTCORE_BROWSER_FAMILY_ID') != family_id:
            raise RuntimeError('Configure the browser family identity before using AWS access.')
        self.store = store
        self.assignment_id = assignment_id
        self.preserve_session = False
        if store:
            with store._connect() as db:
                db.execute("CREATE TABLE IF NOT EXISTS browser_sessions (assignment_id TEXT PRIMARY KEY REFERENCES goal_assignments(id) ON DELETE CASCADE, session_id TEXT NOT NULL, expires_at REAL NOT NULL)")
        config = get_settings()
        self.client = BrowserClient(config.strands_region)
        self.aws_session = None
        if config.aws_profile and hasattr(self.client, 'data_plane_client'):
            self.aws_session = boto3.Session(profile_name=config.aws_profile, region_name=config.strands_region)
            for attribute, service in (
                ('control_plane_client', 'bedrock-agentcore-control'),
                ('data_plane_client', 'bedrock-agentcore'),
            ):
                previous = getattr(self.client, attribute, None)
                if previous and hasattr(previous, 'close'):
                    previous.close()
                setattr(self.client, attribute, self.aws_session.client(service))
        self.playwright = None
        self.browser = None
        self.page = None
        self.session_id = None

    def directory(self):
        return [definition('inspect_page','Read the current page URL, title and accessible DOM.'),
                definition('navigate','Navigate to an explicitly requested HTTPS website.',{'url':field('url','HTTPS website URL')},True),
                definition('click','Click exactly one observed element by role and accessible name.',{'role':field('role','Observed ARIA role'),'name':field('name','Exact observed accessible name')},True),
                definition('fill','Fill exactly one observed field by label.',{'label':field('label','Exact observed label'),'text':field('text','Value to enter')},True)]

    async def validate(self):
        # Listing verifies the configured IAM identity without starting a session.
        config = get_settings()
        session = boto3.Session(profile_name=config.aws_profile or None,region_name=config.strands_region)
        client = session.client('bedrock-agentcore')
        try:
            await asyncio.to_thread(client.list_browser_sessions,browserIdentifier='aws.browser.v1',maxResults=1)
        finally:
            client.close()

    async def start(self):
        if self.page:
            return
        try:
            saved = None
            if self.store and self.assignment_id:
                with self.store._connect() as db:
                    saved = db.execute("SELECT * FROM browser_sessions WHERE assignment_id=?",(self.assignment_id,)).fetchone()
            if saved:
                if saved['expires_at'] <= time.time():
                    raise ValueError('The managed browser session expired. Revise the task to inspect and prepare a new session.')
                self.session_id = saved['session_id']
                self.client._identifier = 'aws.browser.v1'
                self.client._session_id = self.session_id
            else:
                self.session_id = await asyncio.to_thread(self.client.start,session_timeout_seconds=900)
                if self.store and self.assignment_id:
                    with self.store._connect() as db:
                        db.execute("INSERT INTO browser_sessions VALUES (?,?,?)",(self.assignment_id,self.session_id,time.time()+900))
            url,headers = await asyncio.to_thread(self._automation_stream)
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(url,headers=headers)
            if not self.browser.contexts or not self.browser.contexts[0].pages:
                raise RuntimeError('AgentCore returned no browser page.')
            self.page = self.browser.contexts[0].pages[0]
            self.page.set_default_timeout(10000)
        except BaseException:
            await self.close()
            raise

    def _automation_stream(self):
        if not self.aws_session:
            return self.client.generate_ws_headers()
        endpoint = self.client.data_plane_client.meta.endpoint_url
        host = endpoint.removeprefix('https://').rstrip('/')
        path = f'/browser-streams/{self.client.identifier}/sessions/{self.client.session_id}/automation'
        credentials = self.aws_session.get_credentials()
        if not credentials:
            raise RuntimeError('The configured AWS profile has no credentials.')
        request = AWSRequest(
            method='GET',
            url=f'https://{host}{path}',
            headers={'host':host,'x-amz-date':datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%SZ')},
        )
        frozen = credentials.get_frozen_credentials()
        SigV4Auth(frozen,'bedrock-agentcore',get_settings().strands_region).add_auth(request)
        headers = {
            'Host':host,
            'X-Amz-Date':request.headers['x-amz-date'],
            'Authorization':request.headers['Authorization'],
            'Upgrade':'websocket',
            'Connection':'Upgrade',
            'Sec-WebSocket-Version':'13',
            'Sec-WebSocket-Key':base64.b64encode(secrets.token_bytes(16)).decode(),
        }
        if frozen.token:
            headers['X-Amz-Security-Token'] = frozen.token
        return f'wss://{host}{path}', headers

    async def call(self,name,arguments):
        methods = {item['name']:item for item in self.directory()}
        if name not in methods or set(arguments) != set(methods[name]['inputSchema']['json']['required']):
            raise ValueError('Use an exact browser capability and its documented arguments.')
        await self.start()
        if name == 'navigate':
            url = urlsplit(arguments['url'])
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise ValueError('A public HTTPS URL without embedded credentials is required.')
            await self.page.goto(arguments['url'],wait_until='domcontentloaded')
        elif name == 'click':
            target = self.page.get_by_role(arguments['role'],name=arguments['name'],exact=True)
            if await target.count() != 1:
                raise ValueError('The observed element is absent or ambiguous. Inspect the page again.')
            await target.click()
        elif name == 'fill':
            target = self.page.get_by_label(arguments['label'],exact=True)
            if await target.count() != 1:
                raise ValueError('The observed field is absent or ambiguous. Inspect the page again.')
            await target.fill(arguments['text'])
        return {'status':'success','session_id':self.session_id,'url':self.page.url,'title':await self.page.title(),'snapshot':await self.page.locator('body').aria_snapshot()}

    async def close(self):
        try:
            if self.playwright:
                await self.playwright.stop()
        finally:
            self.playwright = None
            self.browser = self.page = None
            try:
                if self.session_id and not self.preserve_session:
                    await asyncio.to_thread(self.client.stop)
                    if self.store and self.assignment_id:
                        with self.store._connect() as db:
                            db.execute("DELETE FROM browser_sessions WHERE assignment_id=?",(self.assignment_id,))
                    self.session_id = None
            finally:
                for attribute in ('control_plane_client', 'data_plane_client'):
                    client = getattr(self.client, attribute, None)
                    if client and hasattr(client, 'close'):
                        client.close()
