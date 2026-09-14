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

analyzer = QueryAnalyzer()
selector = RelevanceSelector()

# Using escaped Unicode for safety
question = 'من هو رئيس اللجنة الأمنية في 20 أكتوبر 2026؟'
# Don't print the question to avoid encoding issues
# print('Question: [Arabic: من هو رئيس اللجنة الأمنية في 20 أكتوبر 2026؟]')
intent = analyzer.analyze(question)
# print(f'Intent: {intent}')
# print(f'Decision numbers: {intent.decision_numbers}')
# print(f'Dates: {intent.dates}')
# print(f'Entities: {intent.entities}')
# print(f'Committee types: {intent.committee_types}')

candidate_arabic = make_candidate(
    text='رئيس اللجنة الأمنية هو محمود بن علي في 20 أكتوبر 2026',
    decision_number=50,
    decision_year=2026,
    publication_date=datetime(2026, 10, 20),
    committee_type='safety',
    entities=['محمود بن علي']
)

candidate_wrong_date = make_candidate(
    text='رئيس اللجنة الأمنية هو علي حصن في 25 أكتوبر 2026',
    decision_number=51,
    decision_year=2026,
    publication_date=datetime(2026, 10, 25),
    committee_type='safety',
    entities=['علي حصن']
)

candidates = [candidate_wrong_date, candidate_arabic]
# print('\nCandidates:')
# for i, c in enumerate(candidates):
#     print(f'  {i}: decision_number={c.decision_number}, decision_year={c.decision_year}, date={c.publication_date}, committee={c.committee_type}, entities={c.entities}')

# print('\n=== Detailed scoring ===')
scores = []
for i, candidate in enumerate(candidates):
    relevance_score, match_flags, reasons = selector._compute_relevance(intent, candidate)
    scores.append(relevance_score)
    # print(f'Candidate {i}:')
    # print(f'  Relevance score: {relevance_score:.4f}')
    # print(f'  Above threshold (0.38)? {relevance_score >= 0.38}')
    # print(f'  Match flags: {match_flags}')
    # print(f'  Reasons: {reasons}')
    # print()

relevant = selector.select(intent, candidates)
# print(f'Selector results: {len(relevant)} relevant documents')
# for i, r in enumerate(relevant):
#     print(f'  {i}: decision_number={r.decision_number}, date={r.publication_date}, score={r.relevance_score:.4f}')

# Output results in a way that avoids encoding issues
print(f"SCORES:{scores[0]:.4f},{scores[1]:.4f}")
print(f"THRESHOLD:0.38")
print(f"ABOVE_THRESHOLD:{scores[0] >= 0.38},{scores[1] >= 0.38}")
print(f"SELECTED_COUNT:{len(relevant)}")
if len(relevant) > 0:
    print(f"SELECTED_0_DECISION_NUMBER:{relevant[0].decision_number}")
    print(f"SELECTED_0_DATE:{relevant[0].publication_date}")
    print(f"SELECTED_0_SCORE:{relevant[0].relevance_score:.4f}")
if len(relevant) > 1:
    print(f"SELECTED_1_DECISION_NUMBER:{relevant[1].decision_number}")
    print(f"SELECTED_1_DATE:{relevant[1].publication_date}")
    print(f"SELECTED_1_SCORE:{relevant[1].relevance_score:.4f}")