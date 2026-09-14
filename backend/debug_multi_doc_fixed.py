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

def debug_multi_document():
    print("=== MULTI-DOCUMENT RELEVANCE DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Question asking for multiple aspects (implies multiple docs might be relevant)
    question = "Présidents des comités de sécurité et technique"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")
    print(f"Intent comparison_flag: {intent.comparison_flag}")
    print(f"Intent multi_indicator_flag: {intent.multi_indicator_flag}")
    print(f"Selector threshold: {selector._RELEVANCE_THRESHOLD}")

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
    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'irrelevant' if i==0 else 'safety' if i==1 else 'technical'}):")
        print(f"  Text: {candidate.text}")
        print(f"  Decision number: {candidate.decision_number}")
        print(f"  Decision year: {candidate.decision_year}")
        print(f"  Committee type: {candidate.committee_type}")
        print(f"  Entities: {candidate.entities}")
        print(f"  Retrieval score: {candidate.score}")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold ({selector._RELEVANCE_THRESHOLD})? {relevance_score >= selector._RELEVANCE_THRESHOLD}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant candidates:")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, committee={r.committee_type}, entities={r.entities}, relevance={r.relevance_score:.4f}")

if __name__ == "__main__":
    debug_multi_document()