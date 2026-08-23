#!/usr/bin/env python3
"""
Comprehensive diagnostic script to identify the 'not found' issue.
"""
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Setup path
import sys
sys.path.insert(0, 'D:\\Ingenirie\\Stage\\GCT-AI-Assistant\\backend')

from app.core.config import settings
from main import app

print("=" * 80)
print("DIAGNOSTIC: Source Document 'Not Found' Issue")
print("=" * 80)

# 1. Check documents directory
print("\n1. CHECKING DOCUMENTS DIRECTORY")
print("-" * 80)
docs_dir = Path(settings.documents_dir)
print(f"Documents dir: {docs_dir}")
print(f"Absolute path: {docs_dir.resolve()}")
print(f"Exists: {docs_dir.exists()}")

pdf_files = sorted([f.name for f in docs_dir.glob("*.pdf")])
print(f"Total PDFs: {len(pdf_files)}")
if pdf_files:
    print(f"Examples:")
    for f in pdf_files[:3]:
        print(f"  - {f}")

# 2. Check ChromaDB index
print("\n2. CHECKING CHROMADB INDEX")
print("-" * 80)
from app.retrieval import retrieve

try:
    results = retrieve("test", top_k=3)
    print(f"Retrieved {len(results)} results from ChromaDB")

    print("\nFiles referenced in ChromaDB:")
    indexed_files = set()
    for r in results:
        fn = r.get('file_name', '')
        indexed_files.add(fn)
        print(f"  - {fn}")

    print("\nFiles that EXIST on disk:")
    existing_files = set(pdf_files)
    for fn in list(indexed_files)[:5]:
        exists = fn in existing_files
        status = "EXISTS" if exists else "MISSING"
        print(f"  - {fn} [{status}]")

    missing = indexed_files - existing_files
    if missing:
        print(f"\n*** WARNING: {len(missing)} files in index but NOT on disk ***")
        for fn in list(missing)[:5]:
            print(f"  - {fn}")

except Exception as e:
    print(f"ERROR retrieving from ChromaDB: {e}")

# 3. Test the API endpoint directly
print("\n3. TESTING API ENDPOINT")
print("-" * 80)
client = TestClient(app)

# Pick a file that we know exists
test_file = pdf_files[0] if pdf_files else None

if test_file:
    print(f"Testing with file: {test_file}")
    print(f"Full path on disk: {docs_dir / test_file}")
    print(f"File exists: {(docs_dir / test_file).exists()}")

    # Test endpoint
    url = f'/api/v1/documents/{test_file}/content'
    print(f"\nCalling: GET {url}")

    response = client.get(
        url,
        headers={'Authorization': 'Bearer dev-user-gct'}
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    if response.status_code == 200:
        print(f"SUCCESS!")
        print(f"  - file_name: {data.get('file_name')}")
        print(f"  - total_pages: {data.get('total_pages')}")
        print(f"  - content length: {len(data.get('content', ''))} chars")
    else:
        print(f"ERROR: {data.get('detail', 'Unknown error')}")
else:
    print("ERROR: No PDF files found in documents directory!")

# 4. Test with a file from ChromaDB results
print("\n4. TESTING WITH FILE FROM CHROMADB")
print("-" * 80)

try:
    results = retrieve("test", top_k=1)
    if results:
        retrieved_file = results[0].get('file_name')
        print(f"File from ChromaDB: {retrieved_file}")

        file_path = docs_dir / retrieved_file
        exists_on_disk = file_path.exists()
        print(f"Exists on disk: {exists_on_disk}")

        if exists_on_disk:
            # Try to fetch it
            response = client.get(
                f'/api/v1/documents/{retrieved_file}/content',
                headers={'Authorization': 'Bearer dev-user-gct'}
            )
            print(f"API Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Detail: {response.json().get('detail')}")
        else:
            print(f"*** FILE MISSING FROM DISK ***")
            print(f"Expected at: {file_path}")
except Exception as e:
    print(f"Error: {e}")

# 5. Summary and recommendations
print("\n5. SUMMARY & RECOMMENDATIONS")
print("-" * 80)

if pdf_files and len(pdf_files) > 0:
    print("✓ PDF files exist on disk")

    # Try a simple end-to-end test
    test_response = client.get(
        f'/api/v1/documents/{pdf_files[0]}/content',
        headers={'Authorization': 'Bearer dev-user-gct'}
    )

    if test_response.status_code == 200:
        print("✓ API endpoint is working with existing files")
        print("\nRECOMMENDATIONS:")
        print("1. The API works - the 'not found' error is from trying to access")
        print("   a file that doesn't exist on disk but is in the ChromaDB index")
        print("2. Solution: Rebuild the ChromaDB index")
        print("   Run: ./venv/Scripts/python.exe fix_chromadb_index.py")
        print("3. Then restart the backend")
    else:
        print("✗ API endpoint failed even with existing files")
        print(f"Error: {test_response.json().get('detail')}")
        print("\nRECOMMENDATIONS:")
        print("1. Check backend logs for detailed error")
        print("2. Verify authentication token is correct")
        print("3. Restart the backend server")
else:
    print("✗ No PDF files found in documents directory")
    print("Please check that PDFs are in:", docs_dir.resolve())

print("\n" + "=" * 80)
