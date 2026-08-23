# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GCT AI Assistant — a local business AI assistant for Groupe Chimique Tunisien (GCT). A RAG system over ~50 French/Arabic administrative PDFs (GCT decision notes, referenced as "N° XXX/2026"). All working code lives in `backend/`; the repo root also has an empty `notes/` dir. Code, comments, and docstrings are in French.

**Stack**: Python 3.12, FastAPI, LangChain, Ollama (local LLM), ChromaDB, sentence-transformers. Pinned deps in `backend/requirements.txt`, config via pydantic-settings in `backend/app/core/config.py` reading `.env` (see `.env.example`).

## Project Constraints (non-negotiable)

- **`data/test_questions_v2.json` is a benchmark-only dataset.** It must never become the knowledge base; the backend must not depend on it, and the benchmark must remain independent of the production ingestion/RAG pipeline.
- **Never hardcode the 50 PDF filenames, decision numbers (`N° XXX/2026`), or benchmark questions** anywhere in production code. GCT employees must be able to add new PDFs without backend changes — ingestion must be data-driven (discover PDFs from `data/documents/`, track via the manifest).
- The 50 PDFs are a development/test dataset only.

## Commands

Run everything from `backend/`:

```bash
# Tests — run with the venv Python (pytest 7.4.3 installed there)
./venv/Scripts/python.exe -m pytest -q                                   # fast suite (34 pass, heavy tests skipped)
./venv/Scripts/python.exe -m pytest --run-heavy tests/test_retrieval_integration.py -q  # real ChromaDB + E5 (slow)
./venv/Scripts/python.exe -m pytest --run-heavy tests/test_ollama_integration.py -q     # real local LLM (slow)
./venv/Scripts/python.exe -m pytest --run-heavy tests/test_rag_integration.py -q        # full RAG (E5 + Ollama)
# ⚠ La machine a 8 Go de RAM : mistral (~5,1 Go) domine ; l'embedding
#   (multilingual-e5-small, ~0,12 Go) est léger. Ne pas lancer deux tests heavy
#   d'affilée ; `ollama stop mistral:latest` libère la RAM avant un test E5.

# Ingestion pipeline (E5 embeddings)
./venv/Scripts/python.exe scripts/ingest_documents.py --dry-run        # preview [NEW]/[MODIFIED]/[SKIP], no writes
./venv/Scripts/python.exe scripts/ingest_documents.py                  # real index (unchanged docs are SKIP'd)
./venv/Scripts/python.exe scripts/ingest_documents.py --force-reindex  # ignore manifest, rebuild everything

# Retrieval demo (real Arabic questions against the existing ChromaDB; no Ollama)
./venv/Scripts/python.exe scripts/test_retrieval.py                     # sample questions
./venv/Scripts/python.exe scripts/test_retrieval.py "une question"      # custom question

# Ollama connection test (generic prompt -> local LLM)
./venv/Scripts/python.exe scripts/test_ollama.py                        # model from config (mistral:latest)
./venv/Scripts/python.exe scripts/test_ollama.py qwen2.5-coder:7b       # explicit model

# Full RAG demo (retrieval -> grounded prompt -> Ollama -> answer + sources)
./venv/Scripts/python.exe scripts/test_rag.py                            # sample questions
./venv/Scripts/python.exe scripts/test_rag.py "une question"             # custom question

# Frontend (React + Vite, dans frontend/)
cd frontend && npm install                 # installer les dépendances (la 1ère fois)
npm run dev                                # serveur de dev sur http://127.0.0.1:5173
npm test                                   # tests frontend (Vitest + Testing Library)
npm run build                              # build de production -> frontend/dist/

# API REST (FastAPI, lazy : aucun modèle chargé au démarrage)
./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000   # start server
curl http://127.0.0.1:8000/api/v1/health                                # health
curl -X POST http://127.0.0.1:8000/api/v1/ask -H "Content-Type: application/json" \
     -d '{"question": "Quel est l'objet de la décision ?"}'              # ask (lent : charge E5 + mistral)
# Swagger : http://127.0.0.1:8000/docs

# Analysis/benchmark scripts (each inserts its parent into sys.path itself)
python scripts/benchmark_embeddings.py      # embedding model benchmark (R@1/3/5, MRR) — production benchmark, do not modify
./venv/Scripts/python.exe scripts/benchmark_embedding_candidates.py  # experimental candidate comparison (e5-large/small/MiniLM; NOT production)
python scripts/verify_questions_v2.py       # validates test_questions_v2.json against PDFs
python scripts/extract_decision_numbers.py  # scans PDFs for N° XXX/2026, writes data/decision_numbers.json
python scripts/analyze_pdfs.py              # dump all PDF text to stdout
```

