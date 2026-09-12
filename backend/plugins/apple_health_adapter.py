"""Read normalized HealthKit samples pushed by the signed-in iPhone companion."""
import re

from app.task_store import now
from plugins.api_adapters import definition, field


SAMPLE_UNITS = {
    'step_count': 'count',
    'active_energy': 'kcal',
    'walking_running_distance': 'm',
    'heart_rate': 'count/min',
    'sleep_analysis': 'stage',
}
class AppleHealthAdapter:
    def __init__(self, family_id, store):
        self.family_id = family_id
        self.store = store

    def directory(self):
        filters = {'child_id':field('child_id','Child profile ID'),'date':field('date','Date in YYYY-MM-DD format')}
        return [
            definition('read_daily_activity','Read synced steps, active energy, and walking or running distance for one child and date.',filters),
            definition('read_sleep','Read synced sleep stages for one child and date.',filters),
            definition('read_heart_rate','Read synced heart-rate samples for one child and date.',filters),
            definition('latest_sync','Read when Apple Health last synchronized and how many samples are available.'),
        ]

    def sync(self, samples, deleted_ids):
        changed_at = now()
        rows = []
        for sample in samples:
            expected = SAMPLE_UNITS.get(sample.sample_type)
            if expected != sample.unit:
                raise ValueError(f'{sample.sample_type} must use the normalized unit {expected}.')
            rows.append((
                self.family_id,sample.external_id,sample.child_id,sample.sample_type,
                sample.start_at.isoformat(),sample.end_at.isoformat(),sample.value,
                sample.unit,sample.source,changed_at,
            ))
        with self.store._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.executemany(
                'DELETE FROM apple_health_samples WHERE family_id=? AND external_id=?',
                ((self.family_id, external_id) for external_id in deleted_ids),
            )
            db.executemany('''INSERT INTO apple_health_samples
                    (family_id,external_id,child_id,sample_type,start_at,end_at,value,unit,source,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT (family_id,external_id) DO UPDATE SET
                    child_id=excluded.child_id,sample_type=excluded.sample_type,start_at=excluded.start_at,
                    end_at=excluded.end_at,value=excluded.value,unit=excluded.unit,
                    source=excluded.source,updated_at=excluded.updated_at''', rows)
            if rows or deleted_ids:
                from app.automation_store import AutomationStore
                AutomationStore(self.store).enqueue_event(self.family_id,{row[2] for row in rows},"health",changed_at,
                    {"source":"apple-health","child_ids":sorted({row[2] for row in rows}),"changed_samples":len(rows),"deleted_ids":deleted_ids},db)
        return self.latest_sync()

    def latest_sync(self):
        with self.store._connect() as db:
            row=db.execute('SELECT COUNT(*) AS sample_count,MAX(updated_at) AS synced_at FROM apple_health_samples WHERE family_id=?',(self.family_id,)).fetchone()
        return {'status':'success','data':{'sample_count':row['sample_count'],'synced_at':row['synced_at']}}

    async def call(self,name,arguments):
        if name == 'latest_sync':
            if arguments:
                raise ValueError('latest_sync does not accept arguments.')
            return self.latest_sync()
        if name not in {'read_daily_activity','read_sleep','read_heart_rate'} or set(arguments) != {'child_id','date'}:
            raise ValueError('Use an exact Apple Health capability and its documented arguments.')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',arguments['date']):
            raise ValueError('Date must use YYYY-MM-DD.')
        types = {
            'read_daily_activity':('step_count','active_energy','walking_running_distance'),
            'read_sleep':('sleep_analysis',),
            'read_heart_rate':('heart_rate',),
        }[name]
        placeholders=','.join('?' for _ in types)
        with self.store._connect() as db:
            rows=db.execute(f'''SELECT external_id,sample_type,start_at,end_at,value,unit,source
                FROM apple_health_samples WHERE family_id=? AND child_id=?
                AND substr(start_at,1,10)=? AND sample_type IN ({placeholders})
                ORDER BY start_at LIMIT 500''',(self.family_id,arguments['child_id'],arguments['date'],*types)).fetchall()
        return {'status':'success','data':{'samples':[dict(row) for row in rows]}}

    async def validate(self):
        status=self.latest_sync()
        if not status['data']['sample_count']:
            raise ValueError('No Apple Health data has been synchronized from an authorized iPhone.')
        return status
