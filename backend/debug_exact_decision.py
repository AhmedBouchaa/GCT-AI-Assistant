# -*- coding: utf-8 -*-
from app.relevance.query_analyzer import QueryAnalyzer
from app.relevance.selector import RelevanceSelector
from app.relevance.models import CandidateDoc
from datetime import datetime

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

def debug_exact_decision():
    print("=== EXACT DECISION NUMBER DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "Décision N° 015/2026 sur la sécurité"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Selector threshold: {selector._RELEVANCE_THRESHOLD}")

    # Exact match
    candidate_exact = make_candidate(
        text="Contenu de la décision 15/2026",
        decision_number=15,
        decision_year=2026
    )

    # Wrong year
    candidate_wrong_year = make_candidate(
        text="Contenu de la décision 15/2025",
        decision_number=15,
        decision_year=2025
    )

    # Wrong number
    candidate_wrong_number = make_candidate(
        text="Contenu de la décision 16/2026",
        decision_number=16,
        decision_year=2026
    )

    candidates = [candidate_wrong_year, candidate_wrong_number, candidate_exact]
    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'wrong_year' if i==0 else 'wrong_number' if i==1 else 'exact'}):")
        print(f"  Text: {candidate.text}")
        print(f"  Decision number: {candidate.decision_number}")
        print(f"  Decision year: {candidate.decision_year}")
        print(f"  Retrieval score: {candidate.score}")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold ({selector._RELEVANCE_THRESHOLD})? {relevance_score >= selector._RELEVANCE_THRESHOLD}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant candidates:")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, relevance={r.relevance_score:.4f}")
        print(f"  Text: {r.text}")

if __name__ == "__main__":
    debug_exact_decision()