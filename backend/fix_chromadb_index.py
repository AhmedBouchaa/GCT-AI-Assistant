#!/usr/bin/env python3
"""
Fix script: Clean up ChromaDB index and rebuild with correct documents.
This resolves the 'File not found' errors when clicking on sources.
"""
import shutil
from pathlib import Path
from app.core.config import settings

def main():
    print("=" * 70)
    print("FIX: Clean ChromaDB Index and Rebuild")
    print("=" * 70)

    # Step 1: Check documents directory
    docs_dir = Path(settings.documents_dir)
    pdf_files = sorted([f.name for f in docs_dir.glob("*.pdf")])

    print(f"\n1. Documents directory: {docs_dir.resolve()}")
    print(f"   Total PDFs found: {len(pdf_files)}")
    if pdf_files:
        print(f"   First: {pdf_files[0]}")
        print(f"   Last: {pdf_files[-1]}")

    # Step 2: Backup and remove ChromaDB
    chroma_dir = Path(settings.chroma_persist_directory)
    if chroma_dir.exists():
        backup_dir = chroma_dir.parent / f"{chroma_dir.name}.backup"
        print(f"\n2. Backing up ChromaDB...")
        print(f"   From: {chroma_dir.resolve()}")
        print(f"   To:   {backup_dir.resolve()}")

        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(chroma_dir, backup_dir)
        print(f"   [DONE] Backup created")

        # Remove old index
        print(f"\n3. Removing old ChromaDB index...")
        shutil.rmtree(chroma_dir)
        print(f"   [DONE] Old index removed")
    else:
        print(f"\n2-3. ChromaDB directory doesn't exist (first run)")

    # Step 4: Rebuild index
    print(f"\n4. Rebuilding ChromaDB index with current documents...")
    print(f"   Collection: {settings.chroma_collection_name}")
    print(f"   Model: {settings.embedding_model}")
    print(f"   Files to index: {len(pdf_files)}")

    from app.ingest import IngestionService

    service = IngestionService()
    indexed = 0
    failed = 0
    skipped = 0

    for i, pdf_file in enumerate(pdf_files, 1):
        file_path = docs_dir / pdf_file
        print(f"   [{i}/{len(pdf_files)}] {pdf_file}...", end=" ", flush=True)

        try:
            result = service.ingest_document(file_path)
            if result["status"] == "indexed":
                print(f"[indexed]")
                indexed += 1
            elif result["status"] == "skipped":
                print(f"[skipped]")
                skipped += 1
            else:
                print(f"[{result['status']}]")
                failed += 1
        except Exception as e:
            print(f"[ERROR: {str(e)[:50]}]")
            failed += 1

    print(f"\n5. Indexing complete!")
    print(f"   Indexed: {indexed}")
    print(f"   Failed: {failed}")
    print(f"   Skipped: {skipped}")

    # Step 5: Verify
    print(f"\n6. Verifying index...")
    from app.retrieval import retrieve

    try:
        results = retrieve("test", top_k=1)
        if results:
            print(f"   [OK] Retrieved test query")
            first_file = results[0].get("file_name")
            print(f"   First result: {first_file}")

            # Check if file exists
            test_path = docs_dir / first_file
            if test_path.exists():
                print(f"   [OK] File exists on disk")
            else:
                print(f"   [ERROR] File does not exist on disk!")
                return False
        else:
            print(f"   [WARNING] No results returned from test query")
    except Exception as e:
        print(f"   [ERROR] Verification failed: {e}")
        return False

    print(f"\n" + "=" * 70)
    print("SUCCESS! Index has been rebuilt and verified.")
    print("=" * 70)
    print(f"\nYou can now:")
    print(f"  1. Restart the backend: ./venv/Scripts/python.exe -m uvicorn main:app")
    print(f"  2. Ask a question")
    print(f"  3. Click on a source to view the document")
    print(f"\nIf you still get 'Not found' errors:")
    print(f"  - Check browser console (F12) for debug logs")
    print(f"  - The file_name in the source should match a file in {docs_dir}")
    print(f"  - Backup of old index saved at: {backup_dir}")

    return True

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')

    success = main()
    sys.exit(0 if success else 1)
