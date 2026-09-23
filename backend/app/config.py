from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = REPO_DIR / "data" / "career_quest"
    frontend_dist: Path = REPO_DIR / "frontend" / "dist"
    cors_origins: list[str] = ["*"]

    # true -> never call an LLM; the deterministic engine explains recommendations itself
    use_mocks: bool = False

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-6-luna"
    openai_reasoning_effort: str = "none"  # empty string -> parameter is not sent
    llm_timeout_s: float = 9.0  # ТЗ: AI recommendation must arrive within 10 s

    # Optional second provider (NVIDIA NIM is OpenAI-compatible)
    fallback_api_key: str = ""
    fallback_base_url: str = "https://integrate.api.nvidia.com/v1"
    fallback_model: str = "meta/llama-3.3-70b-instruct"

    @property
    def llm_enabled(self) -> bool:
        return not self.use_mocks and bool(self.openai_api_key or self.fallback_api_key)


settings = Settings()
