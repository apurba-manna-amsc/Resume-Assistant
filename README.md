# 🤖 Resume Assistant

Transform your resume to match any job description using AI and your GitHub projects, with an intelligent chatbot for further customization!

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://resume-assistant-bxjnp2xgwgsw5k7k8hqxlj.streamlit.app/)

## 🌟 Features

- **AI-Powered Resume Generation**: Automatically customize your resume based on job descriptions
- **GitHub Integration**: Fetch and summarize your GitHub projects automatically
- **Multi-Format Support**: Upload resumes in PDF, TXT, or MD formats
- **Interactive Editor**: Edit your resume with an intuitive form-based interface
- **Intelligent Chatbot**: Continue customizing your resume through natural conversation after generation
- **Real-time Resume Updates**: Modify specific sections, add content, or refine details via chat
- **PDF Export**: Generate professional PDF resumes with one click
- **Parallel Processing**: Fast GitHub repository analysis using concurrent processing

## 🚀 Live Demo

Try the application here: [Resume Assistant](https://resume-assistant-bxjnp2xgwgsw5k7k8hqxlj.streamlit.app/)

## 📋 How It Works

1. **Upload Your Resume**: Upload your existing resume (PDF/TXT/MD) or paste the text
2. **Add Projects**: Connect your GitHub username or manually input project descriptions
3. **Paste Job Description**: Add the job description you're targeting
4. **Generate**: AI analyzes everything and creates a customized resume
5. **Chat to Customize**: Use the intelligent chatbot to further refine and update your resume
6. **Edit & Refine**: Use the interactive editor for manual adjustments
7. **Export**: Download your professional PDF resume

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **AI/ML**: Groq API for AI-powered content generation
- **PDF Processing**: pdfplumber for text extraction
- **PDF Generation**: Custom PDF generator
- **APIs**: GitHub API for repository analysis
- **Concurrency**: ThreadPoolExecutor for parallel processing

## 📦 Installation

### Prerequisites

- Python 3.8+
- Groq API Key

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/apurba-manna-amsc/resume-assistant.git
   cd resume-assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Run the application**
   ```bash
   streamlit run main.py
   ```

## 📁 Project Structure

```
resume-assistant/
├── main.py                 # Main Streamlit application
├── resume_generator.py     # AI resume generation logic
├── pdf_generator.py        # PDF creation utilities
├── resume_chat_widget.py   # Intelligent chatbot for resume customization
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (create this)
└── README.md              # This file
```

## 🔧 Configuration

### Required Environment Variables

- `GROQ_API_KEY`: Your Groq API key for AI functionality

### Optional GitHub Token

For better GitHub API rate limits, you can provide a GitHub personal access token in the UI. This is optional but recommended for users with many repositories.

## 📖 Usage Guide

### Step 1: Resume Input
- **Upload Method**: Upload your resume file (PDF, TXT, MD)
- **Paste Method**: Copy and paste your resume text directly

### Step 2: Projects Input
- **GitHub Username**: Automatically fetch and summarize your repositories
- **Manual Input**: Describe your projects manually
- **Both**: Combine GitHub projects with additional manual descriptions

### Step 3: Job Description
- Paste the complete job description you're targeting
- The AI will analyze requirements and tailor your resume accordingly

### Step 4: Generate & Customize
- Click "Generate Customized Resume" 
- **Use the chatbot** to make specific updates (e.g., "Add more details to my Python experience" or "Rewrite the summary to emphasize leadership")
- Use the interactive editor for manual refinements
- Preview your resume in structured format

### Step 5: Export
- Generate and download a professional PDF resume
- Filename includes your name and timestamp

## 🎯 Key Features Explained

### Intelligent Chatbot for Resume Customization
- **Post-generation refinement**: Continue improving your resume after initial generation
- **Natural language updates**: Simply tell the bot what you want to change
- **Section-specific modifications**: Update individual sections like experience, skills, or summary
- **Content enhancement**: Ask for more details, better phrasing, or specific improvements
- **Real-time updates**: See changes reflected immediately in your resume
- **Examples of chat commands**:
  - "Make my summary more compelling"
  - "Add more technical details to my first job"
  - "Rewrite my Python project description to highlight scalability"
  - "Update my skills section to match the job requirements better"

### AI Resume Customization
- Analyzes job descriptions for key requirements
- Matches your experience and projects to job needs
- Optimizes content for ATS (Applicant Tracking Systems)

### GitHub Integration
- Fetches all public repositories
- Extracts and analyzes README files
- Generates concise project summaries
- Uses parallel processing for fast execution

### Interactive Chat Assistant
- **Conversational resume editing**: Update your resume through natural conversation
- **Contextual understanding**: The bot understands your resume structure and content
- **Intelligent suggestions**: Get AI-powered recommendations for improvements
- **Instant updates**: Changes are applied in real-time to your resume data

### Smart PDF Generation
- Professional formatting
- ATS-friendly layout
- Preserves all sections and formatting

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

**Apurba Manna**
- Email: 98apurbamanna@gmail.com
- GitHub: [@apurba-manna-amsc](https://github.com/apurba-manna-amsc)
- LinkedIn: [apurba-manna](https://linkedin.com/in/apurba-manna)

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🔍 Troubleshooting

### Common Issues

1. **"GROQ_API_KEY not found"**
   - Ensure you've created a `.env` file with your Groq API key
   - Check that the key is valid and active

2. **GitHub rate limits**
   - Provide a GitHub personal access token for higher rate limits
   - Wait and try again if you hit the limit

3. **PDF generation fails**
   - Ensure all required resume sections have content
   - Check that the resume data is properly formatted

4. **File upload issues**
   - Supported formats: PDF, TXT, MD
   - Ensure files are not corrupted or password-protected

## 🎉 Acknowledgments

- Thanks to the Streamlit team for the amazing framework
- Groq for providing powerful AI capabilities
- GitHub for the comprehensive API

---

⭐ If you find this project helpful, please consider giving it a star on GitHub!
