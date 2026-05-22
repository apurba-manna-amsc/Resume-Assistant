"""Streamlit entry point. Run with: streamlit run main.py"""

import logging

from resume_assistant.ui import ResumeAssistantApp
from resume_assistant.ui.logging_setup import configure_logging

configure_logging()

if __name__ == "__main__":
    try:
        ResumeAssistantApp().run_app()
    except Exception:
        logging.getLogger(__name__).exception("Fatal error starting Resume Assistant")
