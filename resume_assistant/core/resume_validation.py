"""Validate and normalize resume JSON before edit and PDF export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

REQUIRED_TOP_LEVEL_KEYS = (
    "overview",
    "contact_info",
    "skills",
    "work_experience",
    "projects",
    "education",
    "certifications",
    "achievements",
)


@dataclass
class ResumeValidationResult:
    """Outcome of schema validation; ``normalized`` is safe for the editor and PDF."""

    valid: bool
    export_ready: bool
    normalized: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        lines = [line.strip().lstrip("• ").strip() for line in value.splitlines()]
        return [line for line in lines if line]
    return [str(value).strip()] if str(value).strip() else []


def _normalize_overview(raw: Any, fixes: List[str]) -> Dict[str, str]:
    if not isinstance(raw, dict):
        fixes.append("Replaced invalid overview with an empty object.")
        raw = {}
    return {
        "name": _as_str(raw.get("name")),
        "current_role": _as_str(raw.get("current_role")),
        "company": _as_str(raw.get("company")),
        "professional_summary": _as_str(raw.get("professional_summary")),
    }


def _normalize_contact(raw: Any, fixes: List[str]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        fixes.append("Replaced invalid contact_info with defaults.")
        raw = {}
    links = raw.get("profile_links")
    if not isinstance(links, dict):
        fixes.append("Reset profile_links to an empty object.")
        links = {}
    return {
        "phone": _as_str(raw.get("phone")),
        "email": _as_str(raw.get("email")),
        "location": _as_str(raw.get("location")),
        "profile_links": {
            "LinkedIn": _as_str(links.get("LinkedIn")),
            "GitHub": _as_str(links.get("GitHub")),
            "Portfolio": _as_str(links.get("Portfolio")),
        },
    }


def _normalize_work_experience(raw: Any, fixes: List[str]) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        fixes.append("work_experience was not a list; reset to [].")
        return []
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            fixes.append(f"Skipped work_experience[{i}] (not an object).")
            continue
        desc = item.get("description")
        if isinstance(desc, str):
            fixes.append(f"Converted work_experience[{i}].description from text to bullets.")
        out.append(
            {
                "title": _as_str(item.get("title")),
                "company": _as_str(item.get("company")),
                "duration": _as_str(item.get("duration")),
                "location": _as_str(item.get("location")),
                "description": _as_str_list(desc),
            }
        )
    return out


def _normalize_projects(raw: Any, fixes: List[str]) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        fixes.append("projects was not a list; reset to [].")
        return []
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            fixes.append(f"Skipped projects[{i}] (not an object).")
            continue
        tech = item.get("technologies")
        if isinstance(tech, str):
            fixes.append(f"Split projects[{i}].technologies from a comma-separated string.")
            tech = [t.strip() for t in tech.split(",") if t.strip()]
        elif not isinstance(tech, list):
            tech = []
        links = item.get("links")
        if isinstance(links, str):
            links = [line.strip() for line in links.splitlines() if line.strip()]
        elif not isinstance(links, list):
            links = []
        desc = item.get("description")
        if isinstance(desc, str):
            fixes.append(f"Converted projects[{i}].description from text to bullets.")
        out.append(
            {
                "name": _as_str(item.get("name")),
                "duration": _as_str(item.get("duration")),
                "description": _as_str_list(desc),
                "technologies": [str(t).strip() for t in tech if str(t).strip()],
                "links": [str(link).strip() for link in links if str(link).strip()],
            }
        )
    return out


def _normalize_education(raw: Any, fixes: List[str]) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        fixes.append("education was not a list; reset to [].")
        return []
    out: List[Dict[str, str]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            fixes.append(f"Skipped education[{i}] (not an object).")
            continue
        out.append(
            {
                "degree": _as_str(item.get("degree")),
                "institution": _as_str(item.get("institution")),
                "duration": _as_str(item.get("duration")),
            }
        )
    return out


def _normalize_certifications(raw: Any, fixes: List[str]) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        fixes.append("certifications was not a list; reset to [].")
        return []
    out: List[Dict[str, str]] = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            fixes.append(f"Wrapped certifications[{i}] string as a certification object.")
            out.append({"name": item.strip(), "issuer": "", "date": "", "credential_id": ""})
            continue
        if not isinstance(item, dict):
            fixes.append(f"Skipped certifications[{i}] (invalid type).")
            continue
        out.append(
            {
                "name": _as_str(item.get("name")),
                "issuer": _as_str(item.get("issuer")),
                "date": _as_str(item.get("date")),
                "credential_id": _as_str(item.get("credential_id")),
            }
        )
    return out


def validate_and_normalize_resume(
    data: Any,
    *,
    require_name_for_export: bool = True,
) -> ResumeValidationResult:
    """
    Validate resume JSON structure, coerce types for PDF/export, and collect issues.
    """
    errors: List[str] = []
    warnings: List[str] = []
    fixes: List[str] = []

    if not isinstance(data, dict):
        return ResumeValidationResult(
            valid=False,
            export_ready=False,
            normalized={},
            errors=["Resume data must be a JSON object (dictionary)."],
        )

    unknown_keys = sorted(set(data.keys()) - set(REQUIRED_TOP_LEVEL_KEYS))
    if unknown_keys:
        warnings.append(f"Unknown top-level fields (ignored): {', '.join(unknown_keys)}")

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            fixes.append(f"Added missing top-level key: {key}")

    overview = _normalize_overview(data.get("overview"), fixes)
    contact_info = _normalize_contact(data.get("contact_info"), fixes)
    skills_raw = data.get("skills")
    if isinstance(skills_raw, str):
        fixes.append("Split skills from a comma-separated string into a list.")
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    else:
        skills = _as_str_list(skills_raw)

    normalized: Dict[str, Any] = {
        "overview": overview,
        "contact_info": contact_info,
        "skills": skills,
        "work_experience": _normalize_work_experience(data.get("work_experience"), fixes),
        "projects": _normalize_projects(data.get("projects"), fixes),
        "education": _normalize_education(data.get("education"), fixes),
        "certifications": _normalize_certifications(data.get("certifications"), fixes),
        "achievements": _as_str_list(data.get("achievements")),
    }

    if not overview["name"]:
        if require_name_for_export:
            errors.append("Overview.name is required for PDF export.")
        else:
            warnings.append("Overview.name is empty.")
    if not overview["professional_summary"]:
        warnings.append("Professional summary is empty.")
    if not contact_info["email"]:
        warnings.append("Email is missing in contact_info.")
    if not skills:
        warnings.append("Skills list is empty.")
    if not normalized["work_experience"] and not normalized["projects"]:
        warnings.append("No work experience or projects — PDF may look sparse.")

    for i, job in enumerate(normalized["work_experience"]):
        if not job["title"] and not job["company"]:
            warnings.append(f"work_experience[{i}]: missing both title and company.")
        if not job["description"]:
            warnings.append(f"work_experience[{i}]: no bullet descriptions.")

    for i, proj in enumerate(normalized["projects"]):
        if not proj["name"]:
            warnings.append(f"projects[{i}]: missing project name.")

    export_ready = len(errors) == 0
    valid = export_ready and not any(
        msg.startswith("Resume data must") for msg in errors
    )

    return ResumeValidationResult(
        valid=valid,
        export_ready=export_ready,
        normalized=normalized,
        errors=errors,
        warnings=warnings,
        fixes_applied=fixes,
    )
