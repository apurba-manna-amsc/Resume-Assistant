"""Streamlit UI: resume upload, GitHub projects, AI tailoring, editor, chat, PDF export."""

import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, Optional

import pdfplumber
import requests
import streamlit as st
from dotenv import load_dotenv

from app_errors import (
    AppError,
    FileProcessingError,
    GitHubApiError,
    PdfExportError,
    ResumeJsonParseError,
    format_exception_for_user,
    github_error_from_response,
    log_exception,
    show_user_error,
    show_user_warning,
)
from groq_client import GroqClient
from groq_models import GroqModelInfo, default_model_id
from groq_rate_limiter import RateLimitSnapshot
from groq_resume_service import GroqResumeService
from resume_chat_sidebar import ResumeChatSidebar
from resume_pdf_exporter import ResumePdfExporter

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class ResumeAssistantApp:
    """Main Streamlit application wiring input, Groq, editor, chat, and PDF export."""

    def __init__(self):
        self._groq_resume_service: Optional[GroqResumeService] = None
        self._pdf_exporter: Optional[ResumePdfExporter] = None
        self._chat_sidebar: Optional[ResumeChatSidebar] = None
        self.configure_streamlit_page()

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

    def configure_streamlit_page(self):
        """Set Streamlit page title, icon, and layout."""
        st.set_page_config(
            page_title="AI Resume Customization System",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
    def ensure_groq_api_key_configured(self) -> bool:
        """Return False and show an error if GROQ_API_KEY is missing."""
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
            self._init_groq_session()
            return True
        except AppError as exc:
            show_user_error(exc, context="Configuration")
            return False

    def _init_groq_session(self) -> None:
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

    def render_groq_model_settings(self) -> None:
        """Model picker, free-model list, and live rate-limit counters."""
        catalog: list[GroqModelInfo] = st.session_state.get("groq_model_catalog") or []
        if not catalog:
            show_user_warning("No Groq chat models loaded. Check your API key.")
            return

        free_models = [m for m in catalog if m.is_free]
        paid_models = [m for m in catalog if not m.is_free]

        with st.expander("AI model and rate limits", expanded=True):
            col_refresh, col_info = st.columns([1, 3])
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

            st.markdown("**Free chat models** (typical Groq free tier)")
            if free_models:
                st.markdown(
                    ", ".join(f"`{m.id}`" for m in free_models)
                )
            else:
                st.caption("No models marked free. Set GROQ_FREE_MODEL_IDS in .env to customize.")

            if paid_models:
                with st.expander("Other available models", expanded=False):
                    st.markdown(", ".join(f"`{m.id}`" for m in paid_models))

            snap: Optional[RateLimitSnapshot] = (
                st.session_state.groq_client.get_rate_limit_snapshot(
                    st.session_state.selected_groq_model
                )
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
                        delta=None,
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

    def parse_uploaded_resume_text(self, uploaded_file) -> str:
        """Extract plain text from an uploaded TXT, PDF, or MD resume file."""
        tmp_file_path: Optional[str] = None
        try:
            if uploaded_file.type == "text/plain":
                text = uploaded_file.read().decode("utf-8")
            elif uploaded_file.type == "application/pdf":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_file_path = tmp_file.name

                text = ""
                with pdfplumber.open(tmp_file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                        if page.annots:
                            for annot in page.annots:
                                uri = annot.get("uri")
                                if uri:
                                    text += f"[Link: {uri}]\n"
            else:
                text = uploaded_file.read().decode("utf-8", errors="replace")

            text = text.strip()
            if not text:
                raise FileProcessingError(
                    "No text could be extracted from this file. "
                    "Try a different PDF or paste your resume as text."
                )
            return text
        except FileProcessingError:
            raise
        except UnicodeDecodeError as exc:
            raise FileProcessingError(
                "Could not read the file encoding. Save as UTF-8 text or PDF and try again."
            ) from exc
        except Exception as exc:
            raise FileProcessingError(
                "Failed to read the uploaded resume. Ensure the file is not password-protected.",
                detail=str(exc),
            ) from exc
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except OSError:
                    logger.warning("Could not delete temp file %s", tmp_file_path)
    

    def fetch_github_readme_contents(self, username: str, token: str = "") -> Dict[str, str]:
        """Fetch public repo README bodies for a GitHub user (parallel downloads)."""
        if not username:
            return {}

        headers = {"Authorization": f"token {token}"} if token else {}
        project_details = {}

        # Create containers for progress tracking
        extraction_container = st.container()

        with extraction_container:
            st.markdown("#### 🔍 **GitHub Repository Extraction**")
            extraction_progress = st.progress(0)
            extraction_status = st.empty()

        try:
            # Step 1: Fetch all repos
            repos = []
            page = 1
            extraction_status.text("🔍 Fetching repositories list...")

            while True:
                url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
                res = requests.get(url, headers=headers, timeout=30)

                if res.status_code != 200:
                    raise github_error_from_response(res, username)

                data = res.json()
                if not data:
                    break
                repos.extend(data)
                page += 1

            if not repos:
                st.warning("No repositories found for this user.")
                return {}

            total_repos = len(repos)
            readme_count = 0
            progress_step = 1.0 / total_repos

            # Step 2: Define the task
            def fetch_repository_readme(repo):
                try:
                    repo_name = repo["name"]
                    default_branch = repo.get("default_branch", "main")

                    contents_url = (
                        f"https://api.github.com/repos/{username}/{repo_name}"
                        f"/contents?ref={default_branch}"
                    )
                    res = requests.get(contents_url, headers=headers, timeout=30)
                    if res.status_code != 200:
                        return repo_name, None

                    files = res.json()
                    readme_file = next(
                        (f for f in files if f["name"].lower().startswith("readme")),
                        None,
                    )

                    if readme_file and "download_url" in readme_file:
                        readme_res = requests.get(
                            readme_file["download_url"], headers=headers, timeout=30
                        )
                        readme_res.raise_for_status()
                        return repo_name, readme_res.text
                except requests.exceptions.RequestException as exc:
                    logger.debug("README fetch failed for %s: %s", repo.get("name"), exc)
                except (KeyError, TypeError, ValueError) as exc:
                    logger.debug("Unexpected README payload for %s: %s", repo.get("name"), exc)
                return repo["name"], None

            # Step 3: Run in parallel
            max_workers = min(32, (os.cpu_count() or 1) + 4)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(fetch_repository_readme, repo): repo for repo in repos}
                for i, future in enumerate(as_completed(futures)):
                    repo_name, content = future.result()
                    if content:
                        project_details[repo_name] = content
                        readme_count += 1

                    extraction_progress.progress((i + 1) * progress_step)
                    extraction_status.text(f"🔍 Processed {i + 1}/{total_repos}: {repo_name}")

            # Final update
            extraction_status.text(f"✅ **Extraction Complete**: Found README files in {readme_count} out of {total_repos} repositories")
            extraction_progress.progress(1.0)

        except GitHubApiError as exc:
            extraction_status.empty()
            raise
        except requests.exceptions.RequestException as exc:
            log_exception("GitHub fetch", exc)
            raise GitHubApiError(
                "Could not reach GitHub. Check your internet connection and try again.",
                detail=str(exc),
            ) from exc
        except Exception as exc:
            log_exception("GitHub fetch", exc)
            raise GitHubApiError(
                "An unexpected error occurred while fetching GitHub projects.",
                detail=str(exc),
            ) from exc

        return project_details

    
    def summarize_github_projects_with_ui(self, github_projects: Dict[str, str]) -> Dict[str, str]:
        """Summarize each repo README via Groq with Streamlit progress indicators."""
        if not github_projects:
            return {}
        
        # Create container for summarization progress
        summarization_container = st.container()
        
        with summarization_container:
            st.markdown("#### 🤖 **AI Project Summarization**")
            summarization_progress = st.progress(0)
            summarization_status = st.empty()
        
        try:
            summarization_status.text("Starting AI summarization (auto rate-limit pacing)...")

            # Generate summaries with progress tracking
            total_projects = len(github_projects)
            summaries = {}
            
            for i, (project_name, content) in enumerate(github_projects.items()):
                progress = (i + 1) / total_projects
                summarization_progress.progress(progress)
                summarization_status.text(
                    f"Summarizing {project_name} ({i + 1}/{total_projects})..."
                )

                try:
                    summary = self.groq_resume_service.summarize_project_readme(
                        content, project_name
                    )
                    summaries[project_name] = summary
                except AppError as exc:
                    log_exception(f"Summarize {project_name}", exc)
                    show_user_warning(
                        f"Could not summarize **{project_name}**: {format_exception_for_user(exc)} "
                        "Using raw README text instead."
                    )
                    summaries[project_name] = content[:4000]

            summarization_status.text(
                f"Summarization complete: {len(summaries)} project(s) processed."
            )
            summarization_progress.progress(1.0)
            return summaries

        except AppError:
            raise
        except Exception as exc:
            log_exception("GitHub summarization", exc)
            raise AppError(
                "Project summarization failed unexpectedly. Please try again.",
                detail=str(exc),
            ) from exc
    
    def normalize_certification_entry(self, cert: Any) -> Dict[str, str]:
        """Coerce a certification item to the dict shape expected by the form editor."""
        if isinstance(cert, dict):
            return {
                "name": cert.get("name", ""),
                "issuer": cert.get("issuer", ""),
                "date": cert.get("date", ""),
                "credential_id": cert.get("credential_id", ""),
            }
        if isinstance(cert, str):
            return {"name": cert, "issuer": "", "date": "", "credential_id": ""}
        return {"name": "", "issuer": "", "date": "", "credential_id": ""}

    def render_resume_form_editor(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render expandable Streamlit forms for each resume JSON section."""
        st.subheader("📝 Edit Your Resume")
        
        edited_data = {}
        
        # Overview Section
        with st.expander("👤 Overview", expanded=True):
            overview = resume_data.get("overview", {})
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name", value=overview.get("name", ""))
                current_role = st.text_input("Current Role", value=overview.get("current_role", ""))
            with col2:
                company = st.text_input("Current Company", value=overview.get("company", ""))
            
            professional_summary = st.text_area("Professional Summary", 
                                               value=overview.get("professional_summary", ""), 
                                               height=100)
            
            edited_data["overview"] = {
                "name": name,
                "current_role": current_role,
                "company": company,
                "professional_summary": professional_summary
            }
        
        # Contact Information
        with st.expander("📞 Contact Information", expanded=True):
            contact_info = resume_data.get("contact_info", {})
            profile_links = contact_info.get("profile_links", {})
            
            col1, col2 = st.columns(2)
            with col1:
                phone = st.text_input("Phone", value=contact_info.get("phone", ""))
                email = st.text_input("Email", value=contact_info.get("email", ""))
            with col2:
                location = st.text_input("Location", value=contact_info.get("location", ""))
            
            st.subheader("Profile Links")
            col3, col4, col5 = st.columns(3)
            with col3:
                linkedin = st.text_input("LinkedIn", value=profile_links.get("LinkedIn", ""))
            with col4:
                github = st.text_input("GitHub", value=profile_links.get("GitHub", ""))
            with col5:
                portfolio = st.text_input("Portfolio", value=profile_links.get("Portfolio", ""))
            
            edited_data["contact_info"] = {
                "phone": phone,
                "email": email,
                "location": location,
                "profile_links": {
                    "LinkedIn": linkedin,
                    "GitHub": github,
                    "Portfolio": portfolio
                }
            }
        
        # Skills
        with st.expander("🛠️ Skills", expanded=True):
            skills = resume_data.get("skills", [])
            skill_text = ", ".join(skills) if isinstance(skills, list) else str(skills)
            skills_input = st.text_area("Skills (comma-separated)", 
                                      value=skill_text, 
                                      height=100,
                                      help="Enter skills separated by commas")
            edited_data["skills"] = [skill.strip() for skill in skills_input.split(",") if skill.strip()]
        
        # Work Experience
        with st.expander("💼 Work Experience", expanded=True):
            work_experience = resume_data.get("work_experience", [])
            edited_data["work_experience"] = []
            
            # Add button to add new experience
            if st.button("➕ Add New Experience"):
                work_experience.append({
                    "title": "",
                    "company": "",
                    "duration": "",
                    "location": "",
                    "description": []
                })
            
            for i, exp in enumerate(work_experience):
                st.markdown(f"**Experience {i + 1}**")
                col1, col2 = st.columns(2)
                with col1:
                    title = st.text_input(f"Job Title", value=exp.get("title", ""), key=f"exp_title_{i}")
                    company = st.text_input(f"Company", value=exp.get("company", ""), key=f"exp_company_{i}")
                with col2:
                    duration = st.text_input(f"Duration", value=exp.get("duration", ""), key=f"exp_duration_{i}")
                    exp_location = st.text_input(f"Location", value=exp.get("location", ""), key=f"exp_location_{i}")
                
                # Handle description as list or string
                description_list = exp.get("description", [])
                if isinstance(description_list, list):
                    description_text = "\n".join([f"• {desc}" for desc in description_list])
                else:
                    description_text = str(description_list)
                
                description = st.text_area(f"Description (bullet points)", 
                                         value=description_text, 
                                         key=f"exp_desc_{i}",
                                         height=100,
                                         help="Each line will become a bullet point")
                
                # Convert back to list format
                description_list = [line.strip().lstrip("• ").strip() for line in description.split("\n") if line.strip()]
                
                edited_data["work_experience"].append({
                    "title": title,
                    "company": company,
                    "duration": duration,
                    "location": exp_location,
                    "description": description_list
                })
        
        # Projects
        with st.expander("🚀 Projects", expanded=True):
            projects = resume_data.get("projects", [])
            edited_data["projects"] = []
            
            # Add button to add new project
            if st.button("➕ Add New Project"):
                projects.append({
                    "name": "",
                    "duration": "",
                    "description": [],
                    "technologies": [],
                    "links": []
                })
            
            for i, proj in enumerate(projects):
                st.markdown(f"**Project {i + 1}**")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input(f"Project Name", value=proj.get("name", ""), key=f"proj_name_{i}")
                with col2:
                    duration = st.text_input(f"Duration", value=proj.get("duration", ""), key=f"proj_duration_{i}")
                
                # Handle description as list or string
                description = proj.get("description", [])
                if isinstance(description, list):
                    description_text = "\n".join([f"• {desc}" for desc in description])
                else:
                    description_text = str(description)
                
                description_input = st.text_area(f"Achievements", 
                                                value=description_text, 
                                                key=f"proj_desc_{i}",
                                                help="Each line will become a bullet point")
                
                # Technologies
                technologies = proj.get("technologies", [])
                tech_text = ", ".join(technologies) if isinstance(technologies, list) else str(technologies)
                tech_input = st.text_input(f"Technologies (comma-separated)", 
                                         value=tech_text, 
                                         key=f"proj_tech_{i}")
                
                # Links
                links = proj.get("links", [])
                links_text = "\n".join(links) if isinstance(links, list) else str(links)
                links_input = st.text_area(f"Links", 
                                         value=links_text, 
                                         key=f"proj_links_{i}",
                                         help="One link per line")
                
                edited_data["projects"].append({
                    "name": name,
                    "duration": duration,
                    "description": [line.strip().lstrip("• ").strip() for line in description_input.split("\n") if line.strip()],
                    "technologies": [tech.strip() for tech in tech_input.split(",") if tech.strip()],
                    "links": [link.strip() for link in links_input.split("\n") if link.strip()]
                })
        
        # Education
        with st.expander("🎓 Education", expanded=True):
            education = resume_data.get("education", [])
            edited_data["education"] = []
            
            # Add button to add new education
            if st.button("➕ Add New Education"):
                education.append({
                    "degree": "",
                    "institution": "",
                    "duration": ""
                })
            
            for i, edu in enumerate(education):
                st.markdown(f"**Education {i + 1}**")
                col1, col2 = st.columns(2)
                with col1:
                    degree = st.text_input(f"Degree", value=edu.get("degree", ""), key=f"edu_degree_{i}")
                    institution = st.text_input(f"Institution", value=edu.get("institution", ""), key=f"edu_inst_{i}")
                with col2:
                    duration = st.text_input(f"Duration", value=edu.get("duration", ""), key=f"edu_duration_{i}")
                
                edited_data["education"].append({
                    "degree": degree,
                    "institution": institution,
                    "duration": duration
                })
        
        # Certifications
        with st.expander("🏆 Certifications", expanded=False):
            certifications = resume_data.get("certifications", [])
            edited_data["certifications"] = []
            
            # Add button to add new certification
            if st.button("➕ Add New Certification"):
                certifications.append({
                    "name": "",
                    "issuer": "",
                    "date": "",
                    "credential_id": ""
                })
            
            for i, cert in enumerate(certifications):
                cert = self.normalize_certification_entry(cert)
                st.markdown(f"**Certification {i + 1}**")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input(f"Certification Name", value=cert.get("name", ""), key=f"cert_name_{i}")
                    issuer = st.text_input(f"Issuer", value=cert.get("issuer", ""), key=f"cert_issuer_{i}")
                with col2:
                    date = st.text_input(f"Date", value=cert.get("date", ""), key=f"cert_date_{i}")
                    credential_id = st.text_input(f"Credential ID", value=cert.get("credential_id", ""), key=f"cert_id_{i}")
                
                edited_data["certifications"].append({
                    "name": name,
                    "issuer": issuer,
                    "date": date,
                    "credential_id": credential_id
                })
        
        # Achievements
        with st.expander("🏅 Achievements", expanded=False):
            achievements = resume_data.get("achievements", [])
            if isinstance(achievements, list):
                achievements_text = "\n".join([f"• {ach}" for ach in achievements])
            else:
                achievements_text = str(achievements)
            
            achievements_input = st.text_area("Achievements", 
                                            value=achievements_text, 
                                            height=100,
                                            help="Each line will become a bullet point")
            
            edited_data["achievements"] = [line.strip().lstrip("• ").strip() for line in achievements_input.split("\n") if line.strip()]
        
        return edited_data
    
    def _is_placeholder_resume(self, data: Dict[str, Any]) -> bool:
        name = (data.get("overview") or {}).get("name", "")
        return name.strip() in ("", "Your Name")

    def run_app(self):
        """Run the full Streamlit workflow from input through export."""
        try:
            self._run_app_body()
        except AppError as exc:
            show_user_error(exc)
        except Exception as exc:
            log_exception("Unhandled app error", exc)
            show_user_error(exc)

    def _run_app_body(self):
        st.title("ResumeBot")
        st.markdown(
            "Transform your resume to match any job description using AI and your GitHub projects."
        )

        if not self.ensure_groq_api_key_configured():
            return

        self.render_groq_model_settings()

        if st.session_state.get("resume_data"):
            try:
                self.chat_sidebar.process_pending_chat_updates()
            except AppError as exc:
                show_user_error(exc, context="Chat assistant")

        # Initialize session state
        if 'resume_data' not in st.session_state:
            st.session_state.resume_data = None
        if 'project_summaries' not in st.session_state:
            st.session_state.project_summaries = {}
        if 'extracted_resume_text' not in st.session_state:
            st.session_state.extracted_resume_text = ""
        
        # Input Section
        st.header("📥 Input Information")
        
        # Resume Input with extracted text dropdown
        with st.expander("📄 Resume Input", expanded=True):
            resume_input_method = st.radio("Choose input method:", ["Upload File", "Paste Text"])
            
            resume_text = ""
            if resume_input_method == "Upload File":
                uploaded_file = st.file_uploader("Upload your resume", type=['txt', 'pdf', 'md'])
                if uploaded_file:
                    try:
                        resume_text = self.parse_uploaded_resume_text(uploaded_file)
                        st.session_state.extracted_resume_text = resume_text
                        st.success("Resume file loaded successfully.")
                        with st.expander("View extracted text", expanded=False):
                            st.text_area(
                                "Extracted resume text",
                                value=resume_text,
                                height=300,
                                disabled=True,
                            )
                    except FileProcessingError as exc:
                        show_user_error(exc, context="Resume upload")
                        st.session_state.extracted_resume_text = ""
            else:
                resume_text = st.text_area("Paste your resume text here:", height=200)
                st.session_state.extracted_resume_text = resume_text
        
        # Projects Input
        with st.expander("🗂️ Projects Input", expanded=True):
            project_input_method = st.radio("Choose project source:", ["GitHub Username", "Manual Input", "Both"])
            
            github_projects = {}
            manual_projects = ""
            
            if project_input_method in ["GitHub Username", "Both"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    github_username = st.text_input("GitHub Username:")
                with col2:
                    github_token = st.text_input("GitHub Token (Optional):", type="password")
                
                if github_username and st.button("Fetch & summarize GitHub projects"):
                    try:
                        with st.spinner("Fetching GitHub repositories..."):
                            github_projects = self.fetch_github_readme_contents(
                                github_username, github_token
                            )

                        if not github_projects:
                            show_user_warning(
                                "No README files were found in this user's public repositories."
                            )
                        else:
                            with st.spinner("Summarizing projects with AI..."):
                                summarized_projects = self.summarize_github_projects_with_ui(
                                    github_projects
                                )
                            st.session_state.project_summaries.update(summarized_projects)
                            st.success(
                                f"Processed {len(summarized_projects)} project(s) from GitHub."
                            )
                            with st.expander("View processed projects", expanded=False):
                                for repo_name, summary in summarized_projects.items():
                                    preview = summary[:300] + ("..." if len(summary) > 300 else "")
                                    st.markdown(f"**{repo_name}** — {preview}")
                    except AppError as exc:
                        show_user_error(exc, context="GitHub projects")
            
            if project_input_method in ["Manual Input", "Both"]:
                manual_projects = st.text_area("Manual Project Descriptions:", 
                                              placeholder="Describe your projects here...", 
                                              height=150)
                if manual_projects:
                    st.session_state.project_summaries["manual_projects"] = manual_projects
        
        # Job Description Input
        with st.expander("💼 Job Description", expanded=True):
            job_description = st.text_area("Paste the job description here:", 
                                         placeholder="Enter the complete job description...", 
                                         height=200)
        
        # Generate Resume Button
        if st.button("Generate customized resume", type="primary"):
            if not st.session_state.extracted_resume_text.strip():
                show_user_error(
                    AppError("Please upload or paste your resume before generating."),
                    context="Validation",
                )
                return
            if not st.session_state.project_summaries and not manual_projects.strip():
                show_user_error(
                    AppError(
                        "Please add GitHub projects or manual project descriptions before generating."
                    ),
                    context="Validation",
                )
                return
            if not job_description.strip():
                show_user_error(
                    AppError("Please paste the target job description before generating."),
                    context="Validation",
                )
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
                        "Resume was created with a minimal template because generation did not fully complete. "
                        "Review and edit all sections, or try again after a short wait (rate limits)."
                    )
                else:
                    st.success("Resume generated successfully.")
            except (AppError, ResumeJsonParseError) as exc:
                show_user_error(exc, context="Resume generation")
            except ValueError as exc:
                show_user_error(exc, context="Resume generation")
        
        # Edit and Preview Section
        if st.session_state.resume_data:
            st.header("Edit and preview")

            if st.session_state.get("chat_messages"):
                last_message = st.session_state.chat_messages[-1]
                if last_message.get("type") == "success":
                    st.info("Resume was updated via the chat assistant.")

            tab1, tab2 = st.tabs(["Edit resume", "Raw JSON"])

            with tab1:
                try:
                    edited_resume = self.render_resume_form_editor(st.session_state.resume_data)
                except Exception as exc:
                    log_exception("Resume form editor", exc)
                    show_user_error(exc, context="Editor")
                    edited_resume = st.session_state.resume_data

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save changes"):
                        st.session_state.resume_data = edited_resume
                        st.success("Resume saved.")
                        st.rerun()
                with col2:
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
            default_pdf_name = f"{safe_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"

            if st.button("Generate PDF", type="primary", key="generate_pdf_btn"):
                try:
                    with st.spinner("Building PDF..."):
                        filename = self.pdf_exporter.export_resume_to_pdf(
                            st.session_state.resume_data,
                            default_pdf_name,
                        )
                        with open(filename, "rb") as pdf_file:
                            st.session_state["pdf_download_bytes"] = pdf_file.read()
                            st.session_state["pdf_download_name"] = filename
                        try:
                            os.remove(filename)
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

        self.chat_sidebar.render_sidebar_chat()

