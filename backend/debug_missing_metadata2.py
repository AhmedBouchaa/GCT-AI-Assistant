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

def debug_missing_metadata():
    print("=== MISSING METADATA FALLBACK TEST ===")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()

    question = "Information sur la sécurité industrielle"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Intent decision_numbers: {intent.decision_numbers}")
    print(f"Intent dates: {intent.dates}")
    print(f"Intent entities: {intent.entities}")
    print(f"Intent committee_types: {intent.committee_types}")

    # Candidate with no metadata but relevant text
    candidate_no_metadata = make_candidate(
        text="La sécurité industrielle est primordiale pour la protection des travailleurs.",
        # No decision_number, date, committee_type, entities
    )

    # Candidate with no metadata and irrelevant text
    candidate_irrelevant = make_candidate(
        text="Les profits financiers ont augmenté ce trimestre.",
        # No metadata
    )

    candidates = [candidate_irrelevant, candidate_no_metadata]
    print(f"\nCandidates:")
    for i, c in enumerate(candidates):
        print(f"  {i}: text='{c.text[:50]}...', score={c.score}")

    print(f"\n=== Detailed scoring ===")
    for i, candidate in enumerate(candidates):
        relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
        print(f"Candidate {i} ({'irrelevant' if i==0 else 'relevant'}):")
        print(f"  Relevance score: {relevance_score:.4f}")
        print(f"  Above threshold (0.37)? {relevance_score >= 0.37}")
        print(f"  Match flags: {match_flags}")
        print(f"  Reasons: {reasons}")
        print()

    relevant = selector.select(intent, candidates)
    print(f"Selected {len(relevant)} relevant documents:")
    for i, r in enumerate(relevant):
        print(f"  {i}: text='{r.text[:50]}...', score={r.relevance_score:.4f}")

if __name__ == "__main__":
    debug_missing_metadata()