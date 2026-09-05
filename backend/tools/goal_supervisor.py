from strands import tool


def supervisor_tools(family_id):
    from app.main import task_store, goal_tasks

    @tool
    def list_goal_tasks() -> list[dict]:
        """Read the authoritative family task boards, evidence and open questions."""
        return task_store.list(family_id)

    @tool
    async def create_family_goal(child_id: str, request: str) -> dict:
        """Create a durable goal when Mom asks for work. Preserve the requested outcome."""
        goal = task_store.create(family_id,child_id,request)
        await goal_tasks.start(family_id,goal['id'])
        return goal

    @tool
    async def revise_goal_plan(goal_id: str, instruction: str) -> dict:
        """Ask the planner to revise a goal, preserving task identities and completed evidence."""
        await goal_tasks.revise(family_id,goal_id,instruction)
        return task_store.get(family_id,goal_id)

    @tool
    def get_family_context() -> dict:
        """Read the family profile; never look for child identity in external plugins."""
        return task_store.family_context(family_id)

    return [list_goal_tasks,create_family_goal,revise_goal_plan,get_family_context]
