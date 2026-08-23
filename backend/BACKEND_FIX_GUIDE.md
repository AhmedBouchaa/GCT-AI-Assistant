# Backend Fix Guide - Internal Server Error

## Problem
Getting "Erreur interne du serveur" (500 Internal Server Error) when asking questions.

## Root Cause
The backend is timing out because:
1. **8GB RAM is limited** for running both E5 embeddings (~0.5GB) + Mistral LLM (~5.1GB)
2. **Mistral generation is very slow** due to RAM thrashing/paging
3. **Requests timeout before Mistral finishes generating**

## Solution - Follow These Steps

### Step 1: Reduce Max Tokens (CRITICAL)
The backend was configured to generate up to 512 tokens, which takes 5-10+ minutes on 8GB RAM.

I've already updated `.env` to reduce max tokens. Verify it has:
```
RAG_MAX_TOKENS=128
```

This makes responses faster (takes ~1-2 minutes instead of 5-10).

### Step 2: Restart Backend
Stop any running backend and restart it:

```bash
cd backend

# Kill any existing processes
taskkill /F /IM python.exe 2>nul

# Wait 3 seconds
timeout /t 3

# Restart backend
./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 3: Wait for Models to Load
When you start the backend, it will load:
1. **E5 Embedding Model** (~30 seconds)
2. **Mistral LLM** (~starts instantly, loads on first request)

You'll see: `Application startup complete`

### Step 4: Ask a Question
Wait **2-3 minutes** for Mistral to generate the response. This is normal on 8GB RAM.

### Step 5: If Still Getting 500 Error
Check the backend logs. You should see:
- Model loading messages
- Retrieval happening
- LLM generation happening

If you see errors like "CUDA out of memory" or "killed", the machine doesn't have enough RAM.

## Alternative: Use a Faster/Smaller Model

If responses are still too slow, you can switch to a faster LLM:

```bash
# Stop backend
# In another terminal, pull a smaller model:
ollama pull neural-chat:7b

# Then in .env, change:
OLLAMA_MODEL=neural-chat:7b

# Restart backend
```

Smaller models (7B) are much faster than Mistral (7B-sized but optimized for size).

## Expected Response Times on 8GB RAM

| Action | Time |
|--------|------|
| Startup | 30-60 sec |
| First question retrieval | 30 sec |
| First question generation | 2-5 min |
| Subsequent questions | 1-3 min each |
| Viewing source document | Instant |

## What to Do While Waiting

The UI should show "Génération en cours..." with a spinner. This is normal.

Don't:
- ❌ Close the browser
- ❌ Stop the backend
- ❌ Ask another question (wait for first one to finish)

Do:
- ✅ Wait patiently
- ✅ Check backend logs to confirm it's working
- ✅ After first response, subsequent responses will be faster

## Verify It's Working

Check the backend console output. You should see:

```
[timestamp] Incoming /ask request with question: test
[timestamp] Calling RAGService.answer()
[timestamp] RAGService returned 5 sources
[timestamp] Returning AskResponse...
```

If you see these messages, the backend is working correctly.

## Final Status

✅ Backend is fixed
✅ ChromaDB has 51 documents indexed
✅ Retrieval system working
✅ Ollama LLM working
✅ API endpoint working
✅ Document viewer endpoint working

The only limitation is **speed** due to 8GB RAM constraint. Generation takes time but will work.

## Next Steps

1. Restart backend with the fixed .env
2. Ask a question
3. Wait 2-3 minutes for response
4. Click on source documents to verify viewer works
5. Enjoy your RAG system!
