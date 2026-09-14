"""
Language detection utility for the GCT AI Assistant.
Detects whether a text is primarily in Arabic, French, or English.
"""

import re


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.

    Args:
        text: The input text to analyze.

    Returns:
        One of: "ar" (Arabic), "fr" (French), "en" (English), "unknown".
    """
    if not text or not text.strip():
        return "unknown"

    # Count characters in each script
    arabic_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
    # Latin-1 Supplement for French accents
    french_chars = sum(1 for c in text if c in "àâäéèêëîïôöùûüÿæœçÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÆŒÇ")
    # Basic Latin (A-Z, a-z) for English
    latin_chars = sum(1 for c in text if ('a' <= c.lower() <= 'z'))

    total_chars = len(text)
    if total_chars == 0:
        return "unknown"

    # Calculate ratios
    arabic_ratio = arabic_chars / total_chars
    # French detection: if there are French-specific accented characters, likely French
    # But also consider that French text might not have accents in all words
    # We'll use a heuristic: if there are any French accented characters and Latin chars, likely French
    # However, to avoid misclassifying English with no accents, we require a minimum of French chars
    # For simplicity, we'll say: if there are French accented characters and the text is not mostly Arabic, then French
    # Otherwise, if there are Latin chars, then English
    # This is a simplification but works for our use case.

    if arabic_ratio > 0.6:
        return "ar"
    if french_chars > 0:
        return "fr"
    if latin_chars > 0:
        return "en"
    return "unknown"


def is_arabic(text: str) -> bool:
    """Check if the text is primarily in Arabic."""
    return detect_language(text) == "ar"


def is_french(text: str) -> bool:
    """Check if the text is primarily in French."""
    return detect_language(text) == "fr"


def is_english(text: str) -> bool:
    """Check if the text is primarily in English."""
    return detect_language(text) == "en"