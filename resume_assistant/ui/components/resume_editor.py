"""Streamlit form editor for resume JSON sections."""

from typing import Any, Dict

import streamlit as st

EDITOR_EPOCH_KEY = "resume_editor_epoch"


def bump_resume_editor_epoch() -> int:
    """Increment widget key generation so the form reloads from session resume_data."""
    epoch = int(st.session_state.get(EDITOR_EPOCH_KEY, 0)) + 1
    st.session_state[EDITOR_EPOCH_KEY] = epoch
    return epoch


def normalize_certification_entry(cert: Any) -> Dict[str, str]:
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


def render_resume_form_editor(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """Render expandable Streamlit forms for each resume JSON section."""
    epoch = int(st.session_state.get(EDITOR_EPOCH_KEY, 0))

    def k(suffix: str) -> str:
        return f"resume_ed_{epoch}_{suffix}"

    edited_data = {}

    with st.expander("Overview", expanded=True):
        overview = resume_data.get("overview", {})
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Full Name", value=overview.get("name", ""), key=k("overview_name")
            )
            current_role = st.text_input(
                "Current Role",
                value=overview.get("current_role", ""),
                key=k("overview_role"),
            )
        with col2:
            company = st.text_input(
                "Current Company",
                value=overview.get("company", ""),
                key=k("overview_company"),
            )

        professional_summary = st.text_area(
            "Professional Summary",
            value=overview.get("professional_summary", ""),
            height=100,
            key=k("overview_summary"),
        )

        edited_data["overview"] = {
            "name": name,
            "current_role": current_role,
            "company": company,
            "professional_summary": professional_summary,
        }

    with st.expander("Contact", expanded=False):
        contact_info = resume_data.get("contact_info", {})
        profile_links = contact_info.get("profile_links", {})

        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input(
                "Phone", value=contact_info.get("phone", ""), key=k("contact_phone")
            )
            email = st.text_input(
                "Email", value=contact_info.get("email", ""), key=k("contact_email")
            )
        with col2:
            location = st.text_input(
                "Location",
                value=contact_info.get("location", ""),
                key=k("contact_location"),
            )

        st.subheader("Profile Links")
        col3, col4, col5 = st.columns(3)
        with col3:
            linkedin = st.text_input(
                "LinkedIn",
                value=profile_links.get("LinkedIn", ""),
                key=k("contact_linkedin"),
            )
        with col4:
            github = st.text_input(
                "GitHub",
                value=profile_links.get("GitHub", ""),
                key=k("contact_github"),
            )
        with col5:
            portfolio = st.text_input(
                "Portfolio",
                value=profile_links.get("Portfolio", ""),
                key=k("contact_portfolio"),
            )

        edited_data["contact_info"] = {
            "phone": phone,
            "email": email,
            "location": location,
            "profile_links": {
                "LinkedIn": linkedin,
                "GitHub": github,
                "Portfolio": portfolio,
            },
        }

    with st.expander("Skills", expanded=True):
        skills = resume_data.get("skills", [])
        skill_text = ", ".join(skills) if isinstance(skills, list) else str(skills)
        skills_input = st.text_area(
            "Skills (comma-separated)",
            value=skill_text,
            height=100,
            help="Enter skills separated by commas",
            key=k("skills"),
        )
        edited_data["skills"] = [
            skill.strip() for skill in skills_input.split(",") if skill.strip()
        ]

    with st.expander("Work experience", expanded=True):
        work_experience = resume_data.get("work_experience", [])
        edited_data["work_experience"] = []

        if st.button("Add experience", key=k("add_work_exp")):
            work_experience.append(
                {
                    "title": "",
                    "company": "",
                    "duration": "",
                    "location": "",
                    "description": [],
                }
            )

        for i, exp in enumerate(work_experience):
            if i > 0:
                st.divider()
            st.markdown(f"**Role {i + 1}**")
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input(
                    "Job Title", value=exp.get("title", ""), key=k(f"exp_title_{i}")
                )
                company = st.text_input(
                    "Company", value=exp.get("company", ""), key=k(f"exp_company_{i}")
                )
            with col2:
                duration = st.text_input(
                    "Duration", value=exp.get("duration", ""), key=k(f"exp_duration_{i}")
                )
                exp_location = st.text_input(
                    "Location", value=exp.get("location", ""), key=k(f"exp_location_{i}")
                )

            description_list = exp.get("description", [])
            if isinstance(description_list, list):
                description_text = "\n".join([f"• {desc}" for desc in description_list])
            else:
                description_text = str(description_list)

            description = st.text_area(
                "Description (bullet points)",
                value=description_text,
                key=k(f"exp_desc_{i}"),
                height=100,
                help="Each line will become a bullet point",
            )

            description_list = [
                line.strip().lstrip("• ").strip()
                for line in description.split("\n")
                if line.strip()
            ]

            edited_data["work_experience"].append(
                {
                    "title": title,
                    "company": company,
                    "duration": duration,
                    "location": exp_location,
                    "description": description_list,
                }
            )

    with st.expander("Projects", expanded=True):
        projects = resume_data.get("projects", [])
        edited_data["projects"] = []

        if st.button("Add project", key=k("add_project")):
            projects.append(
                {
                    "name": "",
                    "duration": "",
                    "description": [],
                    "technologies": [],
                    "links": [],
                }
            )

        for i, proj in enumerate(projects):
            if i > 0:
                st.divider()
            st.markdown(f"**Project {i + 1}**")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Project Name",
                    value=proj.get("name", ""),
                    key=k(f"proj_name_{i}"),
                )
            with col2:
                duration = st.text_input(
                    "Duration",
                    value=proj.get("duration", ""),
                    key=k(f"proj_duration_{i}"),
                )

            description = proj.get("description", [])
            if isinstance(description, list):
                description_text = "\n".join([f"• {desc}" for desc in description])
            else:
                description_text = str(description)

            description_input = st.text_area(
                "Achievements",
                value=description_text,
                key=k(f"proj_desc_{i}"),
                help="Each line will become a bullet point",
            )

            technologies = proj.get("technologies", [])
            tech_text = (
                ", ".join(technologies)
                if isinstance(technologies, list)
                else str(technologies)
            )
            tech_input = st.text_input(
                "Technologies (comma-separated)",
                value=tech_text,
                key=k(f"proj_tech_{i}"),
            )

            links = proj.get("links", [])
            links_text = "\n".join(links) if isinstance(links, list) else str(links)
            links_input = st.text_area(
                "Links",
                value=links_text,
                key=k(f"proj_links_{i}"),
                help="One link per line",
            )

            edited_data["projects"].append(
                {
                    "name": name,
                    "duration": duration,
                    "description": [
                        line.strip().lstrip("• ").strip()
                        for line in description_input.split("\n")
                        if line.strip()
                    ],
                    "technologies": [
                        tech.strip() for tech in tech_input.split(",") if tech.strip()
                    ],
                    "links": [
                        link.strip()
                        for link in links_input.split("\n")
                        if link.strip()
                    ],
                }
            )

    with st.expander("Education", expanded=False):
        education = resume_data.get("education", [])
        edited_data["education"] = []

        if st.button("Add education", key=k("add_education")):
            education.append({"degree": "", "institution": "", "duration": ""})

        for i, edu in enumerate(education):
            st.markdown(f"**Education {i + 1}**")
            col1, col2 = st.columns(2)
            with col1:
                degree = st.text_input(
                    "Degree", value=edu.get("degree", ""), key=k(f"edu_degree_{i}")
                )
                institution = st.text_input(
                    "Institution",
                    value=edu.get("institution", ""),
                    key=k(f"edu_inst_{i}"),
                )
            with col2:
                duration = st.text_input(
                    "Duration",
                    value=edu.get("duration", ""),
                    key=k(f"edu_duration_{i}"),
                )

            edited_data["education"].append(
                {
                    "degree": degree,
                    "institution": institution,
                    "duration": duration,
                }
            )

    with st.expander("Certifications", expanded=False):
        certifications = resume_data.get("certifications", [])
        edited_data["certifications"] = []

        if st.button("Add certification", key=k("add_cert")):
            certifications.append(
                {"name": "", "issuer": "", "date": "", "credential_id": ""}
            )

        for i, cert in enumerate(certifications):
            cert = normalize_certification_entry(cert)
            st.markdown(f"**Certification {i + 1}**")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Certification Name",
                    value=cert.get("name", ""),
                    key=k(f"cert_name_{i}"),
                )
                issuer = st.text_input(
                    "Issuer", value=cert.get("issuer", ""), key=k(f"cert_issuer_{i}")
                )
            with col2:
                date = st.text_input(
                    "Date", value=cert.get("date", ""), key=k(f"cert_date_{i}")
                )
                credential_id = st.text_input(
                    "Credential ID",
                    value=cert.get("credential_id", ""),
                    key=k(f"cert_id_{i}"),
                )

            edited_data["certifications"].append(
                {
                    "name": name,
                    "issuer": issuer,
                    "date": date,
                    "credential_id": credential_id,
                }
            )

    with st.expander("Achievements", expanded=False):
        achievements = resume_data.get("achievements", [])
        if isinstance(achievements, list):
            achievements_text = "\n".join([f"• {ach}" for ach in achievements])
        else:
            achievements_text = str(achievements)

        achievements_input = st.text_area(
            "Achievements",
            value=achievements_text,
            height=100,
            help="Each line will become a bullet point",
            key=k("achievements"),
        )

        edited_data["achievements"] = [
            line.strip().lstrip("• ").strip()
            for line in achievements_input.split("\n")
            if line.strip()
        ]

    return edited_data
