"""OBSOLÈTE depuis la règle 1-PDF=1-unité : conservé pour compat, non utilisé par l'ingestion.

Le pipeline documentaire (`app.ingest.service`) n'appelle plus ce module ;
chaque PDF est indexé comme une seule unité (un seul embedding `passage:`).
"""
from pathlib import Path
from typing import List, Dict

from .cleaner import clean_text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, object]]:
    """Split text into overlapping word-based chunks."""
    cleaned = clean_text(text)
    if not cleaned:
        return []

    words = cleaned.split()
    if not words:
        return []

    if chunk_size <= 0:
        chunk_size = 500
    if overlap < 0:
        overlap = 0

    step = max(1, chunk_size - overlap)
    chunks: List[Dict[str, object]] = []

    start_index = 0
    chunk_index = 0
    while start_index < len(words):
        end_index = min(len(words), start_index + chunk_size)
        chunk_words = words[start_index:end_index]
        if not chunk_words:
            break

        chunks.append(
            {
                "chunk_index": chunk_index,
                "text": " ".join(chunk_words),
            }
        )

        if end_index >= len(words):
            break

        start_index += step
        chunk_index += 1

    return chunks


def build_chunks(
    doc_id: str,
    pdf_path: str | Path,
    pages: List[Dict],
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict]:
    """Assemble l'interface complète des chunks consommée par ``ChromaStore``.

    ``chunk_text`` ne produit que ``chunk_index``/``text`` ; cette fonction
    enrichit chaque chunk avec un identifiant stable et unique dans le document
    (``chunk_id`` = ``{doc_id}_p{page}_c{index}``) ainsi que ``doc_id``,
    ``file_name``, ``file_path``, ``page_number`` et ``chunk_index``.

    Les pages sans texte (``requires_ocr``) sont ignorées tant que l'OCR n'est
    pas implémenté.
    """
    chunks: List[Dict] = []
    for page in pages:
        text = (page.get("text") or "").strip()
        if page.get("requires_ocr"):
            continue
        for chunk in chunk_text(clean_text(text), chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                {
                    "chunk_id": f"{doc_id}_p{page['page_number']}_c{chunk['chunk_index']}",
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "doc_id": doc_id,
                    "file_name": Path(pdf_path).name,
                    "file_path": str(pdf_path),
                    "page_number": page["page_number"],
                }
            )
    return chunks
