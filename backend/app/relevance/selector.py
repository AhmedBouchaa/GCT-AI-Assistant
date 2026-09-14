"""Relevance selector for filtering retrieved candidates based on query intent."""

from __future__ import annotations

import re
from datetime import date
from typing import List, Set, Tuple
from .models import CandidateDoc, QueryIntent, RelevantDoc


class RelevanceSelector:
    """Selects relevant documents from retrieved candidates using deterministic scoring."""

    # Weights for combining different score components
    _RETRIEVAL_WEIGHT = 0.1
    _METADATA_WEIGHT = 0.4
    _TEXTUAL_WEIGHT = 0.5

    # Threshold for considering a candidate relevant
    _RELEVANCE_THRESHOLD = 0.35

    def select(self, query_intent: QueryIntent, candidates: List[CandidateDoc]) -> List[RelevantDoc]:
        """Select relevant candidates based on query intent.

        Args:
            query_intent: Structured intent extracted from the question.
            candidates: List of documents retrieved by the existing retriever.

        Returns:
            List of relevant documents (empty if none meet relevance threshold).
        """
        if not candidates:
            return []

        relevant_docs: List[RelevantDoc] = []

        for candidate in candidates:
            # Compute relevance score and match flags
            relevance_score, match_flags, reasons = self._compute_relevance(
                query_intent, candidate
            )

            # Only include if above threshold
            if relevance_score >= self._RELEVANCE_THRESHOLD:
                # Create RelevantDoc extending CandidateDoc
                relevant_doc = RelevantDoc(
                    text=candidate.text,
                    score=candidate.score,
                    distance=candidate.distance,
                    doc_id=candidate.doc_id,
                    file_name=candidate.file_name,
                    file_path=candidate.file_path,
                    page_number=candidate.page_number,
                    chunk_index=candidate.chunk_index,
                    chunk_id=candidate.chunk_id,
                    decision_number=candidate.decision_number,
                    decision_year=candidate.decision_year,
                    publication_date=candidate.publication_date,
                    committee_type=candidate.committee_type,
                    entities=candidate.entities,
                    relevance_score=relevance_score,
                    match_flags=match_flags,
                    reasons=reasons,
                )
                relevant_docs.append(relevant_doc)

        return relevant_docs

    def _compute_relevance(
        self, query_intent: QueryIntent, candidate: CandidateDoc
    ) -> Tuple[float, dict, List[str]]:
        """Compute relevance score for a single candidate.

        Returns:
            Tuple of (relevance_score, match_flags, reasons)
        """
        match_flags = {}
        reasons = []

        # 1. Retrieval score (normalized to [0,1] - assume already normalized)
        retrieval_score = max(0.0, min(1.0, candidate.score))

        # 2. Metadata matching
        metadata_score, metadata_flags, metadata_reasons = self._compute_metadata_match(
            query_intent, candidate
        )
        match_flags.update(metadata_flags)
        reasons.extend(metadata_reasons)

        # 3. Textual relevance (token overlap)
        textual_score, textual_flags, textual_reasons = self._compute_textual_match(
            query_intent, candidate
        )
        match_flags.update(textual_flags)
        reasons.extend(textual_reasons)

        # Combine scores
        relevance_score = (
            self._RETRIEVAL_WEIGHT * retrieval_score
            + self._METADATA_WEIGHT * metadata_score
            + self._TEXTUAL_WEIGHT * textual_score
        )

        # Ensure score is in [0,1]
        relevance_score = max(0.0, min(1.0, relevance_score))

        return relevance_score, match_flags, reasons

    def _compute_metadata_match(
        self, query_intent: QueryIntent, candidate: CandidateDoc
    ) -> Tuple[float, dict, List[str]]:
        """Compute metadata-based match score.

        Returns:
            Tuple of (metadata_score, match_flags, reasons)
        """
        score = 0.0
        flags = {}
        reasons = []

        # Decision number and year match
        if query_intent.decision_numbers and candidate.decision_number is not None and candidate.decision_year is not None:
            match = False
            for num, year in query_intent.decision_numbers:
                if candidate.decision_number == num and candidate.decision_year == year:
                    match = True
                    break
            if match:
                score += 0.5
                flags["decision_number_match"] = True
                reasons.append(f"Exact decision number match: N° {num}/{year}")
            else:
                # explicit contradiction
                score -= 0.5
                flags["decision_number_mismatch"] = True
                reasons.append(f"Decision number mismatch: expected one of {query_intent.decision_numbers}, got {candidate.decision_number}/{candidate.decision_year}")

        # Date match
        if query_intent.dates and candidate.publication_date is not None:
            match = False
            for dt in query_intent.dates:
                if candidate.publication_date.date() == dt.date():
                    match = True
                    break
            if match:
                score += 0.85
                flags["date_match"] = True
                reasons.append(f"Exact date match: {dt.date().isoformat()}")
            else:
                # explicit contradiction
                score -= 0.85
                flags["date_mismatch"] = True
                reasons.append(f"Date mismatch: expected one of {query_intent.dates}, got {candidate.publication_date.date().isoformat()}")

        # Entity match (exact string match in entities)
        if query_intent.entities and candidate.entities:
            question_entities_set: Set[str] = set(e.lower() for e in query_intent.entities)
            candidate_entities_set: Set[str] = set(e.lower() for e in candidate.entities)
            overlap = question_entities_set & candidate_entities_set
            if overlap:
                # Boost proportional to overlap, max 0.2
                entity_score = min(0.2, 0.2 * len(overlap) / max(1, len(query_intent.entities)))
                score += entity_score
                flags["entity_match"] = True
                reasons.append(f"Entity overlap: {', '.join(overlap)}")

        # Committee type match
        if query_intent.committee_types and candidate.committee_type:
            match = False
            for ct in query_intent.committee_types:
                if candidate.committee_type.lower() == ct.lower():
                    match = True
                    break
            if match:
                score += 0.5
                flags["committee_match"] = True
                reasons.append(f"Committee type match: {candidate.committee_type}")
            else:
                # explicit contradiction
                score -= 0.5
                flags["committee_mismatch"] = True
                reasons.append(f"Committee type mismatch: expected one of {query_intent.committee_types}, got {candidate.committee_type}")

        # Normalize metadata score to [0,1] (we clip negative values to 0)
        metadata_score = max(0.0, min(1.0, score))

        return metadata_score, flags, reasons

    # Comparison patterns (same as in QueryAnalyzer for consistency)
    _COMPARISON_PATTERNS = [
        r"\bcompare\b", r"\bcomparer\b", r"\bمقارنة\b",
        r"\bversus\b", r"\bvs\b", r"\bcontre\b",
        r"\bmeilleur\b", r"\bأفضل\b", r"\bbetter\b",
        r"\bpire\b", r"\bassou\b", r"\b(?:ال)?أسوأ\b",
        r"\bdifférence\b", r"\bifference\b", r"\b(?:ال)?فرق\b", r"\bdifference\b",
    ]

    def _compute_textual_match(
        self, query_intent: QueryIntent, candidate: CandidateDoc
    ) -> Tuple[float, dict, List[str]]:
        """Compute textual relevance via token overlap.

        Returns:
            Tuple of (textual_score, match_flags, reasons)
        """
        # Tokenize question and candidate text (alphanumeric + Arabic letters)
        def tokenize(text: str) -> List[str]:
            # Match sequences of letters (including Arabic) and digits
            return re.findall(r'[\w؀-ۿ]+', text.lower(), flags=re.UNICODE)

        question_tokens: Set[str] = set(tokenize(query_intent.raw_question))
        candidate_tokens: Set[str] = set(tokenize(candidate.text))

        if not question_tokens:
            return 0.0, {}, []

        overlap = question_tokens & candidate_tokens
        # Jaccard similarity: overlap / union
        union = question_tokens | candidate_tokens
        jaccard = len(overlap) / len(union) if union else 0.0

        # Also compute overlap coefficient: overlap / min(len(q), len(c))
        overlap_coeff = len(overlap) / min(len(question_tokens), len(candidate_tokens)) if min(len(question_tokens), len(candidate_tokens)) else 0.0

        # Use the average of Jaccard and overlap coefficient
        textual_score = (jaccard + overlap_coeff) / 2.0

        # Bonus for comparison questions: if the query has a comparison flag and the candidate contains a comparison word
        if query_intent.comparison_flag:
            for pattern in self._COMPARISON_PATTERNS:
                if re.search(pattern, candidate.text, re.IGNORECASE):
                    textual_score = min(1.0, textual_score + 0.5)  # Boost by 0.5, capped at 1.0
                    break  # Only apply bonus once per candidate

        flags = {}
        reasons = []
        if overlap:
            flags["textual_overlap"] = True
            reasons.append(f"Textual overlap: {len(overlap)} common tokens")

        return textual_score, flags, reasons