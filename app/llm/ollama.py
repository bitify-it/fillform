import logging
from typing import Any

import httpx

from app.api.schemas.responses import LLMHealthResponse
from app.core.errors import LLMError
from app.llm.json_parsing import (
    parse_json_object as _parse_json_object,
)
from app.llm.json_parsing import (
    repair_system_prompt as _repair_system_prompt,
)
from app.llm.json_parsing import (
    repair_user_prompt as _repair_user_prompt,
)

logger = logging.getLogger(__name__)


class OllamaClient:
    provider = "ollama"

    def __init__(
        self,
        endpoint: str,
        model: str,
        temperature: float,
        timeout_seconds: float,
        json_repair_attempts: int,
        num_ctx: int = 16384,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.json_repair_attempts = json_repair_attempts
        self.num_ctx = num_ctx

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        logger.info("llm.generate_json.start provider=%s model=%s", self.provider, self.model)
        raw_response = await self._generate_text(system_prompt, user_prompt)
        parsed = _parse_json_object(raw_response)
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
            raw_response = await self._generate_text(
                system_prompt=_repair_system_prompt(),
                user_prompt=_repair_user_prompt(raw_response),
            )
            parsed = _parse_json_object(raw_response)
            if parsed is not None:
                logger.info(
                    "llm.generate_json.repaired provider=%s model=%s repair_attempt=%s",
                    self.provider,
                    self.model,
                    attempt,
                )
                return parsed

        raise LLMError("Ollama returned a non-JSON response after repair attempts.")

    async def health_check(self) -> LLMHealthResponse:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.endpoint}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            return LLMHealthResponse(
                provider=self.provider,
                model=self.model,
                endpoint=self.endpoint,
                available=False,
                model_available=False,
                error=f"Ollama health check failed: {exc}",
            )

        models = payload.get("models", [])
        model_names = {
            model.get("name")
            for model in models
            if isinstance(model, dict) and isinstance(model.get("name"), str)
        }
        return LLMHealthResponse(
            provider=self.provider,
            model=self.model,
            endpoint=self.endpoint,
            available=True,
            model_available=self.model in model_names,
            error=None if self.model in model_names else "Configured model was not found.",
        )

    async def _generate_text(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.endpoint}/api/generate", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

        try:
            raw_response = response.json()["response"]
        except (KeyError, TypeError) as exc:
            raise LLMError("Ollama response does not contain a response field.") from exc

        if not isinstance(raw_response, str):
            raise LLMError("Ollama response field must be a string.")
        return raw_response
