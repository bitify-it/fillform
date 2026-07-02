from app.core.config import Settings
from app.core.errors import ConfigurationError
from app.llm.anthropic import AnthropicClient
from app.llm.base import LLMClient
from app.llm.ollama import OllamaClient
from app.llm.openai_compatible import OpenAICompatibleClient

OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "openai_compatible",
    "vllm",
    "lmstudio",
    "together",
    "groq",
}


def create_llm_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        return OllamaClient(
            endpoint=settings.llm_endpoint,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
            json_repair_attempts=settings.llm_json_repair_attempts,
            num_ctx=settings.llm_num_ctx,
        )

    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return OpenAICompatibleClient(
            endpoint=settings.llm_endpoint,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
            json_repair_attempts=settings.llm_json_repair_attempts,
            api_key=settings.llm_api_key,
        )

    if provider in {"anthropic", "claude"}:
        # Anthropic uses its official endpoint; LLM_ENDPOINT defaults to Ollama
        # and is intentionally not forwarded here.
        return AnthropicClient(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
            json_repair_attempts=settings.llm_json_repair_attempts,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.llm_api_key,
        )

    if provider == "llamacpp":
        raise ConfigurationError(f"Provider '{provider}' is planned but not implemented yet.")

    raise ConfigurationError(f"Unsupported LLM provider '{settings.llm_provider}'.")
