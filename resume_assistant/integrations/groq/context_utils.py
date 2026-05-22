"""Truncate prompts to fit each Groq model's context window."""

from __future__ import annotations

import logging
from typing import Optional

from resume_assistant.integrations.groq.models import GroqModelInfo

logger = logging.getLogger(__name__)

# Models below this should not summarize full GitHub READMEs without truncation.
MIN_CONTEXT_FOR_README = 8192
CHARS_PER_TOKEN_ESTIMATE = 3.5


def find_model_info(models: list[GroqModelInfo], model_id: str) -> Optional[GroqModelInfo]:
    for model in models:
        if model.id == model_id:
            return model
    return None


def estimate_max_input_chars(
    context_window: int,
    *,
    reserved_tokens: int = 900,
    output_tokens: int = 300,
    cap: int = 12000,
) -> int:
    """Rough max README characters that fit in context alongside prompts."""
    available = context_window - reserved_tokens - output_tokens
    chars = int(max(available, 500) * CHARS_PER_TOKEN_ESTIMATE)
    return max(1500, min(chars, cap))


def truncate_text_for_model(
    text: str,
    model_id: str,
    models: list[GroqModelInfo],
    *,
    reserved_tokens: int = 900,
    output_tokens: int = 300,
) -> str:
    """Shorten text so chat completion stays within the model context window."""
    info = find_model_info(models, model_id)
    context_window = info.context_window if info and info.context_window else 131072
    max_chars = estimate_max_input_chars(
        context_window,
        reserved_tokens=reserved_tokens,
        output_tokens=output_tokens,
    )

    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    break_at = truncated.rfind("\n\n")
    if break_at > int(max_chars * 0.5):
        truncated = truncated[:break_at]

    logger.info(
        "Truncated input for %s: %s → %s chars (context_window=%s)",
        model_id,
        len(text),
        len(truncated),
        context_window,
    )
    return truncated + "\n\n[Content truncated to fit model context limit.]"
