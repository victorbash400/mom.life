import boto3

from agents.model import FamilyBedrockModel
from app.config import Settings


def test_kimi_structured_output_keeps_thinking_disabled():
    settings = Settings(_env_file=None)
    session = boto3.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
    model = FamilyBedrockModel(boto_session=session, model_id=settings.strands_model_id, additional_request_fields=settings.model_request_fields)
    for choice in [None, {"any": {}}, {"tool": {"name": "GoalPlan"}}]:
        assert model._get_additional_request_fields(choice) == {"additionalModelRequestFields": {"thinking": {"type": "disabled"}}}


def test_other_models_keep_strands_forced_tool_behavior():
    settings = Settings(_env_file=None, strands_model_id="other-model")
    assert settings.model_request_fields == {}
    session = boto3.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
    model = FamilyBedrockModel(boto_session=session, model_id="other-model", additional_request_fields={"thinking": {"type": "enabled"}})
    assert model._get_additional_request_fields({"any": {}}) == {}
