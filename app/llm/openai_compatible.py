import logging
from typing import Any

import httpx

from app.api.schemas.responses import LLMHealthResponse
from app.core.errors import LLMError
from app.llm.json_parsing import (
    parse_json_object,
    repair_system_prompt,
    repair_user_prompt,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    """Client for any OpenAI-compatible Chat Completions endpoint.

    Works with the OpenAI API and drop-in servers such as vLLM, LM Studio,
    Together, Groq, OpenRouter and llama.cpp's server.
    """

    provider = "openai"

    def __init__(
        self,
        endpoint: str,
        model: str,
        temperature: float,
        timeout_seconds: float,
        json_repair_attempts: int,
        api_key: str | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.json_repair_attempts = json_repair_attempts
        self.api_key = api_key

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        logger.info("llm.generate_json.start provider=%s model=%s", self.provider, self.model)
        raw_response = await self._chat(system_prompt, user_prompt)
        parsed = parse_json_object(raw_response)
        if parsed is not None:
            logger.info(
                "llm.generate_json.parsed provider=%s model=%s attempt=0",
                self.provider,
                self.model,
            )
            return parsed

        for attempt in range(1, self.json_repair_attempts + 1):
            logger.warning(
                "llm.generate_json.invalid_json provider=%s model=%s repair_attempt=%s",
                self.provider,
                self.model,
                attempt,
            )
            raw_response = await self._chat(
                repair_system_prompt(),
                repair_user_prompt(raw_response),
            )
            parsed = parse_json_object(raw_response)
            if parsed is not None:
                logger.info(
                    "llm.generate_json.repaired provider=%s model=%s repair_attempt=%s",
                    self.provider,
                    self.model,
                    attempt,
                )
                return parsed

        raise LLMError("OpenAI-compatible provider returned non-JSON after repair attempts.")

    async def health_check(self) -> LLMHealthResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.endpoint}/models", headers=self._headers())
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

    async def _chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.endpoint}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("OpenAI-compatible response has no message content.") from exc

        if not isinstance(content, str):
            raise LLMError("OpenAI-compatible message content must be a string.")
        return content

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
