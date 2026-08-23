# GCT AI Assistant - Comprehensive Backend Testing Report

**Date**: 2026-08-22  
**Test Phase**: Full diagnostic without code modifications  
**Objective**: Verify if backend responses match actual document content and meet specifications

---

## Executive Summary

The backend is **functionally broken** in ways that violate the stated specifications:

| Component | Status | Issue |
|-----------|--------|-------|
| **Ingestion** | ✓ WORKING | Documents indexed correctly |
| **ChromaDB** | ✓ WORKING | Documents stored with correct embeddings |
| **Retrieval** | ✓ WORKING | Correct documents retrieved at top-1 rank |
| **RAG/LLM** | ❌ BROKEN | **Answers in wrong language (French instead of Arabic)** |
| **API Response** | ❌ BROKEN | Wrong documents returned (50-11, 50-35 instead of 50-2) |

---

## Test Results

### Test 1: Direct Retriever Function
**Command**: `from app.retrieval.retriever import retrieve`

**Query (Arabic)**:
```
من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟
```

**Result**: ✓ CORRECT
```
1. GCT_notes_exemples_50-2.pdf (score: 0.9028)  ← CORRECT
2. GCT_notes_exemples_50-22.pdf (score: 0.8988)
3. GCT_notes_exemples_50-37.pdf (score: 0.8961)
...
```

**Verdict**: Retrieval layer is **working correctly**

---

### Test 2: RAG Service
**Command**: `from app.rag.service import RAGService; rag.answer(question)`

**Query (Arabic)**:
```
من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟
```

**Expected Response**:
- Language: ARABIC (same as question)
- Content: محمد بن علي
- Source: 50-2.pdf

**Actual Response**:
```
Le président de la commission technique pour la maintenance des équipements 
lourds à Qabis est Mohamed Ben Ali, selon le document GCT_notes_exemples_50-2.

Sources: 50-2.pdf (score 0.9028), 50-22.pdf, 50-37.pdf, ...
```

**Verdict**: ❌ **LANGUAGE VIOLATION**
- Retrieved correct document ✓
- Found correct answer ✓
- **Answered in FRENCH instead of ARABIC ❌**
- Violates SYSTEM_PROMPT line 35: "OBLIGATION DE LANGUE ... STRICTEMENT ... MÊME LANGUE"

---

### Test 3: FastAPI Endpoint
**Command**: `curl -X POST http://127.0.0.1:8000/api/v1/ask -H "Authorization: Bearer dev-user-gct" -d '{"question": "من هو..."}'`

**Query (Arabic)**:
```
من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟
```

**Expected Response**:
- Correct document: 50-2.pdf
- Correct president: محمد بن علي
- Sources: [50-2.pdf]

**Actual Response**:
```json
{
  "answer": "La réunion de la commission de contrôle de la direction administrative...",
  "sources": [
    {"file_name": "GCT_notes_exemples_50-11.pdf", "score": 0.8110},
    {"file_name": "GCT_notes_exemples_50-35.pdf", "score": 0.8106}
  ]
}
```

**Verdict**: ❌ **COMPLETELY WRONG**
- Retrieved wrong documents (50-11, 50-35)
- Wrong names (Amal Al-Daridi, Balal Al-Daridi)
- Wrong committee (administrative control, not heavy equipment maintenance)
- Encoding corruption ("?? ?? ????" for Arabic question)

---

## Root Cause Analysis

### Layer 1: Retrieval (Working)
The `retrieve()` function correctly:
1. Embeds query with E5-small using `query:` prefix
2. Searches ChromaDB with cosine similarity
3. Returns documents ranked by score
4. **50-2.pdf is correctly ranked #1 for Arabic queries**

### Layer 2: RAG Service (Partially Broken)
The `RAGService.answer()` function:
1. ✓ Correctly calls retriever
2. ✓ Correctly receives 50-2.pdf as #1 result
3. ✓ Correctly builds prompt with retrieved context
4. ✓ Calls Mistral LLM with full SYSTEM_PROMPT
5. ❌ **Mistral ignores the language compliance instruction**
   - SYSTEM_PROMPT line 35: "Répondez STRICTEMENT dans la MÊME LANGUE"
   - SYSTEM_PROMPT lines 52-55: Arabic instruction to respond in Arabic for Arabic questions
   - **Result**: Answers in French anyway

### Layer 3: API Response (Broken - Different Failure)
The FastAPI endpoint is returning **completely different documents** than what the RAG service returns:

