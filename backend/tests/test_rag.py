"""Tests unitaires du service RAG (retriever et Ollama mockés).

Aucun modèle réel n'est chargé ici : le service est testé isolément. Le test
d'intégration réel (ChromaDB + E5 + Ollama) est dans test_rag_integration.py.
"""
import pytest

from app.llm import OllamaError, OllamaUnavailableError
from app.rag import (
    NOT_FOUND_MESSAGE,
    RAGGenerationError,
    RAGRetrievalError,
    RAGService,
    RAGUnavailableError,
    SYSTEM_PROMPT,
)

ARABIC_QUESTION = "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة؟"

RESULT_1 = {
    "text": "La commission technique est présidée par M. Ahmed Ben Salah.",
    "score": 0.9,
    "distance": 0.1,
    "doc_id": "doc1",
    "file_name": "GCT_notes_exemples_50-1.pdf",
    "file_path": "data/documents/GCT_notes_exemples_50-1.pdf",
    "page_number": 1,
    "chunk_index": 0,
    "chunk_id": "doc1_p1_c0",
}

RESULT_2 = {
    "text": "La commission assure le suivi de la maintenance préventive.",
    "score": 0.7,
    "distance": 0.3,
    "doc_id": "doc2",
    "file_name": "GCT_notes_exemples_50-2.pdf",
    "file_path": "data/documents/GCT_notes_exemples_50-2.pdf",
    "page_number": 2,
    "chunk_index": 0,
    "chunk_id": "doc2_p2_c0",
}


class FakeRetriever:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error
        self.calls = []

    def __call__(self, question, top_k=5):
        self.calls.append({"question": question, "top_k": top_k})
        if self.error is not None:
            raise self.error
        return self.results


class FakeOllama:
    def __init__(self, text="réponse générée", error=None):
        self.text = text
        self.error = error
        self.calls = []
        self.base_url = "http://localhost:11434"

    def generate(self, prompt, system_prompt=None, temperature=0.7, num_predict=None):
        if self.error is not None:
            raise self.error
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "num_predict": num_predict,
            }
        )
        return self.text


def _make_service(results=None, retriever_error=None, ollama_error=None, min_score=None):
    retriever = FakeRetriever(results, error=retriever_error)
    ollama = FakeOllama(error=ollama_error)
    service = RAGService(retriever=retriever, ollama_client=ollama, min_score=min_score)
    return service, retriever, ollama


def test_empty_question_rejected():
    service, _, _ = _make_service(results=[RESULT_1])

    with pytest.raises(ValueError):
        service.answer("")
    with pytest.raises(ValueError):
        service.answer("   ")


def test_retriever_called_with_requested_top_k():
    service, retriever, _ = _make_service(results=[RESULT_1])

    service.answer("Question ?", top_k=3)

    assert retriever.calls[-1]["top_k"] == 3
    assert retriever.calls[-1]["question"] == "Question ?"


def test_retrieved_chunks_inserted_into_prompt():
    service, _, ollama = _make_service(results=[RESULT_1, RESULT_2])

    service.answer("Question ?", top_k=2)

    prompt = ollama.calls[-1]["prompt"]
    assert "La commission technique est présidée par M. Ahmed Ben Salah." in prompt
    assert "La commission assure le suivi de la maintenance préventive." in prompt
    assert "QUESTION :" in prompt


def test_ollama_receives_generated_prompt():
    service, _, ollama = _make_service(results=[RESULT_1])

    service.answer("Question ?", top_k=1)

    assert len(ollama.calls) == 1
    assert "CONTEXTE :" in ollama.calls[0]["prompt"]


def test_answer_returned():
    service, _, _ = _make_service(results=[RESULT_1])

    result = service.answer("Question ?")

    assert result["answer"] == "réponse générée"
    assert result["question"] == "Question ?"


