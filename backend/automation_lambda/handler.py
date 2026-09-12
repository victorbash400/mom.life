"""Scheduler target: accept a wake durably even when the application is offline."""
import json
import os
from pathlib import Path
from datetime import datetime, UTC

import boto3
import psycopg


def handler(event, context):
    secret = boto3.client('secretsmanager',endpoint_url=os.environ['SECRETS_ENDPOINT_URL']).get_secret_value(SecretId=os.environ['DATABASE_SECRET_ARN'])
    database_url = secret['SecretString']
    identity = event['automation_id']
    version = int(event['version'])
    scheduled_at = event['scheduled_at']
    wake_id = f'{identity}:{version}:{scheduled_at}'
    with psycopg.connect(database_url,connect_timeout=10,sslmode='verify-full',sslrootcert=str(Path(__file__).with_name('rds-ca.pem'))) as db:
        # Same transaction boundary as application updates/cancellation.
        db.execute('SELECT pg_advisory_xact_lock(72461902)')
        row = db.execute('''SELECT a.goal_id FROM automations a JOIN family_tasks g ON g.id=a.goal_id
            WHERE a.id=%s AND a.version=%s AND a.enabled=1 AND g.status!='paused' ''', (identity,version)).fetchone()
        if not row:
            return {'status':'ignored'}
        inserted = db.execute('''INSERT INTO automation_wakes(id,automation_id,version,context,created_at)
            VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
            (wake_id,identity,version,json.dumps({'source':'aws_scheduler','scheduled_at':scheduled_at}),datetime.now(UTC).isoformat())).rowcount
        if inserted:
            db.execute("SELECT pg_notify('mom_life_automations',%s)", (row[0],))
    return {'status':'saved' if inserted else 'duplicate'}
