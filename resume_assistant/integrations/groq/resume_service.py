"""Groq API client for README summaries and tailored resume JSON generation."""

import json
import logging
from typing import Any, Dict, Optional

from resume_assistant.core.errors import ResumeJsonParseError
from resume_assistant.integrations.groq.client import GroqClient
from resume_assistant.integrations.groq.constants import FALLBACK_MODEL_ID
from resume_assistant.integrations.groq.rate_limiter import RateLimitSnapshot
from resume_assistant.integrations.groq.context_utils import truncate_text_for_model
from resume_assistant.prompts.resume_json import build_tailored_resume_prompt

logger = logging.getLogger(__name__)


class GroqResumeService:
    """Calls Groq LLM to summarize projects and build job-tailored resume JSON."""

    def __init__(
        self,
        groq_client: Optional[GroqClient] = None,
        model_id: Optional[str] = None,
    ) -> None:
        self.client = groq_client or GroqClient()
        self.llm_model = model_id or self.client.get_default_model_id()

    def set_model(self, model_id: str) -> None:
        self.llm_model = model_id

    def get_rate_limit_status(self) -> Optional[RateLimitSnapshot]:
        return self.client.get_rate_limit_snapshot(self.llm_model)

    def summarize_project_readme(
        self,
        readme_text: str,
        repo_name: str,
        llm_model: Optional[str] = None,
    ) -> str:
        """Turn a GitHub README into a resume-ready project blurb."""
        if not readme_text or not readme_text.strip():
            return f"Project: {repo_name} — no README content available."

        model = llm_model or self.llm_model
        models = self.client.fetch_chat_models()
        readme_for_model = truncate_text_for_model(
            readme_text, model, models, reserved_tokens=900, output_tokens=300
        )
        prompt = f"""
You are an expert technical resume writer. Transform this GitHub README into a concise, professional project summary for a resume.

**Project Name:** {repo_name}

**README Content:**
\"\"\"
{readme_for_model}
\"\"\"

Provide only the summary text. Use action verbs, technical keywords, and ATS-friendly language.
"""
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You write compelling project summaries from GitHub repositories.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 300,
        }

        summary = self.client.chat_completion(
            payload, max_retries=3, fallback_model=FALLBACK_MODEL_ID
        )
        summary = summary.replace('"""', "").replace("'''", "")
        return " ".join(summary.split())

    def summarize_all_project_readmes(self, project_details: Dict[str, str]) -> Dict[str, str]:
        """Batch summarization; spacing handled by Groq rate limiter."""
        project_summaries: Dict[str, str] = {}
        for project_name, readme_content in project_details.items():
            project_summaries[project_name] = self.summarize_project_readme(
                readme_content, project_name
            )
        return project_summaries

    def generate_tailored_resume_json(
        self,
        resume_text: str,
        project_summaries: str,
        job_description: str,
    ) -> Dict[str, Any]:
        """Build full resume JSON from resume text, projects, and job description."""
        if not resume_text.strip():
            raise ValueError("Resume text is empty.")
        if not job_description.strip():
            raise ValueError("Job description is empty.")

        prompt = build_tailored_resume_prompt(
            resume_text, project_summaries, job_description
        )
        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert resume optimizer and ATS specialist. "
                        "Always return valid JSON format only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        raw = self.client.chat_completion(
            payload, max_retries=3, fallback_model=FALLBACK_MODEL_ID
        )
        cleaned = self.extract_json_from_llm_response(raw)
        try:
            resume_data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ResumeJsonParseError(
                "The AI response was not valid JSON. Try generating again or shorten your inputs."
            ) from exc

        if not isinstance(resume_data, dict):
            raise ResumeJsonParseError(
                "The AI returned resume data in an unexpected format. Please try again."
            )
        return resume_data

    def extract_json_from_llm_response(self, response_text: str) -> str:
        """Strip markdown and extract the outermost JSON object."""
        response_text = response_text.replace("```json", "").replace("```", "")
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return response_text[start_idx : end_idx + 1]
        return response_text.strip()

    def build_empty_resume_fallback(self) -> Dict[str, Any]:
        """Minimal schema-shaped resume when generation cannot complete."""
        return {
            "overview": {
                "name": "Your Name",
                "current_role": "",
                "company": "",
                "professional_summary": "Generation did not complete. Please edit or try again.",
            },
            "contact_info": {
                "phone": "",
                "email": "",
                "location": "",
                "profile_links": {"LinkedIn": "", "GitHub": "", "Portfolio": ""},
            },
            "skills": [],
            "work_experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
            "achievements": [],
        }
