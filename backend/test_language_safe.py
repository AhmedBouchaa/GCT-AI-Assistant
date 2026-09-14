import sys
import codecs
sys.path.insert(0, '.')

from app.utils.language_detection import detect_language
from app.utils.language_fixer import has_language_mismatch, enforce_language

# Test cases - using only ASCII in the test descriptions
tests = [
    ('من هو الرئيس؟', 'ar'),
    ('Qui est le président ?', 'fr'),
    ('Who is the president?', 'en'),
    ('12345', 'unknown'),
]

# Use a safe way to print results
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ASCII representation
        print(repr(text))

for text, expected in tests:
    detected = detect_language(text)
    match = detected == expected
    safe_print(f"Text: {repr(text)}")
    safe_print(f"  Expected: {expected}, Detected: {detected}, Match: {match}")
    if expected != 'unknown':
        mismatch = has_language_mismatch(text, expected)
        safe_print(f"  Has mismatch for target {expected}: {mismatch}")
        if mismatch:
            fixed = enforce_language(text, expected)
            safe_print(f"  Fixed: {repr(fixed)}")
    safe_print("")