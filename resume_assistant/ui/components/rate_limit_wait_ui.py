"""Streamlit UI for Groq rate-limit wait countdown."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import streamlit as st

WaitCallback = Callable[[str, str, float, float], None]

SESSION_WAIT_KEY = "groq_rate_limit_wait"
PLACEHOLDER_KEY = "_groq_rate_limit_wait_ui"


def _format_wait_duration(seconds: float) -> str:
    secs = max(0, int(seconds))
    if secs >= 3600:
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s"
    if secs >= 60:
        m, s = divmod(secs, 60)
        return f"{m}m {s}s"
    return f"{secs}s"


def format_rate_limit_wait_message(
    model_id: str,
    reason: str,
    remaining_sec: float,
    total_sec: float,
) -> str:
    remaining = _format_wait_duration(remaining_sec)
    total = _format_wait_duration(total_sec)
    reason_text = {
        "low_daily_requests": "daily request quota is low",
        "low_tokens_per_minute": "tokens-per-minute quota is low",
        "min_request_interval": "spacing out requests",
        "rate_limit_429": "rate limit (HTTP 429) was hit",
    }.get(reason, "rate limit")
    cap_note = ""
    if reason == "rate_limit_429" and total_sec >= 119:
        cap_note = " (wait capped — will retry afterward)"
    return (
        f"**Waiting for Groq rate limit reset** — model `{model_id}`: "
        f"{reason_text}. **~{remaining}** remaining (of ~{total} wait){cap_note}."
    )


def init_rate_limit_wait_ui(*, in_sidebar: bool = True) -> None:
    """Create a placeholder for live wait messages during API calls."""
    if PLACEHOLDER_KEY not in st.session_state:
        container = st.sidebar if in_sidebar else st
        st.session_state[PLACEHOLDER_KEY] = container.empty()


def render_rate_limit_wait_banner() -> None:
    """Show active wait state during chunked sleep countdown."""
    wait: Optional[Dict[str, Any]] = st.session_state.get(SESSION_WAIT_KEY)
    placeholder = st.session_state.get(PLACEHOLDER_KEY)
    if not wait or not placeholder:
        if placeholder:
            placeholder.empty()
        return
    remaining = float(wait.get("remaining_sec", 0))
    if remaining <= 0:
        placeholder.empty()
        return
    placeholder.warning(
        format_rate_limit_wait_message(
            wait.get("model_id", "model"),
            wait.get("reason", "rate_limit_429"),
            remaining,
            float(wait.get("total_sec", remaining)),
        )
    )


def clear_rate_limit_wait_ui() -> None:
    st.session_state.pop(SESSION_WAIT_KEY, None)
    placeholder = st.session_state.get(PLACEHOLDER_KEY)
    if placeholder is not None:
        placeholder.empty()


def make_streamlit_wait_callback() -> WaitCallback:
    """Return a callback for GroqRateLimiter to drive the wait banner."""

    def on_wait(
        model_id: str,
        reason: str,
        remaining_sec: float,
        total_sec: float,
    ) -> None:
        if remaining_sec <= 0:
            clear_rate_limit_wait_ui()
            return
        st.session_state[SESSION_WAIT_KEY] = {
            "model_id": model_id,
            "reason": reason,
            "remaining_sec": remaining_sec,
            "total_sec": total_sec,
        }
        render_rate_limit_wait_banner()

    return on_wait


def attach_wait_callback_to_client(client: Any) -> None:
    """Wire Streamlit wait UI to the shared Groq client rate limiter."""
    init_rate_limit_wait_ui(in_sidebar=True)
    client.rate_limiter.set_wait_callback(make_streamlit_wait_callback())
