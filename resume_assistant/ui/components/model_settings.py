"""Groq model picker and rate-limit status UI."""

from __future__ import annotations

import os
from typing import Optional

import streamlit as st

from resume_assistant.core.errors import show_user_warning
from resume_assistant.integrations.groq import GroqClient, GroqModelInfo, default_model_id
from resume_assistant.integrations.groq.rate_limiter import RateLimitSnapshot


def init_groq_session() -> None:
    """Create shared Groq client and model catalog in Streamlit session."""
    if "groq_client" not in st.session_state:
        st.session_state.groq_client = GroqClient()
    if "groq_model_catalog" not in st.session_state:
        st.session_state.groq_model_catalog = (
            st.session_state.groq_client.fetch_chat_models()
        )
    catalog: list[GroqModelInfo] = st.session_state.groq_model_catalog
    if "selected_groq_model" not in st.session_state:
        st.session_state.selected_groq_model = default_model_id(catalog)
    if "_rate_limit_probed_model" not in st.session_state:
        st.session_state._rate_limit_probed_model = ""


def _probe_on_select_enabled() -> bool:
    return os.getenv("GROQ_PROBE_RATE_LIMIT_ON_SELECT", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _maybe_probe_rate_limits(client: GroqClient, model_id: str) -> None:
    """Fetch rate-limit headers when the user picks a new model."""
    if not _probe_on_select_enabled():
        return
    if st.session_state.get("_rate_limit_probed_model") == model_id:
        snap = client.get_rate_limit_snapshot(model_id)
        if snap and (
            snap.remaining_requests is not None or snap.remaining_tokens is not None
        ):
            return
    with st.spinner("Loading rate limits for this model…"):
        client.probe_rate_limits(model_id)
    st.session_state._rate_limit_probed_model = model_id


def render_rate_limit_status(
    client: GroqClient,
    model_id: str,
    model_info: Optional[GroqModelInfo],
) -> None:
    """Show context window and live quota from Groq response headers."""
    if model_info and model_info.context_window:
        st.caption(f"Context window: **{model_info.context_window:,}** tokens")

    snap: Optional[RateLimitSnapshot] = client.get_rate_limit_snapshot(model_id)
    if not snap or (
        snap.remaining_requests is None and snap.remaining_tokens is None
    ):
        st.caption(
            "Rate limits are loaded when you select a model or run an AI action. "
            "Click **Refresh limits** if needed."
        )
        return

    st.markdown("**Rate limits** (from Groq API)")
    if snap.limit_requests is not None and snap.remaining_requests is not None:
        used_req = snap.limit_requests - snap.remaining_requests
        ratio = max(0.0, min(1.0, used_req / snap.limit_requests))
        st.progress(
            1.0 - ratio,
            text=f"Requests: {snap.remaining_requests} / {snap.limit_requests} left",
        )
        if snap.reset_requests_sec is not None:
            st.caption(f"Request window resets in ~{snap.reset_requests_sec:.0f}s")
    elif snap.remaining_requests is not None:
        st.metric("Requests remaining", snap.remaining_requests)

    if snap.limit_tokens is not None and snap.remaining_tokens is not None:
        used_tok = snap.limit_tokens - snap.remaining_tokens
        ratio = max(0.0, min(1.0, used_tok / snap.limit_tokens))
        st.progress(
            1.0 - ratio,
            text=f"Tokens/min: {snap.remaining_tokens:,} / {snap.limit_tokens:,} left",
        )
        if snap.reset_tokens_sec is not None:
            st.caption(f"Token window resets in ~{snap.reset_tokens_sec:.0f}s")
    elif snap.remaining_tokens is not None:
        st.metric("Tokens remaining (per min)", f"{snap.remaining_tokens:,}")

    st.caption("The app waits automatically when quota is low.")


def render_groq_model_settings(*, in_sidebar: bool = False) -> None:
    """Model picker, free-model list, and live rate-limit counters."""
    catalog: list[GroqModelInfo] = st.session_state.get("groq_model_catalog") or []
    if not catalog:
        show_user_warning("No Groq chat models loaded. Check your API key.")
        return

    free_models = [m for m in catalog if m.is_free]
    paid_models = [m for m in catalog if not m.is_free]
    client: GroqClient = st.session_state.groq_client

    def _render_body() -> None:
        if in_sidebar:
            if st.button("Refresh models", key="refresh_groq_models", use_container_width=True):
                st.session_state.groq_model_catalog = client.fetch_chat_models(refresh=True)
                st.rerun()
            if st.button("Refresh limits", key="refresh_groq_rate_limits", use_container_width=True):
                st.session_state._rate_limit_probed_model = ""
                _maybe_probe_rate_limits(client, st.session_state.selected_groq_model)
                st.rerun()
        else:
            col_a, col_b = st.columns([1, 3])
            with col_a:
                if st.button("Refresh models", key="refresh_groq_models"):
                    st.session_state.groq_model_catalog = client.fetch_chat_models(
                        refresh=True
                    )
                    st.rerun()
            with col_b:
                if st.button("Refresh limits", key="refresh_groq_rate_limits"):
                    st.session_state._rate_limit_probed_model = ""
                    _maybe_probe_rate_limits(
                        client, st.session_state.selected_groq_model
                    )
                    st.rerun()

        labels = [m.label for m in catalog]
        model_ids = [m.id for m in catalog]
        current = st.session_state.selected_groq_model
        try:
            default_index = model_ids.index(current)
        except ValueError:
            default_index = 0

        chosen_label = st.selectbox(
            "AI model",
            options=labels,
            index=default_index,
            help="Free-tier models are marked (Free). Rate limits apply per model.",
        )
        new_model = model_ids[labels.index(chosen_label)]
        if new_model != st.session_state.selected_groq_model:
            st.session_state.selected_groq_model = new_model
            st.session_state._rate_limit_probed_model = ""

        _maybe_probe_rate_limits(client, st.session_state.selected_groq_model)

        selected = next(
            (m for m in catalog if m.id == st.session_state.selected_groq_model),
            None,
        )
        if selected and not selected.supports_long_readme:
            show_user_warning(
                f"**{selected.id}** has a small context ({selected.context_window:,} tokens). "
                "Prefer **llama-3.3-70b-versatile** or **llama-3.1-8b-instant** for GitHub READMEs."
            )

        render_rate_limit_status(
            client, st.session_state.selected_groq_model, selected
        )

        if not in_sidebar:
            st.markdown("**Free models**")
            if free_models:
                st.markdown(", ".join(f"`{m.id}`" for m in free_models))
            else:
                st.caption("Set GROQ_FREE_MODEL_IDS in .env to customize.")
            if paid_models:
                with st.expander("Other models", expanded=False):
                    st.markdown(", ".join(f"`{m.id}`" for m in paid_models))
        elif free_models:
            with st.expander("Free models", expanded=False):
                st.markdown(", ".join(f"`{m.id}`" for m in free_models))

    if in_sidebar:
        _render_body()
    else:
        with st.expander("AI model and rate limits", expanded=False):
            _render_body()
