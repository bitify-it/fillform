import logging
from typing import Any

import httpx

from app.api.schemas.responses import LLMHealthResponse
from app.core.errors import LLMError
from app.llm.json_parsing import parse_json_object

logger = logging.getLogger(__name__)

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ENDPOINT = "https://api.anthropic.com"


class AnthropicClient:
    """Client for the Anthropic Messages API.

    JSON output is forced with an assistant prefill (``{``) instead of a native
    JSON mode, so the parsed object is ``"{" + response_text``.
    """

    provider = "anthropic"

    def __init__(
        self,
        model: str,
        temperature: float,
        timeout_seconds: float,
        json_repair_attempts: int,
        max_tokens: int,
        api_key: str | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
    ) -> None:
        self.endpoint = (endpoint or DEFAULT_ENDPOINT).rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.json_repair_attempts = json_repair_attempts
        self.max_tokens = max_tokens
        self.api_key = api_key

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        logger.info("llm.generate_json.start provider=%s model=%s", self.provider, self.model)
        for attempt in range(self.json_repair_attempts + 1):
            raw_response = await self._messages(system_prompt, user_prompt)
            parsed = parse_json_object(raw_response)
            if parsed is not None:
                logger.info(
                    "llm.generate_json.parsed provider=%s model=%s attempt=%s",
                    self.provider,
                    self.model,
                    attempt,
                )
                return parsed
            logger.warning(
                "llm.generate_json.invalid_json provider=%s model=%s repair_attempt=%s",
                self.provider,
                self.model,
                attempt,
            )

        raise LLMError("Anthropic provider returned non-JSON after repair attempts.")

    async def health_check(self) -> LLMHealthResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.endpoint}/v1/models", headers=self._headers())
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            return LLMHealthResponse(
                provider=self.provider,
                model=self.model,
                endpoint=self.endpoint,
                available=False,
                model_available=False,
                error=f"Health check failed: {exc}",
            )

        data = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids = {
            item.get("id")
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        return LLMHealthResponse(
            provider=self.provider,
            model=self.model,
            endpoint=self.endpoint,
            available=True,
            model_available=self.model in model_ids,
            error=None if self.model in model_ids else "Configured model was not found.",
        )

    async def _messages(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": "{"},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.endpoint}/v1/messages",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        try:
            blocks = response.json()["content"]
            text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        except (KeyError, TypeError, AttributeError) as exc:
            raise LLMError("Anthropic response has no text content.") from exc

        # Re-attach the prefilled opening brace stripped by the API.
        return "{" + text

    def _headers(self) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "anthropic-version": ANTHROPIC_VERSION,
            "x-api-key": self.api_key or "",
        }
