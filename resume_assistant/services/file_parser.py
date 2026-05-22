"""Resume file text extraction (PDF, TXT, MD)."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

import pdfplumber

from resume_assistant.core.errors import FileProcessingError

logger = logging.getLogger(__name__)


def parse_uploaded_resume_text(uploaded_file) -> str:
    """Extract plain text from an uploaded TXT, PDF, or MD resume file."""
    tmp_file_path: Optional[str] = None
    try:
        if uploaded_file.type == "text/plain":
            text = uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name

            text = ""
            with pdfplumber.open(tmp_file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    if page.annots:
                        for annot in page.annots:
                            uri = annot.get("uri")
                            if uri:
                                text += f"[Link: {uri}]\n"
        else:
            text = uploaded_file.read().decode("utf-8", errors="replace")

        text = text.strip()
        if not text:
            raise FileProcessingError(
                "No text could be extracted from this file. "
                "Try a different PDF or paste your resume as text."
            )
        return text
    except FileProcessingError:
        raise
    except UnicodeDecodeError as exc:
        raise FileProcessingError(
            "Could not read the file encoding. Save as UTF-8 text or PDF and try again."
        ) from exc
    except Exception as exc:
        raise FileProcessingError(
            "Failed to read the uploaded resume. Ensure the file is not password-protected.",
            detail=str(exc),
        ) from exc
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except OSError:
                logger.warning("Could not delete temp file %s", tmp_file_path)
