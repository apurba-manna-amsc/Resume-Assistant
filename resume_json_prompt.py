"""LLM prompt template for tailored resume JSON generation."""


def build_tailored_resume_prompt(
    resume_text: str, project_summaries: str, job_description: str
) -> str:
    """Return the full instruction prompt for Groq resume JSON generation."""
    return f"""
You are an expert AI resume optimizer and ATS specialist. Your task is to analyze the provided resume, comprehensive project portfolio, and job description to create a highly customized, keyword-optimized JSON resume that maximizes job match potential.

**ANALYSIS REQUIREMENTS:**
1. Extract and match keywords from job description with resume content and all available projects
2. **Intelligently select the most relevant projects** from the complete project portfolio that best align with the job requirements (not limited to projects mentioned in current resume)
3. Identify skill gaps and infer relevant skills from experience and selected projects
4. Quantify achievements wherever possible (add metrics, percentages, numbers)
5. Prioritize experiences most relevant to the target role
6. Optimize for ATS (Applicant Tracking Systems) compatibility
7. Tailor all descriptions to align with job requirements

**PROJECT SELECTION STRATEGY:**
- Analyze ALL provided project summaries, not just those in the current resume
- Score projects based on relevance to job description keywords and requirements
- Select 3-5 most relevant projects that demonstrate skills required for the target role
- Prioritize projects that show progression and match the seniority level of the target position
- Include projects that fill skill gaps or strengthen weak areas in the resume

**JSON SCHEMA - Return ONLY this structured format:**
{{
  "overview": {{
    "name": "Full Name",
    "current_role": "Current Job Title(if applicable)",
    "company": "Current Company (if applicable)",
    "professional_summary": "2-3 sentence summary highlighting most relevant qualifications for this specific job"
  }},
  "contact_info": {{
    "phone": "Phone number",
    "email": "Email address",
    "location": "City, State/Country(if specified)",
    "profile_links": {{
      "LinkedIn": "",
      "GitHub": "",
      "Portfolio": ""
    }}
  }},
  "skills": [],
  "work_experience": [],
  "projects": [],
  "education": [],
  "certifications": [],
  "achievements": []
}}

**CRITICAL RULES - NO FABRICATION:**
- NEVER add fake work experience, education, or achievements
- ONLY use information explicitly provided in the resume and project summaries

---
**RESUME DATA:**
{resume_text}

---
**COMPLETE PROJECT PORTFOLIO:**
{project_summaries}

---
**TARGET JOB DESCRIPTION:**
{job_description}

---
**IMPORTANT:** Return ONLY the final customized JSON object. No markdown, no extra text.
"""
