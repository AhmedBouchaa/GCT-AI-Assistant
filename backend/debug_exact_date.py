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

def debug_exact_date_matching():
    print("=== EXACT DATE MATCHING DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "Événement du 20 octobre 2026"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent dates: {intent.dates}")

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
    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'wrong' if i==0 else 'exact'}):")
        print(f"  Text: {candidate.text}")
        print(f"  Publication date: {candidate.publication_date}")
        print(f"  Retrieval score: {candidate.score}")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold (0.37)? {relevance_score >= 0.37}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant candidates:")
    for i, r in enumerate(relevant):
        print(f"  {i}: publication_date={r.publication_date}, relevance={r.relevance_score:.4f}")
        print(f"  Match flags: {r.match_flags}")
        print(f"  Reasons: {r.reasons}")

if __name__ == "__main__":
    debug_exact_date_matching()