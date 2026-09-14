#!/usr/bin/env python3
"""Debug multi-document relevance."""

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

def debug_multi_document():
    print("=== Debug Multi-Document Relevance ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Question asking for multiple aspects (implies multiple docs might be relevant)
    question = "Présidents des comités de sécurité et technique"
    print(f"Question: {question}")
    intent = analyzer.analyze(question)
    print(f"Intent: {intent}")
    print(f"Committee types: {intent.committee_types}")
    print(f"Multi indicator flag: {intent.multi_indicator_flag}")

    # Two candidates, each matching different aspects
    candidate_safety = make_candidate(
        text="Le président du comité de sécurité est Ahmed.",
        decision_number=8,
        decision_year=2026,
        committee_type="safety",
        entities=["Ahmed"]
    )

    candidate_technical = make_candidate(
        text="Le président du comité technique est Mohamed.",
        decision_number=9,
        decision_year=2026,
        committee_type="technical",
        entities=["Mohamed"]
    )

    # Irrelevant candidate
    candidate_irrelevant = make_candidate(
        text="Information sur les finances.",
        decision_number=7,
        decision_year=2026,
        committee_type="financial",
        entities=["Finance"]
    )

    candidates = [candidate_irrelevant, candidate_safety, candidate_technical]
    print(f"\nCandidates:")
    for i, c in enumerate(candidates):
        print(f"  {i}: committee={c.committee_type}, entities={c.entities}, text='{c.text[:30]}...', retrieval_score={c.score}")

    # Let's manually compute the relevance for each candidate
    print(f"\n=== Manual scoring for safety candidate ===")
    relevance_score_safety, match_flags_safety, reasons_safety = selector._compute_relevance(intent, candidate_safety)
    print(f"Relevance score: {relevance_score_safety}")
    print(f"Match flags: {match_flags_safety}")
    print(f"Reasons: {reasons_safety}")
    print(f"Above threshold (0.38)? {relevance_score_safety >= 0.38}")

    print(f"\n=== Manual scoring for technical candidate ===")
    relevance_score_technical, match_flags_technical, reasons_technical = selector._compute_relevance(intent, candidate_technical)
    print(f"Relevance score: {relevance_score_technical}")
    print(f"Match flags: {match_flags_technical}")
    print(f"Reasons: {reasons_technical}")
    print(f"Above threshold (0.38)? {relevance_score_technical >= 0.38}")

    print(f"\n=== Manual scoring for irrelevant candidate ===")
    relevance_score_irrelevant, match_flags_irrelevant, reasons_irrelevant = selector._compute_relevance(intent, candidate_irrelevant)
    print(f"Relevance score: {relevance_score_irrelevant}")
    print(f"Match flags: {match_flags_irrelevant}")
    print(f"Reasons: {reasons_irrelevant}")
    print(f"Above threshold (0.38)? {relevance_score_irrelevant >= 0.38}")

    # Now run the actual selector
    print(f"\n=== Actual selector results ===")
    relevant = selector.select(intent, candidates)
    print(f"Relevant results: {len(relevant)}")
    for i, r in enumerate(relevant):
        print(f"  {i}: committee={r.committee_type}, entities={r.entities}, score={r.relevance_score}, flags={r.match_flags}")
        print(f"      text='{r.text[:50]}...'")
        print(f"      reasons={r.reasons}")

if __name__ == "__main__":
    debug_multi_document()