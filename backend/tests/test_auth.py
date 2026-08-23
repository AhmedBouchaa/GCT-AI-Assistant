"""Tests de l'authentification locale (Bearer token).

La conftest désactive l'auth par défaut (AUTH_ENABLED=false) ; ici on l'active
via monkeypatch sur ``settings``. Services RAG/ingestion mockés — aucun modèle
réel n'est chargé.
"""
import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.core.config import settings
from main import app

ADMIN = "admin-tok"
USER = "user-tok"


class FakeRAG:
    def answer(self, question, top_k=5, temperature=0.2, max_tokens=512):
        return {
            "question": question,
            "answer": "Réponse",
            "sources": [
                {"file_name": "doc.pdf", "page_number": 1, "score": 0.9, "chunk_id": "x"}
            ],
        }


class FakeIngestion:
    def __init__(self, documents_dir):
        self.documents_dir = documents_dir

    def ingest_document(self, path, force=False):
        return {
            "status": "indexed",
            "file_name": Path(path).name,
            "pages": 1,
            "chunks": 1,
            "message": "ok",
            "ocr_pages": 0,
        }


from pathlib import Path  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_admin_token", ADMIN)
    monkeypatch.setattr(settings, "auth_user_tokens", USER)

    fake_ingestion = FakeIngestion(tmp_path)
    monkeypatch.setattr(routes, "_get_service", lambda: FakeRAG())
    monkeypatch.setattr(routes, "_get_ingestion_service", lambda: fake_ingestion)
    return TestClient(app)


def _auth(token=None):
    return {"Authorization": f"Bearer {token}"} if token else {}


def _files(filename="d.pdf"):
    return {"file": (filename, b"%PDF-1.4 test", "application/pdf")}


def test_health_is_public(client):
    assert client.get("/api/v1/health").status_code == 200


def test_verify_valid_user_returns_user_role(client):
    resp = client.get("/api/v1/auth/verify", headers=_auth(USER))
    assert resp.status_code == 200
    assert resp.json() == {"authenticated": True, "role": "user"}


def test_verify_valid_admin_returns_admin_role(client):
    resp = client.get("/api/v1/auth/verify", headers=_auth(ADMIN))
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_verify_invalid_token_returns_401(client):
    assert client.get("/api/v1/auth/verify", headers=_auth("nope")).status_code == 401
    assert client.get("/api/v1/auth/verify").status_code == 401


def test_ask_without_token_returns_401(client):
    assert client.post("/api/v1/ask", json={"question": "q"}).status_code == 401


def test_ask_invalid_token_returns_401(client):
    resp = client.post("/api/v1/ask", json={"question": "q"}, headers=_auth("nope"))
    assert resp.status_code == 401


def test_ask_user_token_succeeds(client):
    resp = client.post("/api/v1/ask", json={"question": "q"}, headers=_auth(USER))
    assert resp.status_code == 200
    assert resp.json()["answer"] == "Réponse"


def test_ask_admin_token_succeeds(client):
    resp = client.post("/api/v1/ask", json={"question": "q"}, headers=_auth(ADMIN))
    assert resp.status_code == 200


def test_documents_without_token_returns_401(client):
    assert client.post("/api/v1/documents", files=_files()).status_code == 401


def test_documents_user_token_returns_403(client):
    resp = client.post("/api/v1/documents", files=_files(), headers=_auth(USER))
    assert resp.status_code == 403


def test_documents_admin_token_succeeds(client):
    resp = client.post(
        "/api/v1/documents", files=_files("ok.pdf"), headers=_auth(ADMIN)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "indexed"


def test_auth_disabled_allows_requests(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    assert client.post("/api/v1/ask", json={"question": "q"}).status_code == 200
    assert client.get("/api/v1/auth/verify").status_code == 200
