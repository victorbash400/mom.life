import asyncio
from plugins.configuration import setting
from contextlib import ExitStack
from typing import Any

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

from .catalog import plugin_by_id
from .namespaces import namespaces, owner, WORKSPACE_ENDPOINTS, WORKSPACE_PERMISSION_IDS


class PluginToolSession:
    """Load only permitted namespaces and retain their connections for one run."""

    def __init__(self, plugin_ids: list[str], store=None, family_id: str = '') -> None:
        self.plugin_ids = list(dict.fromkeys(namespaces(plugin_ids)))
        self.store = store
        self.family_id = family_id
        self.stack = ExitStack()
        self.assignment_id = None
        self.preserve_browser = False
        self.clients = {}
        self.loaded = {}

    def __enter__(self):
        return self

    async def load(self, plugin_id: str) -> list[dict[str, Any]]:
        if plugin_id not in self.plugin_ids:
            raise ValueError('This namespace is not permitted for the assignment.')
        self.require_access(plugin_id)
        if plugin_id in self.loaded:
            return self.loaded[plugin_id]
        plugin = plugin_by_id(owner(plugin_id))
        simulated = bool(self.store and owner(plugin_id) in self.store.simulator_plugins(self.family_id))
        if simulated:
            if owner(plugin_id) == 'apple-health':
                from plugins.apple_health_adapter import AppleHealthAdapter
                adapter = AppleHealthAdapter(self.family_id,self.store)
            else:
                from plugins.simulator_adapter import SimulatorAdapter
                adapter = SimulatorAdapter(owner(plugin_id),self.family_id,self.store)
            self.clients[plugin_id] = adapter
            self.loaded[plugin_id] = adapter.directory()
            return self.loaded[plugin_id]
        if plugin.transport == 'agentcore':
            from plugins.browser_adapter import BrowserAdapter
            adapter = BrowserAdapter(self.family_id,self.store,self.assignment_id)
            self.clients[plugin_id] = adapter
            self.loaded[plugin_id] = adapter.directory()
            return self.loaded[plugin_id]
        if plugin.transport != 'mcp':
            if owner(plugin_id) == 'apple-health':
                from plugins.apple_health_adapter import AppleHealthAdapter
                adapter = AppleHealthAdapter(self.family_id,self.store)
                self.clients[plugin_id] = adapter
                self.loaded[plugin_id] = adapter.directory()
                return self.loaded[plugin_id]
            if owner(plugin_id) == 'google-workspace':
                from plugins.google_workspace_adapter import GoogleWorkspaceAdapter
                adapter = GoogleWorkspaceAdapter(plugin_id,await self.oauth_token('google-workspace'))
                self.clients[plugin_id] = adapter
                self.loaded[plugin_id] = adapter.directory()
                return self.loaded[plugin_id]
            from plugins.api_adapters import ApiAdapter
            adapter = ApiAdapter(plugin_id, self.family_id, token=await self.oauth_token(plugin_id))
            self.clients[plugin_id] = adapter
            self.loaded[plugin_id] = adapter.directory()
            return self.loaded[plugin_id]
        url = setting(_env_name(plugin_id, 'URL')) or WORKSPACE_ENDPOINTS.get(plugin_id) or plugin.server_url
        oauth_token = await self.oauth_token(owner(plugin_id))
        token = oauth_token or setting(_env_name(owner(plugin_id), 'TOKEN'))
        family_owner = setting(_env_name(owner(plugin_id), 'FAMILY_ID'))
        if plugin_id != 'google-maps' and not oauth_token and family_owner != self.family_id:
            raise RuntimeError('Configure the connection family identity before using these credentials.')
        if not url or not token:
            raise RuntimeError(f'{plugin.name} needs a server URL and authorized access token.')
        if not url.startswith('https://'):
            raise ValueError('Plugin endpoints must use HTTPS.')
        headers = {'X-Goog-Api-Key' if plugin_id == 'google-maps' else 'Authorization': token if plugin_id == 'google-maps' else f'Bearer {token}'}
        client = MCPClient(lambda: streamablehttp_client(url, headers=headers, timeout=15))
        await asyncio.to_thread(self.stack.enter_context, client)
        self.clients[plugin_id] = client
        directory = []
        cursor = None
        while True:
            page = await asyncio.to_thread(client.list_tools_sync, pagination_token=cursor)
            for tool in page:
                spec = tool.tool_spec
                directory.append({'name':spec['name'], 'description':spec.get('description',''), 'inputSchema':spec['inputSchema'], 'requires_approval':False})
            cursor = getattr(page, 'pagination_token', None)
            if not cursor:
                break
        if not directory:
            raise RuntimeError(f'{plugin.name} returned no tools.')
        self.loaded[plugin_id] = directory
        return directory

    async def oauth_token(self,plugin_id):
        if not self.store:
            return None
        from plugins.oauth import OAuthConnections
        return await OAuthConnections(self.store).access_token(self.family_id,plugin_id)

    def require_access(self, plugin_id):
        namespace = plugin_id
        plugin_id = owner(namespace)
        if self.store:
            if plugin_id not in self.store.installed_plugins(self.family_id):
                raise RuntimeError('The plugin has been removed from this family.')
            permissions = self.store.permissions(self.family_id, plugin_id)
            if namespace in WORKSPACE_PERMISSION_IDS:
                if not permissions.get(WORKSPACE_PERMISSION_IDS[namespace], True):
                    raise RuntimeError('This Google Workspace service is disabled for the family.')
                return
            # Coarse provider permissions cannot safely classify arbitrary MCP methods.
            if not all(permissions.get(f'{plugin_id}.{i}', True) for i in range(len(plugin_by_id(plugin_id).permissions))):
                raise RuntimeError('This plugin has disabled permissions. Enable the required permissions before running it.')

    async def call(self, plugin_id, name, arguments, call_id):
        self.require_access(plugin_id)
        if plugin_id not in self.loaded or name not in {t['name'] for t in self.loaded[plugin_id]}:
            raise ValueError('Load the namespace and select an exact tool name first.')
        client = self.clients[plugin_id]
        if isinstance(client, MCPClient):
            return await client.call_tool_async(call_id, name, arguments)
        return await client.call(name, arguments)

    async def close(self):
        try:
            for client in self.clients.values():
                if hasattr(client, 'close') and not isinstance(client, MCPClient):
                    if hasattr(client, 'preserve_session'):
                        client.preserve_session = self.preserve_browser
                    await client.close()
        finally:
            await asyncio.to_thread(self.stack.close)

    def __exit__(self, *args):
        self.stack.close()


def _env_name(plugin_id: str, suffix: str) -> str:
    return f"MOM_LIFE_PLUGIN_{plugin_id.replace('-', '_').replace('.', '_').upper()}_{suffix}"
