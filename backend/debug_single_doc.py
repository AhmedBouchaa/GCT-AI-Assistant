# -*- coding: utf-8 -*-
from datetime import datetime
from app.relevance.query_analyzer import QueryAnalyzer
from app.relevance.selector import RelevanceSelector
from app.relevance.models import CandidateDoc

def make_candidate(text, score=0.8, decision_number=None, decision_year=None, publication_date=None, committee_type='', entities=None):
    return CandidateDoc(
        text=text,
        score=score,
        distance=1.0 - score,
        doc_id=f'doc_{decision_number or 1}',
        file_name=f'GCT_notes_exemples_50-{decision_number or 1}.pdf',
        file_path=f'/data/GCT_notes_exemples_50-{decision_number or 1}.pdf',
        page_number=1,
        chunk_index=0,
        chunk_id=f'doc_{decision_number or 1}_p1_c0',
        decision_number=decision_number,
        decision_year=decision_year,
        publication_date=publication_date,
        committee_type=committee_type,
        entities=entities or [],
    )

def debug_single_document():
    print("=== SINGLE DOCUMENT RELEVANCE DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Question with decision number
    question = "Quel est le contenu de la décision N° 010/2026?"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")

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
    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'match' if i==1 else 'no_match'}):")
        print(f"  Text: {candidate.text}")
        print(f"  Decision number: {candidate.decision_number}")
        print(f"  Decision year: {candidate.decision_year}")
        print(f"  Retrieval score: {candidate.score}")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold (0.65)? {relevance_score >= 0.65}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant candidates:")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, relevance={r.relevance_score:.4f}")

if __name__ == "__main__":
    debug_single_document()