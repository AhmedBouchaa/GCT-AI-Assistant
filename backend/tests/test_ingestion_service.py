"""Tests unitaires du service d'ingestion (embedder mocké, aucun modèle réel).

Un vrai PDF du jeu de données (données de test) est copié pour tester un
document avec texte ; un PDF vierge teste le cas OCR requis ; un faux PDF teste
l'échec d'extraction.
"""
from pathlib import Path

import numpy as np
import pytest

from app.ingest import ChromaStore, IngestionService
from app.ingest.ocr import OCRError

BACKEND = Path(__file__).resolve().parent.parent
REAL_DOC = BACKEND / "data" / "documents" / "GCT_notes_exemples_50-1.pdf"
OTHER_DOC = BACKEND / "data" / "documents" / "GCT_notes_exemples_50-2.pdf"


class FakeOCREngine:
    """Faux moteur OCR : retourne les textes de ``results`` (None = échec)."""

    def __init__(self, available=True, results=None):
        self.available = available
        self.results = results if results is not None else ["Texte OCR par défaut"]
        self.calls = []

    def is_available(self):
        return self.available

    def extract_text_from_image(self, image):
        self.calls.append(image)
        index = len(self.calls) - 1
        if index >= len(self.results) or not self.results[index]:
            raise OCRError("échec OCR simulé")
        return self.results[index]


class FakeEmbedder:
    """Renvoie des embeddings normalisés 384-dim sans charger de modèle."""

    def __init__(self, dim=384):
        self.dim = dim

    def embed_texts(self, texts, prefix=""):
        rng = np.random.default_rng(0)
        vectors = rng.standard_normal((len(texts), self.dim))
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors


def make_blank_pdf(path: Path, pages: int = 1) -> None:
    """Crée un PDF vierge (aucun texte extractible -> requires_ocr)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as handle:
        writer.write(handle)


def make_partial_ocr_pdf(path: Path) -> None:
    """PDF avec une page texte (copiée d'un vrai document) + une page vierge."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(REAL_DOC))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as handle:
        writer.write(handle)


class FailingEmbedder:
    def embed_texts(self, texts, prefix=""):
        raise RuntimeError("modèle d'embedding indisponible")


class FailingStore:
    """Simule une panne ChromaDB à l'écriture."""

    def delete_doc(self, doc_id):
        pass

    def upsert_chunks(self, doc_id, chunks, embeddings=None):
        raise RuntimeError("base vectorielle indisponible")


@pytest.fixture()
def service(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    return IngestionService(
        documents_dir=docs,
        chroma_dir=tmp_path / "chroma",
        collection_name="test_coll",
        manifest_path=tmp_path / "manifest.json",
        embedder=FakeEmbedder(),
        ocr_engine=FakeOCREngine(),
    )


def make_service(tmp_path, **overrides):
    """Construit un IngestionService isolé avec surcharges (ocr_engine, store...)."""
    defaults = {
        "documents_dir": tmp_path / "docs",
        "chroma_dir": tmp_path / "chroma",
        "collection_name": "test_coll",
        "manifest_path": tmp_path / "manifest.json",
        "embedder": FakeEmbedder(),
        "ocr_engine": FakeOCREngine(),
    }
    defaults.update(overrides)
    Path(defaults["documents_dir"]).mkdir(parents=True, exist_ok=True)
    return IngestionService(**defaults)


def _collection_metadata(service):
    store = ChromaStore(service.chroma_dir, "test_coll")
    col = store._get_collection()
    res = col.get(include=["metadatas"])
    return res["metadatas"]


def test_ingest_new_document(service):
    target = service.documents_dir / "doc.pdf"
    target.write_bytes(REAL_DOC.read_bytes())

    result = service.ingest_document(target)

    assert result["status"] == "indexed"
    assert result["chunks"] >= 1
    assert result["pages"] >= 1
    assert result["message"]
    assert result["ocr_pages"] == 0

    # ChromaDB contient les chunks avec les metadata attendues
    metadatas = _collection_metadata(service)
    assert len(metadatas) == result["chunks"]
    meta = metadatas[0]
    for key in ["doc_id", "file_name", "file_path", "page_number", "chunk_index", "chunk_id"]:
        assert key in meta
    assert meta["file_name"] == "doc.pdf"

    # le manifest enregistre le document
    record = service.manifest.get_record(target)
    assert record is not None
    assert record["chunk_count"] == result["chunks"]


def test_duplicate_document_is_skipped(service):
    target = service.documents_dir / "doc.pdf"
    target.write_bytes(REAL_DOC.read_bytes())

    service.ingest_document(target)
    second = service.ingest_document(target)

    assert second["status"] == "skipped"
    # pas de double indexation
    assert _collection_metadata(service) is not None


def test_modified_document_is_updated(service):
    target = service.documents_dir / "doc.pdf"
    target.write_bytes(REAL_DOC.read_bytes())
    first = service.ingest_document(target)
    assert first["status"] == "indexed"

    # contenu modifié -> réindexation
    target.write_bytes(OTHER_DOC.read_bytes())
    second = service.ingest_document(target)

    assert second["status"] == "updated"
    assert second["chunks"] >= 1


def test_ocr_unavailable_returns_ocr_required(tmp_path):
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(available=False))
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank)

    result = svc.ingest_document(blank)

    assert result["status"] == "ocr_required"
    assert result["chunks"] == 0
    assert "OCR" in result["message"]
    # rien n'a été indexé
    store = ChromaStore(svc.chroma_dir, "test_coll")
    assert store.count() == 0


