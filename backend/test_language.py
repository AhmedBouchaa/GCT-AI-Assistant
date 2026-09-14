import sys
sys.path.insert(0, '.')

from app.utils.language_detection import detect_language
from app.utils.language_fixer import has_language_mismatch, enforce_language

# Test cases
tests = [
    ('من هو الرئيس؟', 'ar'),
    ('Qui est le président ?', 'fr'),
    ('Who is the president?', 'en'),
    ('12345', 'unknown'),
]

for text, expected in tests:
    detected = detect_language(text)
    match = detected == expected
    # Safely print the text by using repr to avoid encoding issues
    print(f"Text: {repr(text)}")
    print(f"  Expected: {expected}, Detected: {detected}, Match: {match}")
    if expected != 'unknown':
        mismatch = has_language_mismatch(text, expected)
        print(f"  Has mismatch for target {expected}: {mismatch}")
        if mismatch:
            fixed = enforce_language(text, expected)
            print(f"  Fixed: {repr(fixed)}")
    print()