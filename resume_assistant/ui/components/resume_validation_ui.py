"""Streamlit UI for resume JSON validation status."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from resume_assistant.core.resume_validation import (
    ResumeValidationResult,
    validate_and_normalize_resume,
)
from resume_assistant.ui.components.resume_editor import bump_resume_editor_epoch


def render_resume_validation_panel(result: ResumeValidationResult) -> None:
    """Show validation errors, warnings, and auto-fixes."""
    if result.export_ready:
        st.success("Resume structure is valid and ready for PDF export.")
    elif result.errors:
        st.error("Resume structure has issues that block PDF export.")
    else:
        st.warning("Resume structure needs attention before export.")

    if result.fixes_applied:
        with st.expander(
            f"Auto-fixes applied ({len(result.fixes_applied)})",
            expanded=False,
        ):
            for fix in result.fixes_applied:
                st.markdown(f"- {fix}")

    if result.errors:
        st.markdown("**Errors**")
        for err in result.errors:
            st.markdown(f"- {err}")

    if result.warnings:
        st.markdown("**Warnings**")
        for warn in result.warnings:
            st.markdown(f"- {warn}")

    if not result.errors and not result.warnings and not result.fixes_applied:
        st.caption("All required sections are present with expected types.")


def store_validation_result(result: ResumeValidationResult) -> None:
    st.session_state["resume_validation"] = result


def persist_resume_data(data: Dict[str, Any]) -> ResumeValidationResult:
    """Validate, save to session, and refresh form widget keys."""
    result = validate_and_normalize_resume(data)
    st.session_state.resume_data = result.normalized
    store_validation_result(result)
    bump_resume_editor_epoch()
    return result
