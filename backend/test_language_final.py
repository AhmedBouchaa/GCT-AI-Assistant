import sys
sys.path.insert(0, '.')

from app.utils.language_detection import detect_language, is_arabic, is_french, is_english
from app.utils.language_fixer import has_language_mismatch, enforce_language

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ASCII representation
        print(repr(text))

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

with open("language_detection_results.txt", "w", encoding="utf-8") as f:
    f.write("Language Detection Tests:\n")
    f.write("=" * 50 + "\n")

    all_passed = True
    for text, expected in test_cases:
        detected = detect_language(text)
        passed = detected == expected
        if not passed:
            all_passed = False
        status = "PASS" if passed else "FAIL"
        f.write(f"{status}: '{text}' -> Expected: {expected}, Got: {detected}\n")

    f.write("\n" + "=" * 50 + "\n")
    if all_passed:
        f.write("All language detection tests PASSED\n")
    else:
        f.write("Some language detection tests FAILED\n")

# Test language fixer
fixer_tests = [
    # French text that should be detected as wrong for Arabic target
    ("Le président est Mohamed Ben Ali", "ar", True),  # Should detect mismatch
    ("الرئيس هو محمد بن علي", "fr", True),  # Should detect mismatch
    ("Mohamed Ben Ali is the president", "ar", False),  # Neutral content, no strong mismatch
    ("The president is Mohamed Ben Ali", "fr", False),  # Already French
    ("الرئيس هو محمد بن علي", "ar", False),  # Already Arabic
]

with open("language_fixer_results.txt", "w", encoding="utf-8") as f:
    f.write("\nLanguage Fixer Tests:\n")
    f.write("=" * 50 + "\n")

    for text, target_lang, should_have_mismatch in fixer_tests:
        has_mismatch = has_language_mismatch(text, target_lang)
        passed = has_mismatch == should_have_mismatch
        status = "PASS" if passed else "FAIL"
        f.write(f"{status}: '{text}' (target: {target_lang}) -> Expected mismatch: {should_have_mismatch}, Got: {has_mismatch}\n")

        if has_mismatch:
            fixed = enforce_language(text, target_lang)
            f.write(f"  Fixed: '{fixed}'\n")

    f.write("\n" + "=" * 50 + "\n")
    f.write("Language fixer tests completed\n")

print("Tests completed. See language_detection_results.txt and language_fixer_results.txt")