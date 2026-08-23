"""Tests du service de génération avec retrieval mocké et Ollama mocké.

Aucun modèle n'est chargé : le retriever et le client Ollama sont injectés
(fakes). Le premier test fonctionnel utilise la question arabe imposée et vérifie
que la source ``GCT_notes_exemples_50-2.pdf`` est sélectionnée et que la réponse
identifie ``محمد بن علي``.
"""
from app.generation import (
    GenerationRetrievalError,
    GenerationService,
    build_context,
)
from app.generation.rag_service import not_found_message

QUESTION_AR = (
    "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟"
)

# Résultat de retrieval simulant la note GCT_notes_exemples_50-2.pdf.
_COMMITTEE_TEXT = (
    "تتركب اللجنة الفنية لصيانة المعدات الثقيلة بداية من :\n"
    "رئيس محمد بن علي\n"
    "رئيس مصلحة النقل والمعدات : عضو فيصل الجلاسي\n"
    "رئيس قسم الأمن الصناعي : عضو مريم بن عمر\n"
    "رئيس قسم المراقبة الجودة : عضو ياسين الحداد\n"
    "رئيس مصلحة المحاسبة : عضو أنيس بن علي\n"
    "مدير الإنتاج"
)


def _fake_retriever(results):
    def _retrieve(question, top_k=5):
        return results

    return _retrieve


class _FakeOllama:
    def __init__(self, answer="رئيس اللجنة الفنية لصيانة المعدات الثقيلة هو محمد بن علي."):
        self.answer = answer
        self.last_prompt = None
        self.last_system = None

    def generate(self, prompt, system_prompt=None, temperature=0.2, num_predict=None):
        self.last_prompt = prompt
        self.last_system = system_prompt
        return self.answer


def _committee_result(score=0.9052):
    return [
        {
            "text": _COMMITTEE_TEXT,
            "score": score,
            "distance": 1 - score,
            "doc_id": "GCT_notes_exemples_50-2",
            "file_name": "GCT_notes_exemples_50-2.pdf",
            "file_path": "data/documents/GCT_notes_exemples_50-2.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "chunk_id": "GCT_notes_exemples_50-2_p1_c0",
        }
    ]


def test_answer_identifies_chairman_mocked():
    """Test fonctionnel imposé : la réponse doit identifier محمد بن علي."""
    svc = GenerationService(
        retriever=_fake_retriever(_committee_result()),
        ollama_client=_FakeOllama(),
    )
    result = svc.answer(QUESTION_AR)
    assert "محمد بن علي" in result["answer"]
    assert len(result["sources"]) == 1
    assert result["sources"][0]["file_name"] == "GCT_notes_exemples_50-2.pdf"
    assert result["sources"][0]["page_number"] == 1
    assert result["sources"][0]["score"] == 0.9052


def test_answer_builds_context_with_ollama_mock():
    """Retrieval mocké + Ollama mocké : le contexte et le prompt système sont corrects."""
    fake_ollama = _FakeOllama()
    svc = GenerationService(
        retriever=_fake_retriever(_committee_result()),
        ollama_client=fake_ollama,
    )
    svc.answer(QUESTION_AR)

    # Le prompt système imposé est bien transmis.
    assert fake_ollama.last_system is not None
    # Le contexte contient le format normalisé et le bon document.
    assert "[Document: GCT_notes_exemples_50-2.pdf]" in fake_ollama.last_prompt
    assert "[Page: 1]" in fake_ollama.last_prompt
    assert "[Similarité: 0.9052]" in fake_ollama.last_prompt
    assert _COMMITTEE_TEXT in fake_ollama.last_prompt
    # La question est présente dans le prompt utilisateur.
    assert QUESTION_AR in fake_ollama.last_prompt


def test_answer_empty_context_returns_not_found():
    """Contexte vide -> message « non trouvé », Ollama NON appelé."""
    fake_ollama = _FakeOllama()
    svc = GenerationService(
        retriever=_fake_retriever([]),
        ollama_client=fake_ollama,
    )
    result = svc.answer(QUESTION_AR)
    # Message « non trouvé » en arabe (question arabe).
    assert result["answer"] == not_found_message(QUESTION_AR)
    assert result["sources"] == []
    # Ollama ne doit pas avoir été sollicité.
    assert fake_ollama.last_prompt is None


def test_answer_min_score_threshold_returns_not_found():
    """Si le meilleur score est sous le seuil, réponse « non trouvé »."""
    svc = GenerationService(
        retriever=_fake_retriever(_committee_result(score=0.1)),
        ollama_client=_FakeOllama(),
        min_score=0.5,
    )
    result = svc.answer(QUESTION_AR)
    assert result["sources"] == []
    assert result["answer"] == not_found_message(QUESTION_AR)


def test_answer_propagates_retrieval_error():
    """Une erreur de retrieval est mappée en GenerationRetrievalError."""
    def _boom(question, top_k=5):
        raise RuntimeError("ChromaDB down")

    svc = GenerationService(retriever=_boom, ollama_client=_FakeOllama())
    try:
        svc.answer(QUESTION_AR)
        assert False, "GenerationRetrievalError attendue"
    except GenerationRetrievalError:
        pass


def test_empty_question_raises_value_error():
    svc = GenerationService(
        retriever=_fake_retriever([]),
        ollama_client=_FakeOllama(),
    )
    try:
        svc.answer("   ")
        assert False, "ValueError attendue"
    except ValueError:
        pass


def test_build_context_format():
    """Vérifie le format [Document]/[Page]/[Similarité]/[Texte] du contexte."""
    ctx = build_context(_committee_result())
    assert "[Document: GCT_notes_exemples_50-2.pdf]" in ctx
    assert "[Page: 1]" in ctx
    assert "[Similarité: 0.9052]" in ctx
    assert _COMMITTEE_TEXT in ctx
