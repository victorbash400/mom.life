from fastapi import APIRouter, Request


router = APIRouter(prefix="/api/education")


@router.get("")
def education(request: Request) -> dict[str, object]:
    from app.main import task_store
    return {"snapshots": task_store.education_snapshots(request.state.family_id)}
