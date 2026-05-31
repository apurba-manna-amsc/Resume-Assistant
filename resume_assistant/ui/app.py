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
    ResumeValidationError,
    log_exception,
    show_user_error,
    show_user_warning,
)
from resume_assistant.core.resume_validation import ResumeValidationResult
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
from resume_assistant.ui.components.resume_editor import (
    bump_resume_editor_epoch,
    render_resume_form_editor,
)
from resume_assistant.ui.components.resume_validation_ui import (
    persist_resume_data,
    render_resume_validation_panel,
)
from resume_assistant.ui.logging_setup import configure_logging
from resume_assistant.ui.theme import (
    inject_app_styles,
    render_page_header,
    render_readiness_bar,
    render_resume_preview_card,
)

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
            page_title="ResumeBot — AI Resume Tailor",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="expanded",
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

    @staticmethod
    def _validate_and_store_resume(data: Dict[str, Any]) -> ResumeValidationResult:
        return persist_resume_data(data)

    def run_app(self) -> None:
        try:
            self._run_app_body()
        except AppError as exc:
            show_user_error(exc)
        except Exception as exc:
            log_exception("Unhandled app error", exc)
            show_user_error(exc)

    def _init_session_defaults(self) -> None:
        for key, default in (
            ("resume_data", None),
            ("project_summaries", {}),
            ("extracted_resume_text", ""),
        ):
            if key not in st.session_state:
                st.session_state[key] = default

    def _render_sidebar(self) -> None:
        with st.sidebar:
            st.markdown("### Settings")
            render_groq_model_settings(in_sidebar=True)
            if st.session_state.get("resume_data"):
                st.divider()
                st.markdown("### Resume assistant")
                st.caption(
                    "After generating, use the chat below to edit sections "
                    '(e.g. "Add Python to my skills").'
                )

    def _run_app_body(self) -> None:
        inject_app_styles()
        render_page_header()

        if not self.ensure_groq_api_key_configured():
            return

        self._init_session_defaults()
        self._render_sidebar()

        if st.session_state.get("resume_data"):
            try:
                self.chat_sidebar.process_pending_chat_updates()
            except AppError as exc:
                show_user_error(exc, context="Chat assistant")

        manual_projects = st.session_state.project_summaries.get("manual_projects", "")

        tab_resume, tab_projects, tab_job = st.tabs(
            ["Resume", "Projects", "Job description"]
        )

        with tab_resume:
            self._render_resume_input()
        with tab_projects:
            manual_projects = self._render_projects_input(manual_projects)
        with tab_job:
            job_description = self._render_job_input()

        render_readiness_bar(
            has_resume=bool(st.session_state.extracted_resume_text.strip()),
            has_projects=bool(st.session_state.project_summaries),
            has_job=bool(job_description.strip()),
            has_generated=bool(st.session_state.resume_data),
        )

        self._render_generate_section(manual_projects, job_description)
        self._render_edit_and_export()
        self.chat_sidebar.render_sidebar_chat()

    def _render_resume_input(self) -> str:
        st.caption("Upload or paste your current resume.")
        method = st.radio(
            "Input method",
            ["Upload file", "Paste text"],
            horizontal=True,
            label_visibility="collapsed",
        )
        if method == "Upload file":
            uploaded = st.file_uploader(
                "Resume file",
                type=["txt", "pdf", "md"],
                help="Supported: TXT, PDF, Markdown",
            )
            if uploaded:
                try:
                    text = parse_uploaded_resume_text(uploaded)
                    st.session_state.extracted_resume_text = text
                    st.success(f"Loaded **{uploaded.name}** ({len(text):,} characters).")
                    with st.expander("Preview extracted text", expanded=False):
                        st.text_area(
                            "Extracted text",
                            value=text,
                            height=280,
                            disabled=True,
                            label_visibility="collapsed",
                        )
                except FileProcessingError as exc:
                    show_user_error(exc, context="Resume upload")
                    st.session_state.extracted_resume_text = ""
        else:
            st.session_state.extracted_resume_text = st.text_area(
                "Paste resume text",
                value=st.session_state.extracted_resume_text,
                height=220,
                placeholder="Paste your full resume here…",
            )
        return ""

    def _render_projects_input(self, manual_projects: str) -> str:
        st.caption("Import GitHub READMEs or describe projects manually.")
        source = st.radio(
            "Project source",
            ["GitHub", "Manual", "Both"],
            horizontal=True,
            label_visibility="collapsed",
        )
        if source in ("GitHub", "Both"):
            c1, c2 = st.columns([2, 1])
            with c1:
                username = st.text_input("GitHub username", placeholder="octocat")
            with c2:
                token = st.text_input(
                    "Token (optional)",
                    type="password",
                    help="Increases rate limits for private repos you can access.",
                )
            if username:
                if st.button(
                    "Fetch & summarize repositories",
                    type="secondary",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Fetching GitHub repositories…"):
                            repos = fetch_github_readmes_with_ui(username, token)
                        if repos:
                            with st.spinner("Summarizing with AI (rate limits auto-managed)…"):
                                summaries = summarize_projects_with_ui(
                                    repos, self.groq_resume_service
                                )
                            st.session_state.project_summaries.update(summaries)
                            st.success(f"Added **{len(summaries)}** project(s).")
                            with st.expander("Project summaries", expanded=False):
                                for name, summary in summaries.items():
                                    preview = summary[:280] + (
                                        "…" if len(summary) > 280 else ""
                                    )
                                    st.markdown(f"**{name}** — {preview}")
                        else:
                            show_user_warning(
                                "No README files found in this user's public repositories."
                            )
                    except AppError as exc:
                        show_user_error(exc, context="GitHub projects")

        if source in ("Manual", "Both"):
            manual_projects = st.text_area(
                "Manual project descriptions",
                value=manual_projects,
                placeholder="Describe side projects, internships, or portfolio work…",
                height=140,
            )
            if manual_projects.strip():
                st.session_state.project_summaries["manual_projects"] = manual_projects

        if st.session_state.project_summaries:
            with st.expander(
                f"Loaded projects ({len(st.session_state.project_summaries)})",
                expanded=False,
            ):
                for name in st.session_state.project_summaries:
                    st.markdown(f"- **{name}**")

        return manual_projects

    def _render_job_input(self) -> str:
        st.caption("Paste the full job posting so the AI can tailor your resume.")
        return st.text_area(
            "Job description",
            placeholder="Paste the complete job description…",
            height=240,
            key="job_description_input",
        )

    def _render_generate_section(
        self, manual_projects: str, job_description: str
    ) -> None:
        st.markdown(
            """
            <div class="rb-action-card">
                <h3>Generate tailored resume</h3>
                <p>Uses your resume, projects, and job description with the AI model
                selected in the sidebar.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ready = (
            bool(st.session_state.extracted_resume_text.strip())
            and bool(st.session_state.project_summaries or manual_projects.strip())
            and bool(job_description.strip())
        )
        if not ready:
            missing = []
            if not st.session_state.extracted_resume_text.strip():
                missing.append("resume")
            if not st.session_state.project_summaries and not manual_projects.strip():
                missing.append("projects")
            if not job_description.strip():
                missing.append("job description")
            st.caption(f"Still needed: {', '.join(missing)}.")

        if st.button(
            "Generate customized resume",
            type="primary",
            use_container_width=True,
            disabled=not ready,
        ):
            try:
                with st.spinner("Generating tailored resume…"):
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
                    validation = self._validate_and_store_resume(resume_json)
                if self._is_placeholder_resume(st.session_state.resume_data):
                    show_user_warning(
                        "Resume was created with a minimal template because "
                        "generation did not fully complete."
                    )
                else:
                    if validation.export_ready:
                        st.success(
                            "Resume generated and validated. Edit below or export to PDF."
                        )
                    else:
                        show_user_warning(
                            "Resume generated but validation reported issues. "
                            "Open the **Validation** tab before exporting."
                        )
                    st.balloons()
            except (AppError, ResumeJsonParseError) as exc:
                show_user_error(exc, context="Resume generation")
            except ValueError as exc:
                show_user_error(exc, context="Resume generation")

    def _render_edit_and_export(self) -> None:
        if not st.session_state.resume_data:
            return

        if "resume_validation" not in st.session_state:
            self._validate_and_store_resume(st.session_state.resume_data)

        validation: Optional[ResumeValidationResult] = st.session_state.get(
            "resume_validation"
        )

        st.divider()
        st.subheader("Edit & export")
        render_resume_preview_card(st.session_state.resume_data)

        if validation:
            if validation.export_ready:
                st.caption("Structure validated — ready for PDF export.")
            else:
                st.caption("Fix validation errors before exporting to PDF.")

        if st.session_state.get("chat_messages"):
            last = st.session_state.chat_messages[-1]
            if last.get("type") == "success":
                st.info("Resume updated via the sidebar assistant.")

        tab_edit, tab_validate, tab_json, tab_pdf = st.tabs(
            ["Form editor", "Validation", "Raw JSON", "PDF export"]
        )

        with tab_edit:
            try:
                edited = render_resume_form_editor(st.session_state.resume_data)
            except Exception as exc:
                log_exception("Resume form editor", exc)
                show_user_error(exc, context="Editor")
                edited = st.session_state.resume_data
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Save changes", type="primary", use_container_width=True):
                    result = self._validate_and_store_resume(edited)
                    if result.export_ready:
                        st.success("Resume saved and validated.")
                    else:
                        show_user_warning(
                            "Resume saved with validation issues. See the Validation tab."
                        )
                    st.rerun()
            with c2:
                if st.button("Re-validate", use_container_width=True):
                    self._validate_and_store_resume(st.session_state.resume_data)
                    st.rerun()
            with c3:
                if st.button("Discard unsaved edits", use_container_width=True):
                    bump_resume_editor_epoch()
                    st.rerun()

        with tab_validate:
            if validation:
                render_resume_validation_panel(validation)
            if st.button("Run validation again", key="revalidate_btn"):
                result = self._validate_and_store_resume(st.session_state.resume_data)
                render_resume_validation_panel(result)
                st.rerun()

        with tab_json:
            st.json(st.session_state.resume_data)

        with tab_pdf:
            overview = st.session_state.resume_data.get("overview") or {}
            safe_name = "".join(
                c if c.isalnum() or c in (" ", "-", "_") else "_"
                for c in (overview.get("name") or "resume")
            ).strip() or "resume"
            pdf_name = f"{safe_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
            st.caption("Build a PDF from the saved resume JSON (save edits first).")
            export_ready = validation.export_ready if validation else False
            if validation and not export_ready:
                show_user_warning(
                    "PDF export is blocked until validation passes. "
                    "Fix errors in the Validation tab (e.g. add your full name)."
                )
            if st.button(
                "Build PDF",
                type="primary",
                key="generate_pdf_btn",
                disabled=not export_ready,
            ):
                try:
                    with st.spinner("Building PDF…"):
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
                    st.success("PDF ready — download below.")
                except (PdfExportError, ResumeValidationError) as exc:
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
                    use_container_width=True,
                )
