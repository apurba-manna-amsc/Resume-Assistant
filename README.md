# ResumeBot — AI Resume Customization System

Tailor your resume to any job description using **Groq LLMs**, **GitHub project summaries**, and a **sidebar chat assistant**. Edit in a structured form, validate JSON before export, and download a professional PDF.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://resume-assistant-sgcjwzkfggfyzy7ggxcmuh.streamlit.app/)

## Live app

**[https://resume-assistant-sgcjwzkfggfyzy7ggxcmuh.streamlit.app/](https://resume-assistant-sgcjwzkfggfyzy7ggxcmuh.streamlit.app/)**

Open the link, add your **Groq API key** in Streamlit Cloud secrets (or use a local `.env` when running yourself), then follow the on-screen workflow.

---

## What it does

ResumeBot helps you produce a **job-targeted resume** without starting from scratch:

1. You provide your **current resume**, **projects** (GitHub or manual), and a **job description**.
2. Groq generates structured **resume JSON** (overview, experience, skills, projects, education, etc.).
3. You **refine** via the form editor or natural-language **chat** (“Add Python to my skills”, “Change my title to Product Engineer”).
4. A **validation layer** checks schema and required fields before PDF export.
5. You **export** an ATS-friendly PDF.

The app is built for real-world Groq free-tier limits: **dynamic model discovery**, **rate-limit headers from the API**, proactive throttling, and a **live countdown** in the sidebar when waiting for quota reset.

---

## Features

| Area | Capability |
|------|------------|
| **Resume input** | Upload PDF, TXT, or Markdown; or paste plain text (`pdfplumber` / text decode) |
| **GitHub projects** | Fetch public repo READMEs, summarize each with Groq, show progress per repo |
| **Manual projects** | Free-text project descriptions; combine with GitHub summaries |
| **AI generation** | Full resume JSON tailored to the job description (ATS-oriented prompt) |
| **Model picker** | Lists models from `GET /v1/models`; quotas from Groq `x-ratelimit-*` headers |
| **Rate limiting** | Per-model tracking, proactive waits, 429 retry, fallback model, UI countdown |
| **Form editor** | Section-based editing (overview, contact, skills, experience, projects, …) |
| **Chat assistant** | Sidebar chat applies structured edits via Groq-generated Python commands |
| **Validation** | Normalize types, report errors/warnings, block PDF until valid (e.g. name required) |
| **Raw JSON tab** | Inspect and debug the structured resume |
| **PDF export** | ReportLab-based, professional layout |
| **Errors** | User-friendly messages in the UI; detailed logs server-side |

---

## How to use (workflow)

### 1. Resume tab
- **Upload file** (PDF / TXT / MD) or **paste text**.
- A success message confirms extraction; preview optional.

### 2. Projects tab
- **GitHub**: enter username (optional token for higher GitHub rate limits) → **Fetch & summarize repositories**.
- **Manual**: describe side projects, internships, portfolio work.
- **Both**: merge GitHub summaries with manual notes.

### 3. Job description tab
- Paste the full job posting.

### 4. Generate
- Status pills show what is ready (resume, projects, job, generated).
- Click **Generate customized resume** when all inputs are present.
- Pick an AI model in the **sidebar** (see [Model selection](#model-selection--rate-limits)).

### 5. Edit & export
- **Form editor** — change fields directly; **Save changes** runs validation.
- **Validation** — errors, warnings, auto-fixes (e.g. string skills → list).
- **Raw JSON** — full document.
- **PDF export** — enabled only when validation passes.
- **Sidebar chat** — after generation, ask for edits in plain English.

### Example chat commands
- “Add Python and FastAPI to my skills”
- “Update my current role to Senior Developer”
- “Change work experience title at index 0 to Product Engineer”
- “Add a bullet about leading a team of five”

---

## UI overview

```
┌─────────────────────────────────────────────────────────────────┐
│  ResumeBot — hero, readiness pills (resume / projects / job)    │
├─────────────────────────────────────────────────────────────────┤
│  [ Resume ] [ Projects ] [ Job description ]                    │
│  … inputs …                                                     │
│  [ Generate customized resume ]                                 │
├─────────────────────────────────────────────────────────────────┤
│  Edit & export                                                  │
│  [ Form editor ] [ Validation ] [ Raw JSON ] [ PDF export ]     │
└─────────────────────────────────────────────────────────────────┘

Sidebar: rate-limit wait banner · Settings (model + quotas) · Chat
```

After **chat** or **generate**, the form editor refreshes automatically (widget epoch) so it stays in sync with Raw JSON.

---

## Model selection & rate limits

Groq does **not** expose RPM/RPD/TPM in the models list API. ResumeBot:

1. Loads **model metadata** from `GET /v1/models` (context window, max output tokens).
2. Loads **live quotas** from response headers (`x-ratelimit-limit-requests`, `x-ratelimit-remaining-requests`, etc.) via **Refresh all limits** or on first load (`GROQ_PROBE_ALL_LIMITS_ON_REFRESH=1`).
3. Sorts models by **daily request cap** (highest first) and warns on **strict quotas** (low daily cap from headers).
4. Shows **progress bars** for remaining requests and tokens per minute.
5. During waits, displays a **sidebar countdown** (e.g. “~54s remaining”) for low quota or HTTP 429.

**Practical tips**
- Prefer **`llama-3.1-8b-instant`** for many GitHub README summaries (high daily quota).
- Use **`llama-3.3-70b-versatile`** for best generation quality (lower daily cap).
- Avoid **`groq/compound-mini`** for bulk work unless you need agent/tools (very low daily cap).

---

## Resume JSON schema

Generated and edited data follows this structure (see `resume_assistant/prompts/resume_json.py`):

```json
{
  "overview": {
    "name": "",
    "current_role": "",
    "company": "",
    "professional_summary": ""
  },
  "contact_info": {
    "phone": "",
    "email": "",
    "location": "",
    "profile_links": { "LinkedIn": "", "GitHub": "", "Portfolio": "" }
  },
  "skills": [],
  "work_experience": [
    { "title": "", "company": "", "duration": "", "location": "", "description": [] }
  ],
  "projects": [
    { "name": "", "duration": "", "description": [], "technologies": [], "links": [] }
  ],
  "education": [{ "degree": "", "institution": "", "duration": "" }],
  "certifications": [{ "name": "", "issuer": "", "date": "", "credential_id": "" }],
  "achievements": []
}
```

Validation (`resume_assistant/core/resume_validation.py`) normalizes types, fills missing keys, and requires **`overview.name`** before PDF export.

---

## Technology stack

| Layer | Technology |
|-------|------------|
| UI | [Streamlit](https://streamlit.io/) |
| LLM | [Groq API](https://console.groq.com/) (OpenAI-compatible chat completions) |
| GitHub | REST API (repo list + README contents) |
| Resume upload | `pdfplumber`, plain text / Markdown |
| PDF export | `reportlab` |
| Config | `python-dotenv` |
| HTTP | `requests` |

---

## Project structure

```
Resume-Assistant/
├── main.py                          # Entry: streamlit run main.py
├── streamlit_app.py                 # Compatibility shim
├── requirements.txt
├── .env.example
├── docs/
│   ├── ARCHITECTURE.md              # Layers and data flow
│   └── CODE_REFERENCE.md            # Module index
└── resume_assistant/
    ├── config/settings.py
    ├── core/
    │   ├── errors.py                # Typed errors + UI messages
    │   └── resume_validation.py     # Schema validate / normalize
    ├── integrations/
    │   ├── groq/
    │   │   ├── client.py            # Chat completions + probes
    │   │   ├── models.py            # Model catalog from API
    │   │   ├── rate_limiter.py      # Headers, waits, countdown hooks
    │   │   ├── resume_service.py    # Summarize READMEs, generate JSON
    │   │   └── context_utils.py     # Truncate prompts per context window
    │   └── github/client.py         # Fetch READMEs (parallel)
    ├── services/
    │   ├── file_parser.py           # Upload → text
    │   └── chat_editor.py           # Chat → resume update commands
    ├── export/pdf_exporter.py
    ├── prompts/resume_json.py       # Full resume generation prompt
    └── ui/
        ├── app.py                   # ResumeAssistantApp
        ├── theme.py                 # Layout / CSS
        └── components/
            ├── model_settings.py
            ├── github_projects.py
            ├── resume_editor.py
            ├── resume_validation_ui.py
            ├── chat_sidebar.py
            └── rate_limit_wait_ui.py
```

**Layer rule:** only `resume_assistant/ui/` imports Streamlit. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Installation (local)

### Prerequisites
- Python 3.10+ recommended
- [Groq API key](https://console.groq.com/keys)

### Steps

```bash
git clone https://github.com/apurba-manna-amsc/resume-assistant.git
cd resume-assistant

python -m venv resume_env
# Windows
resume_env\Scripts\activate
# macOS / Linux
source resume_env/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and set GROQ_API_KEY=...

streamlit run main.py
```

Open `http://localhost:8501`.

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | **Required.** Groq API key |
| `GROQ_DEFAULT_MODEL` | Default model id (must exist in your account) |
| `GROQ_FREE_MODEL_IDS` | Optional comma list to mark models in UI |
| `GROQ_MIN_REMAINING_REQUESTS` | Wait when daily requests ≤ this (default `2`) |
| `GROQ_MIN_REMAINING_TOKENS_RATIO` | Wait when TPM ratio below this (default `0.15`) |
| `GROQ_MIN_REQUEST_INTERVAL_SEC` | Minimum gap between calls (default `1.0`) |
| `GROQ_RATE_LIMIT_BUFFER_SEC` | Extra buffer on reset waits (default `0.5`) |
| `GROQ_RETRY_DELAY_SEC` | Fallback delay when headers missing (default `10`) |
| `GROQ_PROBE_ALL_LIMITS_ON_REFRESH` | Probe all models for headers on refresh (default `1`) |
| `GROQ_MAX_WAIT_SEC` | Max UI block time on 429 (default `120`) |

**Streamlit Cloud:** set the same variables under **App settings → Secrets** (TOML), e.g.:

```toml
GROQ_API_KEY = "gsk_..."
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
```

**GitHub token** is optional and entered in the UI (not `.env`) to reduce GitHub API rate limits for private repos you can access.

---

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. [Share an app](https://share.streamlit.io/) → connect the repo.
3. Main file path: **`main.py`**
4. Add secrets (`GROQ_API_KEY`, etc.).
5. Deploy — live URL format: `https://<app-name>-<id>.streamlit.app/`

Current production URL:  
**https://resume-assistant-sgcjwzkfggfyzy7ggxcmuh.streamlit.app/**

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `GROQ_API_KEY is not configured` | Add key to `.env` locally or Streamlit secrets; restart |
| Long waits / 429 | Check sidebar countdown; switch to `llama-3.1-8b-instant`; use **Refresh all limits** |
| “Reduce the length of messages” (400) | Model context too small; pick larger-context model or shorter READMEs |
| GitHub rate limit | Add personal access token in Projects tab; wait and retry |
| Form editor out of sync after chat | Fixed via editor epoch — refresh page if on an old deploy |
| PDF export disabled | Open **Validation** tab; add **Full name** and fix errors |
| PDF / upload failures | Use supported formats; ensure PDF is not password-protected |

Logs: run locally with `streamlit run main.py` and watch the terminal for `resume_assistant.*` log lines.

---

## Contributing

Contributions are welcome. Open an issue or pull request on GitHub.

---

## Contact

**Apurba Manna**

- Email: [98apurbamanna@gmail.com](mailto:98apurbamanna@gmail.com)
- GitHub: [@apurba-manna-amsc](https://github.com/apurba-manna-amsc)
- LinkedIn: [apurba-manna](https://linkedin.com/in/apurba-manna)

---

## License

This project is open source under the [MIT License](LICENSE).

---

## Acknowledgments

- [Streamlit](https://streamlit.io/) for the app framework  
- [Groq](https://groq.com/) for fast LLM inference  
- [GitHub](https://github.com/) for repository and README APIs  

If this project helps you land an interview, consider giving the repo a star.
