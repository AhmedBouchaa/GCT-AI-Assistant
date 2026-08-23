"""Tests de l'endpoint POST /api/v1/documents (service d'ingestion mocké).

Valide le comportement HTTP : validation du fichier, sauvegarde, mapping des
statuts d'ingestion. Aucun modèle réel n'est chargé.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from main import app

VALID_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


class FakeIngestionService:
    def __init__(self, result=None):
        self.result = result or {
            "status": "indexed",
            "file_name": "doc.pdf",
            "pages": 2,
            "chunks": 3,
            "message": "Document indexé avec succès.",
            "ocr_pages": 0,
        }
        self.documents_dir = None  # défini par la fixture
        self.calls = []

    def ingest_document(self, path, force=False):
        self.calls.append({"path": Path(path), "force": force})
        return self.result


@pytest.fixture()
def client(monkeypatch, tmp_path):
    fake = FakeIngestionService()
    fake.documents_dir = tmp_path
    monkeypatch.setattr(routes, "_get_ingestion_service", lambda: fake)
    return TestClient(app), fake


def test_upload_valid_pdf(client):
    http, fake = client

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("doc.pdf", VALID_PDF, "application/pdf")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "indexed"
    assert data["file_name"] == "doc.pdf"
    assert data["pages"] == 2
    assert data["chunks"] == 3

    # le fichier a été sauvegardé dans documents_dir puis ingéré
    assert len(fake.calls) == 1
    saved = fake.calls[0]["path"]
    assert saved.name == "doc.pdf"
    assert saved.exists()
    assert saved.read_bytes() == VALID_PDF


def test_upload_empty_file_rejected(client):
    http, _ = client

    resp = http.post("/api/v1/documents", files={"file": ("empty.pdf", b"", "application/pdf")})

    assert resp.status_code == 400


def test_upload_non_pdf_rejected(client):
    http, _ = client

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("not.pdf", b"plain text content", "application/pdf")},
    )

    assert resp.status_code == 400


def test_upload_non_pdf_extension_rejected(client):
    http, _ = client

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("doc.txt", VALID_PDF, "text/plain")},
    )

    assert resp.status_code == 400


def test_upload_ocr_required_mapped(client):
    http, fake = client
    fake.result = {
        "status": "ocr_required",
        "file_name": "scan.pdf",
        "pages": 1,
        "chunks": 0,
        "message": "OCR requis mais non supporté : le document n'a pas de texte extractible.",
        "ocr_pages": 1,
    }

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("scan.pdf", VALID_PDF, "application/pdf")},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ocr_required"
    assert "OCR" in resp.json()["message"]


def test_upload_partial_ocr_mapped(client):
    http, fake = client
    fake.result = {
        "status": "indexed",
        "file_name": "mixte.pdf",
        "pages": 2,
        "chunks": 1,
        "message": "Document indexé avec succès. 1 page(s) en échec OCR (2) ignorée(s).",
        "ocr_pages": 1,
    }

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("mixte.pdf", VALID_PDF, "application/pdf")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "indexed"
    assert data["ocr_pages"] == 1
    assert "OCR" in data["message"]


def test_upload_duplicate_mapped(client):
    http, fake = client
    fake.result = {
        "status": "skipped",
        "file_name": "doc.pdf",
        "pages": 0,
        "chunks": 3,
        "message": "Document déjà indexé (inchangé).",
        "ocr_pages": 0,
    }

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("doc.pdf", VALID_PDF, "application/pdf")},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"


def test_upload_ingestion_failure_mapped(client):
    http, fake = client
    fake.result = {
        "status": "failed",
        "file_name": "bad.pdf",
        "pages": 0,
        "chunks": 0,
        "message": "Extraction impossible.",
        "ocr_pages": 0,
    }

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("bad.pdf", VALID_PDF, "application/pdf")},
    )

    assert resp.status_code == 422
    assert "Extraction impossible" in resp.json()["detail"]


@pytest.mark.parametrize("filename", ["../evil.pdf", "..\\evil.pdf"])
def test_upload_path_traversal_is_sanitized(client, filename):
    http, fake = client

    resp = http.post(
        "/api/v1/documents",
        files={"file": (filename, VALID_PDF, "application/pdf")},
    )

    # le fichier est sauvé dans documents_dir avec le basename uniquement
    assert resp.status_code == 200
    saved = fake.calls[0]["path"]
    assert saved.name == "evil.pdf"
    assert saved.parent == fake.documents_dir
    assert ".." not in str(saved)


def test_upload_same_filename_reuses_same_path(client):
    http, fake = client

    http.post("/api/v1/documents", files={"file": ("doc.pdf", VALID_PDF, "application/pdf")})
    http.post("/api/v1/documents", files={"file": ("doc.pdf", VALID_PDF, "application/pdf")})

    # même nom -> même chemin : la déduplication (skipped/updated) est gérée
    # par IngestionService (couverte par les tests du service)
    assert len(fake.calls) == 2
    assert fake.calls[0]["path"] == fake.calls[1]["path"]


def test_upload_service_exception_returns_clean_500(client):
    http, fake = client
    fake.ingest_document = lambda path, force=False: (_ for _ in ()).throw(
        RuntimeError("panne ChromaDB")
    )

    resp = http.post(
        "/api/v1/documents",
        files={"file": ("doc.pdf", VALID_PDF, "application/pdf")},
    )

    assert resp.status_code == 500
    assert "ingestion" in resp.json()["detail"]
