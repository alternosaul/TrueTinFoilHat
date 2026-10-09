from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    mode: Literal["local", "hosted"] = "local"
    db_url: str = "sqlite:///./data/truetinfoilhat.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    ollama_think: bool = False
    ollama_timeout: float = 600
    anthropic_default_model: str = "claude-haiku-5-5"
    wayback_years_back: int = 1
    cors_origins: str = "http://localhost:5173"
    user_agent: str = "TrueTinFoilHat/0.1 (+https://github.com/alternosaul/TrueTinFoilHat)"
    classify_batch_size: int = 10

    @property
    def ollama_enabled(self) -> bool:
        return self.mode == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