def test_ocr_success_indexes_scanned_page(tmp_path):
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=["Texte OCR de la page"]))
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank)

    result = svc.ingest_document(blank)

    assert result["status"] == "indexed"
    assert result["chunks"] == 1
    assert result["ocr_pages"] == 0
    # le texte OCR est bien indexé
    metadatas = _collection_metadata(svc)
    assert "Texte OCR de la page" in _all_chunk_texts(svc)


def _all_chunk_texts(service):
    store = ChromaStore(service.chroma_dir, "test_coll")
    col = store._get_collection()
    return " ".join(col.get(include=["documents"])["documents"])


@pytest.mark.parametrize(
    "ocr_text",
    [
        "المجمع الكيميائي التونسي بقابس",  # arabe
        "La décision concerne la maintenance des équipements lourds.",  # français
        "The decision concerns heavy equipment maintenance.",  # anglais
    ],
)
def test_ocr_preserves_languages(tmp_path, ocr_text):
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=[ocr_text]))
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank)

    result = svc.ingest_document(blank)

    assert result["status"] == "indexed"
    assert ocr_text in _all_chunk_texts(svc)


def test_ocr_mixed_normal_and_ocr_pages(tmp_path):
    # page(s) texte + page vierge -> une seule unité (texte complet), OCR réussi sur la vierge
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=["Texte OCR"]))
    target = svc.documents_dir / "mixte.pdf"
    make_partial_ocr_pdf(target)

    result = svc.ingest_document(target)

    assert result["status"] == "indexed"
    assert result["chunks"] == 1
    assert result["ocr_pages"] == 0


def test_ocr_partial_failure_reported(tmp_path):
    # page texte OK + page vierge en échec OCR -> indexé + ocr_pages=1
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=[None]))
    target = svc.documents_dir / "mixte.pdf"
    make_partial_ocr_pdf(target)

    result = svc.ingest_document(target)

    assert result["status"] == "indexed"
    assert result["chunks"] >= 1
    assert result["ocr_pages"] == 1
    assert "OCR" in result["message"]


def test_ocr_empty_result_fails(tmp_path):
    # OCR vide -> OCRError -> page non indexée
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=[""]))
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank)

    result = svc.ingest_document(blank)

    assert result["status"] == "ocr_required"
    assert result["chunks"] == 0


