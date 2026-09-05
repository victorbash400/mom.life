import asyncio

import boto3

from app.config import get_settings


async def discard_goal_browser_sessions(store,goal_id):
    with store._connect() as db:
        if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='browser_sessions'").fetchone():
            return
        rows=db.execute('SELECT b.* FROM browser_sessions b JOIN goal_assignments a ON a.id=b.assignment_id WHERE a.goal_id=?',(goal_id,)).fetchall()
    if not rows:
        return
    config=get_settings()
    session=boto3.Session(profile_name=config.aws_profile or None,region_name=config.strands_region)
    client=session.client('bedrock-agentcore')
    try:
        for row in rows:
            try:
                await asyncio.to_thread(client.stop_browser_session,browserIdentifier='aws.browser.v1',sessionId=row['session_id'])
            except client.exceptions.ResourceNotFoundException:
                pass
            with store._connect() as db:
                db.execute('DELETE FROM browser_sessions WHERE assignment_id=?',(row['assignment_id'],))
    finally:
        client.close()
