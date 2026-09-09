from app.task_store import now
from plugins.catalog import PLUGINS, plugin_by_id, plugin_snapshot
from plugins.runtime import PluginToolSession
from plugins.namespaces import namespaces
from plugins.namespaces import WORKSPACE_PERMISSION_IDS
from plugins.configuration import setting


class PluginService:
    def __init__(self, store):
        self.store = store

    def list(self, family_id):
        installed = self.store.installed_plugins(family_id)
        with self.store._connect() as db:
            validated = {row['plugin_id']:row['validated_at'] for row in db.execute('SELECT * FROM plugin_connections WHERE family_id=?',(family_id,))}
        from plugins.oauth import OAuthConnections
        oauth = OAuthConnections(self.store)
        identities = {plugin_id:oauth.identity(family_id,plugin_id) for plugin_id in installed}
        return [{**plugin_snapshot(plugin,plugin.id in installed,self.store.permissions(family_id,plugin.id)),
                 'connected':plugin.id in installed and plugin.id in validated,
                 'validated_at':validated.get(plugin.id),
                 'account_label': (identities.get(plugin.id) or {}).get('email'),
                 'account_name': (identities.get(plugin.id) or {}).get('name'),
                 'account_picture': (identities.get(plugin.id) or {}).get('picture'),
                 'setup_fields': self.setup_fields(plugin.id)} for plugin in PLUGINS]

    async def validate(self, family_id, plugin_id):
        plugin_by_id(plugin_id)
        if plugin_id not in self.store.installed_plugins(family_id):
            raise ValueError('Install this plugin first.')
        with self.store._connect() as db:
            db.execute('DELETE FROM plugin_connections WHERE family_id=? AND plugin_id=?',(family_id,plugin_id))
        session = PluginToolSession([plugin_id],self.store,family_id)
        try:
            directory = []
            plugin_permissions = self.store.permissions(family_id,plugin_id)
            enabled_namespaces = [namespace for namespace in namespaces([plugin_id]) if plugin_id != 'google-workspace' or plugin_permissions.get(WORKSPACE_PERMISSION_IDS[namespace],True)]
            if not enabled_namespaces:
                raise ValueError('Enable at least one Google Workspace service before connecting.')
            for namespace in enabled_namespaces:
                directory.extend(await session.load(namespace))
            if plugin_id == 'google-workspace':
                for namespace in enabled_namespaces:
                    await session.clients[namespace].validate()
            elif plugin_id in {'whatsapp','google-classroom','fitbit','withings','apple-health'}:
                await session.clients[plugin_id].validate()
            elif plugin_id == 'agentcore-browser':
                await session.clients[plugin_id].validate()
            with self.store._connect() as db:
                db.execute('INSERT INTO plugin_connections VALUES (?,?,?) ON CONFLICT (family_id,plugin_id) DO UPDATE SET validated_at=excluded.validated_at',(family_id,plugin_id,now()))
            return {'tools':len(directory),'plugin':next(p for p in self.list(family_id) if p['id']==plugin_id)}
        finally:
            await session.close()


    @staticmethod
    def setup_fields(plugin_id):
        prefix = 'MOM_LIFE_PLUGIN_' + plugin_id.replace('-','_').upper()
        if plugin_id in {'google-workspace','google-classroom','todoist','notion','canva','apple-health'}:
            return []
        if plugin_id == 'google-maps':
            return [{'name':prefix+'_TOKEN','configured':bool(setting(prefix+'_TOKEN'))}]
        if plugin_id in {'fitbit','withings'}:
            names = [prefix+'_OAUTH_CLIENT_ID',prefix+'_OAUTH_REDIRECT_URI']
            return [{'name':name,'configured':bool(setting(name))} for name in names]
        suffixes = ['FAMILY_ID']
        if plugin_id != 'agentcore-browser':
            suffixes.append('TOKEN')
        extra = {
            'whatsapp':['PHONE_NUMBER_ID','API_VERSION','VERIFY_TOKEN','APP_SECRET'],
        }
        suffixes.extend(extra.get(plugin_id,[]))
        return [{'name':prefix+'_'+suffix,'configured':bool(setting(prefix+'_'+suffix))} for suffix in suffixes]