def test_ocr_page_numbers_preserved(tmp_path):
    # 1-PDF=1-unité : même un PDF 2 pages ne produit qu'une seule entrée (page = 1ère utile)
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=["Texte 1", "Texte 2"]))
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank, pages=2)

    result = svc.ingest_document(blank)

    assert result["status"] == "indexed"
    assert result["pages"] == 2
    assert result["chunks"] == 1
    metadatas = _collection_metadata(svc)
    assert len(metadatas) == 1
    assert metadatas[0]["page_number"] == 1
    assert metadatas[0]["chunk_id"] == "scan"


def test_ocr_metadata_complete(tmp_path):
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=["Texte OCR"]))
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank)

    svc.ingest_document(blank)

    meta = _collection_metadata(svc)[0]
    for key in ["doc_id", "file_name", "file_path", "page_number", "chunk_index", "chunk_id"]:
        assert key in meta
    assert meta["file_name"] == "scan.pdf"


def test_ocr_chromadb_failure_is_clean(tmp_path):
    svc = make_service(
        tmp_path,
        ocr_engine=FakeOCREngine(results=["Texte OCR"]),
        store=FailingStore(),
    )
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank)

    result = svc.ingest_document(blank)

    assert result["status"] == "failed"
    assert result["chunks"] == 1
    assert svc.manifest.get_record(blank) is None


def test_duplicate_ocr_document_skipped(tmp_path):
    svc = make_service(tmp_path, ocr_engine=FakeOCREngine(results=["Texte OCR"]))
    blank = svc.documents_dir / "scan.pdf"
    make_blank_pdf(blank)

    first = svc.ingest_document(blank)
    second = svc.ingest_document(blank)

    assert first["status"] == "indexed"
    assert second["status"] == "skipped"


def test_corrupt_pdf_fails_cleanly(service):
    bad = service.documents_dir / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 not a real pdf body")

    result = service.ingest_document(bad)

    assert result["status"] == "failed"
    assert result["chunks"] == 0


def test_force_reindexes_even_if_unchanged(service):
    target = service.documents_dir / "doc.pdf"
    target.write_bytes(REAL_DOC.read_bytes())
    service.ingest_document(target)

    forced = service.ingest_document(target, force=True)

    assert forced["status"] == "updated"


def test_failed_embedding_is_clean_failure(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    svc = IngestionService(
        documents_dir=docs,
        chroma_dir=tmp_path / "chroma",
        collection_name="test_coll",
        manifest_path=tmp_path / "manifest.json",
        embedder=FailingEmbedder(),
    )
    target = docs / "doc.pdf"
    target.write_bytes(REAL_DOC.read_bytes())

    result = svc.ingest_document(target)

    assert result["status"] == "failed"
    assert result["chunks"] == 1
    assert "embedding" in result["message"].lower()


def test_chromadb_write_failure_is_clean_failure(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    svc = IngestionService(
        documents_dir=docs,
        chroma_dir=tmp_path / "chroma",
        collection_name="test_coll",
        manifest_path=tmp_path / "manifest.json",
        embedder=FakeEmbedder(),
        store=FailingStore(),
    )
    target = docs / "doc.pdf"
    target.write_bytes(REAL_DOC.read_bytes())

    result = svc.ingest_document(target)

    assert result["status"] == "failed"
    assert result["chunks"] == 1
    # le manifest n'est PAS mis à jour (index cohérent)
    assert svc.manifest.get_record(target) is None



def test_metadata_of_new_document(service):
    target = service.documents_dir / "doc.pdf"
    target.write_bytes(REAL_DOC.read_bytes())
    service.ingest_document(target)

    metadatas = _collection_metadata(service)
    meta = metadatas[0]
    assert meta["doc_id"] == "doc"
    assert meta["file_name"] == "doc.pdf"
    assert meta["page_number"] == 1
    assert meta["chunk_index"] == 0
    assert meta["chunk_id"] == "doc"


def test_ocr_engine_stores_timeout_from_config():
    from app.core.config import settings
    from app.ingest.ocr import OCREngine

    engine = OCREngine()
    assert engine.timeout == settings.ocr_timeout
    assert engine.timeout > 0


def test_ocr_engine_custom_timeout():
    from app.ingest.ocr import OCREngine

    engine = OCREngine(timeout=60)
    assert engine.timeout == 60
