"""Shared Groq HTTP client with per-model rate limiting."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from resume_assistant.core.errors import ConfigurationError, GroqApiError, groq_error_from_exception
from resume_assistant.integrations.groq.constants import GROQ_CHAT_URL
from resume_assistant.integrations.groq.models import GroqModelInfo, default_model_id, fetch_groq_models
from resume_assistant.integrations.groq.rate_limiter import GroqRateLimiter, RateLimitSnapshot

load_dotenv()
logger = logging.getLogger(__name__)

CHAT_URL = GROQ_CHAT_URL


def _is_context_length_error(response: requests.Response) -> bool:
    try:
        body = response.json()
        err = body.get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
    except (ValueError, AttributeError, requests.exceptions.JSONDecodeError):
        msg = response.text[:300]
    lower = msg.lower()
    return "reduce the length" in lower or "context length" in lower or "too large" in lower


class GroqClient:
    """Groq API wrapper: model list, chat completions, dynamic rate limits."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
        if not self.api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your Groq API key."
            )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.rate_limiter = GroqRateLimiter()
        self._models_cache: Optional[List[GroqModelInfo]] = None

    def fetch_chat_models(self, *, refresh: bool = False) -> List[GroqModelInfo]:
        if self._models_cache is None or refresh:
            self._models_cache = fetch_groq_models(self.api_key)
        return self._models_cache

    def get_default_model_id(self) -> str:
        return default_model_id(self.fetch_chat_models())

    def get_rate_limit_snapshot(self, model_id: str) -> Optional[RateLimitSnapshot]:
        return self.rate_limiter.get_snapshot(model_id)

    def probe_rate_limits(self, model_id: str) -> Optional[RateLimitSnapshot]:
        """
        Minimal chat request to read x-ratelimit-* headers for the given model.
        Used when the user selects a model before any full AI task runs.
        """
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0,
        }
        try:
            self.chat_completion(payload, max_retries=1, fallback_model=None)
        except GroqApiError:
            # Headers may still have been stored on the failed response.
            pass
        return self.get_rate_limit_snapshot(model_id)

    def chat_completion(
        self,
        payload: Dict[str, Any],
        *,
        max_retries: int = 3,
        fallback_model: Optional[str] = None,
    ) -> str:
        """
        Call chat completions with proactive throttling and 429 retries.
        Updates rate-limit state from every response.
        """
        model = payload.get("model") or self.get_default_model_id()
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            self.rate_limiter.wait_before_request(model)
            attempt_payload = {**payload, "model": model}
            try:
                response = requests.post(
                    CHAT_URL,
                    headers=self.headers,
                    json=attempt_payload,
                    timeout=120,
                )
                self.rate_limiter.update_from_headers(model, response.headers)

                if response.status_code == 429:
                    self.rate_limiter.wait_after_429(model, response.headers)
                    last_error = requests.HTTPError(response=response)
                    if fallback_model and fallback_model != model:
                        logger.info("Rate limit on %s, switching to %s", model, fallback_model)
                        model = fallback_model
                    continue

                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    raise GroqApiError(
                        "The AI returned an empty response. Please try again.",
                        detail=str(data)[:500],
                    )
                return choices[0]["message"]["content"].strip()

            except requests.exceptions.HTTPError as exc:
                last_error = exc
                if exc.response is not None:
                    self.rate_limiter.update_from_headers(model, exc.response.headers)
                    status = exc.response.status_code
                    if status == 429 and attempt < max_retries:
                        self.rate_limiter.wait_after_429(model, exc.response.headers)
                        if fallback_model and fallback_model != model:
                            model = fallback_model
                        continue
                    if (
                        status == 400
                        and attempt < max_retries
                        and fallback_model
                        and fallback_model != model
                        and _is_context_length_error(exc.response)
                    ):
                        logger.info(
                            "Context length exceeded for %s, switching to %s",
                            model,
                            fallback_model,
                        )
                        model = fallback_model
                        continue
                if attempt >= max_retries:
                    raise groq_error_from_exception(exc) from exc
                logger.warning("Groq HTTP error attempt %s/%s: %s", attempt, max_retries, exc)

            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt >= max_retries:
                    raise groq_error_from_exception(exc) from exc
                logger.warning("Groq network error attempt %s/%s: %s", attempt, max_retries, exc)

            except (KeyError, IndexError, TypeError) as exc:
                raise GroqApiError(
                    "Unexpected response format from the AI service.",
                    detail=str(exc),
                ) from exc

        raise groq_error_from_exception(last_error)  # type: ignore[arg-type]
