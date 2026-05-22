"""GitHub project fetch and Groq summarization UI."""

from __future__ import annotations

from typing import Dict

import streamlit as st

from resume_assistant.core.errors import (
    AppError,
    format_exception_for_user,
    log_exception,
    show_user_warning,
)
from resume_assistant.integrations.github import GitHubRepositoryClient
from resume_assistant.integrations.groq import GroqResumeService


def fetch_github_readmes_with_ui(
    username: str,
    token: str = "",
) -> Dict[str, str]:
    """Fetch READMEs with Streamlit progress indicators."""
    client = GitHubRepositoryClient()
    container = st.container()
    with container:
        st.markdown("#### GitHub repository extraction")
        progress = st.progress(0)
        status = st.empty()
        status.text("Fetching repositories list...")

    def on_progress(current: int, total: int, repo_name: str) -> None:
        progress.progress(current / total)
        status.text(f"Processed {current}/{total}: {repo_name}")

    try:
        result = client.fetch_readme_contents(
            username, token, on_progress=on_progress
        )
        if not result:
            st.warning("No repositories found or no README files extracted.")
        else:
            status.text(
                f"Extraction complete: README files in {len(result)} repositories"
            )
            progress.progress(1.0)
        return result
    except AppError:
        status.empty()
        raise


def summarize_projects_with_ui(
    github_projects: Dict[str, str],
    groq_service: GroqResumeService,
) -> Dict[str, str]:
    """Summarize each repo README via Groq with progress UI."""
    if not github_projects:
        return {}

    container = st.container()
    with container:
        st.markdown("#### AI project summarization")
        progress = st.progress(0)
        status = st.empty()

    try:
        status.text("Starting AI summarization (auto rate-limit pacing)...")
        total = len(github_projects)
        summaries: Dict[str, str] = {}

        for i, (project_name, content) in enumerate(github_projects.items()):
            progress.progress((i + 1) / total)
            status.text(f"Summarizing {project_name} ({i + 1}/{total})...")
            try:
                summaries[project_name] = groq_service.summarize_project_readme(
                    content, project_name
                )
            except AppError as exc:
                log_exception(f"Summarize {project_name}", exc)
                show_user_warning(
                    f"Could not summarize **{project_name}**: "
                    f"{format_exception_for_user(exc)} Using raw README text instead."
                )
                summaries[project_name] = content[:4000]

        status.text(f"Summarization complete: {len(summaries)} project(s) processed.")
        progress.progress(1.0)
        return summaries
    except AppError:
        raise
    except Exception as exc:
        log_exception("GitHub summarization", exc)
        raise AppError(
            "Project summarization failed unexpectedly. Please try again.",
            detail=str(exc),
        ) from exc
