"""Fetch and classify Groq models for the UI."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import requests

from resume_assistant.core.errors import GroqApiError, groq_error_from_exception
from resume_assistant.integrations.groq.constants import GROQ_MODELS_URL

logger = logging.getLogger(__name__)

MODELS_URL = GROQ_MODELS_URL

# Chat-capable models suitable for resume generation (excludes audio / guard-only).
CHAT_MODEL_BLOCKLIST = (
    "whisper",
    "orpheus",
    "prompt-guard",
    "safeguard",
)

# Default free-tier chat models on Groq (override with GROQ_FREE_MODEL_IDS in .env).
DEFAULT_FREE_MODEL_IDS: Set[str] = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
    "groq/compound-mini",
}

# Small-context models (e.g. allam-2-7b at 4096) are poor for long README summarization.
MIN_CONTEXT_FOR_README = 8192


@dataclass(frozen=True)
class GroqModelInfo:
    """One Groq model entry for display in the model picker."""

    id: str
    owned_by: str
    context_window: int
    max_completion_tokens: int
    is_free: bool
    is_chat: bool

    @property
    def label(self) -> str:
        tier = "Free" if self.is_free else "Paid / limited"
        ctx_note = ""
        if self.context_window and self.context_window < MIN_CONTEXT_FOR_README:
            ctx_note = f", {self.context_window // 1000}k ctx"
        return f"{self.id} ({tier}{ctx_note})"

    @property
    def supports_long_readme(self) -> bool:
        return self.context_window >= MIN_CONTEXT_FOR_README


def _load_free_model_ids() -> Set[str]:
    extra = os.getenv("GROQ_FREE_MODEL_IDS", "").strip()
    ids = set(DEFAULT_FREE_MODEL_IDS)
    if extra:
        ids.update(m.strip() for m in extra.split(",") if m.strip())
    return ids


def is_chat_model(model_id: str) -> bool:
    """True if the model supports text chat completions for this app."""
    lower = model_id.lower()
    return not any(block in lower for block in CHAT_MODEL_BLOCKLIST)


def fetch_groq_models(api_key: str, timeout: int = 30) -> List[GroqModelInfo]:
    """Load active chat models from Groq ``GET /v1/models``."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(MODELS_URL, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        raise groq_error_from_exception(exc) from exc

    free_ids = _load_free_model_ids()
    models: List[GroqModelInfo] = []

    for item in payload.get("data") or []:
        if not isinstance(item, dict):
            continue
        if item.get("active") is False:
            continue
        model_id = item.get("id") or ""
        if not model_id or not is_chat_model(model_id):
            continue
        models.append(
            GroqModelInfo(
                id=model_id,
                owned_by=str(item.get("owned_by") or ""),
                context_window=int(item.get("context_window") or 0),
                max_completion_tokens=int(item.get("max_completion_tokens") or 0),
                is_free=model_id in free_ids,
                is_chat=True,
            )
        )

    models.sort(key=lambda m: (not m.is_free, m.id))
    if not models:
        raise GroqApiError(
            "No chat models were returned from Groq. Check your API key and try again."
        )
    logger.info("Loaded %s Groq chat models (%s marked free)", len(models), sum(m.is_free for m in models))
    return models


def default_model_id(models: List[GroqModelInfo]) -> str:
    """Pick default: env override, else first free model, else first model."""
    preferred = os.getenv("GROQ_DEFAULT_MODEL", "").strip()
    if preferred and any(m.id == preferred for m in models):
        return preferred
    for model in models:
        if model.is_free:
            return model.id
    return models[0].id
