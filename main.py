import streamlit as st
import json
import os
from typing import Dict, Any
import requests
import time
from resume_generator import ResumeGenerator
from pdf_generator import ResumePDFGenerator
from dotenv import load_dotenv
import tempfile
import pdfplumber
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import streamlit as st
from typing import Dict
from datetime import datetime
# from resume_chat_widget import FloatingChatWidget  # Import new chat widget
from resume_chat_widget import SidebarChatWidget  # New import

# Load environment variables
load_dotenv()

class StreamlitResumeApp:
    def __init__(self):
        self.resume_generator = ResumeGenerator()
        self.pdf_generator = ResumePDFGenerator()
        # self.chat_widget = FloatingChatWidget()  # Use new chat widget
        self.chat_widget = SidebarChatWidget()  # Change from FloatingChatWidget
        self.setup_page()
    
    def setup_page(self):
        """Configure Streamlit page settings"""
        st.set_page_config(
            page_title="AI Resume Customization System",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
    def validate_environment(self) -> bool:
        """Check if required environment variables are set"""
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            st.error("❌ GROQ_API_KEY not found in environment variables. Please set it up for the application to work.")
            return False
        return True
    
    def extract_text_from_file(self, uploaded_file) -> str:
        """Extract text from uploaded file"""
        try:
            if uploaded_file.type == "text/plain":
                return str(uploaded_file.read(), "utf-8")
            elif uploaded_file.type == "application/pdf":
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_file_path = tmp_file.name
                    
                        text = ""
                        with pdfplumber.open(tmp_file_path) as pdf:
                            for page in pdf.pages:
                                # Extract text from page
                                page_text = page.extract_text()
                                if page_text:
                                    text += page_text + "\n"

                                # Extract hyperlinks (annotations)
                                if page.annots:
                                    for annot in page.annots:
                                        uri = annot.get("uri")
                                        if uri:
                                            text += f"[Link: {uri}]\n"

                    
                    os.unlink(tmp_file_path)  # Clean up temp file
                    return text.strip()
                except Exception as e:
                    st.error(f"Error extracting text from PDF: {str(e)}")
                    return None
            else:
                return str(uploaded_file.read(), "utf-8")
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            return ""
    

    def get_github_projects(self, username: str, token: str = "") -> Dict[str, str]:
        """Fetch GitHub repositories and their README files using parallel processing."""
        if not username:
            return {}

        headers = {"Authorization": f"token {token}"} if token else {}
        project_details = {}

        # Create containers for progress tracking
        extraction_container = st.container()

        with extraction_container:
            st.markdown("#### 🔍 **GitHub Repository Extraction**")
            extraction_progress = st.progress(0)
            extraction_status = st.empty()

        try:
            # Step 1: Fetch all repos
            repos = []
            page = 1
            extraction_status.text("🔍 Fetching repositories list...")

            while True:
                url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
                res = requests.get(url, headers=headers)

                if res.status_code != 200:
                    st.error(f"Failed to fetch repositories: {res.status_code}")
                    return {}

                data = res.json()
                if not data:
                    break
                repos.extend(data)
                page += 1

            if not repos:
                st.warning("No repositories found for this user.")
                return {}

            total_repos = len(repos)
            readme_count = 0
            progress_step = 1.0 / total_repos

            # Step 2: Define the task
            def fetch_readme(repo):
                try:
                    repo_name = repo["name"]
                    default_branch = repo.get("default_branch", "main")

                    contents_url = f"https://api.github.com/repos/{username}/{repo_name}/contents?ref={default_branch}"
                    res = requests.get(contents_url, headers=headers)
                    if res.status_code != 200:
                        return repo_name, None

                    files = res.json()
                    readme_file = next((f for f in files if f["name"].lower().startswith("readme")), None)

                    if readme_file and "download_url" in readme_file:
                        readme_content = requests.get(readme_file["download_url"]).text
                        return repo_name, readme_content
                except Exception:
                    pass
                return repo["name"], None

            # Step 3: Run in parallel
            max_workers = min(32, (os.cpu_count() or 1) + 4)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(fetch_readme, repo): repo for repo in repos}
                for i, future in enumerate(as_completed(futures)):
                    repo_name, content = future.result()
                    if content:
                        project_details[repo_name] = content
                        readme_count += 1

                    extraction_progress.progress((i + 1) * progress_step)
                    extraction_status.text(f"🔍 Processed {i + 1}/{total_repos}: {repo_name}")

            # Final update
            extraction_status.text(f"✅ **Extraction Complete**: Found README files in {readme_count} out of {total_repos} repositories")
            extraction_progress.progress(1.0)

        except Exception as e:
            extraction_status.error(f"❌ Error during extraction: {str(e)}")
            return {}

        return project_details

    
    def generate_project_summaries_with_progress(self, github_projects: Dict[str, str]) -> Dict[str, str]:
        """Generate project summaries with progress tracking"""
        if not github_projects:
            return {}
        
        # Create container for summarization progress
        summarization_container = st.container()
        
        with summarization_container:
            st.markdown("#### 🤖 **AI Project Summarization**")
            summarization_progress = st.progress(0)
            summarization_status = st.empty()
        
        try:
            summarization_status.text("🤖 Starting AI summarization process...")
            time.sleep(0.5)  # Brief pause for UI update
            
            # Generate summaries with progress tracking
            total_projects = len(github_projects)
            summaries = {}
            
            for i, (project_name, content) in enumerate(github_projects.items()):
                progress = (i + 1) / total_projects
                summarization_progress.progress(progress)
                summarization_status.text(f"🤖 Summarizing {project_name} ({i + 1}/{total_projects})...")
                
                # Call the actual summarization method
                try:
                    summary = self.resume_generator.summarize_readme(content, project_name)
                    summaries[project_name] = summary
                except Exception as e:
                    st.warning(f"⚠️ Failed to summarize {project_name}: {str(e)}")
                    summaries[project_name] = content  # Fallback to original content
            
            # Update final summarization status
            summarization_status.text(f"✅ **Summarization Complete**: Generated summaries for {len(summaries)} projects")
            summarization_progress.progress(1.0)
            
            return summaries
            
        except Exception as e:
            summarization_status.error(f"❌ Error during summarization: {str(e)}")
            return github_projects  # Return original projects if summarization fails
    
    def render_json_editor(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render structured form for editing resume JSON based on new schema"""
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
    
    def run(self):
        """Main application runner with new floating chat widget"""
        
        # Handle chat processing FIRST (before any UI rendering)
        self.chat_widget.handle_message_processing()
        
        st.title("📝 ResumeBot...")
        st.markdown("Transform your resume to match any job description using AI and your GitHub projects!")
        
        if not self.validate_environment():
            return
        
        # Initialize session state
        if 'resume_data' not in st.session_state:
            st.session_state.resume_data = None
        if 'project_summaries' not in st.session_state:
            st.session_state.project_summaries = {}
        if 'extracted_resume_text' not in st.session_state:
            st.session_state.extracted_resume_text = ""
        
        # Input Section
        st.header("📥 Input Information")
        
        # Resume Input with extracted text dropdown
        with st.expander("📄 Resume Input", expanded=True):
            resume_input_method = st.radio("Choose input method:", ["Upload File", "Paste Text"])
            
            resume_text = ""
            if resume_input_method == "Upload File":
                uploaded_file = st.file_uploader("Upload your resume", type=['txt', 'pdf', 'md'])
                if uploaded_file:
                    resume_text = self.extract_text_from_file(uploaded_file)
                    st.session_state.extracted_resume_text = resume_text
                    
                    # Show extracted text in dropdown
                    if resume_text:
                        with st.expander("👀 View Extracted Text", expanded=False):
                            st.text_area("Extracted Resume Text:", 
                                        value=resume_text, 
                                        height=300, 
                                        disabled=True,
                                        help="This is the text extracted from your uploaded file")
            else:
                resume_text = st.text_area("Paste your resume text here:", height=200)
                st.session_state.extracted_resume_text = resume_text
        
        # Projects Input
        with st.expander("🗂️ Projects Input", expanded=True):
            project_input_method = st.radio("Choose project source:", ["GitHub Username", "Manual Input", "Both"])
            
            github_projects = {}
            manual_projects = ""
            
            if project_input_method in ["GitHub Username", "Both"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    github_username = st.text_input("GitHub Username:")
                with col2:
                    github_token = st.text_input("GitHub Token (Optional):", type="password")
                
                if github_username and st.button("🚀 Fetch & Summarize GitHub Projects"):
                    # Step 1: Fetch GitHub Projects
                    with st.spinner("Fetching GitHub repositories..."):
                        github_projects = self.get_github_projects(github_username, github_token)
                    
                    # Step 2: Generate Project Summaries if projects were found
                    if github_projects:
                        summarized_projects = self.generate_project_summaries_with_progress(github_projects)
                        st.session_state.project_summaries.update(summarized_projects)
                        
                        # Success message
                        st.success(f"🎉 **Process Complete!** Successfully processed {len(summarized_projects)} projects")
                        
                        # Show fetched and summarized projects
                        with st.expander("📋 View Processed Projects", expanded=False):
                            for repo_name, summary in summarized_projects.items():
                                with st.container():
                                    st.markdown(f"### 🔹 **{repo_name}**")
                                    st.markdown(f"**Summary:** {summary[:300]}{'...' if len(summary) > 300 else ''}")
                                    st.markdown("---")
                    else:
                        st.warning("⚠️ No projects found or failed to fetch repositories")
            
            if project_input_method in ["Manual Input", "Both"]:
                manual_projects = st.text_area("Manual Project Descriptions:", 
                                              placeholder="Describe your projects here...", 
                                              height=150)
                if manual_projects:
                    st.session_state.project_summaries["manual_projects"] = manual_projects
        
        # Job Description Input
        with st.expander("💼 Job Description", expanded=True):
            job_description = st.text_area("Paste the job description here:", 
                                         placeholder="Enter the complete job description...", 
                                         height=200)
        
        # Generate Resume Button
        if st.button("🚀 Generate Customized Resume", type="primary"):
            if not st.session_state.extracted_resume_text:
                st.error("❌ Please provide your resume text")
                return
            if not st.session_state.project_summaries and not manual_projects:
                st.error("❌ Please provide project information")
                return
            if not job_description:
                st.error("❌ Please provide job description")
                return
            
            with st.spinner("🔄 Generating customized resume..."):
                # Prepare project text
                all_projects = "\n\n".join([
                    f"**{name}**: {content}" 
                    for name, content in st.session_state.project_summaries.items()
                ])
                
                # Generate resume
                try:
                    resume_json = self.resume_generator.generate_structured_resume(
                        st.session_state.extracted_resume_text, all_projects, job_description
                    )
                    st.session_state.resume_data = resume_json
                    st.success("✅ Resume generated successfully!")
                except Exception as e:
                    st.error(f"❌ Error generating resume: {str(e)}")
                    return
        
        # Edit and Preview Section
        if st.session_state.resume_data:
            st.header("✏️ Edit & Preview")
            
            # Show notification if resume was updated via chat
            if hasattr(st.session_state, 'chat_messages') and st.session_state.chat_messages:
                last_message = st.session_state.chat_messages[-1]
                if last_message.get('type') == 'success':
                    st.info("💬 Resume was updated via chat assistant")
            
            # Tab layout for editing options
            tab1, tab2 = st.tabs(["📝 Edit Resume", "🔍 Raw JSON"])
            
            with tab1:
                edited_resume = self.render_json_editor(st.session_state.resume_data)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Update Resume"):
                        st.session_state.resume_data = edited_resume
                        st.success("✅ Resume updated!")
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Reset Changes"):
                        st.rerun()
            
            with tab2:
                st.json(st.session_state.resume_data)
            
            # PDF Generation Section
            st.header("📄 Generate PDF")
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                try:
                    with st.spinner("📄 Generating PDF..."):
                        filename = self.pdf_generator.generate_resume_pdf(
                            st.session_state.resume_data,
                            f"{st.session_state.resume_data['overview']['name']}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
                        )
                        
                        # Read the generated PDF file
                        with open(filename, "rb") as pdf_file:
                            pdf_data = pdf_file.read()
                        
                        st.download_button(
                            label="📥 Download PDF",
                            data=pdf_data,
                            file_name=filename,
                            mime="application/pdf",
                            key="download_pdf"
                        )
                        
                        # Clean up the temporary file
                        os.remove(filename)
                        
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {str(e)}")
        
        # IMPORTANT: Render floating chat widget at the very end
        self.chat_widget.render_chat_widget()

# Run the application
if __name__ == "__main__":
    app = StreamlitResumeApp()

    app.run()

