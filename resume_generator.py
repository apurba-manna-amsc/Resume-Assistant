import requests
import json
import time
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ResumeGenerator:
    """
    AI-powered resume generator that creates structured, ATS-friendly resumes
    tailored to specific job descriptions using LLM capabilities.
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.llm_model = "llama3-70b-8192"
        
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
    
    def summarize_readme(self, readme_text: str, repo_name: str,llm_model = "llama3-70b-8192") -> str:
        """
        Enhanced README summarization for resume-ready project descriptions
        
        Args:
            readme_text (str): The README content to summarize
            repo_name (str): Name of the repository
        
        Returns:
            str: Professional project summary suitable for resume
        """
        # You can paste your custom prompt here
        prompt = f"""
You are an expert technical resume writer. Your task is to transform a GitHub README into a concise, professional project summary suitable for resumes and job applications.

**Project Name:** {repo_name}

**README Content:**
\"\"\"
{readme_text}
\"\"\"

**Requirements:**
Createa a professional short summary that includes:

1. **Project Purpose**: What problem does it solve or what functionality does it provide?
2. **Technical Stack**: Key technologies, frameworks, languages, and tools used
3. **Implementation Highlights**: Notable features, algorithms, integrations, or technical achievements
4. **Impact/Results**: Quantifiable outcomes, performance improvements, or user benefits (if mentioned)

**Guidelines:**
- Use action verbs (developed, implemented, built, designed, optimized)
- Include specific technical terms and technologies for keyword matching
- Mention any APIs, databases, cloud services, or third-party integrations
- Highlight unique technical contributions or problem-solving approaches
- Keep it professional and achievement-focused
- Avoid marketing language or excessive adjectives
- Make it ATS-friendly with relevant technical keywords

**Output Format:**
Provide only the summarized description without additional commentary or labels.

