# Quick Reference: Click Source to View File Feature

## For Users

### How to Use
1. Ask a question in the chat (Arabic, French, or English)
2. Receive an answer with source documents listed below
3. **Click on any source card** to view the document
4. A modal opens showing the document content
5. Use **Previous/Next buttons** or the **page number input** to navigate
6. Click **the X button** or outside the modal to close

### What You'll See
- **Document filename** (e.g., "GCT_notes_exemples_50-2.pdf")
- **Page number** (e.g., "Page 2 of 5")
- **Extracted text** from that page
- **Navigation controls** if the document has multiple pages

### Features
- ✓ View any source document instantly
- ✓ Navigate to any page
- ✓ Text is extracted and formatted for readability
- ✓ Works on all devices (desktop, tablet, mobile)

---

## For Developers

### Backend Endpoint

**Route**: `GET /api/v1/documents/{file_name}/content`

**Authentication**: Required (Bearer token, user or admin role)

**Parameters**:
```
Path:
  - file_name: str (required) - PDF filename, e.g. "GCT_notes_exemples_50-2.pdf"

Query:
  - page_number: int (optional) - Which page to retrieve (1-indexed, default: 1)
```

**Response** (200 OK):
```json
{
  "file_name": "GCT_notes_exemples_50-2.pdf",
  "page_number": 1,
  "total_pages": 5,
  "content": "extracted text from page 1..."
}
```

**Error Responses**:
- `400 Bad Request` - Invalid filename or page number
- `403 Forbidden` - Path traversal attempt detected
- `404 Not Found` - File does not exist
- `500 Internal Server Error` - Extraction or read error

**Example Usage**:
```bash
# Get first page of a document
curl -H "Authorization: Bearer dev-user-gct" \
  http://127.0.0.1:8000/api/v1/documents/GCT_notes_exemples_50-2.pdf/content

# Get specific page
curl -H "Authorization: Bearer dev-user-gct" \
  "http://127.0.0.1:8000/api/v1/documents/GCT_notes_exemples_50-2.pdf/content?page_number=2"
```

### Frontend API Function

**Function**: `getDocumentContent(fileName, pageNumber = null)`

**Location**: `frontend/src/api.js`

**Parameters**:
- `fileName` (string, required): PDF filename
- `pageNumber` (number, optional): Which page to retrieve (1-indexed)

**Returns**: Promise that resolves to:
```javascript
{
  file_name: "GCT_notes_exemples_50-2.pdf",
  page_number: 1,
  total_pages: 5,
  content: "extracted text..."
}
```

**Example Usage**:
```javascript
import { getDocumentContent } from './api';

// Get first page
const data = await getDocumentContent("GCT_notes_exemples_50-2.pdf");

// Get specific page
const data = await getDocumentContent("GCT_notes_exemples_50-2.pdf", 2);

// Handle errors
try {
  const data = await getDocumentContent("document.pdf", 1);
  console.log(data.content);
} catch (error) {
  console.error("Failed to load document:", error.message);
}
```

### Frontend Components

**SourceViewer Component**: `frontend/src/components/SourceViewer.jsx`

**Props**:
- `source` (object, required) - Source object with `file_name` and optional `page_number`
- `onClose` (function, required) - Callback when modal should close

**Example Usage**:
```javascript
import SourceViewer from './components/SourceViewer';

// In your component
const [selectedSource, setSelectedSource] = useState(null);

// Render
{selectedSource && <SourceViewer source={selectedSource} onClose={() => setSelectedSource(null)} />}
```

---

## Key Implementation Details

### Security
- ✓ Path traversal prevention (validates filename)
- ✓ Extension check (PDF only)
- ✓ Full path resolution verification
- ✓ Authentication required
- ✓ No tracebacks exposed to frontend

### Performance
- ✓ One page extracted at a time (not full document)
- ✓ Modal rendered only when needed
- ✓ CSS animations are GPU-accelerated
- ✓ Lazy loading of content

### Accessibility
- ✓ Semantic HTML (`<button>` elements, `<h2>` headers)
- ✓ ARIA labels on all interactive elements
- ✓ Keyboard navigation support
- ✓ Screen reader friendly

---

## Testing

### Run All Tests
```bash
cd backend
./venv/Scripts/python.exe -m pytest -q
```

### Run Specific Tests
```bash
# Language detection tests
./venv/Scripts/python.exe -m pytest tests/test_language_compliance.py -v

# API tests
./venv/Scripts/python.exe -m pytest tests/test_api.py -v

# All except heavy tests
./venv/Scripts/python.exe -m pytest -q
```

### Test Results
- ✓ 137 passed, 16 skipped
- ✓ All language detection tests passing
- ✓ All API tests passing
- ✓ No regressions in existing functionality

---

## Bonus: Language Detection Fix

The language detection algorithm was improved to handle mixed-language text correctly.

### Before
- "من هو president" (Arabic with English word) → "unknown" ❌
- "Qui est الرئيس" (French with Arabic word) → "unknown" ❌

### After
- "من هو president" → "ar" ✓
- "Qui est الرئيس" → "fr" ✓

**How It Works**:
1. Extract words (sequences of characters)
2. Classify each word as Arabic-only, Latin-only, or mixed
3. Determine primary language by word majority (>50%)
4. Use keyword detection as fallback for French vs English

---

## Troubleshooting

### "File not found" error
- Verify the PDF exists in `backend/data/documents/`
- Check the filename spelling and capitalization
- Ensure the file was successfully ingested

### "Invalid page number" error
- Page numbers are 1-indexed (first page is 1, not 0)
- Check that the page number doesn't exceed total pages
- Example: If document has 5 pages, valid page numbers are 1-5

### "Path traversal attempt" error
- Don't include `/` or `\` in filename
- Don't use `..` or `.` prefixes
- Use only the filename, not a full path

### Modal doesn't open
- Check browser console for JavaScript errors
- Verify token is valid (use `/api/v1/auth/verify` endpoint)
- Ensure backend is running and accessible

### Text doesn't display
- Some PDFs may not have extractable text (scanned images)
- OCR support is available for such PDFs (see CLAUDE.md)
- If OCR was required during ingestion, document may not be fully indexed

---

## Configuration

### Environment Variables
No new environment variables needed. Uses existing:
- `DOCUMENTS_DIR` - Where PDFs are stored (default: `./data/documents`)
- `AUTH_ENABLED` - Whether authentication is required

### Settings (backend/app/core/config.py)
```python
documents_dir: str = "./data/documents"
```

This directory is used to find and serve PDFs to users.

---

## Production Deployment Notes

1. **Ensure PDFs are ingested**: Run `./scripts/ingest_documents.py`
2. **Test endpoint**: `curl http://localhost:8000/api/v1/documents/GCT_notes_exemples_50-1.pdf/content`
3. **Check CORS**: Frontend must be able to call the endpoint (check `CORS_ORIGINS`)
4. **Monitor logs**: Watch for file access errors or encoding issues
5. **Test on multiple browsers**: Especially on mobile/tablet

---

## Related Documentation

- **API Routes**: `backend/app/api/routes.py`
- **PDF Extraction**: `backend/app/utils/pdf_extractor.py`
- **Frontend API Client**: `frontend/src/api.js`
- **SourceViewer Component**: `frontend/src/components/SourceViewer.jsx`
- **Full Implementation Details**: `IMPLEMENTATION_COMPLETE.md`

