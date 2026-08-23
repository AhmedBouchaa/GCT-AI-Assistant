"""Test d'intégration RAG complet : vraie ChromaDB + vrai E5 + vrai Ollama.

Marqué ``heavy`` (voir conftest.py) : chargé uniquement avec
``--run-heavy``. Attention à la RAM (8 Go) : E5 (PyTorch) et mistral (Ollama)
cohabitent pendant ce test ; ne pas le lancer en parallèle d'autres tests heavy.

Usage:
    ./venv/Scripts/python.exe -m pytest --run-heavy tests/test_rag_integration.py -q
"""
import pytest

pytest.importorskip("chromadb")
pytest.importorskip("ollama")

pytestmark = pytest.mark.heavy

from app.rag import RAGService


def test_real_rag_end_to_end():
    service = RAGService()  # retriever lazy partagé (E5) + OllamaClient (modèle configuré)

    result = service.answer(
        "Quel est l'objet de la décision concernant la maintenance des équipements lourds ?",
        top_k=5,
        temperature=0.2,
    )

    # La question a bien été traitée et la génération a produit une réponse
    # non vide (une réponse « non trouvée » est un résultat de grounding valide :
    # le modèle refuse d'inventer une information absente du contexte).
    assert result["question"]
    assert isinstance(result["answer"], str)
    assert result["answer"].strip()

    # La récupération a retourné de vrais chunks de la collection -> sources.
    assert len(result["sources"]) >= 1
    assert result["sources"][0]["file_name"].endswith(".pdf")
    assert result["sources"][0]["page_number"] is not None
