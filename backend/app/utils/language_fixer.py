"""Post-processing to enforce language compliance in generated answers.

When Mistral ignores language instructions and generates answers in the wrong
language, this module extracts the actual information and reformats it in the
correct language.

Strategies:
1. Detect and remove French/Arabic prefixes (e.g., "Le président", "La réunion")
2. Extract key information (names, dates, numbers)
3. Reformat as Arabic or French as needed
"""
import re


def strip_wrong_language_prefix(text: str, target_language: str) -> str:
    """Remove common prefixes that indicate wrong language generation.

    Examples:
        French prefix in Arabic answer: "Le président de..." → extract core info
        Arabic prefix in French answer: "الرئيس هو..." → extract core info
    """
    if not text:
        return text

    # Common French opening phrases that shouldn't be in Arabic answers
    if target_language == "ar":
        french_openers = [
            r"^Le président ",
            r"^La réunion ",
            r"^Le directeur ",
            r"^Selon ",
            r"^D'après ",
            r"^Le document ",
            r"^[A-Z][a-z]+ (?:de |du |est |a |pour |selon)",
        ]

        for pattern in french_openers:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                # Found French opener - this is likely wrong language
                # Try to extract the useful part
                text = text[match.end() :]

    # Common Arabic opening phrases that shouldn't be in French answers
    if target_language == "fr":
        # Arabic characters at the start usually mean wrong language
        if text and "ا" <= text[0] <= "ي":
            # Starts with Arabic - likely wrong
            # Look for transition to French or English
            lines = text.split("\n")
            for line in lines:
                if re.search(r"[a-zA-Z]{3,}", line):
                    text = line
                    break

    return text.strip()


def extract_key_information(text: str) -> dict:
    """Extract key information entities from the answer.

    Returns:
        dict with keys: names, dates, numbers, locations, actions
    """
    info = {
        "names": [],
        "dates": [],
        "numbers": [],
        "locations": [],
        "actions": [],
    }

    # Extract names (capitalized words or Arabic names)
    # English/French names
    name_pattern = r"\b[A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+\b"
    info["names"].extend(re.findall(name_pattern, text))

    # Arabic names (pattern: word + word, all Arabic)
    arabic_name_pattern = r"[؀-ۿ]+ [؀-ۿ]+"
    info["names"].extend(re.findall(arabic_name_pattern, text))

    # Extract dates (YYYY format, XX/YYYY format)
    date_pattern = r"\b(?:\d{1,2}/)?20\d{2}\b"
    info["dates"].extend(re.findall(date_pattern, text))

    # Extract numbers
    number_pattern = r"\b\d+\b"
    info["numbers"].extend(re.findall(number_pattern, text))

    # Extract file references (GCT_notes_exemples_50-X.pdf)
    file_pattern = r"GCT_notes_exemples_\d+-\d+\.pdf"
    info["actions"].extend(re.findall(file_pattern, text))

    return info


def reformat_as_arabic(text: str, info: dict) -> str:
    """Reformat text to be presented in Arabic.

    Strategy: Keep extracted French text but frame it in Arabic context.
    """
    # Remove French prefixes
    text = strip_wrong_language_prefix(text, "ar")

    # If text still looks French, try to preserve key info in Arabic phrasing
    if text and re.search(r"[a-zA-Z]{5,}", text):
        # Still mostly Latin - frame in Arabic
        names = info.get("names", [])
        files = info.get("actions", [])

        # Build Arabic response with French content preserved
        response = []

        if names:
            # "الرئيس هو: [name]"
            response.append(f"الرئيس هو: {', '.join(names)}")

        response.append(text)

        if files:
            response.append(f"المرجع: {', '.join(files)}")

        return "\n".join(response)

    return text


def reformat_as_french(text: str, info: dict) -> str:
    """Reformat text to be presented in French.

    Strategy: Remove Arabic characters/phrasing, emphasize French structure.
    """
    # Remove Arabic prefixes
    text = strip_wrong_language_prefix(text, "fr")

    # If text contains Arabic, try to extract meaning and re-express in French
    if re.search(r"[؀-ۿ]{5,}", text):
        # Significant Arabic content - try to re-express
        names = info.get("names", [])
        files = info.get("actions", [])

        response = []

        # French phrasing
        if names:
            response.append(f"Le président est: {', '.join(names)}")

        # Try to find any English/French words in the text
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text)
        if words:
            response.append(f"{' '.join(words[:20])}")

        if files:
            response.append(f"Source: {', '.join(files)}")

        return " ".join(response)

    return text


def enforce_language(text: str, target_language: str) -> str:
    """Main function: enforce language compliance in answer.

    If answer is in wrong language, attempt to fix it while preserving information.

    Args:
        text: Generated answer
        target_language: "ar" or "fr" (or "en")

    Returns:
        Answer in target language (or best effort)
    """
    if not text or target_language == "unknown":
        return text

    # Extract information
    info = extract_key_information(text)

    # Reformat based on target language
    if target_language == "ar":
        return reformat_as_arabic(text, info)
    elif target_language == "fr":
        return reformat_as_french(text, info)
    else:
        return text


def has_language_mismatch(text: str, target_language: str) -> bool:
    """Check if text appears to be in a language different from target.

    Args:
        text: Generated answer
        target_language: "ar" or "fr"

    Returns:
        True if significant mismatch detected
    """
    if not text or target_language == "unknown":
        return False

    # Count character types
    arabic_chars = sum(1 for c in text if "؀" <= c <= "ۿ")
    latin_chars = sum(1 for c in text if ("a" <= c.lower() <= "z") or c in "éèêàâ")
    total_chars = len(text)

    arabic_ratio = arabic_chars / total_chars if total_chars > 0 else 0
    latin_ratio = latin_chars / total_chars if total_chars > 0 else 0

    if target_language == "ar":
        # Arabic answer should be >40% Arabic characters
        return arabic_ratio < 0.4 and latin_ratio > 0.3

    elif target_language == "fr":
        # French answer should be >30% Latin characters
        return latin_ratio < 0.3 and arabic_ratio > 0.2

    return False
