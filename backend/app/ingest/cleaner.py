import re
import unicodedata
from typing import Optional


def clean_text(text: Optional[str]) -> str:
    """Normalize raw text for ingestion: unicode normalization, whitespace cleanup, NUL removal."""
    if not text:
        return ""

    # NUL bytes (\x00) from pypdf/PyMuPDF page extraction break downstream prompts/embeddings
    text = text.replace("\x00", "")

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    cleaned = " ".join(lines)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()
