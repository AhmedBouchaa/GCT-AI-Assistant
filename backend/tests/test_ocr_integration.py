"""Test d'intégration OCR réel (Tesseract + PyMuPDF), marqué ``heavy``.

Crée un PDF « scanné » (image seule, sans couche texte) à partir d'un vrai
document, puis vérifie que l'ingestion OCR extrait le texte et indexe la page.

Ne dépend PAS de mistral ni d'e5-large (embedder fake) ; nécessite le binaire
Tesseract + les traineddata dans ``data/tessdata``. Ignoré si indisponible.

Usage:
    ./venv/Scripts/python.exe -m pytest --run-heavy tests/test_ocr_integration.py -q
"""
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.heavy

from app.ingest import ChromaStore, IngestionService
from app.ingest.ocr import OCREngine

BACKEND = Path(__file__).resolve().parent.parent
REAL_DOC = BACKEND / "data" / "documents" / "GCT_notes_exemples_50-1.pdf"


class _FakeEmbedder:
    def embed_texts(self, texts, prefix=""):
        rng = np.random.default_rng(0)
        vectors = rng.standard_normal((len(texts), 384))
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def make_scanned_pdf(path: Path) -> None:
    """Crée un PDF image-seule (simule un scan) à partir d'une vraie page."""
    import fitz

    src = fitz.open(str(REAL_DOC))
    pix = src[0].get_pixmap(dpi=150)
    src.close()

    img_pdf = fitz.open()
    page = img_pdf.new_page(width=pix.width, height=pix.height)
    page.insert_image(page.rect, stream=pix.tobytes("png"))
    img_pdf.save(str(path))
    img_pdf.close()


def test_real_ocr_extracts_scanned_page(tmp_path):
    engine = OCREngine()
    if not engine.is_available():
        pytest.skip("Tesseract ou traineddata indisponibles")

    docs = tmp_path / "docs"
    docs.mkdir()
    svc = IngestionService(
        documents_dir=docs,
        chroma_dir=tmp_path / "chroma",
        collection_name="ocr_coll",
        manifest_path=tmp_path / "manifest.json",
        embedder=_FakeEmbedder(),
        ocr_engine=engine,
    )

    scanned = docs / "scan.pdf"
    make_scanned_pdf(scanned)

    result = svc.ingest_document(scanned)

    assert result["status"] == "indexed"
    assert result["chunks"] >= 1

    store = ChromaStore(svc.chroma_dir, "ocr_coll")
    col = store._get_collection()
    res = col.get(include=["documents", "metadatas"])
    text = " ".join(res["documents"])
    # L'OCR a extrait du contenu exploitable (le document est une décision GCT).
    assert len(text.strip()) > 30
    assert res["metadatas"][0]["file_name"] == "scan.pdf"
    assert res["metadatas"][0]["page_number"] == 1
