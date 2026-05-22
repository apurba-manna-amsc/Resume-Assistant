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


def render_groq_model_settings(*, in_sidebar: bool = False) -> None:
    """Model picker, free-model list, and live rate-limit counters."""
    catalog: list[GroqModelInfo] = st.session_state.get("groq_model_catalog") or []
    if not catalog:
        show_user_warning("No Groq chat models loaded. Check your API key.")
        return

    free_models = [m for m in catalog if m.is_free]
    paid_models = [m for m in catalog if not m.is_free]

    def _render_body() -> None:
        if st.button("Refresh models", key="refresh_groq_models", use_container_width=in_sidebar):
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
            "AI model",
            options=labels,
            index=default_index,
            help="Free-tier models are marked (Free). Rate limits apply per model.",
        )
        st.session_state.selected_groq_model = model_ids[labels.index(chosen_label)]

        selected = next(
            (m for m in catalog if m.id == st.session_state.selected_groq_model),
            None,
        )
        if selected and not selected.supports_long_readme:
            show_user_warning(
                f"**{selected.id}** has a small context ({selected.context_window:,} tokens). "
                "Prefer **llama-3.3-70b-versatile** or **llama-3.1-8b-instant** for GitHub READMEs."
            )

        snap: Optional[RateLimitSnapshot] = st.session_state.groq_client.get_rate_limit_snapshot(
            st.session_state.selected_groq_model
        )
        if snap and (
            snap.remaining_requests is not None or snap.remaining_tokens is not None
        ):
            cols = st.columns(2)
            if snap.remaining_requests is not None:
                cols[0].metric("Requests left", snap.remaining_requests)
            if snap.remaining_tokens is not None:
                cols[1].metric("Tokens / min", snap.remaining_tokens)
            st.caption("Auto-pacing when quota is low.")
        else:
            st.caption("Rate limits show after the first AI call.")

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
