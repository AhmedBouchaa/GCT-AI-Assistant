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

def debug_comparison():
    print("=== COMPARISON QUESTION DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "Quel président est meilleur, Ahmed ou Mohamed?"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent comparison_flag: {intent.comparison_flag}")

    # Candidate that actually compares
    candidate_comparison = make_candidate(
        text="Comparaison des présidents: Ahmed est meilleur que Mohamed.",
        decision_number=12,
        decision_year=2026,
        entities=["Ahmed", "Mohamed"]
    )

    # Candidate that just mentions both without comparison
    candidate_no_comparison = make_candidate(
        text="Ahmed et Mohamed sont présidents de différents comités.",
        decision_number=13,
        decision_year=2026,
        entities=["Ahmed", "Mohamed"]
    )

    candidates = [candidate_no_comparison, candidate_comparison]
    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'no_comparison' if i==0 else 'comparison'}):")
        print(f"  Text: {candidate.text}")
        print(f"  Decision number: {candidate.decision_number}")
        print(f"  Entities: {candidate.entities}")
        print(f"  Retrieval score: {candidate.score}")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold (0.35)? {relevance_score >= 0.35}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant candidates:")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, relevance={r.relevance_score:.4f}")
        print(f"  Text: {r.text}")

if __name__ == "__main__":
    debug_comparison()