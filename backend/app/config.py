from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuSynth"

    database_url: str
    redis_url: str
    rag_service_url: str = "http://python-rag:8000"
    jwt_secret: str
    jwt_expiration_seconds: int = 3600

    mock_llm: bool = True
    llm_provider: str = "openrouter"
    local_llm_fast_mode: bool = False
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    ollama_base_url: str = "http://host.docker.internal:11434/v1/chat/completions"
    ollama_model: str = "qwen2.5:3b"

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    council_model_1: str = "arcee-ai/trinity-large-preview:free"
    council_model_2: str = "stepfun/step-3.5-flash:free"
    council_model_3: str = "nvidia/nemotron-3-nano-30b-a3b:free"
    chairman_model: str = "gemini-3-flash-preview"

    stage_timeout: int = 30
    llm_timeout: int = 120
    request_timeout: int = 120

    rate_limit_rps: int = 5
    rate_limit_window_seconds: int = 60
    redis_cache_ttl_seconds: int = 3600
    semantic_cache_threshold: float = 0.85
    top_k_chunks: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def semantic_threshold(self) -> float:
        return self.semantic_cache_threshold

    @property
    def council_models(self) -> list[str]:
        return [self.council_model_1, self.council_model_2, self.council_model_3]


@lru_cache
def get_settings() -> Settings:
    return Settings()