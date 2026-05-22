# Code reference

Short description of each module, class, and function. Names reflect purpose.

## Project layout

| File | Purpose |
|------|---------|
| `main.py` | Streamlit entry point (`streamlit run main.py`). |
| `streamlit_app.py` | Full UI: inputs, GitHub fetch, generation, editor, PDF, chat. |
| `groq_resume_service.py` | Groq API: README summaries and tailored resume JSON. |
| `resume_pdf_exporter.py` | ReportLab PDF export from resume JSON. |
| `resume_chat_sidebar.py` | Sidebar chat UI and session handling. |
| `resume_chat_editor.py` | NL chat → Python commands → in-place JSON edits. |
| `app_errors.py` | Typed errors and user-safe messages for the GUI. |
| `resume_json_prompt.py` | LLM prompt template for tailored resume JSON. |
| `requirements.txt` | Python dependencies. |
| `.env` | Secrets (not committed); see `.env.example`. |
| `.devcontainer/devcontainer.json` | GitHub Codespaces / Dev Container setup. |

---

## `app_errors.py`

| Name | Description |
|------|-------------|
| `AppError` | Base exception with `user_message` shown in Streamlit. |
| `ConfigurationError` | Missing `GROQ_API_KEY` or similar setup issues. |
| `GroqApiError` / `GroqRateLimitError` | Groq API failures (401, 429, 5xx, network). |
| `ResumeJsonParseError` | LLM returned invalid resume JSON. |
| `GitHubApiError` | GitHub API failures (404, 403 rate limit, etc.). |
| `FileProcessingError` | Resume upload / PDF text extraction failed. |
| `PdfExportError` | ReportLab PDF build failed. |
| `ChatUpdateError` | Chat commands could not be applied. |
| `format_exception_for_user` | Maps any exception to a safe UI string. |
| `show_user_error` | Logs detail and displays `st.error` in Streamlit. |
| `github_error_from_response` | Builds `GitHubApiError` from HTTP response. |
| `groq_error_from_exception` | Builds `GroqApiError` from `requests` exception. |

---

## `main.py`

| Name | Description |
|------|-------------|
| *(module)* | Boots `ResumeAssistantApp` when run as `streamlit run main.py`. |

---

## `streamlit_app.py`

**Class: `ResumeAssistantApp`** — Orchestrates the Streamlit resume workflow.

| Function | Description |
|----------|-------------|
| `__init__` | Creates Groq service, PDF exporter, and chat sidebar; configures the page. |
| `configure_streamlit_page` | Sets title, icon, wide layout, and sidebar state. |
| `ensure_groq_api_key_configured` | Verifies `GROQ_API_KEY` is set; shows error if missing. |
| `parse_uploaded_resume_text` | Reads TXT/MD directly; extracts text (and links) from PDF via pdfplumber. |
| `fetch_github_readme_contents` | Lists user repos and downloads READMEs in parallel (`fetch_repository_readme`). |
| `fetch_repository_readme` | *(nested)* Fetches one repo’s README from the GitHub API. |
| `summarize_github_projects_with_ui` | Calls Groq per repo with progress bar and inter-request delay. |
| `normalize_certification_entry` | Converts string or dict certifications to a standard dict for the form. |
| `render_resume_form_editor` | Expandable forms for overview, contact, skills, jobs, projects, education, certs, achievements. |
| `run_app` | Main loop: chat processing, inputs, generate, edit, PDF download, sidebar chat. |

---

## `groq_resume_service.py`

**Class: `GroqResumeService`** — Groq chat-completions for resume content.

| Function | Description |
|----------|-------------|
| `__init__` | Loads API key, headers, model id, and delay settings from env. |
| `wait_for_rate_limit_backoff` | Sleeps after errors; honors `Retry-After` on HTTP 429. |
| `summarize_project_readme` | Turns a GitHub README into a resume-ready project blurb. |
| `summarize_all_project_readmes` | Batch summarization with delay between repos (CLI/batch use). |
| `generate_tailored_resume_json` | Builds full resume JSON from resume text, projects, and job description. |
| `extract_json_from_llm_response` | Strips markdown and extracts `{...}` from the model reply. |
| `validate_resume_json_schema` | Checks legacy required fields (optional validation). |
| `build_empty_resume_fallback` | Returns empty schema-shaped JSON when generation fails. |

---

## `resume_pdf_exporter.py`

**Class: `ResumePdfExporter`** — ReportLab PDF builder.

| Function | Description |
|----------|-------------|
| `__init__` | Loads sample styles and custom paragraph styles. |
| `define_pdf_paragraph_styles` | Registers fonts/sizes for header, bullets, sections, etc. |
| `export_resume_to_pdf` | Builds the PDF story and writes `filename`. |
| `render_pdf_header_section` | Name, location, phone, email, profile links. |
| `render_pdf_summary_section` | Objective / professional summary. |
| `render_pdf_skills_section` | Comma-separated skills line. |
| `render_company_duration_row` | Two-column company name and date range. |
| `render_pdf_experience_section` | Jobs with titles, locations, and bullets. |
| `append_pdf_bullet_list` | Adds bullet paragraphs to the story. |
| `render_pdf_projects_section` | Project names, tech, and achievement bullets. |
| `render_pdf_education_section` | `Institution - Degree \| Duration` lines. |
| `render_pdf_achievements_section` | Achievement bullets. |
| `render_pdf_certifications_section` | Certification bullets. |

---

## `resume_chat_sidebar.py`

**Class: `ResumeChatSidebar`** — Streamlit sidebar chat for post-generation edits.

| Function | Description |
|----------|-------------|
| `__init__` | Creates `ResumeChatEditor` and initializes session state. |
| `init_chat_session_state` | Ensures `chat_messages`, `chat_processing`, `previous_input` keys exist. |
| `inject_chat_sidebar_styles` | Injects light/dark-aware CSS for the chat panel. |
| `render_sidebar_chat` | Renders sidebar when `resume_data` is in session. |
| `render_sidebar_message_list` | Shows last 8 messages or empty state. |
| `render_sidebar_message_input` | Text input, send/clear, and example commands. |
| `on_chat_input_submit` | Enter key handler to enqueue a message. |
| `enqueue_user_chat_message` | Appends user message and sets processing flag. |
| `process_pending_chat_updates` | Runs Groq parse + apply on the latest user message (call at app start). |

---

## `resume_chat_editor.py`

**Class: `ResumeChatEditor`** — Natural language → resume JSON mutations.

| Function | Description |
|----------|-------------|
| `__init__` | Loads Groq credentials and default model. |
| `parse_chat_request_to_commands` | Asks Groq for a Python list of `resume['...']` assignment strings. |
| `extract_command_list_from_llm_response` | Parses `[...]` from the model output safely. |
| `apply_update_commands_to_resume` | `exec`s each command against the resume dict in place. |

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Required. Groq API authentication. |
| `GROQ_REQUEST_DELAY_SEC` | Seconds between consecutive Groq calls (default `3`). |
| `GROQ_RETRY_DELAY_SEC` | Base backoff multiplier on retry (default `10`). |
