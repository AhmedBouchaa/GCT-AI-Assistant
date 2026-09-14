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

def debug_single_document():
    print("=== SINGLE DOCUMENT TEST ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "Quel est le contenu de la décision N° 010/2026?"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")

    candidate_match = make_candidate(
        text="Le contenu de la décision N° 010/2026 concerne la sécurité.",
        decision_number=10,
        decision_year=2026,
        score=0.7
    )

    candidate_no_match = make_candidate(
        text="Contenu d'une autre décision sur la finance.",
        decision_number=5,
        decision_year=2026,
        score=0.9
    )

    candidates = [candidate_no_match, candidate_match]
    print(f"\nCandidates:")
    for i, c in enumerate(candidates):
        print(f"  {i}: decision_number={c.decision_number}, decision_year={c.decision_year}, score={c.score}")

    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"\nCandidate {i} ({'match' if i==1 else 'no match'}):")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")

    relevant = selector.select(intent, candidates)
    print(f"\nSelected {len(relevant)} relevant documents:")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, score={r.relevance_score:.4f}")

def debug_multilingual_arabic():
    print("\n\n=== MULTILINGUAL ARABIC TEST ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Using the exact question from the test
    question = "من هو رئيس اللجنة الأمنية في 20 أكتوبر 2026؟"
    intent = analyzer.analyze(question)
    print(f"Question: [Arabic]")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")

    candidate_arabic = make_candidate(
        text="رئيس اللجنة الأمنية هو محمد بن علي في 20 أكتوبر 2026",
        decision_number=50,
        decision_year=2026,
        publication_date=datetime(2026, 10, 20),
        committee_type="safety",
        entities=["محمد بن علي"]
    )

    candidate_wrong_date = make_candidate(
        text="رئيس اللجنة الأمنية هو علي حسن في 25 أكتوبر 2026",
        decision_number=51,
        decision_year=2026,
        publication_date=datetime(2026, 10, 25),
        committee_type="safety",
        entities=["علي حسن"]
    )

    candidates = [candidate_wrong_date, candidate_arabic]
    print(f"\nCandidates:")
    for i, c in enumerate(candidates):
        print(f"  {i}: decision_number={c.decision_number}, decision_year={c.decision_year}, date={c.publication_date}")

    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"\nCandidate {i} ({'wrong date' if i==0 else 'match'}):")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")

    relevant = selector.select(intent, candidates)
    print(f"\nSelected {len(relevant)} relevant documents:")
    for i, r in enumerate(relevant):
        print(f"  {i}: decision_number={r.decision_number}, date={r.publication_date}, score={r.relevance_score:.4f}")

if __name__ == "__main__":
    debug_single_document()
    debug_multilingual_arabic()