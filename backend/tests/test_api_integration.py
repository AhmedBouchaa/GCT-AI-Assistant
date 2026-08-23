"""Test d'intégration HTTP : POST /api/v1/ask avec le VRAI pipeline RAG.

Marqué ``heavy`` (voir conftest.py) : charge E5 (PyTorch) et mistral (Ollama)
simultanément -> long sur cette machine 8 Go. Ne pas lancer en parallèle
d'autres tests heavy.

Usage:
    ./venv/Scripts/python.exe -m pytest --run-heavy tests/test_api_integration.py -q
"""
import pytest

pytest.importorskip("chromadb")
pytest.importorskip("ollama")

pytestmark = pytest.mark.heavy

from fastapi.testclient import TestClient

from main import app


def test_ask_over_http_real_pipeline():
    client = TestClient(app)

    resp = client.post(
        "/api/v1/ask",
        json={
            "question": (
                "Quel est l'objet de la décision concernant la maintenance "
                "des équipements lourds ?"
            ),
            "top_k": 5,
            "temperature": 0.2,
            "max_tokens": 256,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["question"]
    assert isinstance(data["answer"], str)
    assert data["answer"].strip()
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["file_name"].endswith(".pdf")
