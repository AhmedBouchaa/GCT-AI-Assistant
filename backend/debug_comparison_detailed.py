# -*- coding: utf-8 -*-
from datetime import datetime
from app.relevance.query_analyzer import QueryAnalyzer
from app.relevance.selector import RelevanceSelector
from app.relevance.models import CandidateDoc

def make_candidate(text, score=0.8, doc_id='test', file_name='test.pdf', page_number=1, chunk_index=0, decision_number=None, decision_year=None, publication_date=None, committee_type='', entities=None):
    return CandidateDoc(
        text=text,
        score=score,
        distance=1.0 - score,
        doc_id=doc_id,
        file_name=file_name,
        file_path=f'/data/{file_name}',
        page_number=page_number,
        chunk_index=chunk_index,
        chunk_id=f'{doc_id}_p{page_number}_c{chunk_index}',
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
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")
    print(f"Intent comparison_flag: {intent.comparison_flag}")
    print(f"Intent multi_indicator_flag: {intent.multi_indicator_flag}")

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
    print(f"\nCandidates:")
    for i, c in enumerate(candidates):
        print(f"  {i}: decision_number={c.decision_number}, decision_year={c.decision_year}, entities={c.entities}, score={c.score}")

    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'no comparison' if i==0 else 'comparison'}):")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold (0.37)? {relevance_score >= 0.37}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant documents:")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, entities={r.entities}, score={r.relevance_score:.4f}")

if __name__ == "__main__":
    debug_comparison()