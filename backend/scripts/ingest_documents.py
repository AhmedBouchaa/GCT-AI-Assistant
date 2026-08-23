"""Orchestrateur d'ingestion des documents PDF vers ChromaDB (CLI).

Découvre automatiquement tous les PDF sous ``data/documents`` (recherche récursive),
puis délègue l'indexation de chaque document à ``IngestionService``
(extraction -> chunking -> embeddings E5 -> ChromaDB -> manifest) — la MÊME
implémentation que l'API ``POST /api/v1/documents``.

Les documents déjà indexés et inchangés sont ignorés (SKIP) via le manifest (sha256).
Un document modifié est réindexé (anciens chunks supprimés puis réinsérés).
Aucun nom de fichier ni numéro de décision n'est hardcodé : les nouveaux PDF ajoutés
dans ``data/documents`` sont pris en compte sans modification du code.

Usage:
    python scripts/ingest_documents.py --dry-run        # aperçu, aucune modification
    python scripts/ingest_documents.py                  # indexation réelle
    python scripts/ingest_documents.py --force-reindex  # ignore le manifest, réindexe tout
"""
import argparse
import sys
from pathlib import Path

# Permet d'importer le package ``app`` quel que soit le répertoire de travail.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.ingest import IngestionService
from app.ingest.manifest import IngestionManifest

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _resolve(path: str | Path) -> Path:
    """Résout un chemin relatif par rapport au répertoire backend."""
    p = Path(path)
    return p if p.is_absolute() else (BACKEND_DIR / p)


def classify(pdf_path: Path, manifest: IngestionManifest, force_reindex: bool) -> str:
    """Détermine l'action à effectuer pour un document."""
    is_known = manifest.get_record(pdf_path) is not None
    changed = manifest.should_index(pdf_path) if is_known else True

    if force_reindex:
        return "MODIFIED" if is_known else "NEW"
    if not is_known:
        return "NEW"
    return "MODIFIED" if changed else "SKIP"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingestion des PDF GCT vers ChromaDB.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les actions (NEW/MODIFIED/SKIP) sans modifier ChromaDB ni le manifest.",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Ignore le manifest et réindexe tous les documents.",
    )
    parser.add_argument(
        "--documents-dir",
        default=str(BACKEND_DIR / "data" / "documents"),
        help="Répertoire des PDF (recherche récursive).",
    )
    parser.add_argument(
        "--chroma-dir",
        default=settings.chroma_persist_directory,
        help="Répertoire de persistance ChromaDB.",
    )
    parser.add_argument(
        "--manifest-path",
        default=str(BACKEND_DIR / "data" / "ingestion_manifest.json"),
        help="Fichier manifest d'indexation.",
    )
    parser.add_argument(
        "--collection",
        default=settings.chroma_collection_name,
        help="Nom de la collection ChromaDB.",
    )
    args = parser.parse_args()

    documents_dir = _resolve(args.documents_dir)
    if not documents_dir.exists():
        print(f"ERREUR: répertoire documents introuvable: {documents_dir}")
        sys.exit(1)

    chroma_dir = _resolve(args.chroma_dir)
    manifest_path = _resolve(args.manifest_path)

    pdf_files = sorted(documents_dir.rglob("*.pdf"))
    if not pdf_files:
        print(f"Aucun PDF trouvé dans {documents_dir}")
        return

    print(f"Documents: {len(pdf_files)} PDF découverts dans {documents_dir}")
    if args.dry_run:
        print("Mode DRY-RUN: aucune modification de ChromaDB ni du manifest.")
    print()

    service = IngestionService(
        documents_dir=documents_dir,
        chroma_dir=chroma_dir,
        collection_name=args.collection,
        manifest_path=manifest_path,
    )
    manifest = service.manifest

    counts = {"NEW": 0, "MODIFIED": 0, "SKIP": 0}

    for pdf in pdf_files:
        doc_id = pdf.stem
        action = classify(pdf, manifest, args.force_reindex)
        counts[action] += 1
        print(f"[{action}] {pdf.name}  (doc_id={doc_id})")

        if action == "SKIP" or args.dry_run:
            continue

        result = service.ingest_document(pdf, force=args.force_reindex)

        if result["status"] == "failed":
            print(f"    [ERREUR] {result['message']}")
        elif result["status"] == "ocr_required":
            print(f"    [AVERTISSEMENT] {result['message']}")
        else:
            print(f"    -> {result['chunks']} chunk(s) indexé(s) ({result['status']})")
            if result["ocr_pages"]:
                print(
                    f"    [AVERTISSEMENT] {result['ocr_pages']} page(s) sans texte "
                    "ignorée(s) (OCR non supporté)"
                )

    print(
        f"\nRésumé: {counts['NEW']} nouveau(x), "
        f"{counts['MODIFIED']} modifié(s), {counts['SKIP']} inchangé(s)."
    )
    if args.dry_run:
        print("Aucune modification effectuée (dry-run).")


if __name__ == "__main__":
    main()
