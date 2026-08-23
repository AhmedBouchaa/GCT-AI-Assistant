# Backend Response Testing Report
**Date**: 2026-08-22  
**Test Environment**: Local 8GB machine, no code modifications  
**Objective**: Verify if backend responses match actual document content

---

## Test 1: Arabic Question (من هو رئيس اللجنة الفنية...)

### Question Sent
```
من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟
```
(Who is the president of the technical committee for heavy equipment maintenance in the production units in Qabis?)

### Actual Document Content (50-2.pdf)
- **Committee**: اللجنة الفنية لصيانة المعدات الثقيلة (Technical Committee for Heavy Equipment Maintenance)
- **Location**: قابس (Qabis) ✓
- **President**: محمد بن علي ✓
- **Members**: 
  - فيصل الجلاصي (رئيس مصلحة النقل والمعدات)
  - مريم بن عمر (رئيس قسم المراقبة الجودة)
  - ياسين الحداد (رئيس مصلحة المحاسبة)
  - أنيس بن علي (مدير الإنتاج)
- **Decision Number**: N° 002/2026

### Backend Response
```json
{
  "answer": "La réunion de la commission de contrôle de la direction administrative de Qabis...",
  "sources": [
    {"file_name": "GCT_notes_exemples_50-11.pdf", "score": 0.8110},
    {"file_name": "GCT_notes_exemples_50-35.pdf", "score": 0.8106"}
  ]
}
```

### Verdict: ❌ COMPLETELY WRONG

**Issues:**
1. **Retrieved wrong documents**: 50-11.pdf and 50-35.pdf (about administrative control commission)
2. **Retrieved wrong names**: "Amal Al-Daridi", "Balal Al-Daridi", etc.
3. **Response in wrong language**: Answered in French when question was in Arabic
4. **Missing correct document**: 50-2.pdf should be #1, but wasn't retrieved at all
5. **Encoding corruption**: Question displayed as "?? ?? ????" in response

---

## Analysis: Why is the Retrieval Wrong?

### What We Know From Diagnostics
1. **Document Similarity**: 50-2.pdf and 50-22.pdf are 99.17% similar in embedding space
2. **Language-Dependent Ranking**: 
   - Arabic queries: 50-2.pdf ranks #1
   - French queries: 50-22.pdf ranks #1
3. **Score Margin**: Extremely small (~0.00148 for French)

### Why Didn't 50-2.pdf Appear in Results?
The Arabic query should have retrieved 50-2.pdf (which it does in our diagnostics), but the backend returned 50-11.pdf and 50-35.pdf instead. This suggests:

1. **Top-K Mismatch**: The retriever may be using different `top_k` settings
2. **Collection Issue**: Might be querying wrong ChromaDB collection
3. **Model Loading Issue**: E5-small might not have loaded correctly on first call
4. **Scoring Transformation**: Score calculation might be inverted or different

---

## Critical Finding: System Not Performing as Designed

| Component | Status | Evidence |
|-----------|--------|----------|
| **Ingestion** | ✓ Working | 50-2.pdf is indexed (verified in ChromaDB) |
| **Document Storage** | ✓ Working | Content verified: محمد بن علي present |
| **Embeddings** | ? Unknown | E5-small loading slow (8GB RAM constraint) |
| **Retrieval** | ❌ FAILING | Returns wrong documents entirely |
| **LLM** | ❌ FAILING | Generates incorrect answer based on wrong docs |
| **Language Detection** | ❌ FAILING | Answered French query in French, Arabic in French |

---

## What SHOULD Happen

For the Arabic question "من هو رئيس اللجنة الفنية...":

1. ✓ Embed query with E5-small (with `query:` prefix)
2. ✓ Retrieve top-5 from ChromaDB using cosine similarity
3. ✓ **Expected #1 result**: 50-2.pdf (score > 0.8)
4. ✓ Extract context: "رئيس محمد بن علي"
5. ✓ Send to Mistral with context
6. ✓ Generate answer in Arabic (matching query language)
7. ✓ Return answer + sources (50-2.pdf, page 1)

**What Actually Happened**:
- ❌ Retrieved 50-11.pdf, 50-35.pdf (completely wrong documents)
- ❌ Extracted wrong names from wrong documents
- ❌ Generated French response instead of Arabic
- ❌ Sources don't match the question asked

---

## Next Steps to Diagnose

1. **Check retrieval directly** (bypass RAG layer):
   ```python
   from app.retrieval.retriever import retrieve
   results = retrieve("من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟", top_k=5)
   ```

2. **Verify ChromaDB collection**:
   - Count documents
   - Check if 50-2.pdf exists
   - Verify embeddings are 384-dim (e5-small)

3. **Check if models loaded correctly**:
   - E5-small model initialized?
   - Mistral loaded successfully?
   - Memory constraints causing truncation?

4. **Verify prompt construction**:
   - SYSTEM_PROMPT respecting language
   - Retrieved chunks being passed correctly
   - LLM receiving complete context

---

## Conclusion

**The backend is producing incorrect responses** that don't match the actual document content. The retrieval layer is returning completely different documents than what we verified exists in ChromaDB during our diagnostics. This is a **critical failure** that makes the RAG system unreliable.

**Status**: System NOT working as intended. User-visible failures prevent the AI assistant from providing correct answers.