def test_sources_returned():
    service, _, _ = _make_service(results=[RESULT_1, RESULT_2])

    result = service.answer("Question ?", top_k=2)

    assert len(result["sources"]) == 2
    src = result["sources"][0]
    assert src["file_name"] == "GCT_notes_exemples_50-1.pdf"
    assert src["page_number"] == 1
    assert src["score"] == 0.9
    assert src["chunk_id"] == "doc1_p1_c0"
    # Pas de metadata interne inutile exposée.
    assert "text" not in src and "file_path" not in src


def test_duplicate_sources_are_deduplicated():
    duplicate = dict(RESULT_1)
    duplicate["chunk_id"] = "doc1_p1_c0"  # même chunk_id que RESULT_1
    service, _, _ = _make_service(results=[RESULT_1, duplicate])

    result = service.answer("Question ?", top_k=2)

    assert len(result["sources"]) == 1


def test_no_results_returns_not_found_without_calling_ollama():
    service, _, ollama = _make_service(results=[])

    result = service.answer("Question ?")

    assert result["answer"] == NOT_FOUND_MESSAGE
    assert result["sources"] == []
    assert ollama.calls == []


def test_ollama_unavailable_is_converted():
    service, _, _ = _make_service(
        results=[RESULT_1],
        ollama_error=OllamaUnavailableError("down"),
    )

    with pytest.raises(RAGUnavailableError) as exc_info:
        service.answer("Question ?")

    assert "Ollama" in str(exc_info.value)


def test_ollama_error_is_handled():
    service, _, _ = _make_service(
        results=[RESULT_1],
        ollama_error=OllamaError("http 500"),
    )

    with pytest.raises(RAGGenerationError) as exc_info:
        service.answer("Question ?")

    assert "génération" in str(exc_info.value).lower()


def test_retrieval_error_is_converted():
    service, _, _ = _make_service(
        retriever_error=RuntimeError("boom"),
    )

    with pytest.raises(RAGRetrievalError):
        service.answer("Question ?")


def test_system_prompt_contains_grounding_rules():
    service, _, ollama = _make_service(results=[RESULT_1])

    service.answer("Question ?")

    system_prompt = ollama.calls[-1]["system_prompt"]
    assert "uniquement à partir du contexte" in system_prompt
    assert "N'inventez jamais" in system_prompt
    assert "ne trouve pas cette information" in system_prompt


def test_system_prompt_constant_has_grounding_rules():
    assert "CONTEXTE" not in SYSTEM_PROMPT or "contexte" in SYSTEM_PROMPT
    assert "uniquement" in SYSTEM_PROMPT.lower()
    assert "inventez" in SYSTEM_PROMPT.lower()
    assert "ne trouve pas" in SYSTEM_PROMPT.lower()


def test_arabic_question_works_at_service_level():
    service, retriever, ollama = _make_service(results=[RESULT_1, RESULT_2])

    result = service.answer(ARABIC_QUESTION, top_k=2)

    assert result["question"] == ARABIC_QUESTION
    assert result["answer"] == "réponse générée"
    assert retriever.calls[-1]["question"] == ARABIC_QUESTION
    assert len(result["sources"]) == 2


def test_max_tokens_bounds_generation():
    service, _, ollama = _make_service(results=[RESULT_1])

    service.answer("Question ?", max_tokens=256)

    assert ollama.calls[-1]["num_predict"] == 256


def test_min_score_threshold_configurable():
    # Résultat en dessous du seuil -> pas de génération.
    service, _, ollama = _make_service(results=[RESULT_1], min_score=0.95)

    result = service.answer("Question ?")

    assert result["answer"] == NOT_FOUND_MESSAGE
    assert ollama.calls == []

    # Résultat au-dessus du seuil -> génération.
    service2, _, ollama2 = _make_service(results=[RESULT_1], min_score=0.8)
    result2 = service2.answer("Question ?")
    assert result2["answer"] == "réponse générée"
    assert len(ollama2.calls) == 1
