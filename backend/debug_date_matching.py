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

def debug_exact_date_matching():
    print("=== EXACT DATE MATCHING TEST ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "�v�nement du 20 octobre 2026"  # This is garbled in the test file, but let's see what the analyzer does
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")

    # Exact match
    candidate_exact = make_candidate(
        text="Quelque chose s'est produit ce jour-l�.",
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
        print(f"  {i}: publication_date={c.publication_date}, score={c.score}")

    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'wrong' if i==0 else 'exact'}):")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold (0.37)? {relevance_score >= 0.37}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant documents:")
    for i, r in enumerate(relevant):
        print(f"  {i}: publication_date={r.publication_date}, score={r.relevance_score:.4f}")

if __name__ == "__main__":
    debug_exact_date_matching()