**Environment note**: `backend/venv/` has the runtime deps (chromadb 1.5.9, sentence-transformers, pypdf, numpy, ollama 0.6.2, fastapi 0.115.6) and pytest 7.4.3 (versions match `requirements.txt`, which was updated to pin the installed working versions — e.g. `ollama==0.6.2` for the `Client` API, `fastapi==0.115.6` because older FastAPI TestClient breaks with `httpx 0.28`).

**Embedding model (migrated to e5-small)**: the single config source is `settings.embedding_model` (`EMBEDDING_MODEL` in `.env`) = `intfloat/multilingual-e5-small` (384-dim, ~0.12 Go). `E5EmbeddingService()` defaults to it, so **ingestion and retrieval use the same model**. Active collection: `gct_documents_v2` (384-dim, e5-small index). **Fallback `gct_documents` (1024-dim, e5-large index) is kept intact** — rollback = set `settings.chroma_collection_name`/`CHROMA_COLLECTION_NAME` back to `gct_documents` (config-only, no reindex needed). To reindex into a fresh collection with the current model: `scripts/ingest_documents.py --force-reindex --collection <name>`. Installed versions diverge from other pins (e.g. chromadb 0.4.22). The global `python` also has pytest but **no chromadb/pydantic_settings**, so real-DB work must run under the venv. **Ollama server**: running on `http://localhost:11434` with `mistral:latest` and `qwen2.5-coder:7b` installed. The machine has only **8 Go RAM** — E5-large (~2–3 Go) and a resident LLM (~5 Go) can't coexist; tests needing real models are marked `heavy` and skipped by default. Don't change dependency pins just to fix an environment gap — report it instead.

## Migration & Rollback (embedding model)

- **Changer de modèle d'embedding implique de REBÂTIR l'index** (les dimensions/espaces vectoriels changent). La procédure : modifier `EMBEDDING_MODEL` → `python scripts/ingest_documents.py --force-reindex --collection <nom_v2>` → vérifier la dimension (`chromadb` : `len(emb[0]) == dim attendue`) → basculer `CHROMA_COLLECTION_NAME` → re-tester.
- **Rollback** : garder l'ancienne collection (ex: `gct_documents`, 1024-dim) et repasser `CHROMA_COLLECTION_NAME` dessus — changement de configuration uniquement, aucun reindex.

