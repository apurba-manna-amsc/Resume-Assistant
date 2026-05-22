"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    groq_default_model: str
    groq_free_model_ids: str
    groq_min_remaining_requests: int
    groq_min_remaining_tokens_ratio: float
    groq_min_request_interval_sec: float
    groq_rate_limit_buffer_sec: float
    groq_retry_delay_sec: float


@lru_cache
def get_settings() -> Settings:
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_default_model=os.getenv("GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile").strip(),
        groq_free_model_ids=os.getenv("GROQ_FREE_MODEL_IDS", "").strip(),
        groq_min_remaining_requests=int(os.getenv("GROQ_MIN_REMAINING_REQUESTS", "2")),
        groq_min_remaining_tokens_ratio=float(os.getenv("GROQ_MIN_REMAINING_TOKENS_RATIO", "0.15")),
        groq_min_request_interval_sec=float(os.getenv("GROQ_MIN_REQUEST_INTERVAL_SEC", "1.0")),
        groq_rate_limit_buffer_sec=float(os.getenv("GROQ_RATE_LIMIT_BUFFER_SEC", "0.5")),
        groq_retry_delay_sec=float(os.getenv("GROQ_RETRY_DELAY_SEC", "10")),
    )
