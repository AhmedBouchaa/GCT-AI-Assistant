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

def debug_weights():
    print("=== WEIGHTS DEBUG ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Test case: Arabic date matching
    question = "من هو رئيس اللجنة الأمنية في 20 أكتوبر 2026؟"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")

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
    print(f"\n=== Component scores ===")
    for i, candidate in enumerate(candidates):
        # Compute each component separately
        retrieval_score = max(0.0, min(1.0, candidate.score))

        metadata_score, metadata_flags, metadata_reasons = selector._compute_metadata_match(intent, candidate)

        textual_score, textual_flags, textual_reasons = selector._compute_textual_match(intent, candidate)

        # Combined score with current weights
        combined = (
            selector._RETRIEVAL_WEIGHT * retrieval_score
            + selector._METADATA_WEIGHT * metadata_score
            + selector._TEXTUAL_WEIGHT * textual_score
        )

        print(f"Candidate {i} ({'wrong date' if i==0 else 'correct'}):")
        print(f"  Retrieval: {retrieval_score:.3f} * {selector._RETRIEVAL_WEIGHT} = {selector._RETRIEVAL_WEIGHT * retrieval_score:.3f}")
        print(f"  Metadata:  {metadata_score:.3f} * {selector._METADATA_WEIGHT} = {selector._METADATA_WEIGHT * metadata_score:.3f} [{', '.join(metadata_reasons) if metadata_reasons else 'none'}]")
        print(f"  Textual:   {textual_score:.3f} * {selector._TEXTUAL_WEIGHT} = {selector._TEXTUAL_WEIGHT * textual_score:.3f} [{', '.join(textual_reasons) if textual_reasons else 'none'}]")
        print(f"  Combined:  {combined:.3f}")
        print(f"  Threshold: {selector._RELEVANCE_THRESHOLD:.3f}")
        print(f"  Pass:      {combined >= selector._RELEVANCE_THRESHOLD}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant candidates:")
    for i, r in enumerate(relevant):
        print(f"  {i}: {r.file_name}, relevance={r.relevance_score:.3f}")

if __name__ == "__main__":
    debug_weights()