**Ollama — réglages mémoire mesurés / recommandés (PAS appliqués automatiquement)** :
- **`num_ctx` : NE PAS descendre sous 4096.** Mesuré : le prompt RAG complet (system + 5 chunks + question) fait **~3198 tokens** (les 5 chunks arabes/français seuls ≈ 2743 tokens) → `num_ctx=2048` TRONQUE le contexte (perte de chunks) = réponse non fiable. `4096` est le minimum sûr pour `top_k=5`.
- **`keep_alive="1m"` (par requête) : sûr et vérifié** — mistral se décharge ~1 min après la réponse, libérant ~5 Go entre requêtes.
- **Variables serveur recommandées (requièrent un redémarrage d'Ollama, PAS appliquées)** : `OLLAMA_KEEP_ALIVE=1m`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`.
- La génération sur cette machine 8 Go est limitée par le paging (~10-17 min /ask) ; le seul vrai correctif structurel serait un LLM plus petit (milestone futur, nécessite approbation + téléchargement). GPU offload non viable (iGPU Intel Iris Xe 1 Go).

## Architecture

There are **two parallel, disconnected code paths** — be careful which one you're working in:

1. **Analysis/benchmark path (working)**: `app/utils/pdf_extractor.py` exposes `PDFExtractor`, used directly by every `scripts/*.py`. Scripts do one-off tasks: extract PDF text, summarize, verify benchmark questions against document content, and benchmark embedding models (`scripts/benchmark_embeddings.py`).

2. **Ingestion pipeline (working)**: `app/ingest/` holds the pipeline: `clean_text` (unicode/whitespace normalization) → `chunk_text` (overlapping **word** chunks, chunk_size 500/overlap 50) → `build_chunks` (in `chunker.py`; enriches each chunk with `chunk_id = {doc_id}_p{page}_c{index}`, doc_id, file_name, file_path, page_number; skips empty/`requires_ocr` pages) → `E5EmbeddingService` (sentence-transformers, `settings.embedding_model` = `multilingual-e5-small`, E5 `passage:` prefix) → `ChromaStore` (cosine HNSW, collection ids `{doc_id}:{chunk_id}`, metadata derived from the chunks), with `IngestionManifest` (sha256) tracking indexed files to avoid reindexing. **`IngestionService` (`app/ingest/service.py`) est l'implémentation UNIQUE d'ingestion d'un document** (statuts indexed/updated/skipped/ocr_required/failed) — utilisée par l'API `POST /api/v1/documents` ET par le CLI `scripts/ingest_documents.py` (qui découvre `data/documents/**/*.pdf`, SKIP inchangés, réindexe les modifiés). Config : `documents_dir`, `ingestion_manifest_path` dans `settings`. The deleted pre-refactor modules survive only as `.pyc` files in `__pycache__` (e.g. `manager`, `ingestion_service`) — don't reference them.

3. **Retrieval layer (working)**: `app/retrieval/retriever.py` — `Retriever` class + `retrieve(query, top_k=5)` convenience (lazy shared instance → E5 model loads once per process). Pipeline: validate non-empty question → embed with E5 **`query:`** prefix (index side used `passage:`) → `ChromaStore.query(...)` on collection `gct_documents` → format results. **Score semantics are explicit and must not be conflated**: ChromaDB returns a `distance` (smaller = better; for the configured cosine space `distance = 1 − cosine_similarity`), and the retriever also returns `score` = `1 − distance` (larger = better). Each result carries `text`, `score`, `distance`, `doc_id`, `file_name`, `file_path`, `page_number`, `chunk_index`, `chunk_id`. `ChromaStore` gained `query()` and `space()` for this. Demo: `scripts/test_retrieval.py`. **This is the production retrieval layer and is intentionally separate from the benchmark** (which does full-document in-memory cosine in `scripts/benchmark_embeddings.py`).

4. **LLM layer (working)**: `app/llm/ollama_client.py` — `OllamaClient` with `generate(prompt, system_prompt=None, temperature=0.7, num_predict=None)` and `list_models()`. **Deliberately domain-agnostic**: knows nothing about PDFs/ChromaDB/retrieval/benchmark. Uses the installed `ollama` (0.6.2) `Client` API against `settings.ollama_base_url` / `settings.ollama_model` (default `mistral:latest`, detected on the local server). Errors are classified: `OllamaError` (HTTP/model error) vs `OllamaUnavailableError` (server down). Demo: `scripts/test_ollama.py`.

5. **RAG layer (working, unit-tested + E2E proven)**: `app/rag/service.py` — `RAGService.answer(question, top_k=5, temperature=0.2, max_tokens=512) -> {question, answer, sources}`. Wires the EXISTING `app.retrieval.retrieve(...)` (lazy shared retriever) + `OllamaClient.generate(...)` (config model).

6. **API layer (working)**: `main.py` (FastAPI) + `app/api/{schemas,routes}.py`. Endpoints: `GET /api/v1/health`, `GET /api/v1/health/ollama`, `GET /api/v1/auth/verify`, `POST /api/v1/ask` (`{question, top_k, temperature, max_tokens}` → `{question, answer, sources}`), `POST /api/v1/documents` (upload PDF → ingestion via `IngestionService`, retourne `{file_name, status, pages, chunks, message, ocr_pages}` ; statuts : indexed/updated/skipped/ocr_required/failed). `python-multipart` est requis pour l'upload (installé dans le venv).

## Authentification (locale, légère)

- **Rôles** : `user` (chat via `POST /api/v1/ask`), `admin` (ingestion via `POST /api/v1/documents`). Endpoints `health` publics.
- **Mécanisme** : Bearer token (`Authorization: Bearer <token>`). `app/api/auth.py` : `require_user` / `require_admin` (dépendances FastAPI), `verify` (401 token invalide/absent, 403 rôle insuffisant).
- **Configuration** : `settings.auth_enabled` (défaut True), `settings.auth_admin_token`, `settings.auth_user_tokens` (séparés par des virgules) — via `.env` (gitignoré), jamais dans le code. `auth_enabled=false` désactive l'auth (développement local). Tokens de dev dans `backend/.env` : `dev-admin-gct` / `dev-user-gct`.
- **Frontend** : écran de connexion (token) → `GET /api/v1/auth/verify` → rôle ; token stocké dans `localStorage` (`gct_token`) ; bouton « Documents » visible uniquement pour `admin` ; bouton « Déconnexion ».
- **Tests** : la `conftest` désactive l'auth pour les tests existants (`AUTH_ENABLED=false`) ; `tests/test_auth.py` l'active via monkeypatch (401/403/rôles). **No model is loaded at startup** — `routes._get_service()` creates `RAGService` lazily on first `/ask` (E5 then mistral load on demand). Error mapping: validation → 400, `RAGRetrievalError` → 500, `RAGUnavailableError` → 503, `RAGGenerationError` → 502, unexpected → 500 (no tracebacks). CORS disabled by default (`settings.cors_origins` empty); enable via `CORS_ORIGINS`. Swagger at `/docs`. `fastapi==0.115.6` installed (must be ≥0.115: older TestClient breaks with `httpx 0.28`). `app/rag/prompts.py` holds the anti-hallucination `SYSTEM_PROMPT` (answer only from context, same language as question, cite source + page, explicit "not found" message) and the grounded `build_user_prompt(question, results)` (CONTEXT blocks → QUESTION → RÉPONSE). Empty/no results → `NOT_FOUND_MESSAGE` WITHOUT calling Ollama. Errors mapped to `RAGRetrievalError` / `RAGUnavailableError` / `RAGGenerationError` (clean messages, no tracebacks). Sources deduped by `chunk_id`; only `file_name`, `page_number`, `score`, `chunk_id` exposed. Optional `min_score` threshold (default `None` = disabled — documents are near-identical, don't add an arbitrary threshold). Demo: `scripts/test_rag.py`. **Real E2E requires E5 + mistral resident simultaneously → on this 8 Go machine it works but takes ~7–8 min under RAM thrashing (E5 ~2,2 Go + mistral ~5,1 Go + apps); free RAM (`ollama stop mistral:latest`) before and after.**

Other `app/` subpackages (`models`, `services`, `vector_store`, `embeddings`) are **empty docstring placeholders** — the README describes them, but they aren't implemented. `config.py` defaults `ollama_embedding_model` to `nomic-embed-text`, which is unrelated to the E5 model the ingest pipeline actually uses.

## Frontend (React + Vite)

- **Structure** : `frontend/` — `src/main.jsx` (montage React), `src/App.jsx` (chat : messages, sources, états), `src/api.js` (client API), `src/styles.css`, `src/App.test.jsx` (tests Vitest), `src/test/setup.js`.
- **Connexion au backend** : `src/api.js` lit `VITE_API_BASE_URL` (`.env` / `.env.example`), défaut `http://127.0.0.1:8000`, et appelle `POST /api/v1/ask` (`{question, top_k, temperature, max_tokens}` → `{question, answer, sources}`). Les sources affichent `file_name` + `page_number` uniquement (pas de chunk_id/score → pas de détails internes).
- **Ajout de document** : bouton « Documents » dans l'en-tête → panneau d'upload → `POST /api/v1/documents` (multipart `file`). L'UI affiche « Document ajouté — X pages / Y chunks », les erreurs, et le message dédié si OCR requis. Aucun vecteur/chunk_id/chemin interne n'est exposé.
- **CORS** : activé par défaut pour le serveur Vite (`http://localhost:5173`, `http://127.0.0.1:5173`) via `settings.cors_origins` (configurable). Le frontend ne fonctionne pas sans backend lancé.
- **RTL** : les messages arabes sont affichés avec `dir="rtl"` (détection automatique).
- **Tests frontend** : `cd frontend && npm test` (Vitest + jsdom, fetch mocké). Les tests backend (`./venv/Scripts/python.exe -m pytest`) sont indépendants du frontend.

## Ingestion — cycle de vie & comportement

- **Cycle** : `POST /api/v1/documents` (ou `scripts/ingest_documents.py`) → validation (extension `.pdf`, non vide, magic `%PDF`, ≤100 Mo) → sauvegarde dans `documents_dir` → `IngestionService.ingest_document` : extraction → **OCR si page scannée** → nettoyage → chunking → embeddings e5-small (`passage:`) → ChromaDB `gct_documents_v2` → manifest (sha256). **Une seule implémentation** (API + CLI).
- **Statuts** : `indexed` (nouveau), `updated` (contenu modifié/force), `skipped` (déjà indexé, inchangé), `ocr_required` (aucun texte extractible — non indexé, message clair), `failed` (extraction/embedding/écriture ChromaDB).
- **Échecs** : document `failed` → HTTP 422 (message propre) ; erreur inattendue du service → HTTP 500 propre ; fichier trop volumineux → 413 ; non-PDF/vide → 400. En cas d'échec d'écriture ChromaDB, le **manifest n'est PAS mis à jour** (index + manifest restent cohérents). Le fichier reste dans `documents_dir` (non indexé).
- **Dédoublonnage** : basé sur le manifest (chemin absolu + sha256). Même nom re-uploadé avec le même contenu → `skipped` ; contenu différent → `updated` (réindexation). Contenu identique sous un autre nom → nouveau document (sémantique existante).
- **Concurrence** : les uploads sont sérialisés par un verrou (manifest + ChromaDB non thread-safe).
- **Données** : `documents_dir=./data/documents`, `chroma_persist_directory=./data/chroma`, `ingestion_manifest_path=./data/ingestion_manifest.json`.

## OCR (pages scannées)

- **Architecture** : `app/ingest/ocr.py` (`OCREngine`) — Tesseract local via `pytesseract`. `DocumentExtractor` détecte une page `requires_ocr` (texte vide ou <30 car.), la rend en image (PyMuPDF) puis appelle l'OCR. En cas de succès le texte remplace le vide (`requires_ocr=False`) ; en échec, la page reste `requires_ocr` et est comptée dans `ocr_pages` (pages en échec).
- **Langues** : `ara+fra+eng` (`settings.ocr_languages`). Les traineddata vivent dans `backend/data/tessdata` (`ara`, `eng`, `fra`, `osd`).
- **Dépendances** : binaire Tesseract installé via winget (`UB-Mannheim.TesseractOCR`) ; pip : `pytesseract`, `pymupdf`, `Pillow`. Ressources : ~60 Mo installés, RAM ~200-400 Mo (léger).
- **Comportement** : PDF entièrement scanné + OCR réussi → `indexed` (plus jamais bloqué à `ocr_required`) ; partiel → `indexed`/`updated` + `ocr_pages`>0 + numéros de pages en échec dans `message` ; tout en échec → `ocr_required`. Metadata identiques aux chunks normaux (page_number préservé) ; aucun détail OCR exposé dans les réponses RAG.
- **Tests** : le moteur OCR est mocké (`FakeOCREngine`) dans les tests unitaires (la suite ne dépend PAS de Tesseract). Test réel : `./venv/Scripts/python.exe -m pytest --run-heavy tests/test_ocr_integration.py -q` (ignoré si Tesseract indisponible).

## Docker (packaging)

- **`docker-compose.yml`** (racine) — 3 services : `ollama` (LLM local, volume `ollama-models:/root/.ollama`), `backend` (FastAPI + ChromaDB embarquée + Tesseract OCR, volumes `data:/app/data` et `hf-cache:/root/.cache/huggingface`), `frontend` (nginx : build React + proxy `/api` → backend, port `8080:80`).
- **Build** : `docker compose build` puis `docker compose up -d`. Premier démarrage : le conteneur backend **peuple le volume `data` depuis l'image** (base de connaissances existante : ChromaDB, documents, manifest, tessdata — aucun rebuild/migration). Lancer `docker compose exec ollama ollama pull mistral:latest` (modèle LLM) ; e5-small se télécharge au 1er usage (volume `hf-cache`).
- **Réseau/config** : `OLLAMA_BASE_URL=http://ollama:11434`, `TESSERACT_CMD=/usr/bin/tesseract`, `CHROMA_COLLECTION_NAME=gct_documents_v2` via `environment`. Auth injectée via variables compose (`AUTH_ADMIN_TOKEN`, `AUTH_USER_TOKENS`, `.env` racine — défauts dev, à changer).
- **Frontend** : chemins relatifs `/api` (proxy Vite en dev via `vite.config.js`, proxy nginx en Docker). `VITE_API_BASE_URL` vide par défaut (override possible).
- **Startup/health** : backend attend ollama healthy ; frontend attend backend healthy (healthcheck `/api/v1/health`).
- **RAM 8 Go** : le conteneur ollama partage la RAM hôte ; ne pas lancer de builds/tests lourds pendant qu'un modèle est résident.

## Smoke test manuel

1. `cd backend && ./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`
2. `curl -F "file=@chemin.pdf;type=application/pdf" http://127.0.0.1:8000/api/v1/documents` → statut `indexed`.
3. Vérifier : `gct_documents_v2` count + dim 384, metadata, manifest.
4. `POST /api/v1/ask` → réponse ancrée + sources.
5. **⚠ 8 Go de RAM** : le test complet (upload + ask) nécessite ~5,5 Go (e5-small ~0,5 + mistral ~5,1). Si la RAM disponible est insuffisante (autres applications ~6,4 Go), ne pas forcer — vérifier l'ingestion isolément (temp dirs via env : `DOCUMENTS_DIR`, `CHROMA_PERSIST_DIRECTORY`, `INGESTION_MANIFEST_PATH`, `CHROMA_COLLECTION_NAME`).

## Data & Benchmark Format

- `data/documents/` — 50 PDFs named `GCT_notes_exemples_50-{N}.pdf` (gitignored). `doc_id` convention = filename without extension.
- `data/chroma/` — ChromaDB persistence (gitignored).
- `data/test_questions_v2.json` — 30 Arabic benchmark questions; each is `{id, question, expected_pdf, language}` (e.g. question references a decision "القرار رقم N° 006/2026" and `expected_pdf: "GCT_notes_exemples_50-6.pdf"`). Template: `test_questions_template.json`; cleaned variant: `test_questions_v2_corrected.json`. Question `id` maps to the `N` in the expected PDF filename.
- `data/ingestion_manifest.json` — 50 records keyed by absolute file path.
- `data/decision_numbers.json`, `pdf_content.json`, `pdf_content_analysis.txt` — outputs of the analysis scripts.
