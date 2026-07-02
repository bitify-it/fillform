from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    max_upload_bytes: int = Field(default=25 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")
    storage_dir: Path = Field(default=Path("storage"), alias="STORAGE_DIR")

    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gemma4:e4b", alias="LLM_MODEL")
    llm_endpoint: str = Field(default="http://localhost:11434", alias="LLM_ENDPOINT")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_timeout_seconds: float = Field(default=120.0, alias="LLM_TIMEOUT_SECONDS")
    llm_json_repair_attempts: int = Field(default=2, alias="LLM_JSON_REPAIR_ATTEMPTS")
    llm_num_ctx: int = Field(default=16384, alias="LLM_NUM_CTX")
    llm_max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")

    double_check_mode: str = Field(default="low_confidence", alias="DOUBLE_CHECK_MODE")
    double_check_confidence_threshold: float = Field(
        default=0.6,
        alias="DOUBLE_CHECK_CONFIDENCE_THRESHOLD",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
