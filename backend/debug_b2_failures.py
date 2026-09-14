# -*- coding: utf-8 -*-
"""Diagnose the 6 failing B2 tests in detail."""
from datetime import datetime
from app.relevance.query_analyzer import QueryAnalyzer
from app.relevance.selector import RelevanceSelector
from app.relevance.models import CandidateDoc


def make_candidate(text, score=0.8, doc_id="test", file_name="test.pdf",
                   page_number=1, chunk_index=0, decision_number=None,
                   decision_year=None, publication_date=None, committee_type="",
                   entities=None):
    return CandidateDoc(
        text=text, score=score, distance=1.0 - score,
        doc_id=doc_id, file_name=file_name, file_path=f"/data/{file_name}",
        page_number=page_number, chunk_index=chunk_index,
        chunk_id=f"{doc_id}_p{page_number}_c{chunk_index}",
        decision_number=decision_number, decision_year=decision_year,
        publication_date=publication_date, committee_type=committee_type,
        entities=entities or [],
    )


def show(name, question, candidates, expected_count, expected_ids=None):
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"Question: {question}")
    analyzer = QueryAnalyzer()
    selector = RelevanceSelector()
    intent = analyzer.analyze(question)
    print(f"Intent: {intent}")
    print(f"  decision_numbers={intent.decision_numbers}")
    print(f"  dates={[d.date().isoformat() for d in intent.dates]}")
    print(f"  entities={intent.entities}")
    print(f"  committee_types={intent.committee_types}")
    print(f"  comparison={intent.comparison_flag}, multi={intent.multi_indicator_flag}")
    print(f"Threshold: {selector._RELEVANCE_THRESHOLD}")
    print(f"\nCandidate scoring:")
    for i, c in enumerate(candidates):
        score, flags, reasons = selector._compute_relevance(intent, c)
        ok = "PASS" if score >= selector._RELEVANCE_THRESHOLD else "FAIL"
        print(f"  [{ok}] cand{i}: score={score:.4f} | retrieval={c.score} | "
              f"decision={c.decision_number}/{c.decision_year} | "
              f"date={c.publication_date.date().isoformat() if c.publication_date else None} | "
              f"committee={c.committee_type} | entities={c.entities}")
        print(f"       flags={flags}")
        print(f"       reasons={reasons}")
    relevant = selector.select(intent, candidates)
    print(f"\nSelected {len(relevant)} (expected {expected_count})")
    for r in relevant:
        print(f"  - {r.file_name} decision={r.decision_number} date={r.publication_date.date().isoformat() if r.publication_date else None} relevance={r.relevance_score:.4f}")
    if expected_ids:
        actual = {(r.decision_number, r.publication_date.date().isoformat() if r.publication_date else None) for r in relevant}
        print(f"  Expected ids: {expected_ids}")
        print(f"  Actual ids:   {actual}")


# Test 1: test_multi_document_relevance
show(
    "test_multi_document_relevance",
    "Présidents des comités de sécurité et technique",
    [
        make_candidate(text="Information sur les finances.", decision_number=7,
                       decision_year=2026, committee_type="financial",
                       entities=["Finance"]),
        make_candidate(text="Le président du comité de sécurité est Ahmed.",
                       decision_number=8, decision_year=2026,
                       committee_type="safety", entities=["Ahmed"]),
        make_candidate(text="Le président du comité technique est Mohamed.",
                       decision_number=9, decision_year=2026,
                       committee_type="technical", entities=["Mohamed"]),
    ],
    expected_count=2,
    expected_ids={(8, None), (9, None)},
)

# Test 2: test_missing_metadata_fallback
show(
    "test_missing_metadata_fallback",
    "Information sur la sécurité industrielle",
    [
        make_candidate(text="Les profits financiers ont augmenté ce trimestre."),
        make_candidate(text="La sécurité industrielle est primordiale pour la protection des travailleurs."),
    ],
    expected_count=1,
)

# Test 3: test_multilingual_arabic_question
show(
    "test_multilingual_arabic_question",
    "من هو رئيس Committees Amenity في 20 أكتوبر 2026؟",
    [
        make_candidate(text="رئيس Committees Amenity هو علي حسن في 25 أكتوبر 2026",
                       decision_number=51, decision_year=2026,
                       publication_date=datetime(2026, 10, 25),
                       committee_type="safety", entities=["علي حسن"]),
        make_candidate(text="رئيس Committees Amenity هو محمد بن علي في 20 أكتوبر 2026",
                       decision_number=50, decision_year=2026,
                       publication_date=datetime(2026, 10, 20),
                       committee_type="safety", entities=["محمد بن علي"]),
    ],
    expected_count=1,
    expected_ids={(50, "2026-10-20")},
)

# Test 4: test_multilingual_french_question
show(
    "test_multilingual_french_question",
    "Qui est le président du comité de sécurité le 20 octobre 2026?",
    [
        make_candidate(text="Le président du comité de sécurité est Pierre Martin le 25 octobre 2026.",
                       decision_number=31, decision_year=2026,
                       publication_date=datetime(2026, 10, 25),
                       committee_type="safety", entities=["Pierre Martin"]),
        make_candidate(text="Le président du comité de sécurité est Jean Dubois le 20 octobre 2026.",
                       decision_number=30, decision_year=2026,
                       publication_date=datetime(2026, 10, 20),
                       committee_type="safety", entities=["Jean Dubois"]),
    ],
    expected_count=1,
    expected_ids={(30, "2026-10-20")},
)

# Test 5: test_english_question
show(
    "test_english_question",
    "Who is the president of the safety committee on October 20, 2026?",
    [
        make_candidate(text="The president of the safety committee is John Doe on October 25, 2026.",
                       decision_number=41, decision_year=2026,
                       publication_date=datetime(2026, 10, 25),
                       committee_type="safety", entities=["John Doe"]),
        make_candidate(text="The president of the safety committee is Robert Smith on October 20, 2026.",
                       decision_number=40, decision_year=2026,
                       publication_date=datetime(2026, 10, 20),
                       committee_type="safety", entities=["Robert Smith"]),
    ],
    expected_count=1,
    expected_ids={(40, "2026-10-20")},
)

# Test 6: test_candidate_ranking
show(
    "test_candidate_ranking",
    "Président de la commission de sécurité N° 10/2026",
    [
        make_candidate(text="Info sur les finances", decision_number=5,
                       decision_year=2026, score=0.8),
        make_candidate(text="Info générale sur la sécurité", decision_number=9,
                       decision_year=2026, score=0.9),
        make_candidate(text="Info sur la décision 10/2026", decision_number=10,
                       decision_year=2026, score=0.7),
    ],
    expected_count=2,
    expected_ids={(10, None), (9, None)},
)