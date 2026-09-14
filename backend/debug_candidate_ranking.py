# -*- coding: utf-8 -*-
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

def debug_candidate_ranking():
    print("=== CANDIDATE RANKING DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "Président de la commission de sécurité N° 10/2026"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")
    print(f"Selector threshold: {selector._RELEVANCE_THRESHOLD}")

    # Candidate with strong metadata match but lower retrieval score
    candidate_strong_match = make_candidate(
        text="Info sur la décision 10/2026",
        decision_number=10,
        decision_year=2026,
        score=0.7
    )

    # Candidate with weak metadata match but higher retrieval score
    candidate_weak_match = make_candidate(
        text="Info générale sur la sécurité",
        decision_number=9,  # Close but not exact
        decision_year=2026,
        score=0.9
    )

    # Candidate with no match
    candidate_no_match = make_candidate(
        text="Info sur les finances",
        decision_number=5,
        decision_year=2026,
        score=0.8
    )

    candidates = [candidate_no_match, candidate_weak_match, candidate_strong_match]
    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'no_match' if i==0 else 'weak_match' if i==1 else 'strong_match'}):")
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
        print(f"  Match flags: {r.match_flags}")

if __name__ == "__main__":
    debug_candidate_ranking()