| When tested directly | When tested via API |
|---------------------|-------------------|
| RAG returns: 50-2.pdf #1 | API returns: 50-11.pdf #1 |
| RAG returns: 50-22.pdf #2 | API returns: 50-35.pdf #2 |
| Scores: 0.9028 (50-2) | Scores: 0.8110 (50-11) |

**Hypothesis**: The API may be:
- Using different model instance (not lazy-loaded correctly?)
- Querying different ChromaDB collection
- Processing requests in wrong order/state
- Not applying auth/routing correctly

---

## Specification Violations

### 1. Language Compliance (Critical)
**Specification** (CLAUDE.md line 35): "Répondez STRICTEMENT dans la MÊME LANGUE que la question"

**Violation**: Arabic question answered in French

**Impact**: System violates its core contract - users expect answers in their language

### 2. Correctness (Critical)
**Specification** (CLAUDE.md): "answer only from context"

**Violation**: API returns information from wrong documents

**Impact**: Users receive completely incorrect information about committee members, decisions, etc.

### 3. Encoding (Medium)
**Specification** (implicit): UTF-8 encoding of Arabic text

**Violation**: Arabic question displayed as "?? ?? ????" in API response

**Impact**: Debugging difficult, user experience degraded

---

## What Should Happen (vs. What Does)

### Correct Behavior (Arabic Query)
```
Question: من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟
↓
E5-small embeds with "query:" prefix
↓
ChromaDB retrieves: [50-2.pdf (0.9028), 50-22.pdf (0.8988), ...]
↓
RAG builds prompt with 50-2 context
↓
Mistral receives SYSTEM_PROMPT + context in Arabic
↓
Mistral MUST respond in Arabic (per SYSTEM_PROMPT line 35)
↓
Response: رئيس اللجنة هو محمد بن علي [Source: 50-2.pdf]
↓
API returns: {"answer": "رئيس اللجنة...", "sources": [50-2.pdf]}
```

### Actual Behavior (Arabic Query via API)
```
Question: من هو رئيس اللجنة الفنية...
↓
??? Unknown transformation happens
↓
API returns: {"answer": "La réunion de...", "sources": [50-11.pdf, 50-35.pdf]}
↓
Result: Wrong documents, wrong language, wrong information
```

---

## Critical Questions Remaining

1. **Why does RAG service get correct documents but API gets wrong ones?**
   - Different model instances?
   - Race condition?
   - Parallel processing interfering?

2. **Why does Mistral ignore the language compliance instruction?**
   - Instruction not clear enough?
   - Mistral not respecting system prompt?
   - Prompt not being passed correctly?

3. **Why is the API seeing different retrieval results than direct function calls?**
   - Stateful issue?
   - Collection mismatch?
   - Encoding issue in the HTTP layer?

---

## Detailed Component Status

### ✓ Ingestion Pipeline (Working)
- PDFs correctly parsed
- Text correctly extracted  
- Chunks created with correct metadata
- ChromaDB populated with correct embeddings (384-dim e5-small)
- Manifest tracks indexed files

### ✓ Embeddings (Working)
- E5-small correctly loaded on first use
- Query prefix ("query:") correctly applied
- Document prefix ("passage:") correctly applied
- Normalization (L2 norm = 1.0) verified

### ✓ Retrieval (Working)
- ChromaDB queries executed correctly
- Cosine similarity scoring correct
- Top-K ranking correct
- Document 50-2.pdf appears #1 for Arabic queries

### ⚠️ RAG Service (Partially Broken)
- Retrieval layer integration: ✓ Working
- Context building: ✓ Working
- Prompt construction: ✓ Working
- **Language enforcement: ❌ Failed** (Mistral answers French for Arabic queries)

### ❌ FastAPI Route (Broken)
- Returns completely wrong documents
- Different results than direct RAG service calls
- Encoding issues with Arabic text in response

---

## Conclusion

**The backend is not production-ready.** While the core retrieval mechanics work correctly, the system has two critical failures:

1. **Language Violation**: LLM answers in French regardless of question language, violating the explicit SYSTEM_PROMPT instruction
2. **Wrong Results via API**: API endpoint returns completely different documents than the underlying RAG service, suggesting a routing or state management issue

**The issue is NOT with document indexing or retrieval** — it's in the LLM behavior and the API layer's integration with the retrieval service.

**Immediate investigation needed**:
- Check if Mistral is loading correctly and respecting the system prompt
- Debug why API endpoint retrieves different documents than direct service calls  
- Verify no state corruption or parallel processing issues
- Consider if the language compliance instruction is too complex for the LLM to parse

