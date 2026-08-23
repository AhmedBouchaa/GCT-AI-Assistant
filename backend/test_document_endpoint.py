#!/usr/bin/env python3
"""Diagnostic script to test the document content endpoint."""
import sys
sys.path.insert(0, 'D:\\Ingenirie\\Stage\\GCT-AI-Assistant\\backend')

from fastapi.testclient import TestClient
from pathlib import Path
from app.core.config import settings

# Import the app
from main import app

client = TestClient(app)

# Get list of available PDFs
docs_dir = Path(settings.documents_dir)
pdf_files = sorted([f.name for f in docs_dir.glob("*.pdf")])

print(f"Found {len(pdf_files)} PDF files:")
print(f"  First: {pdf_files[0]}")
print(f"  Last: {pdf_files[-1]}")
print()

# Test the endpoint
test_file = pdf_files[0]
print(f"Testing endpoint with: {test_file}")
print()

response = client.get(
    f'/api/v1/documents/{test_file}/content',
    headers={'Authorization': 'Bearer dev-user-gct'}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    data = response.json()
    print(f"\nSuccess!")
    print(f"  File: {data['file_name']}")
    print(f"  Page: {data['page_number']}/{data['total_pages']}")
    print(f"  Content length: {len(data['content'])} chars")
else:
    print(f"\nError!")
    print(f"  Detail: {response.json().get('detail', 'Unknown error')}")
