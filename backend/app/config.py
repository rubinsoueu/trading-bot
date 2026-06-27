from typing import List, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://trading:changeme@db:5432/trading_bot"
    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str = "change-me-please-use-a-secure-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ENCRYPTION_KEY: str = "change-me-to-a-32-byte-base64-key"

    # NVIDIA NIM Settings
    NVIDIA_NIM_API_BASE: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_NIM_API_KEY: str = ""
    NVIDIA_NIM_MODEL: str = "meta/llama-3-70b-instruct"

    # OpenRouter / Fallback Settings
    OPENROUTER_API_BASE: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it"

    # Alerting Settings
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    DISCORD_WEBHOOK_URL: str = ""

    # Trading Defaults
    DEFAULT_TIMEFRAME: str = "1h"
    DEFAULT_INITIAL_CAPITAL: float = 10000.0
    MAX_POSITION_PCT: float = 2.0
    MAX_DRAWDOWN_PCT: float = 10.0
    DAILY_LOSS_LIMIT_PCT: float = 5.0

    CORS_ORIGINS: Any = ["http://localhost:8501", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    model_config = {
        "env_file": os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()