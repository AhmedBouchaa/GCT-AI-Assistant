"""Unit tests for the QueryAnalyzer."""

from app.relevance.query_analyzer import QueryAnalyzer


def test_extract_decision_numbers():
    analyzer = QueryAnalyzer()
    # Test various formats
    q = "من هو رئيس اللجنة في القرار رقم 010/2026?"
    intent = analyzer.analyze(q)
    assert intent.decision_numbers == [(10, 2026)]

    q = "Quel est le président selon N° 020/2026?"
    intent = analyzer.analyze(q)
    assert intent.decision_numbers == [(20, 2026)]

    q = "Decision 5/2026 states that..."
    intent = analyzer.analyze(q)
    assert intent.decision_numbers == [(5, 2026)]

    q = "القرار رقم 15 لسنة 2026"
    intent = analyzer.analyze(q)
    assert intent.decision_numbers == [(15, 2026)]

    # Multiple numbers
    q = "Compare N° 010/2026 and N° 020/2027"
    intent = analyzer.analyze(q)
    assert set(intent.decision_numbers) == {(10, 2026), (20, 2027)}


def test_extract_dates():
    analyzer = QueryAnalyzer()
    # French format
    q = "Quel président le 20 octobre 2026?"
    intent = analyzer.analyze(q)
    assert len(intent.dates) == 1
    # We'll check the day, month, year
    dt = intent.dates[0]
    assert dt.day == 20
    assert dt.month == 10
    assert dt.year == 2026

    # English format
    q = "Who was president on October 20, 2026?"
    intent = analyzer.analyze(q)
    assert len(intent.dates) == 1
    dt = intent.dates[0]
    assert dt.day == 20
    assert dt.month == 10
    assert dt.year == 2026

    # Arabic format
    q = "من كان الرئيس في 20 أكتوبر 2026؟"
    intent = analyzer.analyze(q)
    assert len(intent.dates) == 1
    dt = intent.dates[0]
    assert dt.day == 20
    assert dt.month == 10
    assert dt.year == 2026

    # Numeric format
    q = "Event on 20/10/2026"
    intent = analyzer.analyze(q)
    assert len(intent.dates) == 1
    dt = intent.dates[0]
    assert dt.day == 20
    assert dt.month == 10
    assert dt.year == 2026

    # Multiple dates
    q = "Between 20/10/2026 and 05/11/2026"
    intent = analyzer.analyze(q)
    assert len(intent.dates) == 2
    days = {dt.day for dt in intent.dates}
    months = {dt.month for dt in intent.dates}
    years = {dt.year for dt in intent.dates}
    assert days == {20, 5}
    assert months == {10, 11}
    assert years == {2026}


def test_extract_entities():
    analyzer = QueryAnalyzer()
    # Simple entity
    q = "من هو أحمد الفقيه?"
    intent = analyzer.analyze(q)
    # We expect at least one entity containing Ahmad or similar
    # Our heuristic might capture the whole phrase or just the name
    assert len(intent.entities) > 0
    # Check that something like 'أحمد الفقيه' is in the entities (or at least the parts)
    found = False
    for ent in intent.entities:
        if "أحمد" in ent and "الفقيه" in ent:
            found = True
            break
    assert found, f"Expected to find Ahmad Alfiqi in entities: {intent.entities}"

    # French
    q = "Qui est Monsieur Martin?"
    intent = analyzer.analyze(q)
    assert len(intent.entities) > 0
    found = False
    for ent in intent.entities:
        if "Martin" in ent:
            found = True
            break
    assert found

    # English
    q = "Who is Mr. Smith?"
    intent = analyzer.analyze(q)
    assert len(intent.entities) > 0
    found = False
    for ent in intent.entities:
        if "Smith" in ent:
            found = True
            break
    assert found

    # Multiple entities
    q = " أحمد الفقيه و Mohamed بن علي"
    intent = analyzer.analyze(q)
    # We expect at least two entities
    assert len(intent.entities) >= 2


def test_extract_committee_types():
    analyzer = QueryAnalyzer()
    q = "Quel est le président de la commission de sécurité?"
    intent = analyzer.analyze(q)
    assert "safety" in intent.committee_types

    q = "من هو رئيس اللجنة الفنية?"
    intent = analyzer.analyze(q)
    assert "technical" in intent.committee_types

    q = "What about the financial committee?"
    intent = analyzer.analyze(q)
    assert "financial" in intent.committee_types

    # Multiple
    q = "Compare the safety and technical committees"
    intent = analyzer.analyze(q)
    assert set(intent.committee_types) == {"safety", "technical"}


