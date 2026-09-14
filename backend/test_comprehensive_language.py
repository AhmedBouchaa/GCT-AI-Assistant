import sys
sys.path.insert(0, '.')

from app.utils.language_detection import detect_language, is_arabic, is_french, is_english
from app.utils.language_fixer import has_language_mismatch, enforce_language

# Test cases for language detection
test_cases = [
    # Arabic
    ("من هو الرئيس؟", "ar"),
    ("الرئيس هو محمد بن علي", "ar"),
    ("ما هو تاريخ القرار رقم 006/2026؟", "ar"),
    ("اللجنة الفنية لصيانة المعدات", "ar"),

    # French
    ("Qui est le président ?", "fr"),
    ("Le président est Mohamed Ben Ali", "fr"),
    ("Quelle est la date de la décision numéro 006/2026 ?", "fr"),
    ("La commission technique pour la maintenance des équipements", "fr"),

    # English
    ("Who is the president?", "en"),
    ("The president is Mohamed Ben Ali", "en"),
    ("What is the date of decision number 006/2026?", "en"),
    ("The technical committee for equipment maintenance", "en"),

    # Unknown / mixed
    ("12345", "unknown"),
    ("!@#$%", "unknown"),
    ("", "unknown"),
]

print("Language Detection Tests:")
print("=" * 50)

all_passed = True
for text, expected in test_cases:
    detected = detect_language(text)
    passed = detected == expected
    if not passed:
        all_passed = False
    status = "PASS" if passed else "FAIL"
    print(f"{status}: '{text}' -> Expected: {expected}, Got: {detected}")

print("\n" + "=" * 50)
if all_passed:
    print("All language detection tests PASSED")
else:
    print("Some language detection tests FAILED")

# Test language fixer
print("\nLanguage Fixer Tests:")
print("=" * 50)

fixer_tests = [
    # French text that should be detected as wrong for Arabic target
    ("Le président est Mohamed Ben Ali", "ar", True),  # Should detect mismatch
    ("الرئيس هو محمد بن علي", "fr", True),  # Should detect mismatch
    ("Mohamed Ben Ali is the president", "ar", False),  # Neutral content, no strong mismatch
    ("The president is Mohamed Ben Ali", "fr", False),  # Already French
    ("الرئيس هو محمد بن علي", "ar", False),  # Already Arabic
]

for text, target_lang, should_have_mismatch in fixer_tests:
    has_mismatch = has_language_mismatch(text, target_lang)
    passed = has_mismatch == should_have_mismatch
    status = "PASS" if passed else "FAIL"
    print(f"{status}: '{text}' (target: {target_lang}) -> Expected mismatch: {should_have_mismatch}, Got: {has_mismatch}")

    if has_mismatch:
        fixed = enforce_language(text, target_lang)
        print(f"  Fixed: '{fixed}'")

print("\n" + "=" * 50)
print("Language fixer tests completed")