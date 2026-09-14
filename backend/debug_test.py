#!/usr/bin/env python3
"""Debug test to see what's happening with the selector."""

from datetime import datetime
from app.relevance.query_analyzer import QueryAnalyzer
from app.relevance.selector import RelevanceSelector
from app.relevance.models import CandidateDoc

def make_candidate(
    text: str,
    score: float = 0.8,
    doc_id: str = "test",
    file_name: str = "test.pdf",
    page_number: int = 1,
    chunk_index: int = 0,
    decision_number: int = None,
    decision_year: int = None,
    publication_date: datetime = None,
    committee_type: str = "",
    entities: list = None,
) -> CandidateDoc:
    """Helper to create a CandidateDoc."""
    return CandidateDoc(
        text=text,
        score=score,
        distance=1.0 - score,  # inverse for demo
        doc_id=doc_id,
        file_name=file_name,
        file_path=f"/data/{file_name}",
        page_number=page_number,
        chunk_index=chunk_index,
        chunk_id=f"{doc_id}_p{page_number}_c{chunk_index}",
        decision_number=decision_number,
        decision_year=decision_year,
        publication_date=publication_date,
        committee_type=committee_type,
        entities=entities or [],
    )

def debug_exact_date():
    print("=== Debug Exact Date Matching ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "Événement du 20 octobre 2026"
    print(f"Question: {question}")
    intent = analyzer.analyze(question)
    print(f"Intent: {intent}")
    print(f"Dates: {intent.dates}")

    # Exact match
    candidate_exact = make_candidate(
        text="Quelque chose s'est produit ce jour-là.",
        publication_date=datetime(2026, 10, 20)
    )

    # Wrong date
    candidate_wrong = make_candidate(
        text="Quelque chose s'est produit un autre jour.",
        publication_date=datetime(2026, 10, 21)
    )

    candidates = [candidate_wrong, candidate_exact]
    print(f"\nCandidates:")
    for i, c in enumerate(candidates):
        print(f"  {i}: date={c.publication_date}, text='{c.text[:30]}...'")

    relevant = selector.select(intent, candidates)
    print(f"\nRelevant results: {len(relevant)}")
    for i, r in enumerate(relevant):
        print(f"  {i}: date={r.publication_date}, score={r.relevance_score}, flags={r.match_flags}")
        print(f"      text='{r.text[:50]}...'")
        print(f"      reasons={r.reasons}")

if __name__ == "__main__":
    debug_exact_date()