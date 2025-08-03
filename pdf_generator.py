import json
from typing import Dict, Any, List
from datetime import datetime
import os

# Import all required libraries for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class ResumePDFGenerator:
    """
    Professional PDF resume generator using ReportLab.
    Creates clean, ATS-friendly PDF resumes from structured JSON data.
    
    Note: This class contains the full implementation for PDF generation.
    You mentioned you have the full working code, so you can paste your 
    complete ResumePDFGenerator class implementation here.
    
    The class should include:
    - __init__ method for initialization
    - generate_resume_pdf method as the main entry point
    - Helper methods for formatting different sections
    - Styling and layout configurations
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Define custom styles matching professional resume format"""
        
        # Name header - reduced font size
        self.styles.add(ParagraphStyle(
            name='NameHeader',
            parent=self.styles['Title'],
            fontName='Times-Bold',
            fontSize=18,  # Reduced from 22
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=4,  # Reduced spacing
            spaceBefore=0
        ))
        
        # Contact info - reduced font size
        self.styles.add(ParagraphStyle(
            name='ContactInfo',
            parent=self.styles['Normal'],
            fontName='Times-Roman',
            fontSize=10,  # Reduced from 11
            alignment=TA_CENTER,
            spaceAfter=10,  # Reduced spacing
            spaceBefore=2
        ))
        
        # Section headers - reduced font size
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Normal'],
            fontName='Times-Bold',
            fontSize=10,  # Reduced from 12
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=4,  # Reduced spacing
            spaceBefore=8,  # Reduced spacing
            underlineProportion=0.05,
            underlineGap=1
        ))
        
        # Company header with right-aligned date
        self.styles.add(ParagraphStyle(
            name='CompanyHeader',
            parent=self.styles['Normal'],
            fontName='Times-Bold',
            fontSize=10,  # Reduced from 11
            textColor=colors.black,
            spaceAfter=2,
            spaceBefore=6  # Reduced spacing
        ))
        
        # Job title
        self.styles.add(ParagraphStyle(
            name='JobTitle',
            parent=self.styles['Normal'],
            fontName='Times-Italic',
            fontSize=10,  # Reduced from 11
            textColor=colors.black,
            spaceAfter=3,  # Reduced spacing
            leftIndent=0
        ))
        
        # Client subsection
        self.styles.add(ParagraphStyle(
            name='ClientHeader',
            parent=self.styles['Normal'],
            fontName='Times-Bold',
            fontSize=9,  # Reduced from 10
            textColor=colors.black,
            spaceAfter=3,  # Reduced spacing
            spaceBefore=3
        ))
        
        # Custom body text style
        self.styles.add(ParagraphStyle(
            name='ResumeBodyText',
            parent=self.styles['Normal'],
            fontName='Times-Roman',
            fontSize=9,  # Reduced from 10
            textColor=colors.black,
            spaceAfter=2,  # Reduced spacing
            alignment=TA_JUSTIFY,
            leftIndent=0
        ))
        
        # Bullet points
        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            fontName='Times-Roman',
            fontSize=9,  # Reduced from 10
            textColor=colors.black,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=1,  # Reduced spacing
            alignment=TA_JUSTIFY
        ))
        
        # Skills text
        self.styles.add(ParagraphStyle(
            name='SkillsText',
            parent=self.styles['Normal'],
            fontName='Times-Roman',
            fontSize=9,  # Reduced from 10
            spaceAfter=1,  # Reduced spacing
            alignment=TA_JUSTIFY
        ))
        
        # Education/Project title
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=self.styles['Normal'],
            fontName='Times-Bold',
            fontSize=10,  # Reduced from 11
            textColor=colors.black,
            spaceAfter=2,
            spaceBefore=3  # Reduced spacing
        ))
        
        # Education entry style for single line format
        self.styles.add(ParagraphStyle(
            name='EducationEntry',
            parent=self.styles['Normal'],
            fontName='Times-Roman',
            fontSize=10,
            textColor=colors.black,
            spaceAfter=1,
            spaceBefore=0,
            alignment=TA_LEFT
        ))

    def generate_resume_pdf(self, resume_json, filename="resume.pdf"):
        """
        Generate a professional PDF resume
        
        Args:
            resume_json (dict or str): Resume data in JSON format
            filename (str): Output PDF filename
        """
        # Parse JSON if string is provided
        if isinstance(resume_json, str):
            resume_data = json.loads(resume_json)
        else:
            resume_data = resume_json
        
        # Create PDF document with narrower margins
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            rightMargin=0.5*inch,   # Reduced from 0.75*inch
            leftMargin=0.5*inch,    # Reduced from 0.75*inch
            topMargin=0.3*inch,     # Reduced from 0.6*inch
            bottomMargin=0.3*inch   # Reduced from 0.6*inch
        )
        
        # Build content
        content = []
        
        # Header Section
        content.extend(self._build_header(resume_data))
        
        # Summary Section
        if resume_data.get('overview', {}).get('professional_summary'):
            content.extend(self._build_summary(resume_data))
        
        # Skills Section
        if resume_data.get('skills'):
            content.extend(self._build_skills(resume_data))
        
        # Experience Section
        if resume_data.get('work_experience'):
            content.extend(self._build_experience(resume_data))
        
        # Projects Section
        if resume_data.get('projects'):
            content.extend(self._build_projects(resume_data))
        
        # Education Section
        if resume_data.get('education'):
            content.extend(self._build_education(resume_data))
        
        # Achievements Section
        if resume_data.get('achievements'):
            content.extend(self._build_achievements(resume_data))
        
        # Certifications Section
        if resume_data.get('certifications') and len(resume_data['certifications']) > 0:
            content.extend(self._build_certifications(resume_data))
        
        # Build PDF
        doc.build(content)
        print(f"Resume PDF generated successfully: {filename}")
        return filename

    def _build_header(self, data):
        """Build header section with name and contact info"""
        content = []
        overview = data.get('overview', {})
        contact = data.get('contact_info', {})

        # Name in uppercase with styling
        name = overview.get('name', 'Name')
        content.append(Paragraph(name.upper(), self.styles['NameHeader']))
        content.append(Spacer(1, 4))

        # Contact info (location | phone | email)
        contact_parts = []
        if location := contact.get('location'):
            contact_parts.append(location)
        if phone := contact.get('phone'):
            contact_parts.append(phone)
        if email := contact.get('email'):
            contact_parts.append(f'<a href="mailto:{email}" color="blue">{email}</a>')

        # Profile links (GitHub, LinkedIn, etc.)
        profile_links = contact.get('profile_links', {})
        if isinstance(profile_links, dict):
            for platform, url in profile_links.items():
                if url:
                    link = f'<a href="{url}" color="blue">{platform}</a>'
                    contact_parts.append(link)

        # Join all parts with separator
        if contact_parts:
            contact_text = " | ".join(contact_parts)
            content.append(Paragraph(contact_text, self.styles['ContactInfo']))

        return content


    def _build_summary(self, data):
        """Build summary/objective section"""
        content = []
        summary = data.get('overview', {}).get('professional_summary')
        if summary:
            content.append(Paragraph("<u>OBJECTIVE</u>", self.styles['SectionHeader']))
            content.append(Paragraph(f"{summary}", self.styles['ResumeBodyText']))
            content.append(Spacer(1, 4))  # Reduced spacing
        return content

    def _build_skills(self, data):
        """Build skills section with grouped format"""
        content = []
        skills = data.get('skills', [])
        if skills:
            content.append(Paragraph("<u>TECHNICAL SKILLS</u>", self.styles['SectionHeader']))

            skill = ", ".join(skills)
            content.append(Paragraph(skill, self.styles['SkillsText']))
            
            # Group skills into categories (you can customize this logic)
            # skill_categories = {
            #     'Languages': [],
            #     'Frameworks & Libraries': [],
            #     'AI/ML': [],
            #     'Data Analysis': [],
            #     'Tools': []
            # }
            
            # # Simple categorization logic - you can enhance this
            # for skill in skills:
            #     skill_lower = skill.lower()
            #     if any(lang in skill_lower for lang in ['python', 'sql', 'mysql']):
            #         skill_categories['Languages'].append(skill)
            #     elif any(fw in skill_lower for fw in ['power bi', 'tableau', 'jupyter', 'colab']):
            #         skill_categories['Tools'].append(skill)
            #     elif any(ai in skill_lower for ai in ['ai', 'ml', 'nlp', 'llm', 'asr', 'tts', 'generative']):
            #         skill_categories['AI/ML'].append(skill)
            #     elif any(cloud in skill_lower for cloud in ['cloud', 'dbms']):
            #         skill_categories['Data Analysis'].append(skill)
            #     else:
            #         skill_categories['Tools'].append(skill)
            
            # # Display categorized skills
            # for category, category_skills in skill_categories.items():
            #     if category_skills:
            #         skills_text = f"{category}: {', '.join(category_skills)}"
            #         content.append(Paragraph(skills_text, self.styles['SkillsText']))
            
            # content.append(Spacer(1, 2))  # Reduced spacing
        
        return content

    def _create_company_date_table(self, company, duration):
        """Create a table with company name left-aligned and date right-aligned"""
        data = [[company, duration]]
        table = Table(data, colWidths=[5*inch, 2.5*inch])  # Adjusted for narrower margins
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Times-Bold'),
            ('FONTNAME', (1, 0), (1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),  # Reduced font size
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return table

    def _build_experience(self, data):
        """Build work experience section"""
        content = []
        work_exp = data.get('work_experience', [])
        if work_exp:
            content.append(Paragraph("<u>WORK EXPERIENCE</u>", self.styles['SectionHeader']))
            
            for job in work_exp:
                # Company and date table
                company = job.get('company', 'Company')
                duration = job.get('duration', '')
                content.append(self._create_company_date_table(company, duration))
                
                # Job title and location
                title = job.get('title', 'Position')
                location = job.get('location', '')
                if location:
                    job_title_text = f"{title} | {location}"
                else:
                    job_title_text = title
                content.append(Paragraph(job_title_text, self.styles['JobTitle']))
                
                # Job descriptions
                descriptions = job.get('description', [])
                if descriptions:
                    self._add_bullet_points(content, descriptions)
                
                content.append(Spacer(1, 6))  # Reduced spacing
        
        return content

    def _add_bullet_points(self, content, descriptions):
        """Add bullet points to content"""
        for desc in descriptions:
            bullet_text = f"• {desc}"
            content.append(Paragraph(bullet_text, self.styles['BulletPoint']))

    def _build_projects(self, data):
        """Build projects section"""
        content = []
        projects = data.get('projects', [])
        if projects:
            content.append(Paragraph("<u>PROJECTS</u>", self.styles['SectionHeader']))
            
            for project in projects:
                # Project name and duration
                project_name = project.get('name', 'Project')
                duration = project.get('duration', '')
                tech_list = project.get('technologies', [])
                
                # Format project title with technologies
                if tech_list:
                    project_title = f"{project_name} | {', '.join(tech_list)}"
                else:
                    project_title = project_name
                
                # if duration:
                #     content.append(self._create_company_date_table(project_title, duration))
                # else:
                content.append(Paragraph(project_title, self.styles['SubsectionTitle']))
                
                # # Project description
                # if project.get('description'):
                #     bullet_text = f"• {project['description']}"
                #     content.append(Paragraph(bullet_text, self.styles['BulletPoint']))
                
                # Project achievements
                if project.get('description'):
                    self._add_bullet_points(content, project['description'])
                
                content.append(Spacer(1, 6))  # Reduced spacing
        
        return content

    def _build_education(self, data):
        """Build education section in the requested format"""
        content = []
        education = data.get('education', [])
        if education:
            content.append(Paragraph("<u>EDUCATION</u>", self.styles['SectionHeader']))
            
            for edu in education:
                # Format: Institution - Degree | Duration
                institution = edu.get('institution', 'Institution')
                degree = edu.get('degree', 'Degree')
                duration = edu.get('duration', '')
                
                # Create the single line format
                if duration:
                    education_line = f"{institution} - {degree} | {duration}"
                else:
                    education_line = f"{institution} - {degree}"
                
                content.append(Paragraph(education_line, self.styles['EducationEntry']))
            
            content.append(Spacer(1, 4))  # Reduced spacing
        
        return content

    def _build_achievements(self, data):
        """Build achievements section"""
        content = []
        achievements = data.get('achievements', [])
        if achievements:
            content.append(Paragraph("<u>ACHIEVEMENTS</u>", self.styles['SectionHeader']))
            
            for achievement in achievements:
                bullet_text = f"• {achievement}"
                content.append(Paragraph(bullet_text, self.styles['BulletPoint']))
            
            content.append(Spacer(1, 4))  # Reduced spacing
        
        return content

    def _build_certifications(self, data):
        """Build certifications section"""
        content = []
        certifications = data.get('certifications', [])
        if certifications:
            content.append(Paragraph("<u>CERTIFICATIONS</u>", self.styles['SectionHeader']))
            
            for cert in certifications:
                if isinstance(cert, dict):
                    cert_name = cert.get('name', 'Certification')
                    if cert.get('issuer'):
                        cert_name += f" ({cert['issuer']})"
                    bullet_text = f"• {cert_name}"
                else:
                    bullet_text = f"• {cert}"
                    
                content.append(Paragraph(bullet_text, self.styles['BulletPoint']))
            
            content.append(Spacer(1, 4))  # Reduced spacing
        
        return content


# Example usage and testing
if __name__ == "__main__":
    # Sample resume data for testing
    sample_resume_data = {
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "+1-234-567-8900",
        "location": "New York, NY",
        "linkedin": "linkedin.com/in/johndoe",
        "github": "github.com/johndoe",
        "summary": "Experienced software developer with expertise in full-stack development and AI technologies.",
        "skills": {
            "technical_skills": ["Python", "JavaScript", "React", "Node.js"],
            "programming_languages": ["Python", "JavaScript", "Java", "C++"],
            "frameworks": ["React", "Django", "Express.js", "Spring Boot"],
            "databases": ["PostgreSQL", "MongoDB", "Redis"],
            "tools": ["Git", "Docker", "AWS", "Jenkins"]
        },
        "experience": [
            {
                "title": "Senior Software Developer",
                "company": "Tech Company Inc.",
                "duration": "2020 - Present",
                "location": "New York, NY",
                "description": "Led development of microservices architecture and improved system performance by 40%."
            }
        ],
        "projects": [
            {
                "name": "AI Resume Customizer",
                "description": "Built an AI-powered system to customize resumes based on job descriptions.",
                "technologies": ["Python", "Streamlit", "LLM APIs", "ReportLab"]
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "institution": "University of Technology",
                "year": "2018",
                "gpa": "3.8/4.0"
            }
        ],
        "certifications": ["AWS Certified Developer", "Python Professional Certification"]
    }
    
    # Test PDF generation
    try:
        generator = ResumePDFGenerator()
        filename = generator.generate_resume_pdf(sample_resume_data, "test_resume.pdf")
        print(f"✅ Test PDF generated successfully: {filename}")
    except Exception as e:
        print(f"❌ Error generating test PDF: {str(e)}")
        print("Please implement the ResumePDFGenerator methods with your existing code.")