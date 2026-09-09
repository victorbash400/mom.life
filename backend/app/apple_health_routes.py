from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from plugins.apple_health_adapter import AppleHealthAdapter, SAMPLE_UNITS


router=APIRouter()


class HealthSample(BaseModel):
    external_id: str=Field(min_length=1,max_length=128)
    child_id: str=Field(min_length=1,max_length=128)
    sample_type: str
    start_at: datetime
    end_at: datetime
    value: float
    unit: str=Field(min_length=1,max_length=32)
    source: str=Field(min_length=1,max_length=120)

    @field_validator('sample_type')
    @classmethod
    def supported_type(cls,value):
        if value not in SAMPLE_UNITS:
            raise ValueError('Unsupported Apple Health sample type.')
        return value

    @field_validator('start_at','end_at')
    @classmethod
    def timezone_required(cls,value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Apple Health timestamps must include a timezone.')
        return value


class HealthSync(BaseModel):
    samples: list[HealthSample]=Field(default_factory=list,max_length=500)
    deleted_ids: list[str]=Field(default_factory=list,max_length=500)


@router.post('/api/plugins/apple-health/sync')
def sync_health(request: Request,body: HealthSync):
    from app.auth import families
    from app.main import task_store
    family_id=request.state.family_id
    if 'apple-health' not in task_store.installed_plugins(family_id):
        raise HTTPException(409,'Install Apple Health before synchronizing data.')
    if not body.samples and not body.deleted_ids:
        raise HTTPException(400,'Send at least one changed or deleted HealthKit sample.')
    for sample in body.samples:
        if not families.child(family_id,sample.child_id):
            raise HTTPException(404,'Child profile not found.')
        if sample.end_at < sample.start_at:
            raise HTTPException(400,'A HealthKit sample cannot end before it starts.')
    try:
        return AppleHealthAdapter(family_id,task_store).sync(body.samples,body.deleted_ids)
    except ValueError as error:
        raise HTTPException(400,str(error)) from error
