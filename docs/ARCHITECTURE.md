# Architecture

Modular layout for Resume Assistant. Run the app from the repo root: `streamlit run main.py`.

## Package layout

```
resume_assistant/
├── config/                 # Environment settings
│   └── settings.py
├── core/                   # Shared errors and UI helpers
│   └── errors.py
├── integrations/           # External APIs (no Streamlit)
│   ├── groq/
│   │   ├── client.py       # Chat + rate limits
│   │   ├── models.py       # GET /v1/models
│   │   ├── rate_limiter.py
│   │   ├── resume_service.py
│   │   └── constants.py
│   └── github/
│       └── client.py       # Fetch repo READMEs
├── services/               # App logic (no UI)
│   ├── chat_editor.py
│   └── file_parser.py
├── export/
│   └── pdf_exporter.py
├── prompts/
│   └── resume_json.py
└── ui/                     # Streamlit only
    ├── app.py              # ResumeAssistantApp orchestration
    ├── logging_setup.py
    └── components/
        ├── model_settings.py
        ├── github_projects.py
        ├── resume_editor.py
        └── chat_sidebar.py
```

## Layer rules

| Layer | Responsibility | Depends on |
|-------|----------------|------------|
| `ui` | Streamlit widgets, session state, user messages | `services`, `integrations`, `export`, `core` |
| `services` | Business helpers (parse file, chat commands) | `integrations`, `core` |
| `integrations` | HTTP clients (Groq, GitHub) | `core`, `config` |
| `export` | PDF generation | `core` |
| `prompts` | LLM prompt templates | — |
| `core` | Errors, `show_user_error` | — |

**Do not** import `streamlit` outside `resume_assistant/ui/`.

## Entry points

- `main.py` — production entry
- `streamlit_app.py` — re-exports `ResumeAssistantApp` for compatibility

## Data flow (generate resume)

1. UI collects resume text, projects, job description.
2. `GroqResumeService.generate_tailored_resume_json()` calls `GroqClient.chat_completion()`.
3. `GroqRateLimiter` reads response headers and delays before the next call.
4. JSON is stored in `st.session_state.resume_data`.
5. User edits via `resume_editor` or chat; PDF via `ResumePdfExporter`.
