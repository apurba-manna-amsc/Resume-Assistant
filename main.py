"""Streamlit entry point. Run with: streamlit run main.py"""

import logging

from streamlit_app import ResumeAssistantApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    try:
        ResumeAssistantApp().run_app()
    except Exception:
        logging.getLogger(__name__).exception("Fatal error starting Resume Assistant")
