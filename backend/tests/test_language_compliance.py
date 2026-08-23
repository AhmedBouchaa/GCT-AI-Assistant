"""Tests for language compliance in RAG responses.

Verifies that:
1. Language detection works correctly
2. Arabic questions get Arabic answers
3. French questions get French answers
4. No language mismatches in responses
"""
import pytest

from app.utils.language_detection import detect_language
from app.rag.service import RAGService


class TestLanguageDetection:
    """Test the language detection utility."""

    def test_detect_arabic(self):
        """Test Arabic language detection."""
        assert detect_language("من هو رئيس اللجنة") == "ar"
        assert detect_language("ما هو؟") == "ar"
        assert detect_language("السلام عليكم") == "ar"

    def test_detect_french(self):
        """Test French language detection."""
        assert detect_language("Qui est le président") == "fr"
        assert detect_language("Qu'est-ce que c'est?") == "fr"
        assert detect_language("Bonjour, comment allez-vous?") == "fr"

    def test_detect_english(self):
        """Test English language detection."""
        assert detect_language("Who is the president") == "en"
        assert detect_language("What is this?") == "en"
        assert detect_language("Hello, how are you?") == "en"

    def test_detect_unknown(self):
        """Test unknown/mixed language detection."""
        assert detect_language("123 @#$") == "unknown"
        assert detect_language("") == "unknown"
        assert detect_language("   ") == "unknown"

    def test_detect_mixed(self):
        """Test mixed language text."""
        # Mostly Arabic
        assert detect_language("من هو president") == "ar"
        # Mostly French
        assert detect_language("Qui est الرئيس") == "fr"


class TestRAGServiceLanguageCompliance:
    """Test RAGService language compliance."""

    @pytest.mark.slow
    @pytest.mark.heavy
    def test_arabic_question_gets_arabic_answer(self):
        """Test that Arabic questions get Arabic answers."""
        rag = RAGService()
        result = rag.answer(
            question="من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟",
            top_k=5,
        )

        # Verify question is in result
        assert result["question"]
        assert "من هو" in result["question"] or "اللجنة" in result["question"]

        # Verify answer is in Arabic
        detected_lang = detect_language(result["answer"])
        assert detected_lang == "ar", (
            f"Expected Arabic response, but detected {detected_lang}. "
            f"Answer: {result['answer'][:100]}"
        )

        # Verify sources exist
        assert len(result["sources"]) > 0

    @pytest.mark.slow
    @pytest.mark.heavy
    def test_french_question_gets_french_answer(self):
        """Test that French questions get French answers."""
        rag = RAGService()
        result = rag.answer(
            question="Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis ?",
            top_k=5,
        )

        # Verify question is in result
        assert result["question"]
        assert "Qui" in result["question"] or "président" in result["question"]

        # Verify answer is in French
        detected_lang = detect_language(result["answer"])
        assert detected_lang == "fr", (
            f"Expected French response, but detected {detected_lang}. "
            f"Answer: {result['answer'][:100]}"
        )

        # Verify sources exist
        assert len(result["sources"]) > 0

    @pytest.mark.slow
    @pytest.mark.heavy
    def test_english_question_gets_english_answer(self):
        """Test that English questions get English answers."""
        rag = RAGService()
        result = rag.answer(
            question="Who is the president of the technical committee for heavy equipment maintenance in Qabis?",
            top_k=5,
        )

        # Verify question is in result
        assert result["question"]

        # Verify answer is in English (or contains expected information)
        detected_lang = detect_language(result["answer"])
        assert detected_lang in ("en", "unknown"), (
            f"Expected English response, but detected {detected_lang}. "
            f"Answer: {result['answer'][:100]}"
        )

        # Verify sources exist
        assert len(result["sources"]) > 0

    @pytest.mark.slow
    @pytest.mark.heavy
    def test_arabic_answer_contains_no_french(self):
        """Test that Arabic answers don't accidentally mix in French."""
        rag = RAGService()
        result = rag.answer(
            question="من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟",
            top_k=5,
        )

        answer = result["answer"]
        detected_lang = detect_language(answer)

        # Primary language should be Arabic
        assert detected_lang == "ar", f"Answer not in Arabic: {answer[:100]}"

        # Check that answer doesn't start with French phrases
        # (language should be consistent throughout)
        first_words = answer.split()[:5]
        first_phrase = " ".join(first_words).lower()

        # Common French openers that shouldn't appear
        french_openers = [
            "la réunion",
            "selon le document",
            "le président",
            "la commission",
        ]

        for opener in french_openers:
            assert opener not in first_phrase, (
                f"Answer starts with French phrase '{opener}': {first_phrase}"
            )

    @pytest.mark.slow
    @pytest.mark.heavy
    def test_french_answer_contains_no_arabic_prefix(self):
        """Test that French answers don't accidentally mix in Arabic."""
        rag = RAGService()
        result = rag.answer(
            question="Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis ?",
            top_k=5,
        )

        answer = result["answer"]
        detected_lang = detect_language(answer)

        # Primary language should be French
        assert detected_lang == "fr", f"Answer not in French: {answer[:100]}"

        # Check that answer doesn't start with Arabic
        first_words = answer.split()[:5]
        first_phrase = " ".join(first_words)

        # Should not contain Arabic characters at the start
        has_arabic = any("؀" <= c <= "ۿ" for c in first_phrase)
        assert not has_arabic, (
            f"Answer starts with Arabic characters: {first_phrase}"
        )

    @pytest.mark.slow
    @pytest.mark.heavy
    def test_correct_documents_retrieved(self):
        """Test that the correct documents are retrieved for committee questions."""
        rag = RAGService()
        result = rag.answer(
            question="من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟",
            top_k=5,
        )

        # Verify sources exist
        assert len(result["sources"]) > 0

        # Top source should be document 50-2 (the correct one)
        top_source = result["sources"][0]
        assert "50-2" in top_source.get("file_name", ""), (
            f"Expected 50-2.pdf in sources, got: "
            f"{[s.get('file_name') for s in result['sources'][:3]]}"
        )

    @pytest.mark.slow
    @pytest.mark.heavy
    def test_answer_contains_correct_name(self):
        """Test that the answer contains the correct committee president name."""
        rag = RAGService()
        result = rag.answer(
            question="من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟",
            top_k=5,
        )

        answer = result["answer"]

        # Answer should mention the president's name (in some form)
        # Could be "محمد بن علي" or "Muhammad" or "Mohamed" etc.
        name_variants = [
            "محمد",  # Arabic
            "علي",
            "Muhammad",
            "Mohamed",
            "Ben Ali",
            "بن علي",
        ]

        found = any(variant in answer for variant in name_variants)
        assert found, (
            f"Answer should contain president's name. "
            f"Found: {answer[:200]}"
        )
