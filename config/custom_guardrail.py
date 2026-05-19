from fastapi import HTTPException
from litellm.proxy.guardrails.guardrail_hooks.custom_guardrail import CustomGuardrail
from litellm.proxy._types import UserAPIKeyAuth

from src.guardrails.pii_guardrail import PIIGuardrail


class HiddenLayerPIIGuardrail(CustomGuardrail):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.guardrail = PIIGuardrail()

    def _extract_text_from_messages(self, messages):
        text_parts = []

        for message in messages or []:
            content = message.get("content", "")

            if isinstance(content, str):
                text_parts.append(content)

            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))

        return "\n".join(text_parts)

    def _block_if_pii_detected(self, text, phase):
        result = self.guardrail.inspect(text)

        if not result["allowed"]:
            detected_entities = [
                finding["entity_type"]
                for finding in result["findings"]
            ]

            raise HTTPException(
                status_code=400,
                detail={
                    "error": "PII detected",
                    "phase": phase,
                    "detected_entities": detected_entities,
                    "message": f"Blocked {phase} because sensitive PII was detected."
                }
            )

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache,
        data,
        call_type,
    ):
        messages = data.get("messages", [])
        prompt_text = self._extract_text_from_messages(messages)

        self._block_if_pii_detected(prompt_text, "prompt_input")

        return data

    async def async_post_call_success_hook(
        self,
        data,
        user_api_key_dict: UserAPIKeyAuth,
        response,
    ):
        output_text = ""

        if isinstance(response, dict):
            choices = response.get("choices", [])
        else:
            choices = getattr(response, "choices", [])

        for choice in choices:
            if isinstance(choice, dict):
                message = choice.get("message", {})
                content = message.get("content", "")
            else:
                message = getattr(choice, "message", None)
                content = getattr(message, "content", "") if message else ""

            if isinstance(content, str):
                output_text += content + "\n"

        self._block_if_pii_detected(output_text, "model_output")

        return response