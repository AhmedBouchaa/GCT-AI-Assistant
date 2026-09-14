#!/usr/bin/env python3
"""Debug single document relevance."""

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

def debug_single_document():
    print("=== Debug Single Document Relevance ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Question with decision number
    question = "Quel est le contenu de la décision N° 010/2026?"
    print(f"Question: {question}")
    intent = analyzer.analyze(question)
    print(f"Intent: {intent}")
    print(f"Decision numbers: {intent.decision_numbers}")

    # Candidate with matching decision number
    candidate_match = make_candidate(
        text="Le contenu de la décision N° 010/2026 concerne la sécurité.",
        decision_number=10,
        decision_year=2026,
        score=0.7  # Lower retrieval score but should be selected due to metadata match
    )

    # Candidate without matching decision number
    candidate_no_match = make_candidate(
        text="Contenu d'une autre décision sur la finance.",
        decision_number=5,
        decision_year=2026,
        score=0.9  # Higher retrieval score
    )

    candidates = [candidate_no_match, candidate_match]
    print(f"\nCandidates:")
    for i, c in enumerate(candidates):
        print(f"  {i}: decision_number={c.decision_number}, decision_year={c.decision_year}, text='{c.text[:30]}...', retrieval_score={c.score}")

    # Let's manually compute the relevance for each candidate
    print(f"\n=== Manual scoring for match candidate ===")
    relevance_score_match, match_flags_match, reasons_match = selector._compute_relevance(intent, candidate_match)
    print(f"Relevance score: {relevance_score_match}")
    print(f"Match flags: {match_flags_match}")
    print(f"Reasons: {reasons_match}")
    print(f"Above threshold (0.3)? {relevance_score_match >= 0.3}")

    print(f"\n=== Manual scoring for no match candidate ===")
    relevance_score_no_match, match_flags_no_match, reasons_no_match = selector._compute_relevance(intent, candidate_no_match)
    print(f"Relevance score: {relevance_score_no_match}")
    print(f"Match flags: {match_flags_no_match}")
    print(f"Reasons: {reasons_no_match}")
    print(f"Above threshold (0.3)? {relevance_score_no_match >= 0.3}")

    # Now run the actual selector
    print(f"\n=== Actual selector results ===")
    relevant = selector.select(intent, candidates)
    print(f"Relevant results: {len(relevant)}")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, decision_year={r.decision_year}, score={r.relevance_score}, flags={r.match_flags}")
        print(f"      text='{r.text[:50]}...'")
        print(f"      reasons={r.reasons}")

if __name__ == "__main__":
    debug_single_document()