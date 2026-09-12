from typing import Literal
from strands import tool


def automation_tools(family_id, goal_id=None):
    def manager():
        from app.main import automations
        return automations

    @tool
    def list_automations() -> list[dict]:
        """Read saved automations, their linked tasks, last checks, results and setup errors."""
        items = manager().store.list(family_id)
        return [item for item in items if not goal_id or item['goal_id'] == goal_id]

    @tool
    async def create_automation(task_id: str, instruction: str, trigger: Literal['time','health','incoming'], schedule: str = '', timezone: str = 'UTC') -> dict:
        """Save a standing instruction linked to a task. Describe what to check and when to notify or act.
        health wakes on changed child HealthKit data; incoming wakes on newly received family information.
        time uses AWS at(YYYY-MM-DDTHH:MM:SS), rate(1 minute), rate(1 day), or cron expressions.
        One-time times are local to the supplied IANA timezone. Timed delivery has minute precision.
        Check enabled and failure in the receipt; never promise monitoring when setup failed.
        """
        if goal_id and task_id != goal_id:
            raise ValueError('Create the automation on this assigned task.')
        return await manager().create(family_id,task_id,instruction,trigger,schedule,timezone)

    @tool
    async def change_automation(automation_id: str, enabled: bool, instruction: str = '', schedule: str = '', timezone: str = '') -> dict:
        """Pause, resume or revise an existing rule. Read its current state first. Empty strings preserve existing values."""
        item = manager().store.get(family_id,automation_id)
        if not item or (goal_id and item['goal_id'] != goal_id):
            raise ValueError('Automation not found in this task scope.')
        changes = {'enabled':enabled}
        changes.update({key:value for key,value in {'instruction':instruction,'schedule':schedule,'timezone':timezone}.items() if value})
        return await manager().update(family_id,automation_id,**changes)

    @tool
    async def delete_automation(automation_id: str) -> dict:
        """Cancel future checks and remove the selected automation when requested."""
        item = manager().store.get(family_id,automation_id)
        if not item or (goal_id and item['goal_id'] != goal_id):
            raise ValueError('Automation not found in this task scope.')
        await manager().delete(family_id,automation_id)
        return {'status':'deleted'}

    return [list_automations,create_automation,change_automation,delete_automation]