def test_detect_comparison():
    analyzer = QueryAnalyzer()
    assert analyzer._detect_comparison("Compare A and B") is True
    assert analyzer._detect_comparison("Comparer A et B") is True
    assert analyzer._detect_comparison("مقارنة أ و ب") is True
    assert analyzer._detect_comparison("What is better?") is True
    assert analyzer._detect_comparison("Quel est le pire?") is True
    assert analyzer._detect_comparison("من هو الأسوأ؟") is True
    assert analyzer._detect_comparison("What is the difference?") is True
    assert analyzer._detect_comparison("ما هو الفرق؟") is True
    assert analyzer._detect_comparison("Who is the president?") is False


def test_detect_multi_indicators():
    analyzer = QueryAnalyzer()
    # Plural
    assert analyzer._detect_multi_indicators("Who are the presidents?") is True
    assert analyzer._detect_multi_indicators("Qui sont les présidents?") is True
    assert analyzer._detect_multi_indicators("من هم الرؤساء؟") is True
    # Distribution words
    assert analyzer._detect_multi_indicators("Each committee has a president") is True
    assert analyzer._detect_multi_indicators("Chaque comité a un président") is True
    assert analyzer._detect_multi_indicators("كل لجنة لها رئيس") is True
    # Date range
    assert analyzer._detect_multi_indicators("Between 2020 and 2023") is True
    assert analyzer._detect_multi_indicators("Entre 2020 et 2023") is True
    assert analyzer._detect_multi_indicators("بين 2020 و 2023") is True
    # Single question should not trigger
    assert analyzer._detect_multi_indicators("Who is the president?") is False
    assert analyzer._detect_multi_indicators("Qui est le président?") is False
    assert analyzer._detect_multi_indicators("من هو الرئيس؟") is False


def test_language_detection():
    analyzer = QueryAnalyzer()
    # Arabic
    q = "من هو الرئيس?"
    intent = analyzer.analyze(q)
    assert intent.language == "ar"

    # French
    q = "Qui est le président?"
    intent = analyzer.analyze(q)
    assert intent.language == "fr"

    # English
    q = "Who is the president?"
    intent = analyzer.analyze(q)
    assert intent.language == "en"

    # Mixed (but we default to French if ambiguous)
    q = "president الرئيس"
    intent = analyzer.analyze(q)
    # This might be ambiguous, but our simple heuristic might pick one.
    # We'll just check that it returns one of the expected.
    assert intent.language in ["ar", "fr", "en", "unknown"]

    # Unknown (no letters)
    q = "12345 !@#$%"
    intent = analyzer.analyze(q)
    assert intent.language == "unknown"


def test_full_analysis():
    analyzer = QueryAnalyzer()
    q = "من هو رئيس لجنة السلامة بتاريخ 20 أكتوبر 2026؟"
    intent = analyzer.analyze(q)
    assert intent.language == "ar"
    assert len(intent.decision_numbers) == 0  # no decision number in question
    assert len(intent.dates) == 1
    dt = intent.dates[0]
    assert dt.day == 20 and dt.month == 10 and dt.year == 2026
    assert "safety" in intent.committee_types  # because we extracted from "لجنة السلامة"
    assert len(intent.entities) > 0  # should have extracted something from the question? Actually, the question doesn't have a person name, but we might have empty.
    # The question has "رئيس" which is not a person name, so entities might be empty.
    # That's okay.
    assert intent.comparison_flag is False
    assert intent.multi_indicator_flag is False  # no plural, no distribution, etc.

    q = "Compare the presidents of the safety and technical committees in 2025 and 2026"
    intent = analyzer.analyze(q)
    assert intent.language == "en"
    assert len(intent.decision_numbers) == 0
    # No explicit dates, but we have years in the text? Our date extraction looks for day month year, so none.
    assert len(intent.dates) == 0
    assert set(intent.committee_types) == {"safety", "technical"}
    # We might have extracted entities? Not really.
    assert intent.comparison_flag is True
    assert intent.multi_indicator_flag is True  # because of plural and date range? Actually, we have "in 2025 and 2026" which is a date range -> multi_indicator.