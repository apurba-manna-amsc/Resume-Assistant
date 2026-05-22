"""Application errors and user-facing messages for the Streamlit UI."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base error with a safe message for the GUI."""

    def __init__(self, user_message: str, detail: Optional[str] = None):
        self.user_message = user_message
        self.detail = detail or user_message
        super().__init__(self.detail)


class ConfigurationError(AppError):
    """Missing or invalid environment configuration."""


class GroqApiError(AppError):
    """Groq API request failed."""


class GroqRateLimitError(GroqApiError):
    """Groq rate limit (HTTP 429)."""


class ResumeJsonParseError(AppError):
    """LLM returned resume JSON that could not be parsed."""


class ResumeGenerationError(AppError):
    """Full resume generation failed after retries."""


class GitHubApiError(AppError):
    """GitHub API request failed."""


class FileProcessingError(AppError):
    """Resume file upload or text extraction failed."""


class PdfExportError(AppError):
    """PDF export failed."""


class ChatUpdateError(AppError):
    """Chat-based resume update failed."""


def _safe_github_message(response: requests.Response, username: str) -> str:
    status = response.status_code
    if status == 404:
        return f'GitHub user "{username}" was not found. Check the username and try again.'
    if status == 401:
        return "GitHub rejected the token (401). Check that your personal access token is valid."
    if status == 403:
        try:
            body = response.json()
            msg = body.get("message", "")
        except (json.JSONDecodeError, ValueError):
            msg = response.text[:200]
        if "rate limit" in msg.lower():
            return (
                "GitHub API rate limit reached. Add a personal access token in the Projects section "
                "or wait a few minutes and try again."
            )
        return f"GitHub denied access (403). {msg or 'Check your token or permissions.'}"
    if status == 429:
        return "GitHub rate limit exceeded. Wait a few minutes or use a personal access token."
    return f"GitHub request failed (HTTP {status}). Please try again later."


def github_error_from_response(response: requests.Response, username: str) -> GitHubApiError:
    return GitHubApiError(_safe_github_message(response, username), detail=response.text[:500])


def _safe_groq_message(response: Optional[requests.Response], fallback: str = "") -> str:
    if response is None:
        return fallback or "The AI service is unavailable. Please try again in a few minutes."

    status = response.status_code
    if status == 401:
        return "Invalid Groq API key. Update GROQ_API_KEY in your .env file and restart the app."
    if status == 429:
        return (
            "Groq rate limit reached. Wait a minute, increase GROQ_REQUEST_DELAY_SEC in .env, "
            "or summarize fewer repositories at once."
        )
    if status == 400:
        try:
            body = response.json()
            err = body.get("error", {})
            msg = err.get("message", "") if isinstance(err, dict) else str(err)
        except (json.JSONDecodeError, ValueError, AttributeError):
            msg = response.text[:200]
        return f"AI request was rejected: {msg or 'bad request'}"
    if status >= 500:
        return "The AI service is temporarily down. Please try again in a few minutes."
    return f"AI request failed (HTTP {status}). Please try again."


def groq_error_from_exception(exc: requests.exceptions.RequestException) -> GroqApiError:
    response = getattr(exc, "response", None)
    if response is not None and response.status_code == 429:
        return GroqRateLimitError(_safe_groq_message(response), detail=str(exc))
    if response is not None:
        return GroqApiError(_safe_groq_message(response), detail=str(exc))
    return GroqApiError(
        "Could not reach the AI service. Check your internet connection and try again.",
        detail=str(exc),
    )


def format_exception_for_user(exc: Exception) -> str:
    """Map any exception to a short, user-safe Streamlit message."""
    if isinstance(exc, AppError):
        return exc.user_message
    if isinstance(exc, requests.exceptions.Timeout):
        return "The request timed out. Please try again."
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "Network error. Check your connection and try again."
    if isinstance(exc, json.JSONDecodeError):
        return "Received invalid data from the AI. Please try generating again."
    if isinstance(exc, KeyError):
        return f"Resume data is missing a required field: {exc}. Try regenerating the resume."
    if isinstance(exc, ValueError):
        return str(exc)
    return "Something unexpected went wrong. Please try again or refresh the page."


def log_exception(context: str, exc: Exception) -> None:
    """Log technical detail for operators; never shown verbatim in the GUI."""
    if isinstance(exc, AppError):
        logger.error("%s: %s | detail=%s", context, exc.user_message, exc.detail, exc_info=True)
    else:
        logger.exception("%s: %s", context, exc)


def show_user_error(exc: Exception, *, context: str = "") -> None:
    """Display an error in Streamlit and log the underlying cause."""
    import streamlit as st

    log_exception(context or "UI error", exc)
    prefix = f"**{context}:** " if context else ""
    st.error(f"{prefix}{format_exception_for_user(exc)}")


def show_user_warning(message: str) -> None:
    import streamlit as st

    st.warning(message)
