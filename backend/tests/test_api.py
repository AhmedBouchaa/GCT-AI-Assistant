"""Tests de l'API REST (services mockés, aucun modèle chargé).

Le service RAG est remplacé par un faux ; le test d'intégration réel (POST /ask
avec le vrai pipeline) est dans test_api_integration.py (marqué heavy).
"""
import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.llm import OllamaUnavailableError
from app.rag import RAGGenerationError, RAGRetrievalError, RAGUnavailableError
from main import app

VALID_RESULT = {
    "question": "Quel est l'objet ?",
    "answer": "Réponse générée.",
    "sources": [
        {
            "file_name": "GCT_notes_exemples_50-1.pdf",
            "page_number": 1,
            "score": 0.9,
            "chunk_id": "doc_p1_c0",
        }
    ],
}


class FakeRAGService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def answer(self, question, top_k=5, temperature=0.2, max_tokens=512):
        self.calls.append(
            {
                "question": question,
                "top_k": top_k,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture()
def client(monkeypatch):
    """TestClient avec un faux RAGService injecté dans les routes."""

    def _make(result=VALID_RESULT, error=None):
        fake = FakeRAGService(result=result, error=error)
        monkeypatch.setattr(routes, "_get_service", lambda: fake)
        return TestClient(app), fake

    return _make


def test_health(client):
    http, _ = client()

    resp = http.get("/api/v1/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "model": None}


def test_health_ollama_ok(client, monkeypatch):
    class FakeOllama:
        model = "mistral:latest"

        def list_models(self):
            return ["mistral:latest"]

    monkeypatch.setattr(routes, "OllamaClient", lambda: FakeOllama())
    http, _ = client()

    resp = http.get("/api/v1/health/ollama")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["model"] == "mistral:latest"


def test_health_ollama_unavailable(client, monkeypatch):
    class FakeOllama:
        model = "mistral:latest"

        def list_models(self):
            raise OllamaUnavailableError("down")

    monkeypatch.setattr(routes, "OllamaClient", lambda: FakeOllama())
    http, _ = client()

    resp = http.get("/api/v1/health/ollama")

    assert resp.status_code == 503


def test_ask_valid_question(client):
    http, fake = client()

    resp = http.post("/api/v1/ask", json={"question": "Quel est l'objet ?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Réponse générée."
    assert data["question"] == "Quel est l'objet ?"


def test_ask_rag_service_called_with_parameters(client):
    http, fake = client()

    http.post(
        "/api/v1/ask",
        json={"question": "Question ?", "top_k": 3, "temperature": 0.1, "max_tokens": 100},
    )

    call = fake.calls[-1]
    assert call["question"] == "Question ?"
    assert call["top_k"] == 3
    assert call["temperature"] == 0.1
    assert call["max_tokens"] == 100


def test_ask_sources_returned(client):
    http, _ = client()

    resp = http.post("/api/v1/ask", json={"question": "Quel est l'objet ?"})

    sources = resp.json()["sources"]
    assert len(sources) == 1
    assert sources[0]["file_name"] == "GCT_notes_exemples_50-1.pdf"
    assert sources[0]["page_number"] == 1
    assert sources[0]["score"] == 0.9
    assert sources[0]["chunk_id"] == "doc_p1_c0"


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_ask_empty_question_returns_400(client, question):
    http, _ = client()

    resp = http.post("/api/v1/ask", json={"question": question})

    assert resp.status_code == 400


def test_ask_unavailable_returns_503(client):
    http, _ = client(error=RAGUnavailableError("Ollama injoignable"))

    resp = http.post("/api/v1/ask", json={"question": "Question ?"})

    assert resp.status_code == 503


def test_ask_generation_error_returns_502(client):
    http, _ = client(error=RAGGenerationError("Erreur de génération"))

    resp = http.post("/api/v1/ask", json={"question": "Question ?"})

    assert resp.status_code == 502


def test_ask_retrieval_error_returns_500(client):
    http, _ = client(error=RAGRetrievalError("Erreur retrieval"))

    resp = http.post("/api/v1/ask", json={"question": "Question ?"})

    assert resp.status_code == 500


@pytest.mark.parametrize("top_k", [0, -1, 21])
def test_ask_invalid_top_k_rejected(client, top_k):
    http, _ = client()

    resp = http.post("/api/v1/ask", json={"question": "Question ?", "top_k": top_k})

    assert resp.status_code == 400


@pytest.mark.parametrize("temperature", [-0.1, 2.5])
def test_ask_invalid_temperature_rejected(client, temperature):
    http, _ = client()

    resp = http.post(
        "/api/v1/ask",
        json={"question": "Question ?", "temperature": temperature},
    )

    assert resp.status_code == 400


@pytest.mark.parametrize("max_tokens", [0, 100000])
def test_ask_invalid_max_tokens_rejected(client, max_tokens):
    http, _ = client()

    resp = http.post(
        "/api/v1/ask",
        json={"question": "Question ?", "max_tokens": max_tokens},
    )

    assert resp.status_code == 400
