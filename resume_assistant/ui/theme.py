"""Global Streamlit styling and layout helpers for ResumeBot."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def inject_app_styles() -> None:
    """Inject theme-aware CSS for the main app layout."""
    st.markdown(
        """
        <style>
        :root {
            --rb-accent: #2563eb;
            --rb-accent-soft: #dbeafe;
            --rb-surface: #f8fafc;
            --rb-border: #e2e8f0;
            --rb-text: #0f172a;
            --rb-muted: #64748b;
            --rb-success: #059669;
            --rb-warn: #d97706;
            --rb-radius: 12px;
        }

        @media (prefers-color-scheme: dark) {
            .stApp {
                --rb-accent: #3b82f6;
                --rb-accent-soft: #1e3a5f;
                --rb-surface: #1e293b;
                --rb-border: #334155;
                --rb-text: #f1f5f9;
                --rb-muted: #94a3b8;
                --rb-success: #34d399;
                --rb-warn: #fbbf24;
            }
        }

        .block-container {
            padding-top: 1.25rem;
            max-width: 1100px;
        }

        .rb-hero {
            background: linear-gradient(135deg, var(--rb-accent-soft) 0%, transparent 70%);
            border: 1px solid var(--rb-border);
            border-radius: var(--rb-radius);
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
        }

        .rb-hero h1 {
            font-size: 1.85rem;
            font-weight: 700;
            color: var(--rb-text);
            margin: 0 0 0.35rem 0;
            letter-spacing: -0.02em;
        }

        .rb-hero p {
            color: var(--rb-muted);
            margin: 0;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .rb-step-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.85rem;
        }

        .rb-step {
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.35rem 0.65rem;
            border-radius: 999px;
            border: 1px solid var(--rb-border);
            color: var(--rb-muted);
            background: var(--rb-surface);
        }

        .rb-step.active {
            border-color: var(--rb-accent);
            color: var(--rb-accent);
            background: var(--rb-accent-soft);
        }

        .rb-step.done {
            border-color: var(--rb-success);
            color: var(--rb-success);
        }

        .rb-status-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.5rem 0 1rem 0;
        }

        .rb-pill {
            font-size: 0.8rem;
            font-weight: 600;
            padding: 0.4rem 0.75rem;
            border-radius: 999px;
            border: 1px solid var(--rb-border);
        }

        .rb-pill.ok {
            background: rgba(5, 150, 105, 0.12);
            color: var(--rb-success);
            border-color: transparent;
        }

        .rb-pill.pending {
            background: var(--rb-surface);
            color: var(--rb-muted);
        }

        .rb-action-card {
            border: 1px solid var(--rb-border);
            border-radius: var(--rb-radius);
            padding: 1rem 1.25rem;
            background: var(--rb-surface);
            margin: 0.75rem 0 1.25rem 0;
        }

        .rb-action-card h3 {
            margin: 0 0 0.35rem 0;
            font-size: 1.05rem;
            color: var(--rb-text);
        }

        .rb-action-card p {
            margin: 0 0 0.75rem 0;
            font-size: 0.85rem;
            color: var(--rb-muted);
        }

        div[data-testid="stTabs"] button {
            font-weight: 600;
        }

        .stSidebar [data-testid="stSidebarNav"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header() -> None:
    st.markdown(
        """
        <div class="rb-hero">
            <h1>ResumeBot</h1>
            <p>Tailor your resume to any job description with AI — upload your CV,
            add GitHub projects, paste the role, then generate and export a PDF.</p>
            <div class="rb-step-row">
                <span class="rb-step active">1. Resume</span>
                <span class="rb-step">2. Projects</span>
                <span class="rb-step">3. Job</span>
                <span class="rb-step">4. Generate &amp; export</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _pill(label: str, ready: bool) -> str:
    css = "ok" if ready else "pending"
    icon = "✓" if ready else "○"
    return f'<span class="rb-pill {css}">{icon} {label}</span>'


def render_readiness_bar(
    *,
    has_resume: bool,
    has_projects: bool,
    has_job: bool,
    has_generated: bool,
) -> None:
    pills = "".join(
        [
            _pill("Resume loaded", has_resume),
            _pill("Projects added", has_projects),
            _pill("Job description", has_job),
            _pill("Resume generated", has_generated),
        ]
    )
    st.markdown(f'<div class="rb-status-bar">{pills}</div>', unsafe_allow_html=True)


def render_resume_preview_card(resume_data: Dict[str, Any]) -> None:
    """Compact preview of name, role, and top skills."""
    overview = resume_data.get("overview") or {}
    skills = resume_data.get("skills") or []
    if isinstance(skills, list):
        skill_preview = ", ".join(str(s) for s in skills[:8])
        if len(skills) > 8:
            skill_preview += "…"
    else:
        skill_preview = str(skills)[:120]

    name = overview.get("name") or "Your name"
    role = overview.get("current_role") or "Role"
    company = overview.get("company") or ""
    subtitle = f"{role}" + (f" at {company}" if company else "")

    st.markdown(
        f"""
        <div class="rb-action-card">
            <h3>{name}</h3>
            <p><strong>{subtitle}</strong></p>
            <p style="font-size:0.82rem;">{skill_preview or "No skills listed yet."}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
