from pathlib import Path

from app.ingest.cleaner import clean_text
from app.ingest.chunker import build_chunks, chunk_text
from app.ingest.manifest import IngestionManifest


def test_clean_text_normalizes_whitespace_and_preserves_arabic():
    raw_text = "\n\nBonjour   \n\nمرحبا  \n  monde  \n"

    cleaned = clean_text(raw_text)

    assert "Bonjour" in cleaned
    assert "مرحبا" in cleaned
    assert "monde" in cleaned
    assert "\n\n" not in cleaned


def test_chunk_text_creates_overlapping_chunks():
    # chunk_text est conservé mais n'est plus utilisé par l'ingestion
    # (règle 1-PDF=1-unité). Test conservé comme régression du module legacy.
    text = "a b c d e f g h i j"
    chunks = chunk_text(text, chunk_size=4, overlap=2)

    assert len(chunks) >= 2
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["text"]
    assert chunks[-1]["chunk_index"] == len(chunks) - 1


def test_manifest_detects_unchanged_and_modified_files(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = IngestionManifest(str(manifest_path))
    doc_path = tmp_path / "doc.pdf"
    doc_path.write_bytes(b"hello-world")

    assert manifest.should_index(doc_path) is True

    manifest.mark_indexed(
        doc_path,
        doc_id="doc-1",
        chunk_count=3,
        metadata={"file_name": doc_path.name},
    )

    assert manifest.should_index(doc_path) is False

    doc_path.write_bytes(b"hello-world-updated")
    assert manifest.should_index(doc_path) is True


def test_manifest_tracks_document_status(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = IngestionManifest(str(manifest_path))
    doc_path = tmp_path / "doc.pdf"
    doc_path.write_bytes(b"sample")

    manifest.mark_indexed(doc_path, doc_id="doc-2", chunk_count=2, metadata={"page_count": 1})

    record = manifest.get_record(doc_path)
    assert record is not None
    assert record["doc_id"] == "doc-2"
    assert record["chunk_count"] == 2


def test_build_chunks_creates_stable_ids_with_metadata(tmp_path):
    doc_id = "doc-1"
    pdf_path = tmp_path / "doc-1.pdf"
    pdf_path.write_bytes(b"fake pdf")

    pages = [
        {"page_number": 1, "text": "Bonjour monde  ", "requires_ocr": False},
        {"page_number": 2, "text": "", "requires_ocr": True},  # page OCR ignorée
        {"page_number": 3, "text": "مرحبا بالعالم", "requires_ocr": False},
    ]

    chunks = build_chunks(doc_id, pdf_path, pages, chunk_size=500, overlap=50)

    # La page OCR (sans texte) est ignorée.
    assert len(chunks) == 2

    chunk = chunks[0]
    assert chunk["chunk_id"] == "doc-1_p1_c0"
    assert chunk["chunk_index"] == 0
    assert chunk["doc_id"] == "doc-1"
    assert chunk["file_name"] == "doc-1.pdf"
    assert chunk["file_path"] == str(pdf_path)
    assert chunk["page_number"] == 1
    assert chunk["text"] == "Bonjour monde"

    # L'identifiant est stable et unique pour chaque page/chunk.
    assert chunks[1]["chunk_id"] == "doc-1_p3_c0"
    assert {c["chunk_id"] for c in chunks} == {"doc-1_p1_c0", "doc-1_p3_c0"}


def test_manifest_atomic_write_preserves_original_on_error(tmp_path):
    """Si l'écriture échoue, le manifest original reste intact."""
    manifest_path = tmp_path / "manifest.json"
    manifest = IngestionManifest(str(manifest_path))
    doc_path = tmp_path / "doc.pdf"
    doc_path.write_bytes(b"original")

    # Écrire un premier enregistrement valide.
    manifest.mark_indexed(doc_path, doc_id="original", chunk_count=1)
    original_content = manifest_path.read_text(encoding="utf-8")
    assert "original" in original_content

    # Simuler une erreur pendant l'écriture : ouvrir le manifest en lecture seule
    # pour que _save échoue au rename (fichier cible protégé).
    import os
    import unittest.mock

    real_replace = os.replace

    def fail_replace(src, dst):
        if ".manifest_" in str(src):
            raise OSError("simulated failure")
        return real_replace(src, dst)

    with unittest.mock.patch("os.replace", side_effect=fail_replace):
        try:
            manifest.mark_indexed(doc_path, doc_id="should_not_appear", chunk_count=2)
        except OSError:
            pass

    # Le manifest original doit être intact.
    after_content = manifest_path.read_text(encoding="utf-8")
    assert "original" in after_content
    assert "should_not_appear" not in after_content


def test_manifest_atomic_no_temp_files_left_on_success(tmp_path):
    """Après une écriture réussie, aucun fichier .tmp ne doit rester."""
    manifest_path = tmp_path / "manifest.json"
    manifest = IngestionManifest(str(manifest_path))
    doc_path = tmp_path / "doc.pdf"
    doc_path.write_bytes(b"test")

    manifest.mark_indexed(doc_path, doc_id="doc-ok", chunk_count=1)

    remaining = list(tmp_path.glob(".manifest_*.tmp"))
    assert remaining == []
