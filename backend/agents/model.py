from strands.models import BedrockModel


class FamilyBedrockModel(BedrockModel):
    def _get_additional_request_fields(self, tool_choice):
        fields = self.config.get("additional_request_fields") or {}
        if self.config["model_id"] == "moonshotai.kimi-k2.5" and fields.get("thinking") == {"type": "disabled"}:
            # Kimi accepts disabled thinking with forced tools; Strands strips it for Anthropic.
            return {"additionalModelRequestFields": fields}
        return super()._get_additional_request_fields(tool_choice)
