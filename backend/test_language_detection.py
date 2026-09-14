import sys
sys.path.insert(0, '.')

from app.utils.language_detection import detect_language

tests = [
    ("من هو الرئيس؟", "ar"),
    ("Qui est le président ?", "fr"),
    ("Who is the president?", "en"),
    ("12345", "unknown"),
]

with open("language_test_results.txt", "w", encoding="utf-8") as f:
    for text, expected in tests:
        detected = detect_language(text)
        match = detected == expected
        f.write(f"Text: {repr(text)}\n")
        f.write(f"  Expected: {expected}, Detected: {detected}, Match: {match}\n")
        if expected != 'unknown':
            # We don't have the has_language_mismatch and enforce_language here, but we can skip for now
            pass
        f.write("\n")