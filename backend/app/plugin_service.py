from app.task_store import now
from plugins.catalog import PLUGINS, plugin_by_id, plugin_snapshot
from plugins.runtime import PluginToolSession
from plugins.namespaces import namespaces
from plugins.configuration import setting


class PluginService:
    def __init__(self, store):
        self.store = store

    def list(self, family_id):
        installed = self.store.installed_plugins(family_id)
        with self.store._connect() as db:
            validated = {row['plugin_id']:row['validated_at'] for row in db.execute('SELECT * FROM plugin_connections WHERE family_id=?',(family_id,))}
        return [{**plugin_snapshot(plugin,plugin.id in installed,self.store.permissions(family_id,plugin.id)),
                 'connected':plugin.id in installed and plugin.id in validated,
                 'validated_at':validated.get(plugin.id),
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
            for namespace in namespaces([plugin_id]):
                directory.extend(await session.load(namespace))
            if plugin_id in {'microsoft-family','mychart','amazon-shopping','whatsapp'}:
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
        suffixes = ['FAMILY_ID']
        if plugin_id != 'agentcore-browser':
            suffixes.append('TOKEN')
        extra = {
            'home-assistant':['URL'],
            'mychart':['URL','PATIENT_ID'],
            'whatsapp':['PHONE_NUMBER_ID','API_VERSION'],
            'amazon-shopping':['MARKETPLACE','PARTNER_TAG','VALIDATION_ASIN'],
        }
        suffixes.extend(extra.get(plugin_id,[]))
        return [{'name':prefix+'_'+suffix,'configured':bool(setting(prefix+'_'+suffix))} for suffix in suffixes]
