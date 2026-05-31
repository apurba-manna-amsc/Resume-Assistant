"""Fetch and classify Groq models for the UI."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import requests

from resume_assistant.core.errors import GroqApiError, groq_error_from_exception
from resume_assistant.integrations.groq.constants import GROQ_MODELS_URL
from resume_assistant.integrations.groq.rate_limiter import RateLimitSnapshot

logger = logging.getLogger(__name__)

MODELS_URL = GROQ_MODELS_URL

CHAT_MODEL_BLOCKLIST = (
    "whisper",
    "orpheus",
    "prompt-guard",
    "safeguard",
)

DEFAULT_FREE_MODEL_IDS: Set[str] = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
}

MIN_CONTEXT_FOR_README = 8192
STRICT_DAILY_REQUEST_THRESHOLD = 500


@dataclass
class GroqModelInfo:
    """One Groq model — metadata from GET /v1/models plus live limits from headers."""

    id: str
    owned_by: str
    context_window: int
    max_completion_tokens: int
    is_chat: bool
    object_type: str = "model"
    created: int = 0
    active: bool = True
    public_apps: Optional[Any] = None
    is_free: bool = False
    limit_requests: Optional[int] = None
    limit_tokens: Optional[int] = None
    remaining_requests: Optional[int] = None
    remaining_tokens: Optional[int] = None
    reset_requests_sec: Optional[float] = None
    reset_tokens_sec: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @staticmethod
    def _fmt_count(value: int) -> str:
        if value >= 10_000:
            return f"{value / 1000:.1f}k".replace(".0k", "k")
        if value >= 1_000:
            return f"{value / 1000:.1f}k"
        return str(value)

    @property
    def label(self) -> str:
        parts: List[str] = [self.id]
        if self.limit_requests is not None:
            parts.append(f"{self._fmt_count(self.limit_requests)} req/day")
        if self.context_window:
            ctx_k = self.context_window // 1000
            if self.context_window < MIN_CONTEXT_FOR_README:
                parts.append(f"{ctx_k}k ctx ⚠")
            else:
                parts.append(f"{ctx_k}k ctx")
        if self.has_strict_daily_quota:
            parts.append("strict quota")
        return " · ".join(parts)

    @property
    def supports_long_readme(self) -> bool:
        return self.context_window >= MIN_CONTEXT_FOR_README

    @property
    def has_strict_daily_quota(self) -> bool:
        if self.limit_requests is None:
            return False
        return self.limit_requests <= STRICT_DAILY_REQUEST_THRESHOLD

    @property
    def has_limits_loaded(self) -> bool:
        return self.limit_requests is not None or self.limit_tokens is not None

    def apply_snapshot(self, snap: Optional[RateLimitSnapshot]) -> None:
        if not snap:
            return
        self.limit_requests = snap.limit_requests
        self.limit_tokens = snap.limit_tokens
        self.remaining_requests = snap.remaining_requests
        self.remaining_tokens = snap.remaining_tokens
        self.reset_requests_sec = snap.reset_requests_sec
        self.reset_tokens_sec = snap.reset_tokens_sec

    def to_display_row(self) -> Dict[str, Any]:
        return {
            "Model": self.id,
            "Context": f"{self.context_window:,}" if self.context_window else "—",
            "Max output": f"{self.max_completion_tokens:,}" if self.max_completion_tokens else "—",
            "Requests/day": self._fmt_count(self.limit_requests) if self.limit_requests else "—",
            "Tokens/min": self._fmt_count(self.limit_tokens) if self.limit_tokens else "—",
            "Remaining today": (
                str(self.remaining_requests) if self.remaining_requests is not None else "—"
            ),
            "Owner": self.owned_by or "—",
        }


def _load_free_model_ids() -> Set[str]:
    extra = os.getenv("GROQ_FREE_MODEL_IDS", "").strip()
    ids = set(DEFAULT_FREE_MODEL_IDS)
    if extra:
        ids.update(m.strip() for m in extra.split(",") if m.strip())
    return ids


def is_chat_model(model_id: str) -> bool:
    lower = model_id.lower()
    return not any(block in lower for block in CHAT_MODEL_BLOCKLIST)


def parse_model_from_api(item: Dict[str, Any], free_ids: Set[str]) -> Optional[GroqModelInfo]:
    if not isinstance(item, dict):
        return None
    if item.get("active") is False:
        return None
    model_id = item.get("id") or ""
    if not model_id or not is_chat_model(model_id):
        return None
    return GroqModelInfo(
        id=model_id,
        owned_by=str(item.get("owned_by") or ""),
        context_window=int(item.get("context_window") or 0),
        max_completion_tokens=int(item.get("max_completion_tokens") or 0),
        is_chat=True,
        object_type=str(item.get("object") or "model"),
        created=int(item.get("created") or 0),
        active=bool(item.get("active", True)),
        public_apps=item.get("public_apps"),
        is_free=model_id in free_ids,
        raw=dict(item),
    )


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
        model = parse_model_from_api(item, free_ids)
        if model:
            models.append(model)

    models.sort(key=_model_sort_key)
    if not models:
        raise GroqApiError(
            "No chat models were returned from Groq. Check your API key and try again."
        )
    logger.info("Loaded %s Groq chat models from API", len(models))
    return models


def _model_sort_key(model: GroqModelInfo) -> tuple:
    daily = model.limit_requests if model.limit_requests is not None else -1
    return (-daily, -model.context_window, model.id)


def sync_models_with_snapshots(
    models: List[GroqModelInfo],
    snapshots: Dict[str, RateLimitSnapshot],
) -> List[GroqModelInfo]:
    for model in models:
        model.apply_snapshot(snapshots.get(model.id))
    models.sort(key=_model_sort_key)
    return models


def default_model_id(models: List[GroqModelInfo]) -> str:
    preferred = os.getenv("GROQ_DEFAULT_MODEL", "").strip()
    if preferred and any(m.id == preferred for m in models):
        return preferred

    candidates = [m for m in models if m.supports_long_readme]
    if not candidates:
        candidates = list(models)

    def score(model: GroqModelInfo) -> tuple:
        strict = 1 if model.has_strict_daily_quota else 0
        daily = model.limit_requests or 0
        return (strict, -daily, -model.context_window)

    candidates.sort(key=score)
    return candidates[0].id
