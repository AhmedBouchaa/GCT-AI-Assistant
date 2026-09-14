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

def debug_committee():
    print("=== COMMITTEE DOCUMENT MATCHING TEST ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Arabic committee question
    question = "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Committee types detected: {intent.committee_types}")

    # Winner: exact committee match + entities match
    candidate_match = make_candidate(
        text="رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس هو محمد بن علي.",
        score=0.35,
        decision_number=2,
        decision_year=2026,
        publication_date=datetime(2026, 3, 15),
        committee_type="technical",
        entities=["محمد بن علي"]
    )

    # Partial match: one entity match but wrong committee
    candidate_partial = make_candidate(
        text="محمد بن علي هو رئيس اللجنة العامة.",
        score=0.45,
        decision_number=5,
        decision_year=2026,
        publication_date=datetime(2026, 2, 10),
        committee_type="general",
        entities=["محمد بن علي"]
    )

    # Low retrieval score but exact committee + entities
    candidate_low_retrieval = make_candidate(
        text="اللجنة الفنية - محمد بن علي رئيس.",
        score=0.1,
        decision_number=3,
        decision_year=2026,
        publication_date=datetime(2026, 1, 5),
        committee_type="technical",
        entities=["محمد بن علي"]
    )

    candidates = [candidate_low_retrieval, candidate_partial, candidate_match]
    print(f"\n=== Detailed scoring ===")
    for i, c in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, c)
        print(f"Candidate {i} ({c.file_name}):")
        print(f"  Retrieval score: {c.score}")
        print(f"  Committee: {c.committee_type}, Entities: {c.entities}")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold (0.37)? {relevance_score >= 0.37}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant candidates:")
    for i, r in enumerate(relevant):
        print(f"  {i}: {r.file_name}, relevance={r.relevance_score:.4f}")

if __name__ == "__main__":
    debug_committee()