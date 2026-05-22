"""Streamlit form editor for resume JSON sections."""

from typing import Any, Dict

import streamlit as st


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
            cert = normalize_certification_entry(cert)
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

