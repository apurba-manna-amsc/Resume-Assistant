"""Main Streamlit application orchestration."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st
from dotenv import load_dotenv

from resume_assistant.core.errors import (
    AppError,
    FileProcessingError,
    PdfExportError,
    ResumeJsonParseError,
    log_exception,
    show_user_error,
    show_user_warning,
)
from resume_assistant.export import ResumePdfExporter
from resume_assistant.integrations.groq import GroqClient, GroqResumeService
from resume_assistant.services.file_parser import parse_uploaded_resume_text
from resume_assistant.ui.components.chat_sidebar import ResumeChatSidebar
from resume_assistant.ui.components.github_projects import (
    fetch_github_readmes_with_ui,
    summarize_projects_with_ui,
)
from resume_assistant.ui.components.model_settings import (
    init_groq_session,
    render_groq_model_settings,
)
from resume_assistant.ui.components.resume_editor import render_resume_form_editor
from resume_assistant.ui.logging_setup import configure_logging

load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)


class ResumeAssistantApp:
    """Wires UI sections to integrations and services."""

    def __init__(self) -> None:
        self._groq_resume_service: Optional[GroqResumeService] = None
        self._pdf_exporter: Optional[ResumePdfExporter] = None
        self._chat_sidebar: Optional[ResumeChatSidebar] = None
        self._configure_page()

    def _configure_page(self) -> None:
        st.set_page_config(
            page_title="AI Resume Customization System",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="collapsed",
        )

    @property
    def groq_resume_service(self) -> GroqResumeService:
        client: GroqClient = st.session_state.groq_client
        model_id: str = st.session_state.selected_groq_model
        if self._groq_resume_service is None:
            self._groq_resume_service = GroqResumeService(
                groq_client=client, model_id=model_id
            )
        else:
            self._groq_resume_service.client = client
            self._groq_resume_service.set_model(model_id)
        return self._groq_resume_service

    @property
    def pdf_exporter(self) -> ResumePdfExporter:
        if self._pdf_exporter is None:
            self._pdf_exporter = ResumePdfExporter()
        return self._pdf_exporter

    @property
    def chat_sidebar(self) -> ResumeChatSidebar:
        if self._chat_sidebar is None:
            self._chat_sidebar = ResumeChatSidebar()
        return self._chat_sidebar

    def ensure_groq_api_key_configured(self) -> bool:
        if not os.getenv("GROQ_API_KEY", "").strip():
            show_user_error(
                AppError(
                    "GROQ_API_KEY is not configured. Copy `.env.example` to `.env`, "
                    "add your key, and restart the app."
                ),
                context="Configuration",
            )
            return False
        try:
            init_groq_session()
            return True
        except AppError as exc:
            show_user_error(exc, context="Configuration")
            return False

    @staticmethod
    def _is_placeholder_resume(data: Dict[str, Any]) -> bool:
        name = (data.get("overview") or {}).get("name", "")
        return name.strip() in ("", "Your Name")

    def run_app(self) -> None:
        try:
            self._run_app_body()
        except AppError as exc:
            show_user_error(exc)
        except Exception as exc:
            log_exception("Unhandled app error", exc)
            show_user_error(exc)

    def _run_app_body(self) -> None:
        st.title("ResumeBot")
        st.markdown(
            "Transform your resume to match any job description using AI and your GitHub projects."
        )

        if not self.ensure_groq_api_key_configured():
            return

        render_groq_model_settings()

        if st.session_state.get("resume_data"):
            try:
                self.chat_sidebar.process_pending_chat_updates()
            except AppError as exc:
                show_user_error(exc, context="Chat assistant")

        for key, default in (
            ("resume_data", None),
            ("project_summaries", {}),
            ("extracted_resume_text", ""),
        ):
            if key not in st.session_state:
                st.session_state[key] = default

        st.header("Input information")
        manual_projects = self._render_inputs()
        self._render_generate_section(manual_projects)
        self._render_edit_and_export()
        self.chat_sidebar.render_sidebar_chat()

    def _render_inputs(self) -> str:
        manual_projects = ""
        with st.expander("Resume input", expanded=True):
            method = st.radio("Choose input method:", ["Upload File", "Paste Text"])
            if method == "Upload File":
                uploaded = st.file_uploader("Upload your resume", type=["txt", "pdf", "md"])
                if uploaded:
                    try:
                        text = parse_uploaded_resume_text(uploaded)
                        st.session_state.extracted_resume_text = text
                        st.success("Resume file loaded successfully.")
                        with st.expander("View extracted text", expanded=False):
                            st.text_area("Extracted resume text", value=text, height=300, disabled=True)
                    except FileProcessingError as exc:
                        show_user_error(exc, context="Resume upload")
                        st.session_state.extracted_resume_text = ""
            else:
                st.session_state.extracted_resume_text = st.text_area(
                    "Paste your resume text here:", height=200
                )

        with st.expander("Projects input", expanded=True):
            source = st.radio(
                "Choose project source:",
                ["GitHub Username", "Manual Input", "Both"],
            )
            if source in ("GitHub Username", "Both"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    username = st.text_input("GitHub Username:")
                with c2:
                    token = st.text_input("GitHub Token (Optional):", type="password")
                if username and st.button("Fetch & summarize GitHub projects"):
                    try:
                        with st.spinner("Fetching GitHub repositories..."):
                            repos = fetch_github_readmes_with_ui(username, token)
                        if repos:
                            with st.spinner("Summarizing projects with AI..."):
                                summaries = summarize_projects_with_ui(
                                    repos, self.groq_resume_service
                                )
                            st.session_state.project_summaries.update(summaries)
                            st.success(f"Processed {len(summaries)} project(s) from GitHub.")
                            with st.expander("View processed projects", expanded=False):
                                for name, summary in summaries.items():
                                    preview = summary[:300] + ("..." if len(summary) > 300 else "")
                                    st.markdown(f"**{name}** — {preview}")
                        else:
                            show_user_warning(
                                "No README files were found in this user's public repositories."
                            )
                    except AppError as exc:
                        show_user_error(exc, context="GitHub projects")
            if source in ("Manual Input", "Both"):
                manual_projects = st.text_area(
                    "Manual project descriptions:",
                    placeholder="Describe your projects here...",
                    height=150,
                )
                if manual_projects:
                    st.session_state.project_summaries["manual_projects"] = manual_projects

        with st.expander("Job description", expanded=True):
            st.session_state["_job_description"] = st.text_area(
                "Paste the job description here:",
                placeholder="Enter the complete job description...",
                height=200,
                key="job_description_input",
            )
        return manual_projects

    def _render_generate_section(self, manual_projects: str) -> None:
        job_description = st.session_state.get("_job_description", "")
        if not st.button("Generate customized resume", type="primary"):
            return
        if not st.session_state.extracted_resume_text.strip():
            show_user_error(AppError("Please upload or paste your resume before generating."), context="Validation")
            return
        if not st.session_state.project_summaries and not manual_projects.strip():
            show_user_error(
                AppError("Please add GitHub projects or manual project descriptions before generating."),
                context="Validation",
            )
            return
        if not job_description.strip():
            show_user_error(AppError("Please paste the target job description before generating."), context="Validation")
            return
        try:
            with st.spinner("Generating customized resume..."):
                all_projects = "\n\n".join(
                    f"**{name}**: {content}"
                    for name, content in st.session_state.project_summaries.items()
                )
                if manual_projects.strip():
                    all_projects += f"\n\n**manual_projects**: {manual_projects}"
                resume_json = self.groq_resume_service.generate_tailored_resume_json(
                    st.session_state.extracted_resume_text,
                    all_projects,
                    job_description,
                )
                st.session_state.resume_data = resume_json
            if self._is_placeholder_resume(resume_json):
                show_user_warning(
                    "Resume was created with a minimal template because generation did not fully complete."
                )
            else:
                st.success("Resume generated successfully.")
        except (AppError, ResumeJsonParseError) as exc:
            show_user_error(exc, context="Resume generation")
        except ValueError as exc:
            show_user_error(exc, context="Resume generation")

    def _render_edit_and_export(self) -> None:
        if not st.session_state.resume_data:
            return
        st.header("Edit and preview")
        if st.session_state.get("chat_messages"):
            last = st.session_state.chat_messages[-1]
            if last.get("type") == "success":
                st.info("Resume was updated via the chat assistant.")
        tab1, tab2 = st.tabs(["Edit resume", "Raw JSON"])
        with tab1:
            try:
                edited = render_resume_form_editor(st.session_state.resume_data)
            except Exception as exc:
                log_exception("Resume form editor", exc)
                show_user_error(exc, context="Editor")
                edited = st.session_state.resume_data
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Save changes"):
                    st.session_state.resume_data = edited
                    st.success("Resume saved.")
                    st.rerun()
            with c2:
                if st.button("Discard unsaved edits"):
                    st.rerun()
        with tab2:
            st.json(st.session_state.resume_data)
        st.header("Export PDF")
        overview = st.session_state.resume_data.get("overview") or {}
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_"
            for c in (overview.get("name") or "resume")
        ).strip() or "resume"
        pdf_name = f"{safe_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
        if st.button("Generate PDF", type="primary", key="generate_pdf_btn"):
            try:
                with st.spinner("Building PDF..."):
                    path = self.pdf_exporter.export_resume_to_pdf(
                        st.session_state.resume_data, pdf_name
                    )
                    with open(path, "rb") as f:
                        st.session_state["pdf_download_bytes"] = f.read()
                        st.session_state["pdf_download_name"] = path
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                st.success("PDF ready. Use the download button below.")
            except PdfExportError as exc:
                show_user_error(exc, context="PDF export")
            except Exception as exc:
                log_exception("PDF export", exc)
                show_user_error(exc, context="PDF export")
        if st.session_state.get("pdf_download_bytes"):
            st.download_button(
                label="Download PDF",
                data=st.session_state["pdf_download_bytes"],
                file_name=st.session_state.get("pdf_download_name", "resume.pdf"),
                mime="application/pdf",
                key="download_pdf",
            )
