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

def debug_scoring_breakdown():
    print("=== SCORING BREAKDOWN ANALYSIS ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    # Test case: exact date match
    question = "Événement du 20 octobre 2026"
    intent = analyzer.analyze(question)

    candidate_exact = make_candidate(
        text="Quelque chose s'est produit ce jour-là.",
        publication_date=datetime(2026, 10, 20)
    )

    print(f"Question: {question}")
    print(f"Intent dates: {intent.dates}")
    print(f"Candidate date: {candidate_exact.publication_date}")
    print(f"Candidate text: {candidate_exact.text}")
    print(f"Retrieval score: {candidate_exact.score}")

    # Manually compute each component
    retrieval_score = max(0.0, min(1.0, candidate_exact.score))
    print(f"\nRetrieval component: {selector._RETRIEVAL_WEIGHT} * {retrieval_score} = {selector._RETRIEVAL_WEIGHT * retrieval_score}")

    metadata_score, metadata_flags, metadata_reasons = selector._compute_metadata_match(intent, candidate_exact)
    print(f"Metadata score: {metadata_score} (weighted: {selector._METADATA_WEIGHT * metadata_score})")
    print(f"  Flags: {metadata_flags}")
    print(f"  Reasons: {metadata_reasons}")

    textual_score, textual_flags, textual_reasons = selector._compute_textual_match(intent, candidate_exact)
    print(f"Textual score: {textual_score} (weighted: {selector._TEXTUAL_WEIGHT * textual_score})")
    print(f"  Flags: {textual_flags}")
    print(f"  Reasons: {textual_reasons}")

    # Combined score
    combined = (
        selector._RETRIEVAL_WEIGHT * retrieval_score
        + selector._METADATA_WEIGHT * metadata_score
        + selector._TEXTUAL_WEIGHT * textual_score
    )
    print(f"\nCombined score: {combined}")
    print(f"Threshold: {selector._RELEVANCE_THRESHOLD}")
    print(f"Passes threshold: {combined >= selector._RELEVANCE_THRESHOLD}")

    # Test what happens if we increase date match score to 0.4
    print(f"\n=== WHAT IF DATE MATCH SCORE WAS 0.4 ===")
    # Temporarily modify the score in metadata computation
    original_metadata_score = metadata_score
    # We know date match contributed 0.3 to metadata_score
    adjusted_metadata_score = metadata_score + 0.1  # Increase from 0.3 to 0.4
    adjusted_combined = (
        selector._RETRIEVAL_WEIGHT * retrieval_score
        + selector._METADATA_WEIGHT * adjusted_metadata_score
        + selector._TEXTUAL_WEIGHT * textual_score
    )
    print(f"Adjusted metadata score: {adjusted_metadata_score}")
    print(f"Adjusted combined score: {adjusted_combined}")
    print(f"Adjusted passes threshold: {adjusted_combined >= selector._RELEVANCE_THRESHOLD}")

if __name__ == "__main__":
    debug_scoring_breakdown()