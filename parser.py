"""Extracts plain text from an uploaded PDF resume."""

import pdfplumber
from io import BytesIO


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Takes raw PDF bytes, returns extracted text (best-effort)."""
    text_parts = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    text = "\n".join(text_parts).strip()

    if not text:
        raise ValueError(
            "Could not extract any text from this PDF. "
            "It may be a scanned image rather than a text-based PDF."
        )

    return text
