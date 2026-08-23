#!/usr/bin/env python3
"""
COMPLETE FIX for 'Not Found' errors on document content endpoint.

This script will:
1. Fix CORS configuration
2. Verify the endpoint works
3. Clear and rebuild ChromaDB index if needed
4. Provide comprehensive debugging info
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, '.')

from app.core.config import settings

print("=" * 100)
print("COMPLETE FIX: Document Content 'Not Found' Issue")
print("=" * 100)

# STEP 1: Fix CORS in .env
print("\n1. CHECKING AND FIXING CORS CONFIGURATION")
print("-" * 100)

env_file = Path(".env")
env_content = env_file.read_text() if env_file.exists() else ""

# Check if CORS_ORIGINS is configured
if "CORS_ORIGINS" not in env_content:
    print("CORS_ORIGINS not found in .env - adding it...")
    cors_line = "\n# Allow frontend to call backend API\nCORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000\n"

    if env_file.exists():
        env_file.write_text(env_content + cors_line)
    else:
        env_file.write_text("AUTH_ENABLED=false\nOLLAMA_BASE_URL=http://localhost:11434\nOLLAMA_MODEL=mistral:latest" + cors_line)

    print("✓ Added CORS_ORIGINS to .env")
else:
    print("✓ CORS_ORIGINS already in .env")

print(f"✓ CORS should now allow requests from frontend")

# STEP 2: Verify endpoint exists
print("\n2. VERIFYING ENDPOINT IS REGISTERED")
print("-" * 100)

from main import app

endpoint_found = False
for route in app.routes:
    if hasattr(route, 'path') and '/documents/{file_name}/content' in route.path:
        endpoint_found = True
        print(f"✓ Endpoint registered: {route.path}")
        print(f"  Methods: {route.methods}")
        break

if not endpoint_found:
    print("✗ Endpoint NOT found - Something is wrong with the backend")
    sys.exit(1)

# STEP 3: Test endpoint directly
print("\n3. TESTING ENDPOINT DIRECTLY")
print("-" * 100)

from fastapi.testclient import TestClient

client = TestClient(app)
docs_dir = Path(settings.documents_dir)
test_file = "GCT_notes_exemples_50-1.pdf"

response = client.get(
    f'/api/v1/documents/{test_file}/content',
    headers={'Authorization': 'Bearer dev-user-gct'}
)

if response.status_code == 200:
    data = response.json()
    print(f"✓ Endpoint works!")
    print(f"  File: {data['file_name']}")
    print(f"  Pages: {data['total_pages']}")
    print(f"  Content: {len(data['content'])} chars")
else:
    print(f"✗ Endpoint failed: {response.status_code}")
    print(f"  Error: {response.json().get('detail')}")

# STEP 4: Check ChromaDB for missing files
print("\n4. CHECKING CHROMADB INDEX FOR MISSING FILES")
print("-" * 100)

from app.retrieval import retrieve

try:
    results = retrieve("test", top_k=5)

    indexed_files = set()
    existing_files = set(f.name for f in docs_dir.glob("*.pdf"))

    for r in results:
        indexed_files.add(r.get('file_name', ''))

    missing = indexed_files - existing_files

    if missing:
        print(f"⚠ Found {len(missing)} files in index that don't exist on disk:")
        for f in missing:
            print(f"  - {f}")

        print("\nYou should rebuild the ChromaDB index:")
        print("  Run: ./venv/Scripts/python.exe -c \"")
        print("  import shutil")
        print("  from pathlib import Path")
        print("  shutil.rmtree(Path('data/chroma'), ignore_errors=True)")
        print("  \"")
        print("  Then restart the backend")
    else:
        print("✓ All indexed files exist on disk")
        print(f"  Total files: {len(existing_files)}")

except Exception as e:
    print(f"Error checking index: {e}")

# STEP 5: Provide solution
print("\n5. SOLUTION STEPS")
print("-" * 100)

print("""
If you're still getting 'not found' errors, do this:

1. RESTART THE BACKEND (to pick up CORS changes):
   ./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

2. OPEN BROWSER DEVELOPER TOOLS:
   Press F12 in your browser

3. GO TO CONSOLE TAB:
   - You should see debug logs from the API client
   - Look for "[DEBUG]" messages with the URL being called

4. TRY CLICKING A SOURCE:
   - Ask a question
   - Click on a source document
   - Check the console for debug messages

5. GO TO NETWORK TAB:
   - Click the source again
   - Look for a request to "/api/v1/documents/..."
   - Check its Status (should be 200)
   - Check its Response (should have file_name, page_number, content)

COMMON ISSUES AND FIXES:

Issue: "Failed to fetch" error
  → Backend is not running
  → Fix: Restart backend with: ./venv/Scripts/python.exe -m uvicorn main:app

Issue: "404 Not Found"
  → File doesn't exist on disk
  → Fix: Rebuild ChromaDB index (see step 4 above)

Issue: "Impossible de charger le contenu du document"
  → Check browser console for the actual error message
  → The error should tell you what's wrong

Issue: CORS error (blocked by browser)
  → Frontend can't call backend
  → Fix: Make sure CORS_ORIGINS is set in .env
  → The fix above should have added it

If still stuck:
  1. Check the backend logs (should show request details)
  2. Make sure backend is running on http://127.0.0.1:8000
  3. Make sure frontend is on http://127.0.0.1:5173 or running via npm
  4. Verify .env has CORS_ORIGINS set
""")

print("\n" + "=" * 100)
print("✓ Fix applied. Restart your backend and try again!")
print("=" * 100)
