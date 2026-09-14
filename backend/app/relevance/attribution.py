"""Source attribution for determining which relevant documents actually supported the answer."""

import re
from typing import List, Tuple
from .models import UsedDoc, DisplayedDoc, RelevantDoc


class SourceAttributor:
    """Attributes which relevant documents contributed to the generated answer."""

    def __init__(self, settings=None):
        self.settings = settings or {}
        self.ngram_size = self.settings.get("ngram_size", 2)  # we'll use bigrams and trigrams
        self.evidence_threshold = self.settings.get("evidence_threshold", 0.30)
        self.entity_bonus = self.settings.get("entity_bonus", 0.2)

    def attribute(self, answer: str, relevant_docs: List[RelevantDoc]) -> Tuple[List[UsedDoc], List[DisplayedDoc]]:
        """
        Determine which relevant documents were used to generate the answer and which should be displayed.

        Args:
            answer: The generated answer string
            relevant_docs: List of documents that passed relevance selection

        Returns:
            Tuple of (used_docs, displayed_docs)
            - used_docs: RelevantDoc objects with added used_ngram_overlap, entity_bonus, evidence_strength
            - displayed_docs: subset of used_docs where evidence_strength >= evidence_threshold
        """
        if not answer or not relevant_docs:
            return [], []

        used_docs: List[UsedDoc] = []

        # Precompute answer n-grams and entities
        answer_ngrams = self._get_ngrams(answer, n=self.ngram_size)
        answer_entities = self._extract_entities(answer)

        for doc in relevant_docs:
            # Compute n-gram overlap
            doc_ngrams = self._get_ngrams(doc.text, n=self.ngram_size)
            overlap = 0
            if answer_ngrams:
                overlap = len(answer_ngrams & doc_ngrams) / len(answer_ngrams)
            # Entity bonus: if any answer entity appears in doc text
            entity_bonus = 0.0
            if answer_entities:
                doc_text_lower = doc.text.lower()
                for ent in answer_entities:
                    if ent.lower() in doc_text_lower:
                        entity_bonus = self.entity_bonus
                        break  # one bonus is enough
            evidence_strength = min(1.0, overlap + entity_bonus)

            used_doc = UsedDoc(
                text=doc.text,
                score=doc.score,
                distance=doc.distance,
                doc_id=doc.doc_id,
                file_name=doc.file_name,
                file_path=doc.file_path,
                page_number=doc.page_number,
                chunk_index=doc.chunk_index,
                chunk_id=doc.chunk_id,
                decision_number=doc.decision_number,
                decision_year=doc.decision_year,
                publication_date=doc.publication_date,
                committee_type=doc.committee_type,
                entities=doc.entities,
                relevance_score=doc.relevance_score,
                match_flags=doc.match_flags,
                reasons=doc.reasons,
                used_ngram_overlap=overlap,
                entity_bonus=entity_bonus,
                evidence_strength=evidence_strength,
            )
            used_docs.append(used_doc)

        # Sort used docs by evidence strength (descending)
        used_docs.sort(key=lambda d: d.evidence_strength, reverse=True)

        # Filter for displayed docs
        displayed_docs: List[DisplayedDoc] = [
            DisplayedDoc(**ud.__dict__)
            for ud in used_docs
            if ud.evidence_strength >= self.evidence_threshold
        ]

        return used_docs, displayed_docs

    def _get_ngrams(self, text: str, n: int = 2) -> set:
        """Extract a set of n-grams from text (lowercased, alphanumeric only)."""
        if not text:
            return set()
        # Tokenize: split on non-alphanumeric, keep words of length >=2
        tokens = [token.lower() for token in re.findall(r'\b\w+\b', text) if len(token) >= 2]
        if len(tokens) < n:
            return set()
        ngrams = set()
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i+n])
            ngrams.add(ngram)
        return ngrams

    def _extract_entities(self, text: str) -> List[str]:
        """Extract simple entities from text (reuse same heuristic as query analyzer)."""
        # We'll use a simplified version: look for capitalized sequences and common Arabic name patterns
        entities: List[str] = []
        # Pattern for person names: sequences of two or more capitalized words (for French/English)
        cap_seq = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b')
        for match in cap_seq.finditer(text):
            entities.append(match.group(0).strip())
        # Arabic name patterns: ابن, بنت, بن, etc. followed by Arabic word
        ar_name = re.compile(r'(?:ابن|بنت|بن)\s+[؀-ۿ]{2,}')
        for match in ar_name.finditer(text):
            entities.append(match.group(0).strip())
        # Also catch sequences of Arabic words that might be names (crude)
        # We'll skip for now to avoid false positives
        # Deduplicate
        seen = set()
        unique = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                unique.append(e)
        return unique


# Convenience function
def attribute_sources(answer: str, relevant_docs: List[RelevantDoc], settings: Optional[Dict[str, Any]] = None) -> Tuple[List[UsedDoc], List[DisplayedDoc]]:
    """Convenience function to attribute sources."""
    attributor = SourceAttributor(settings)
    return attributor.attribute(answer, relevant_docs)