**Example Style:**
"Developed a real-time web application using React.js and Node.js that processes user data through REST APIs and MongoDB integration. Implemented JWT authentication, automated testing with Jest, and deployed on AWS with CI/CD pipeline using GitHub Actions. Optimized database queries resulting in 40% faster response times and integrated third-party payment processing APIs.
"""
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            payload = {
            "model": llm_model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a technical resume writing specialist who creates compelling project summaries from GitHub repositories."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent, professional output
            "max_tokens": 300    # Limit response length to keep summaries concise
        }
        
        
            try:
                response = requests.post(self.groq_api_url, headers=self.headers, json=payload)
                response.raise_for_status()
                result = response.json()
                summary = result["choices"][0]["message"]["content"].strip()
                
                # Clean up any potential formatting issues
                summary = summary.replace('"""', '').replace("'''", "")
                summary = ' '.join(summary.split())  # Normalize whitespace
                
                return summary
                
            except requests.exceptions.RequestException as e:
                llm_model = "compound-beta-mini"
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"❌ Failed to summarize {repo_name} after {max_retries} retries. Reason: {e}")
                    return f"Project: {repo_name} - Unable to generate summary"
                else:
                    print(f"⚠️ Retry {retry_count}/{max_retries} for {repo_name}. Waiting 10s...")
                    # time.sleep(10)
        
        return f"Project: {repo_name} - Unable to generate summary"
    
    def generate_project_summaries(self, project_details: Dict[str, str]) -> Dict[str, str]:
        """
        Generate summaries for all projects
        
        Args:
            project_details (dict): Dictionary with project names as keys and README content as values
        
        Returns:
            dict: Dictionary with project names as keys and summaries as values
        """
        project_summaries = {}
        total_projects = len(project_details)
        
        print(f"📝 Starting summarization for {total_projects} projects...")
        
        for i, (project_name, readme_content) in enumerate(project_details.items(), 1):
            print(f"📊 Summarizing project {i}/{total_projects}: {project_name}")
            
            # Add small delay to avoid hitting rate limits
            if i > 1:
                time.sleep(2)
            
            summary = self.summarize_readme(readme_content, project_name)
            project_summaries[project_name] = summary
            
            print(f"✅ Completed {project_name}")
        
        print(f"🎉 All {total_projects} project summaries generated successfully!")
        return project_summaries
    
    def generate_structured_resume(self, resume_text: str, project_summaries: str, job_description: str) -> Dict[str, Any]:
        """
        Generate a customized structured resume based on job description
        
        Args:
            resume_text (str): Resume in markdown/plain text format
            project_summaries (str): Additional project descriptions in plain text
            job_description (str): Target job description
        
        Returns:
            Dict[str, Any]: Structured resume data as a dictionary
        """
        if resume_text and project_summaries and job_description:
            print("we have all the data, now generating structured resume...")
        # You can paste your custom prompt here
        prompt = f"""
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
  "skills": [
    "Technical skills from resume",
    "Skills demonstrated in selected projects",
    "Skills mentioned in job description that candidate has experience with",
    "Relevant tools and technologies",
    "Programming languages",
    "Frameworks and libraries",
    "Soft skills relevant to the role",
    "Industry-specific skills",
    "Certifications and qualifications"
  ],
  "work_experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Start Date - End Date",
      "location": "City, State (if applicable)",
      "description": [
        "Quantified achievement matching job requirements (use numbers, %, $, etc.)",
        "Responsibility rewritten with job description keywords",
        "Impact-focused bullet point with measurable results",
        "Technical accomplishment relevant to target role"
      ]
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "duration": "Timeline",
      "description": [
        "Quantified outcome or result demonstrating the value of the project (e.g., improved performance, user engagement, scalability, etc.)",
        "Responsibility or role within the project using keywords aligned with target job descriptions",
        "Impact-focused point highlighting measurable improvements or challenges solved",
        "Technical achievement emphasizing tools, frameworks, or systems used relevant to the target role"
      ],
      "technologies": [
        "List of technologies used"
      ],
      "links": [
        "GitHub",
        "Live Demo", 
        "Documentation or Case Study"
      ]
    }}
  ],
  "education": [
    {{
      "degree": "Degree Type and Major", 
      "institution": "University/College Name",
      "duration": "Start Year - End Year"
    }}
  ],
  "certifications": [
    {{
      "name": "Certification Name",
      "issuer": "Issuing Organization", 
      "date": "Date Obtained",
      "credential_id": "ID (if applicable)"
    }}
  ],
  "achievements": [
    "Awards and recognitions relevant to the role",
    "Publications, patents, or notable contributions",
    "Leadership roles and initiative outcomes",
    "Quantified professional accomplishments"
  ]
}}

**CRITICAL RULES - NO FABRICATION:**
- NEVER add fake work experience, education, or achievements
- NEVER invent companies, dates, degrees, or certifications that don't exist in source materials
- NEVER create fictional projects or technologies not mentioned
- ONLY use information explicitly provided in the resume and project summaries
- ONLY infer skills that can be reasonably derived from actual experience described
- DO NOT add years of experience, salary figures, or specific metrics unless provided
- DO NOT create achievements or responsibilities not mentioned in source materials
- **Projects can be selected from the complete project portfolio, even if not currently on resume**

**CUSTOMIZATION PRIORITIES (WITHIN FACTUAL CONSTRAINTS):**
- **Select and prioritize projects from the complete portfolio** that best match job requirements
- Reorder and emphasize existing experience most relevant to target role
- Rephrase existing achievements using job description terminology
- Extract and highlight skills that actually appear in resume/projects
- Reorganize content to match job requirements priority
- Use job description keywords ONLY when describing existing experience
- Focus on presenting actual experience in most relevant context
- Optimize existing language for ATS scanning without adding false information
- **Curate project selection to tell the most compelling story for this specific role**

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
**IMPORTANT:** Return ONLY the final customized JSON object. No additional text, explanations, or formatting. Ensure all data is accurate and directly sourced from provided materials while being optimized for the specific job opportunity. **Select the most relevant projects from the complete portfolio to best match the target role.**"""
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert resume optimizer and ATS specialist. You create perfectly structured, keyword-optimized resumes that maximize job application success rates. Always return valid JSON format only."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        max_retries = 1
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"🔄 Generating structured resume (attempt {retry_count + 1}/{max_retries})...")
                
                response = requests.post(self.groq_api_url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                resume_json_str = response.json()["choices"][0]["message"]["content"].strip()
                
                print(f"📄 Raw resume JSON response received.\n {resume_json_str}")
                # Try to extract JSON from the response
                resume_json_str = self._extract_json_from_response(resume_json_str)
                print(f"📄 Cleaned resume JSON string: {resume_json_str}")
                # Parse the JSON
                resume_data = json.loads(resume_json_str)
                return resume_data
                # Validate the structure
                # if self._validate_resume_structure(resume_data):
                #     print("✅ Successfully generated structured resume!")
                #     return resume_data
                # else:
                #     raise ValueError("Invalid resume structure returned")
                    
            except (json.JSONDecodeError, ValueError, requests.exceptions.RequestException) as e:
                print(f"❌ Error generating structured resume: {e}...")
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"❌ Failed to generate valid resume after {max_retries} retries.")
                    # Return a basic structure as fallback
                    return self._get_fallback_resume_structure(resume_text, project_summaries)
                else:
                    print(f"⚠️ Retry {retry_count}/{max_retries}. Error: {str(e)[:100]}...")
                    time.sleep(5)
        
        # This should never be reached, but included for safety
        return self._get_fallback_resume_structure(resume_text, project_summaries)
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON content from LLM response that might contain extra text
        
        Args:
            response_text (str): Raw response from LLM
        
        Returns:
            str: Clean JSON string
        """
        # Remove markdown code blocks
        response_text = response_text.replace("```json", "").replace("```", "")
        
        # Find JSON content between curly braces
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return response_text[start_idx:end_idx + 1]
        
        return response_text.strip()
    
    def _validate_resume_structure(self, resume_data: Dict[str, Any]) -> bool:
        """
        Validate that the resume data has the expected structure
        
        Args:
            resume_data (dict): The parsed resume data
        
        Returns:
            bool: True if structure is valid
        """
        required_fields = ["name", "email", "summary", "skills", "experience", "projects", "education"]
        
        for field in required_fields:
            if field not in resume_data:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate that lists are actually lists
        list_fields = ["experience", "projects", "education"]
        for field in list_fields:
            if not isinstance(resume_data[field], list):
                print(f"❌ Field '{field}' should be a list")
                return False
        
        return True
    
    def _get_fallback_resume_structure(self, resume_text: str, project_summaries: str) -> Dict[str, Any]:
        """
        Generate a basic fallback resume structure when AI generation fails
        
        Args:
            resume_text (str): Original resume text
            project_summaries (str): Project summaries text
        
        Returns:
            Dict[str, Any]: Basic resume structure
        """
        print("⚠️ Using fallback resume structure...")
        
        return {
            "name": "Your Name",
            "email": "your.email@example.com",
            "phone": "Your Phone Number",
            "location": "Your Location",
            "linkedin": "Your LinkedIn",
            "github": "Your GitHub",
            "summary": "Please edit this summary section with your professional summary.",
            "skills": {
                "technical_skills": ["Please", "add", "your", "technical", "skills"],
                "programming_languages": ["Add", "programming", "languages"],
                "frameworks": ["Add", "frameworks"],
                "databases": ["Add", "databases"],
                "tools": ["Add", "tools"]
            },
            "experience": [
                {
                    "title": "Job Title",
                    "company": "Company Name",
                    "duration": "Start Date - End Date",
                    "location": "Location",
                    "description": "Please add your job description and achievements here."
                }
            ],
            "projects": [
                {
                    "name": "Project Name",
                    "description": "Please add project description here.",
                    "technologies": ["Add", "technologies", "used"]
                }
            ],
            "education": [
                {
                    "degree": "Your Degree",
                    "institution": "Your Institution",
                    "year": "Graduation Year",
                    "gpa": "GPA (optional)"
                }
            ],
            "certifications": ["Add your certifications here"],
            "note": "AI generation failed. Please manually edit all sections above."
        }
# Generate the PDF
if __name__ == "__main__":
    generator = ResumeGenerator()
    sample_resume = """# Sample resume text in markdown format
    sample_resume = """

    # Generate PDF from your JSON format
    filename = generator.generate_structured_resume(sample_resume, 
                                                     project_summaries="Sample project summaries",
                                                     job_description="Sample job description")
    print(f"Resume generated: {filename}")