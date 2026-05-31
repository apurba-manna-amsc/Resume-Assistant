"""Groq model picker and rate-limit status UI."""

from __future__ import annotations

import os
from typing import Optional

import streamlit as st

from resume_assistant.core.errors import show_user_warning
from resume_assistant.integrations.groq import GroqClient, GroqModelInfo, default_model_id
from resume_assistant.integrations.groq.rate_limiter import RateLimitSnapshot


def _probe_all_on_refresh() -> bool:
    return os.getenv("GROQ_PROBE_ALL_LIMITS_ON_REFRESH", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def init_groq_session() -> None:
    """Create shared Groq client and model catalog in Streamlit session."""
    client: GroqClient
    if "groq_client" not in st.session_state:
        st.session_state.groq_client = GroqClient()
    client = st.session_state.groq_client

    if "groq_model_catalog" not in st.session_state:
        probe = _probe_all_on_refresh()
        with st.spinner(
            "Loading models from Groq API"
            + (" and fetching rate limits…" if probe else "…")
        ):
            st.session_state.groq_model_catalog = client.fetch_chat_models(
                refresh=True, probe_limits=probe
            )

    catalog: list[GroqModelInfo] = st.session_state.groq_model_catalog
    if "selected_groq_model" not in st.session_state:
        st.session_state.selected_groq_model = default_model_id(catalog)


def _refresh_catalog(client: GroqClient, *, probe_limits: bool) -> None:
    with st.spinner(
        "Refreshing models"
        + (" and rate limits from Groq…" if probe_limits else "…")
    ):
        st.session_state.groq_model_catalog = client.refresh_model_catalog(
            probe_limits=probe_limits
        )


def render_rate_limit_status(
    client: GroqClient,
    model_id: str,
    model_info: Optional[GroqModelInfo],
) -> None:
    """Show context window and live quota from Groq response headers."""
    if model_info:
        if model_info.context_window:
            st.caption(f"Context window: **{model_info.context_window:,}** tokens")
        if model_info.max_completion_tokens:
            st.caption(
                f"Max output: **{model_info.max_completion_tokens:,}** tokens"
            )
        if model_info.limit_requests is not None:
            st.caption(
                f"Daily cap (from API): **{model_info.limit_requests:,}** requests · "
                f"**{model_info.limit_tokens:,}** tokens/min"
                if model_info.limit_tokens
                else f"Daily cap (from API): **{model_info.limit_requests:,}** requests"
            )

    snap: Optional[RateLimitSnapshot] = client.get_rate_limit_snapshot(model_id)
    if not snap and model_info and model_info.has_limits_loaded:
        snap = RateLimitSnapshot(
            model_id=model_id,
            limit_requests=model_info.limit_requests,
            remaining_requests=model_info.remaining_requests,
            reset_requests_sec=model_info.reset_requests_sec,
            limit_tokens=model_info.limit_tokens,
            remaining_tokens=model_info.remaining_tokens,
            reset_tokens_sec=model_info.reset_tokens_sec,
        )

    if not snap or (
        snap.remaining_requests is None and snap.remaining_tokens is None
    ):
        st.caption('Click **Refresh all limits** to load quotas from Groq headers.')
        return

    st.markdown("**Live quota**")
    if snap.remaining_requests == 0:
        reset = snap.reset_requests_sec
        if reset and reset > 60:
            show_user_warning(
                f"**{model_id}** is rate limited. "
                f"Resets in ~{int(reset // 60)} min. Try another model."
            )
        elif reset:
            show_user_warning(
                f"**{model_id}** is rate limited. Resets in ~{int(reset)}s."
            )

    if snap.limit_requests is not None and snap.remaining_requests is not None:
        used_req = snap.limit_requests - snap.remaining_requests
        ratio = max(0.0, min(1.0, used_req / snap.limit_requests))
        st.progress(
            1.0 - ratio,
            text=f"Requests today: {snap.remaining_requests:,} / {snap.limit_requests:,}",
        )
        if snap.reset_requests_sec is not None:
            st.caption(f"Daily window resets in ~{snap.reset_requests_sec:.0f}s")

    if snap.limit_tokens is not None and snap.remaining_tokens is not None:
        used_tok = snap.limit_tokens - snap.remaining_tokens
        ratio = max(0.0, min(1.0, used_tok / snap.limit_tokens))
        st.progress(
            1.0 - ratio,
            text=f"Tokens/min: {snap.remaining_tokens:,} / {snap.limit_tokens:,}",
        )
        if snap.reset_tokens_sec is not None:
            st.caption(f"Token window resets in ~{snap.reset_tokens_sec:.0f}s")

    st.caption("Limits are read from Groq response headers (always up to date for your key).")


def render_model_catalog_table(catalog: list[GroqModelInfo]) -> None:
    if not catalog:
        return
    rows = [m.to_display_row() for m in catalog]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_groq_model_settings(*, in_sidebar: bool = False) -> None:
    """Model picker with API-fetched metadata and live rate limits."""
    catalog: list[GroqModelInfo] = st.session_state.get("groq_model_catalog") or []
    if not catalog:
        show_user_warning("No Groq chat models loaded. Check your API key.")
        return

    client: GroqClient = st.session_state.groq_client

    def _render_body() -> None:
        if in_sidebar:
            if st.button("Refresh models", key="refresh_groq_models", use_container_width=True):
                _refresh_catalog(client, probe_limits=False)
                st.rerun()
            if st.button(
                "Refresh all limits",
                key="refresh_groq_rate_limits",
                use_container_width=True,
            ):
                _refresh_catalog(client, probe_limits=True)
                st.rerun()
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Refresh models", key="refresh_groq_models"):
                    _refresh_catalog(client, probe_limits=False)
                    st.rerun()
            with col_b:
                if st.button("Refresh all limits", key="refresh_groq_rate_limits"):
                    _refresh_catalog(client, probe_limits=True)
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
            help="Sorted by daily request quota (from Groq headers). Labels update when limits are refreshed.",
        )
        st.session_state.selected_groq_model = model_ids[labels.index(chosen_label)]

        selected = next(
            (m for m in catalog if m.id == st.session_state.selected_groq_model),
            None,
        )
        if selected:
            if selected.has_strict_daily_quota:
                show_user_warning(
                    f"**{selected.id}** has a low daily cap "
                    f"({selected.limit_requests:,} req/day from Groq). "
                    "Prefer a higher-quota model for GitHub summarization."
                )
            elif not selected.supports_long_readme:
                show_user_warning(
                    f"**{selected.id}** has a small context ({selected.context_window:,} tokens). "
                    "Long GitHub READMEs may be truncated."
                )

        render_rate_limit_status(
            client, st.session_state.selected_groq_model, selected
        )

        with st.expander("All models (from Groq API)", expanded=False):
            st.caption(
                "Metadata from `GET /v1/models`; daily/token caps from rate-limit headers."
            )
            render_model_catalog_table(catalog)

    if in_sidebar:
        _render_body()
    else:
        with st.expander("AI model and rate limits", expanded=False):
            _render_body()
