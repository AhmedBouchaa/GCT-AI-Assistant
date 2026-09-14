"""Query analyzer for extracting structured intent from user questions."""

import re
from datetime import datetime
from typing import List
from .models import QueryIntent


class QueryAnalyzer:
    """Extracts intent from a user question using lightweight, deterministic rules."""

    # Regex patterns for decision numbers (same as in retriever for consistency)
    _DECISION_PATTERNS = [
        # Forms with slash : N° 010/2026, 010/2026, numero 10/2026, etc.
        re.compile(
            r"(?:N°|N\s*°|numéro|numero|décision|decision|القرار\s*رقم|القرار\s*عدد|العدد\s*:|عدد)?\s*(\d{1,4})\s*/\s*(\d{4})",
            re.IGNORECASE,
        ),
        # Forms arabes avec "لسنة" أو "سنة"
        re.compile(
            r"(?:القرار\s*رقم|القرار\s*عدد|العدد\s*:|عدد|رقم)\s*(\d{1,4})\s+(?:لسنة|سنة)\s+(\d{4})",
            re.IGNORECASE,
        ),
    ]

    # Month names for date parsing (French, English, Arabic)
    _MONTHS_FR = {
        "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
    }
    _MONTHS_EN = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    # Arabic month names (transliterated variants commonly used)
    _MONTHS_AR = {
        "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "مايو": 5, "يونيو": 6,
        "يوليو": 7, "أغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12
    }

    # Committee/topic keywords (multilingual)
    _COMMITTEE_KEYWORDS = {
        "safety": ["safety", "securité", " sécurité", "سلامة", "الأمن الصناعي"],
        "technical": ["technical", "technique", "تقنية", "الصيانة"],
        "financial": ["financial", "financier", "مالية", "المالية"],
        "emergency": ["emergency", "urgence", "طوارئ"],
    }

    # Indicators that suggest multiple documents may be needed
    _MULTI_INDICATORS = [
        # Plural forms and distribution words
        r"\bpresidents\b",
        r"\bprésidents\b",
        r"\b(?:ال)?رؤساء\b",
        r"\b(committees?|commissions?|لجان)\b",
        r"\b(and|et|و)\b",
        r"\b(each|chaque|كل)\b",
        r"\b(every|chaque|كل)\b",
        # Comparison words
        r"\b(compare|comparer|مقارنة|أفضل|أسوأ|versus|vs)\b",
        # Date ranges and lists
        r"\b(between|entre|بين)\b",
        r"\b(and|et|و)\s+\d{4}\b",  # and 2025, et 2025, و 2025
        # Distribution across entities/departments
        r"\b(across|par|cross|dans les)\b",
        r"\b(departments?|services?|الأقسام|الخدمات)\b",
    ]

    def __init__(self):
        # Precompile multi-indicator regexes for efficiency
        self._multi_patterns = [re.compile(pat, re.IGNORECASE) for pat in self._MULTI_INDICATORS]

    def analyze(self, question: str) -> QueryIntent:
        """Analyze the question and return structured intent."""
        if not question or not question.strip():
            return QueryIntent(raw_question=question or "")

        intent = QueryIntent(raw_question=question)

        # 1. Language detection (reuse existing logic, but we can do lightweight version)
        intent.language = self._detect_language(question)

        # 2. Extract decision numbers (N° XXX/2026)
        intent.decision_numbers = self._extract_decision_numbers(question)

        # 3. Extract dates (various formats)
        intent.dates = self._extract_dates(question)

        # 4. Extract named entities (simple heuristic for person names and organizations)
        intent.entities = self._extract_entities(question)

        # 5. Extract committee/types from question
        intent.committee_types = self._extract_committee_types(question)

        # 6. Detect comparison intent
        intent.comparison_flag = self._detect_comparison(question)

        # 7. Detect multi-document indicators
        intent.multi_indicator_flag = self._detect_multi_indicators(question)

        return intent

    def _detect_language(self, text: str) -> str:
        """Lightweight language detection based on Unicode ranges and common words."""
        # Count Arabic characters
        arabic_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
        total_letters = sum(1 for c in text if c.isalpha())
        if total_letters == 0:
            return "unknown"
        arabic_ratio = arabic_chars / total_letters
        if arabic_ratio > 0.6:
            return "ar"
        # Simple French/English discrimination via common words
        text_lower = text.lower()
        french_indicators = ["le", "la", "les", "un", "une", "des", "et", "ou", "est", "sont", "quel", "quelle"]
        english_indicators = ["the", "a", "an", "and", "or", "is", "are", "what", "who", "when"]
        fr_score = sum(1 for w in french_indicators if w in text_lower)
        en_score = sum(1 for w in english_indicators if w in text_lower)
        if fr_score > en_score:
            return "fr"
        elif en_score > fr_score:
            return "en"
        else:
            # Default to French if ambiguous (project primary language)
            return "fr"

    def _extract_decision_numbers(self, text: str) -> List[tuple[int, int]]:
        """Extract decision numbers using the same patterns as the retriever."""
        numbers: List[tuple[int, int]] = []
        seen = set()
        for pat in self._DECISION_PATTERNS:
            for match in pat.finditer(text):
                num_str, year_str = match.group(1), match.group(2)
                try:
                    num_int = int(num_str)
                    year_int = int(year_str)
                except ValueError:
                    continue
                key = (num_int, year_int)
                if key not in seen:
                    seen.add(key)
                    numbers.append(key)
        return numbers

    def _extract_dates(self, text: str) -> List[datetime]:
        """Extract dates from various formats (simplified)."""
        dates: List[datetime] = []
        # Look for patterns like "20 octobre 2026", "octobre 20 2026", "20/10/2026", etc.
        # Day-month-year
        dmy_pattern = re.compile(r"(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})", re.IGNORECASE)
        for match in dmy_pattern.finditer(text):
            day, month_name, year = match.groups()
            try:
                month = self._MONTHS_FR[month_name.lower()]
                dates.append(datetime(int(year), month, int(day)))
            except (KeyError, ValueError):
                pass
        # Month-day-year (English)
        mdy_pattern = re.compile(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})", re.IGNORECASE)
        for match in mdy_pattern.finditer(text):
            month_name, day, year = match.groups()
            try:
                month = self._MONTHS_EN[month_name.lower()]
                dates.append(datetime(int(year), month, int(day)))
            except (KeyError, ValueError):
                pass
        # Arabic month names
        ar_pattern = re.compile(r"(\d{1,2})\s+(يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+(\d{4})")
        for match in ar_pattern.finditer(text):
            day, month_name, year = match.groups()
            try:
                month = self._MONTHS_AR[month_name]
                dates.append(datetime(int(year), month, int(day)))
            except (KeyError, ValueError):
                pass
        # Numeric formats: DD/MM/YYYY or MM/DD/YYYY (assume DD/MM for French/local context)
        numeric_pattern = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")
        for match in numeric_pattern.finditer(text):
            first, second, year = match.groups()
            try:
                # Assume DD/MM/YYYY (day first) as per French convention
                day, month = int(first), int(second)
                if 1 <= month <= 12 and 1 <= day <= 31:
                    dates.append(datetime(int(year), month, day))
            except ValueError:
                pass
        return dates

    def _extract_entities(self, text: str) -> List[str]:
        """Extract simple named entities (person names, organizations) using heuristics."""
        entities: List[str] = []
        # Pattern for person names: Capitalized words possibly with bin/bint/ben/etc.
        # Arabic: prefix like ابن, بنت, etc. followed by name
        ar_name_pattern = re.compile(r"(?:ابن|بنت|بن|بنت\s+ال|ال)\s+[؀-ۿ]{2,}")
        for match in ar_name_pattern.finditer(text):
            entities.append(match.group(0).strip())
        # Arabic: sequences of two or more Arabic words (likely a person name)
        # Each word should be at least 2 characters
        ar_seq_pattern = re.compile(r"[؀-ۿ]{2,}(?:\s+[؀-ۿ]{2,})+")
        for match in ar_seq_pattern.finditer(text):
            entities.append(match.group(0).strip())
        # French: M. / Mme / Monsieur followed by capitalized name
        fr_name_pattern = re.compile(r"(?:M\.?|Mme|Monsieur|Madame)\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*")
        for match in fr_name_pattern.finditer(text):
            entities.append(match.group(0).strip())
        # English: Mr. / Mrs. / Ms. followed by capitalized name
        en_name_pattern = re.compile(r"(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*")
        for match in en_name_pattern.finditer(text):
            entities.append(match.group(0).strip())
        # Also catch sequences of two or more capitalized words (potential orgs)
        cap_seq_pattern = re.compile(r"\b[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+){1,3}\b")
        for match in cap_seq_pattern.finditer(text):
            entities.append(match.group(0).strip())
        # Deduplicate while preserving order
        seen = set()
        unique_entities = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                unique_entities.append(e)
        return unique_entities

    def _extract_committee_types(self, text: str) -> List[str]:
        """Extract committee/department types from question."""
        found: List[str] = []
        text_lower = text.lower()
        for committee_type, keywords in self._COMMITTEE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    found.append(committee_type)
                    break  # only add once per type
        # Additional checks for Arabic feminine forms and common variations
        if "الفنية" in text_lower or "الفني" in text_lower or "تقنية" in text_lower:
            if "technical" not in found:
                found.append("technical")
        if "السلامة" in text_lower or "الأمن" in text_lower:
            if "safety" not in found:
                found.append("safety")
        return list(dict.fromkeys(found))  # deduplicate

    def _detect_comparison(self, text: str) -> bool:
        """Detect if the question is asking for a comparison."""
        comparison_patterns = [
            r"\bcompare\b", r"\bcomparer\b", r"\bمقارنة\b",
            r"\bversus\b", r"\bvs\b", r"\bcontre\b",
            r"\bmeilleur\b", r"\bأفضل\b", r"\bbetter\b",
            r"\bpire\b", r"\bassou\b", r"\b(?:ال)?أسوأ\b",
            r"\bdifférence\b", r"\bifference\b", r"\b(?:ال)?فرق\b", r"\bdifference\b",
        ]
        for pat in comparison_patterns:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    def _detect_multi_indicators(self, text: str) -> bool:
        """Detect indicators suggesting multiple documents may be needed."""
        for pattern in self._multi_patterns:
            if pattern.search(text):
                return True
        return False