from fastapi import APIRouter, HTTPException, Request

from app.schemas import GoalRevision, QuestionAnswer, SkillWrite
from app.event_stream import family_events
from plugins.catalog import plugin_by_id


router = APIRouter()


def services():
    from app.main import task_store, goal_tasks
    return task_store,goal_tasks


@router.post('/api/tasks/{goal_id}/revise')
async def revise(goal_id: str, body: GoalRevision, request: Request):
    family_id = request.state.family_id
    store,manager = services()
    try:
        await manager.revise(family_id,goal_id,body.instruction)
    except ValueError as error:
        raise HTTPException(400,str(error)) from error
    except RuntimeError as error:
        raise HTTPException(503,str(error)) from error
    return store.get(family_id,goal_id)


@router.post('/api/tasks/{goal_id}/questions/{question_id}')
async def answer(goal_id: str, question_id: str, body: QuestionAnswer, request: Request):
    family_id = request.state.family_id
    store,manager = services()
    if not store.get(family_id,goal_id):
        raise HTTPException(404,'Goal not found.')
    question = next((item for item in store.questions(goal_id) if item['id'] == question_id and item['state'] == 'open'), None)
    if not question or not body.answer.strip():
        raise HTTPException(400,'Question is missing, already answered, or the answer is empty.')
    await manager.stop(goal_id)
    try:
        store.answer_question(family_id,goal_id,question_id,body.answer)
    except ValueError as error:
        raise HTTPException(400,str(error)) from error
    await manager.start(family_id,goal_id)
    family_events.publish(family_id,{'type':'goals_changed','goal_id':goal_id})
    return store.get(family_id,goal_id)


@router.post('/api/skills')
def create_skill(body: SkillWrite, request: Request):
    family_id = request.state.family_id
    store,_ = services()
    try:
        for identity in body.required_plugin_ids:
            plugin_by_id(identity)
        identity = store.save_skill(family_id,body)
    except ValueError as error:
        raise HTTPException(400,str(error)) from error
    return next(s for s in store.skills(family_id) if s['id']==identity)


@router.patch('/api/skills/{skill_id}')
def update_skill(skill_id: str, body: SkillWrite, request: Request):
    family_id = request.state.family_id
    store,_ = services()
    try:
        for identity in body.required_plugin_ids:
            plugin_by_id(identity)
        store.save_skill(family_id,body,skill_id)
    except ValueError as error:
        raise HTTPException(400,str(error)) from error
    return next(s for s in store.skills(family_id) if s['id']==skill_id)
