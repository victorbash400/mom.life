from strands import tool


def supervisor_tools(family_id):
    from app.main import task_store, goal_tasks

    @tool
    def list_goal_tasks() -> list[dict]:
        """Read the authoritative family task boards, evidence and open questions."""
        return task_store.list(family_id)

    @tool
    async def create_family_goal(child_id: str, request: str, start_now: bool = True) -> dict:
        """Create a durable goal when Mom asks for work. For ongoing monitoring or future-only work use start_now=False, then create_automation on its id. Preserve the requested outcome."""
        from app.auth import families
        if child_id != 'all' and not families.child(family_id,child_id):
            raise ValueError('Select an existing child or all children.')
        goal = task_store.create(family_id,child_id,request)
        if start_now:
            await goal_tasks.start(family_id,goal['id'])
        else:
            task_store.set_goal_state(goal["id"],run_state="waiting",current_step="Waiting for an automation trigger")
        return task_store.get(family_id,goal["id"])

    @tool
    async def revise_goal_plan(goal_id: str, instruction: str) -> dict:
        """Ask the planner to revise a goal, preserving task identities and completed evidence."""
        await goal_tasks.revise(family_id,goal_id,instruction)
        return task_store.get(family_id,goal_id)

    @tool
    def get_family_context() -> dict:
        """Read the authoritative parent and child profiles when family identity matters."""
        from app.auth import families
        parent, children = families.snapshot(family_id)
        return {"parent": dict(parent), "children": [dict(child) for child in children]}

    from tools.automation_tools import automation_tools
    return [list_goal_tasks,create_family_goal,revise_goal_plan,get_family_context,*automation_tools(family_id)]
