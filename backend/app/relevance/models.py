"""Data models for the relevance selection pipeline."""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional


class QueryIntent:
    """Structured intent extracted from a user question."""

    def __init__(
        self,
        raw_question: str = "",
        language: str = "unknown",
        decision_numbers: Optional[List[tuple[int, int]]] = None,
        dates: Optional[List[datetime]] = None,
        entities: Optional[List[str]] = None,
        committee_types: Optional[List[str]] = None,
        comparison_flag: bool = False,
        multi_indicator_flag: bool = False,
    ):
        self.raw_question = raw_question
        self.language = language  # "ar", "fr", "en", "unknown"
        self.decision_numbers = decision_numbers or []  # [(number, year), ...]
        self.dates = dates or []  # [datetime, ...]
        self.entities = entities or []  # [entity strings]
        self.committee_types = committee_types or []  # ["safety", "technical", ...]
        self.comparison_flag = comparison_flag
        self.multi_indicator_flag = multi_indicator_flag

    def __repr__(self) -> str:
        return (
            f"QueryIntent(language={self.language}, "
            f"{len(self.decision_numbers)} decision numbers, "
            f"{len(self.dates)} dates, "
            f"{len(self.entities)} entities, "
            f"{len(self.committee_types)} committee types, "
            f"comparison={self.comparison_flag}, "
            f"multi={self.multi_indicator_flag})"
        )


class CandidateDoc:
    """A document retrieved by the existing retriever."""

    def __init__(
        self,
        text: str = "",
        score: float = 0.0,
        distance: float = 0.0,
        doc_id: str = "",
        file_name: str = "",
        file_path: str = "",
        page_number: Optional[int] = None,
        chunk_index: Optional[int] = None,
        chunk_id: str = "",
        # Metadata from ingestion (may be None if not present)
        decision_number: Optional[int] = None,
        decision_year: Optional[int] = None,
        publication_date: Optional[datetime] = None,
        committee_type: str = "",
        entities: Optional[List[str]] = None,
    ):
        self.text = text
        self.score = score  # retrieval score (similarity)
        self.distance = distance  # ChromaDB distance
        self.doc_id = doc_id
        self.file_name = file_name
        self.file_path = file_path
        self.page_number = page_number
        self.chunk_index = chunk_index
        self.chunk_id = chunk_id
        self.decision_number = decision_number
        self.decision_year = decision_year
        self.publication_date = publication_date
        self.committee_type = committee_type
        self.entities = entities or []


class RelevantDoc(CandidateDoc):
    """A document that passed relevance selection."""

    def __init__(
        self,
        text: str = "",
        score: float = 0.0,
        distance: float = 0.0,
        doc_id: str = "",
        file_name: str = "",
        file_path: str = "",
        page_number: Optional[int] = None,
        chunk_index: Optional[int] = None,
        chunk_id: str = "",
        decision_number: Optional[int] = None,
        decision_year: Optional[int] = None,
        publication_date: Optional[datetime] = None,
        committee_type: str = "",
        entities: Optional[List[str]] = None,
        # Relevance-specific fields
        relevance_score: float = 0.0,
        match_flags: Optional[dict] = None,
        reasons: Optional[List[str]] = None,
    ):
        super().__init__(
            text=text,
            score=score,
            distance=distance,
            doc_id=doc_id,
            file_name=file_name,
            file_path=file_path,
            page_number=page_number,
            chunk_index=chunk_index,
            chunk_id=chunk_id,
            decision_number=decision_number,
            decision_year=decision_year,
            publication_date=publication_date,
            committee_type=committee_type,
            entities=entities,
        )
        self.relevance_score = relevance_score  # combined relevance score
        self.match_flags = match_flags or {}  # which signals matched
        self.reasons = reasons or []  # human-readable reasons


class UsedDoc(RelevantDoc):
    """A relevant document that may have contributed to the answer."""

    def __init__(
        self,
        text: str = "",
        score: float = 0.0,
        distance: float = 0.0,
        doc_id: str = "",
        file_name: str = "",
        file_path: str = "",
        page_number: Optional[int] = None,
        chunk_index: Optional[int] = None,
        chunk_id: str = "",
        decision_number: Optional[int] = None,
        decision_year: Optional[int] = None,
        publication_date: Optional[datetime] = None,
        committee_type: str = "",
        entities: Optional[List[str]] = None,
        relevance_score: float = 0.0,
        match_flags: Optional[dict] = None,
        reasons: Optional[List[str]] = None,
        # Attribution fields
        used_ngram_overlap: float = 0.0,
        entity_bonus: float = 0.0,
        evidence_strength: float = 0.0,
    ):
        super().__init__(
            text=text,
            score=score,
            distance=distance,
            doc_id=doc_id,
            file_name=file_name,
            file_path=file_path,
            page_number=page_number,
            chunk_index=chunk_index,
            chunk_id=chunk_id,
            decision_number=decision_number,
            decision_year=decision_year,
            publication_date=publication_date,
            committee_type=committee_type,
            entities=entities,
            relevance_score=relevance_score,
            match_flags=match_flags,
            reasons=reasons,
        )
        self.used_ngram_overlap = used_ngram_overlap  # n-gram overlap with answer
        self.entity_bonus = entity_bonus  # bonus if answer entities in doc
        self.evidence_strength = evidence_strength  # combined evidence signal


class DisplayedDoc(UsedDoc):
    """A used document that meets the evidence threshold for display."""

    def __init__(
        self,
        text: str = "",
        score: float = 0.0,
        distance: float = 0.0,
        doc_id: str = "",
        file_name: str = "",
        file_path: str = "",
        page_number: Optional[int] = None,
        chunk_index: Optional[int] = None,
        chunk_id: str = "",
        decision_number: Optional[int] = None,
        decision_year: Optional[int] = None,
        publication_date: Optional[datetime] = None,
        committee_type: str = "",
        entities: Optional[List[str]] = None,
        relevance_score: float = 0.0,
        match_flags: Optional[dict] = None,
        reasons: Optional[List[str]] = None,
        used_ngram_overlap: float = 0.0,
        entity_bonus: float = 0.0,
        evidence_strength: float = 0.0,
    ):
        super().__init__(
            text=text,
            score=score,
            distance=distance,
            doc_id=doc_id,
            file_name=file_name,
            file_path=file_path,
            page_number=page_number,
            chunk_index=chunk_index,
            chunk_id=chunk_id,
            decision_number=decision_number,
            decision_year=decision_year,
            publication_date=publication_date,
            committee_type=committee_type,
            entities=entities,
            relevance_score=relevance_score,
            match_flags=match_flags,
            reasons=reasons,
            used_ngram_overlap=used_ngram_overlap,
            entity_bonus=entity_bonus,
            evidence_strength=evidence_strength,
        )