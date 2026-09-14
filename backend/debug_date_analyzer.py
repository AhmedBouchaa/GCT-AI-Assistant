# -*- coding: utf-8 -*-
from datetime import datetime
from app.relevance.query_analyzer import QueryAnalyzer

def debug_date_extraction():
    analyzer = QueryAnalyzer()
    question = "Événement du 20 octobre 2026"
    print(f"Question: {question}")
    intent = analyzer.analyze(question)
    print(f"Intent dates: {intent.dates}")
    print(f"Intent: {intent}")

    # Let's also test the date extraction directly
    dates = analyzer._extract_dates(question)
    print(f"_extract_dates result: {dates}")

    # Test a known good format
    question2 = "Le événement du 20 octobre 2026"
    dates2 = analyzer._extract_dates(question2)
    print(f"_extract_dates for '{question2}': {dates2}")

if __name__ == "__main__":
    debug_date_extraction()