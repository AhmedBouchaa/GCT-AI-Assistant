"""Service d'ingestion d'un document PDF (implémentation unique).

Encapsule le pipeline existant : extraction -> unité documentaire complète ->
embedding E5 unique -> ChromaDB -> manifest. Utilisé à la fois par l'API
(``POST /api/v1/documents``) et par le script ``scripts/ingest_documents.py``
afin de ne pas dupliquer la logique d'ingestion.

Règle documentaire (depuis la refonte 1-PDF=1-unité) :
- chaque PDF = une seule unité logique (toutes les pages réunies),
- un seul embedding (``passage:``), une seule entrée ChromaDB (id = doc_id).
- ``chunker.py`` est conservé mais n'est plus utilisé par ce service.

Réutilise les composants existants :
- ``DocumentExtractor`` (extraction + détection OCR)
- ``E5EmbeddingService`` (modèle configuré, ex: multilingual-e5-small)
- ``ChromaStore`` (collection active, ex: gct_documents_v2)
- ``IngestionManifest`` (déduplication sha256)
"""
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.ingest.cleaner import clean_text
from app.ingest.embeddings import E5EmbeddingService
from app.ingest.extractor import DocumentExtractor
from app.ingest.manifest import IngestionManifest
from app.ingest.ocr import OCREngine
from app.ingest.store import ChromaStore

# parents[2] = backend (ce module vit dans backend/app/ingest/).
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    """Résout un chemin relatif par rapport au répertoire backend."""
    p = Path(path)
    return p if p.is_absolute() else (BACKEND_DIR / p)


