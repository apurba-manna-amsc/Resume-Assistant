"""Streamlit UI for resume JSON validation status."""

from __future__ import annotations

import streamlit as st

from resume_assistant.core.resume_validation import ResumeValidationResult


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
