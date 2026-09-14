# -*- coding: utf-8 -*-
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

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

def debug_arabic():
    print("=== ARABIC QUESTION DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Arabic question
    question = "من هو رئيس اللجنة الأمنية في 20 أكتوبر 2026؟"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")

    # Correct answer candidate
    candidate_correct = make_candidate(
        text="رئيس اللجنة الأمنية هو محمد بن علي في 20 أكتوبر 2026",
        decision_number=50,
        decision_year=2026,
        publication_date=datetime(2026, 10, 20),
        committee_type="safety",
        entities=["محمد بن علي"]
    )

    # Wrong date candidate
    candidate_wrong_date = make_candidate(
        text="رئيس اللجنة الأمنية هو علي حسين في 25 أكتوبر 2026",
        decision_number=51,
        decision_year=2026,
        publication_date=datetime(2026, 10, 25),
        committee_type="safety",
        entities=["علي حسين"]
    )

    candidates = [candidate_wrong_date, candidate_correct]
    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'wrong date' if i==0 else 'correct'}):")
        print(f"  Text: {candidate.text}")
        print(f"  Decision number: {candidate.decision_number}")
        print(f"  Decision year: {candidate.decision_year}")
        print(f"  Publication date: {candidate.publication_date}")
        print(f"  Committee type: {candidate.committee_type}")
        print(f"  Entities: {candidate.entities}")
        print(f"  Retrieval score: {candidate.score}")
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
    debug_arabic()