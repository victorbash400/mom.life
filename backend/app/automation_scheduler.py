"""AWS owns timers. There is no local timer or polling fallback."""
import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import boto3

from app.config import get_settings


def validate_trigger(trigger, schedule, timezone):
    try:
        zone = ZoneInfo(timezone)
    except (KeyError, ValueError) as error:
        raise ValueError("Choose a valid IANA timezone.") from error
    if trigger not in {'time','health','incoming'}:
        raise ValueError('Choose time, health, or incoming.')
    if trigger != 'time':
        if schedule:
            raise ValueError('Event automations do not need a schedule.')
        return
    if not schedule.startswith(('at(', 'rate(', 'cron(')) or not schedule.endswith(')'):
        raise ValueError('Use an AWS at, rate, or cron schedule.')
    if schedule.startswith('at('):
        target = datetime.fromisoformat(schedule[3:-1])
        if target.tzinfo is not None:
            raise ValueError('Use a local time without an offset; supply its timezone separately.')
        target = target.replace(tzinfo=zone)
        if target <= datetime.now(UTC):
            raise ValueError('Choose a future time.')


class AutomationScheduler:
    def __init__(self, settings=None, client=None):
        self.settings = settings or get_settings()
        self._client = client

    @property
    def client(self):
        if self._client is None:
            session = boto3.Session(profile_name=self.settings.aws_profile or None,region_name=self.settings.strands_region)
            self._client = session.client('scheduler')
        return self._client

    def save(self, item):
        if item['trigger'] != 'time':
            return
        if not self.settings.automation_target_arn or not self.settings.automation_role_arn:
            raise RuntimeError('AWS automation dispatcher is not configured. Run the automation provisioning script.')
        target = {'Arn':self.settings.automation_target_arn,'RoleArn':self.settings.automation_role_arn,
                  'Input':json.dumps({'automation_id':item['id'],'version':item['version'],
                                      'scheduled_at':'<aws.scheduler.scheduled-time>'}),
                  'RetryPolicy':{'MaximumEventAgeInSeconds':86400,'MaximumRetryAttempts':185}}
        if self.settings.automation_dlq_arn:
            target['DeadLetterConfig'] = {'Arn':self.settings.automation_dlq_arn}
        params = {'Name':f"mom-life-{item['id']}",'GroupName':self.settings.automation_schedule_group,
                  'ScheduleExpression':item['schedule'],'ScheduleExpressionTimezone':item['timezone'],
                  'FlexibleTimeWindow':{'Mode':'OFF'},'State':'ENABLED' if item['enabled'] else 'DISABLED',
                  'Target':target,'ActionAfterCompletion':'DELETE' if item['schedule'].startswith('at(') else 'NONE'}
        try:
            self.client.create_schedule(**params)
        except self.client.exceptions.ConflictException:
            self.client.update_schedule(**params)

    def delete(self, item):
        if item['trigger'] != 'time' or item['scheduler_state'] != 'ready':
            return
        try:
            self.client.delete_schedule(Name=f"mom-life-{item['id']}",GroupName=self.settings.automation_schedule_group)
        except self.client.exceptions.ResourceNotFoundException:
            pass
