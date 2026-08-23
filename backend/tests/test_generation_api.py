"""Test léger de l'endpoint POST /api/chat (auth désactivée par conftest).

Le service de génération est mocké (aucun modèle/serveur requis) ; on vérifie
uniquement le câblage de l'endpoint et la forme de la réponse.
"""
from fastapi.testclient import TestClient

from app.api import routes as routes_module
from main import app


class _FakeGenerationService:
    def answer(self, question, top_k=5, temperature=0.2, max_tokens=512):
        return {
            "answer": "رئيس اللجنة الفنية لصيانة المعدات الثقيلة هو محمد بن علي.",
            "sources": [
                {
                    "file_name": "GCT_notes_exemples_50-2.pdf",
                    "page_number": 1,
                    "score": 0.9052,
                }
            ],
        }


def test_chat_endpoint(monkeypatch):
    monkeypatch.setattr(
        routes_module, "_get_generation_service", lambda: _FakeGenerationService()
    )
    client = TestClient(app)
    resp = client.post(
        "/api/chat",
        json={
            "question": "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟",
            "top_k": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert "sources" in body
    assert body["sources"][0]["file_name"] == "GCT_notes_exemples_50-2.pdf"
    assert body["sources"][0]["page_number"] == 1
    assert body["sources"][0]["score"] == 0.9052


def test_chat_endpoint_rejects_empty_question(monkeypatch):
    monkeypatch.setattr(
        routes_module, "_get_generation_service", lambda: _FakeGenerationService()
    )
    client = TestClient(app)
    resp = client.post("/api/chat", json={"question": "   "})
    assert resp.status_code == 400