class IngestionService:
    """Indexe un PDF dans la collection active + manifest."""

    def __init__(
        self,
        documents_dir: Optional[str | Path] = None,
        chroma_dir: Optional[str | Path] = None,
        collection_name: Optional[str] = None,
        manifest_path: Optional[str | Path] = None,
        embedder: Optional[Any] = None,
        store: Optional[ChromaStore] = None,
        ocr_engine: Optional[Any] = None,
    ):
        self.documents_dir = _resolve(documents_dir or settings.documents_dir)
        self.chroma_dir = _resolve(chroma_dir or settings.chroma_persist_directory)
        self.collection_name = collection_name or settings.chroma_collection_name
        self.manifest_path = _resolve(manifest_path or settings.ingestion_manifest_path)

        self.extractor = DocumentExtractor(
            self.documents_dir,
            ocr_engine=ocr_engine if ocr_engine is not None else OCREngine(),
        )
        self.store = store if store is not None else ChromaStore(self.chroma_dir, collection_name=self.collection_name)
        self.manifest = IngestionManifest(self.manifest_path)
        self.embedder = embedder if embedder is not None else E5EmbeddingService()
        # Sériaiise les ingestions (manifest + ChromaDB ne sont pas thread-safe).
        self._lock = threading.Lock()

    def ingest_document(self, pdf_path: str | Path, force: bool = False) -> Dict[str, Any]:
        """Indexe un PDF (sérialisé par un verrou : manifest + ChromaDB ne sont
        pas thread-safe). Délègue à ``_ingest_document_locked``."""
        with self._lock:
            return self._ingest_document_locked(pdf_path, force=force)

    def _ingest_document_locked(self, pdf_path: str | Path, force: bool = False) -> Dict[str, Any]:
        """Indexe un PDF. Retourne un dict ``{status, file_name, pages, chunks,
        message, ocr_pages}``.

        Statuts :
        - ``indexed`` : nouveau document indexé ;
        - ``updated`` : document existant réindexé (contenu modifié ou ``force``) ;
        - ``skipped`` : document déjà indexé et inchangé (déduplication) ;
        - ``ocr_required`` : document sans texte extractible (OCR non supporté) ;
        - ``failed`` : extraction/encodage impossible.
        """
        pdf_path = Path(pdf_path).resolve()

        # 1) Déduplication : déjà indexé et inchangé ?
        record = self.manifest.get_record(pdf_path)
        if not force and record is not None and not self.manifest.should_index(pdf_path):
            return {
                "status": "skipped",
                "file_name": pdf_path.name,
                "pages": 0,
                "chunks": int(record.get("chunk_count", 0)),
                "message": "Document déjà indexé (inchangé).",
                "ocr_pages": 0,
            }

        # 2) Extraction + détection OCR
        try:
            pages = self.extractor.extract_pages(pdf_path)
        except Exception as exc:  # PDF corrompu / non lisible
            return {
                "status": "failed",
                "file_name": pdf_path.name,
                "pages": 0,
                "chunks": 0,
                "message": f"Extraction impossible (fichier illisible ou corrompu) : {exc}",
                "ocr_pages": 0,
            }

        text_pages = [p for p in pages if not p.get("requires_ocr")]
        ocr_pages = [p["page_number"] for p in pages if p.get("requires_ocr")]

        if not text_pages:
            return {
                "status": "ocr_required",
                "file_name": pdf_path.name,
                "pages": len(pages),
                "chunks": 0,
                "message": (
                    "Aucun texte extractible (OCR échoué ou indisponible) : "
                    "le document n'a pas été indexé."
                    + (f" Pages concernées : {', '.join(map(str, ocr_pages))}." if ocr_pages else "")
                ),
                "ocr_pages": len(ocr_pages),
            }

        # 3) Unité documentaire : toutes les pages textuelles réunies en un
        #    seul texte normalisé (une seule entrée Chroma / un seul embedding).
        #    Règle : 1 PDF = 1 unité complète, 1 embedding `passage:`.
        #    `clean_text` normalise chaque page (NFKC + whitespace) puis les
        #    pages sont jointes par "\n\n" pour préserver la structure.
        doc_id = pdf_path.stem
        page_texts: List[str] = []
        first_page_number: Optional[int] = None
        for page in pages:
            if page.get("requires_ocr"):
                continue
            raw = (page.get("text") or "").strip()
            cleaned = clean_text(raw)
            if not cleaned:
                continue
            if first_page_number is None:
                first_page_number = page.get("page_number")
            page_texts.append(cleaned)
        if not page_texts:
            return {
                "status": "failed",
                "file_name": pdf_path.name,
                "pages": len(pages),
                "chunks": 1,
                "message": "Aucun texte exploitable après extraction.",
                "ocr_pages": len(ocr_pages),
            }
        full_text = "\n\n".join(page_texts)
        # Une seule "entrée" documentaire complète. `chunk_id` est conservé
        # uniquement comme alias de compatibilité (voir décision ci-dessous) :
        # il n'existe plus qu'une seule unité, donc chunk_id == doc_id.
        # Contrats: file_name/page_number conservés pour les sources,
        # score reste la similarité cosine (1 - distance).
        doc_entry = {
            "chunk_id": doc_id,
            "chunk_index": 0,
            "text": full_text,
            "doc_id": doc_id,
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "page_number": first_page_number if first_page_number is not None else 1,
        }
        chunks = [doc_entry]

        try:
            texts = [doc_entry["text"]]
            embeddings = self.embedder.embed_texts(texts, prefix="passage:")
        except Exception as exc:
            return {
                "status": "failed",
                "file_name": pdf_path.name,
                "pages": len(pages),
                "chunks": 1,
                "message": f"Génération des embeddings impossible : {exc}",
                "ocr_pages": len(ocr_pages),
            }

        # 4) Mise à jour ChromaDB (suppression de l'ancienne unité si réindexation).
        #    Une erreur d'écriture est mappée en échec propre (le manifest n'est
        #    PAS mis à jour -> l'index reste cohérent).
        try:
            if force or record is not None:
                self.store.delete_doc(doc_id)
            self.store.upsert_chunks(doc_id, chunks, embeddings=embeddings)
        except Exception as exc:
            return {
                "status": "failed",
                "file_name": pdf_path.name,
                "pages": len(pages),
                "chunks": 1,
                "message": f"Écriture dans la base vectorielle impossible : {exc}",
                "ocr_pages": len(ocr_pages),
            }

        # 5) Manifest (chunk_count = 1 : une unité par PDF)
        self.manifest.mark_indexed(
            pdf_path,
            doc_id,
            1,
            metadata={
                "file_name": pdf_path.name,
                "file_path": str(pdf_path),
                "pages_extracted": len(pages),
                "chunk_count": 1,
            },
        )

        status = "updated" if record is not None else "indexed"
        message = (
            "Document réindexé (contenu modifié)."
            if record is not None
            else "Document indexé avec succès."
        )
        if ocr_pages:
            message += (
                f" {len(ocr_pages)} page(s) en échec OCR "
                f"({', '.join(map(str, ocr_pages))}) ignorée(s)."
            )

        return {
            "status": status,
            "file_name": pdf_path.name,
            "pages": len(pages),
            "chunks": 1,
            "message": message,
            "ocr_pages": len(ocr_pages),
        }
