"""Groq model picker and rate-limit status UI."""

from __future__ import annotations

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


def render_groq_model_settings() -> None:
    """Model picker, free-model list, and live rate-limit counters."""
    catalog: list[GroqModelInfo] = st.session_state.get("groq_model_catalog") or []
    if not catalog:
        show_user_warning("No Groq chat models loaded. Check your API key.")
        return

    free_models = [m for m in catalog if m.is_free]
    paid_models = [m for m in catalog if not m.is_free]

    with st.expander("AI model and rate limits", expanded=True):
        col_refresh, _ = st.columns([1, 3])
        with col_refresh:
            if st.button("Refresh models", key="refresh_groq_models"):
                st.session_state.groq_model_catalog = (
                    st.session_state.groq_client.fetch_chat_models(refresh=True)
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
            "Select AI model",
            options=labels,
            index=default_index,
            help="Free-tier models are listed with (Free). Rate limits apply per model.",
        )
        st.session_state.selected_groq_model = model_ids[labels.index(chosen_label)]

        selected = next(
            (m for m in catalog if m.id == st.session_state.selected_groq_model),
            None,
        )
        if selected and not selected.supports_long_readme:
            show_user_warning(
                f"**{selected.id}** has a small context window ({selected.context_window:,} tokens). "
                "GitHub README summarization may fail or be truncated. Prefer "
                "**llama-3.3-70b-versatile** or **llama-3.1-8b-instant** for many repos."
            )

        st.markdown("**Free chat models** (typical Groq free tier)")
        if free_models:
            st.markdown(", ".join(f"`{m.id}`" for m in free_models))
        else:
            st.caption("No models marked free. Set GROQ_FREE_MODEL_IDS in .env to customize.")

        if paid_models:
            with st.expander("Other available models", expanded=False):
                st.markdown(", ".join(f"`{m.id}`" for m in paid_models))

        snap: Optional[RateLimitSnapshot] = st.session_state.groq_client.get_rate_limit_snapshot(
            st.session_state.selected_groq_model
        )
        if snap and (
            snap.remaining_requests is not None or snap.remaining_tokens is not None
        ):
            st.markdown("**Rate limit status** (from last API response for this model)")
            cols = st.columns(2)
            if snap.remaining_requests is not None:
                cols[0].metric(
                    "Requests remaining",
                    snap.remaining_requests,
                    help=f"Resets in ~{snap.reset_requests_sec or '?'}s",
                )
                if snap.limit_requests:
                    cols[0].caption(f"Daily limit: {snap.limit_requests}")
            if snap.remaining_tokens is not None:
                cols[1].metric(
                    "Tokens remaining (per minute)",
                    snap.remaining_tokens,
                    help=f"Resets in ~{snap.reset_tokens_sec or '?'}s",
                )
                if snap.limit_tokens:
                    cols[1].caption(f"TPM limit: {snap.limit_tokens}")
            st.caption(
                "The app waits automatically when quota is low to reduce 429 errors."
            )
        else:
            st.caption(
                "Rate limits appear here after the first AI call for the selected model."
            )
