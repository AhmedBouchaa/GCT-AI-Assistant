"""Routes de l'API REST de l'assistant RAG GCT.

Aucun modèle n'est chargé au démarrage : le service RAG est créé paresseusement
à la première requête /ask (E5 au premier retrieval, mistral au premier appel
Ollama). Les erreurs applicatives sont mappées en codes HTTP propres, sans
traceback exposé.
"""
import logging
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query

from app.api.auth import require_admin, require_user
from app.api.schemas import (
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    DocumentIngestResponse,
    HealthResponse,
)
from app.generation import (
    GenerationOllamaError,
    GenerationRetrievalError,
    GenerationService,
    GenerationUnavailableError,
)
from app.ingest import IngestionService
from app.llm import OllamaClient, OllamaError, OllamaUnavailableError
from app.rag import (
    RAGGenerationError,
    RAGRetrievalError,
    RAGService,
    RAGUnavailableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

_rag_service: Optional[RAGService] = None
_ingestion_service: Optional[IngestionService] = None
_generation_service: Optional[GenerationService] = None

# Routeur de diagnostic : existe uniquement en dev pour prouver quelle
# process Python sert réellement le trafic HTTP (PID / exécutable / cwd)
# et quelles settings ChromaDB/embedding ce process a chargé. Aucun modèle
# n'est chargé ici ; n'interfère pas avec le flux RAG.
debug_router = APIRouter(prefix="/api/debug")

# Taille maximale d'un PDF uploadé (octets).
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

# Sérialise les uploads : sauvegarde + ingestion d'un document à la fois.
_ingestion_lock = threading.Lock()


def _generate_request_id() -> str:
    """Génère un ID unique pour tracer les requêtes."""
    return str(uuid.uuid4())[:8]


def _get_service() -> RAGService:
    """Retourne le service RAG partagé (créé paresseusement, jamais au démarrage)."""
    global _rag_service
    if _rag_service is None:
        logger.info("Creating new RAGService instance")
        _rag_service = RAGService()
    return _rag_service


def _get_generation_service() -> GenerationService:
    """Retourne le service de génération partagé (créé paresseusement)."""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service


def _get_ingestion_service() -> IngestionService:
    """Retourne le service d'ingestion partagé (créé paresseusement)."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Indique que l'API est vivante (aucun modèle chargé). Public."""
    return HealthResponse(status="ok")


@debug_router.post("/ask-debug", tags=["debug"])
def ask_debug(payload: AskRequest, _role: str = Depends(require_user)) -> dict:
    """Debug endpoint comparing direct retriever vs RAG service vs API results.

    Returns raw diagnostic data showing potential divergence between layers.
    Helps identify if different components are seeing different documents.
    """
    from app.retrieval import retrieve

    request_id = _generate_request_id()
    logger.info(f"[{request_id}] Debug /ask-debug endpoint called")

    try:
        # Layer 1: Direct retriever call
        logger.debug(f"[{request_id}] Calling retrieve() directly...")
        retriever_results = retrieve(payload.question, top_k=5)
        retriever_sources = [
            {"file_name": r.get("file_name"), "score": r.get("score")}
            for r in retriever_results[:3]
        ]
        logger.debug(f"[{request_id}] Direct retriever returned: {retriever_sources}")

        # Layer 2: RAG service call
        logger.debug(f"[{request_id}] Calling RAGService.answer()...")
        rag_service = _get_service()
        rag_results = rag_service.answer(
            question=payload.question,
            top_k=5,
        )
        rag_sources = [
            {"file_name": s.get("file_name"), "score": s.get("score")}
            for s in rag_results.get("sources", [])[:3]
        ]
        logger.debug(f"[{request_id}] RAG service returned: {rag_sources}")

        # Compare results
        retriever_files = {s["file_name"] for s in retriever_sources}
        rag_files = {s["file_name"] for s in rag_sources}
        match = retriever_files == rag_files

        logger.info(
            f"[{request_id}] Debug results: retriever={retriever_files}, "
            f"rag={rag_files}, match={match}"
        )

        return {
            "request_id": request_id,
            "question": payload.question,
            "direct_retriever": retriever_sources,
            "rag_service_sources": rag_sources,
            "sources_match": match,
            "rag_service_answer": rag_results.get("answer")[:200] if rag_results.get("answer") else "",
        }
    except Exception as exc:
        logger.exception(f"[{request_id}] Error in debug endpoint")
        raise HTTPException(
            status_code=500,
            detail=f"Debug endpoint error: {exc}"
        )


@debug_router.get("/runtime", tags=["debug"])
def debug_runtime() -> dict:
    """Identité du processus servant réellement le trafic HTTP (diagnostic temporaire).

    Retourne (JSON) : pid, sys.executable, cwd, retriever module path,
    collection name, embedding model, embedding dimension et Chroma path
    tels que le process API les a chargés. Ne modifie aucun modèle.
    """
    import inspect
    import os
    import sys

    from app.core.config import settings as _settings
    from app.retrieval import retriever as _retriever_mod

    eff_retriever = getattr(_retriever_mod, "_default_retriever", None)

    return {
        "pid": os.getpid(),
        "sys_executable": sys.executable,
        "cwd": os.getcwd(),
        "retriever_module_file": os.path.abspath(inspect.getfile(_retriever_mod)),
        "retriever_default_instance": repr(eff_retriever),
        "settings": {
            "chroma_collection_name": _settings.chroma_collection_name,
            "embedding_model": _settings.embedding_model,
            "embedding_dimension": _settings.embedding_dimension,
            "chroma_persist_directory": _settings.chroma_persist_directory,
            "ollama_base_url": _settings.ollama_base_url,
            "ollama_model": _settings.ollama_model,
        },
    }


@router.get("/auth/verify", tags=["auth"])
def auth_verify(role: str = Depends(require_user)) -> dict:
    """Valide le token et retourne le rôle (``user`` ou ``admin``)."""
    return {"authenticated": True, "role": role}


@router.get("/health/ollama", response_model=HealthResponse, tags=["system"])
def health_ollama() -> HealthResponse:
    """Vérifie que le serveur Ollama local est joignable (appel HTTP léger)."""
    client = OllamaClient()
    try:
        client.list_models()
    except (OllamaUnavailableError, OllamaError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama injoignable : {exc}",
        )
    return HealthResponse(status="ok", model=client.model)


@router.post("/ask", response_model=AskResponse, tags=["rag"])
def ask(payload: AskRequest, _role: str = Depends(require_user)) -> AskResponse:
    """Répond à une question à partir des documents indexés (RAG local).

    Authentification requise (token user ou admin). Délègue entièrement à
    ``RAGService.answer`` (aucune logique RAG dupliquée).
    """
    request_id = _generate_request_id()
    logger.info(f"[{request_id}] Incoming /ask request with question: {payload.question[:100]}...")

    try:
        logger.debug(f"[{request_id}] Calling RAGService.answer() with top_k={payload.top_k}")
        result = _get_service().answer(
            question=payload.question,
            top_k=payload.top_k,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
        logger.info(f"[{request_id}] RAGService returned {len(result.get('sources', []))} sources")
        for i, source in enumerate(result.get('sources', [])[:3], 1):
            logger.debug(f"[{request_id}]   {i}. {source.get('file_name')}: score={source.get('score'):.6f}")
    except ValueError:
        logger.warning(f"[{request_id}] Validation error: empty question")
        raise HTTPException(status_code=400, detail="Question invalide (vide).")
    except RAGRetrievalError as exc:
        logger.error(f"[{request_id}] Retrieval error: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de récupération des documents : {exc}",
        )
    except RAGUnavailableError as exc:
        logger.error(f"[{request_id}] Ollama unavailable: {exc}")
        raise HTTPException(status_code=503, detail=str(exc))
    except RAGGenerationError as exc:
        logger.error(f"[{request_id}] Generation error: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # sécurité : message propre, pas de traceback
        logger.exception(f"[{request_id}] Unexpected error in /ask endpoint")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur.")

    logger.debug(f"[{request_id}] Returning AskResponse with answer ({len(result.get('answer', ''))} chars)")
    return AskResponse(**result)


# Routeur dédié pour l'endpoint de génération, monté sur le préfixe « /api »
# (et non « /api/v1 ») pour respecter le chemin demandé : POST /api/chat.
chat_router = APIRouter(prefix="/api")


@chat_router.post("/chat", response_model=ChatResponse, tags=["rag"])
def chat(payload: ChatRequest, _role: str = Depends(require_user)) -> ChatResponse:
    """Répond à une question via la couche de génération RAG (retrieve -> Ollama).

    Authentification requise (token user ou admin). Délègue entièrement à
    ``GenerationService.answer`` : réutilise la récupération existante
    (``app.retrieval.retrieve``) et le client Ollama local. Aucune logique RAG
    dupliquée ici.
    """
    try:
        result = _get_generation_service().answer(
            question=payload.question,
            top_k=payload.top_k,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Question invalide (vide).")
    except GenerationRetrievalError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de récupération des documents : {exc}",
        )
    except GenerationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except GenerationOllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # sécurité : message propre, pas de traceback
        raise HTTPException(status_code=500, detail="Erreur interne du serveur.")

    return ChatResponse(**result)


@router.post("/documents", response_model=DocumentIngestResponse, tags=["documents"])
def upload_document(
    file: UploadFile = File(...),
    _role: str = Depends(require_admin),
) -> DocumentIngestResponse:
    """Ajoute un PDF à la base de connaissances (ingestion réutilisée).

    Authentification ADMIN requise. Valide le fichier (PDF, non vide), le
    sauvegarde dans le répertoire des documents, puis le transmet au pipeline
    d'ingestion existant (extraction -> OCR -> chunking -> embeddings e5-small
    -> ChromaDB -> manifest). Aucune logique d'ingestion n'est dupliquée ici.
    """
    # 1) Validation du fichier
    file_name = Path(file.filename or "").name  # nom nettoyé (anti chemin)
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Seuls les fichiers PDF sont acceptés.",
        )

    # Lecture bornée : évite de charger un fichier énorme en mémoire.
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Le fichier n'est pas un PDF valide.")

    # 2) Sauvegarde sécurisée + ingestion (sérialisées)
    service = _get_ingestion_service()
    try:
        with _ingestion_lock:
            target = service.documents_dir / file_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            result = service.ingest_document(target)
    except Exception as exc:  # sécurité : erreur propre, pas de traceback
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'ingestion du document : {exc}",
        )

    if result["status"] == "failed":
        raise HTTPException(status_code=422, detail=result["message"])

    return DocumentIngestResponse(**result)


@router.get("/documents/{file_name}/content", tags=["documents"])
def get_document_content(
    file_name: str,
    page_number: Optional[int] = Query(None),
    _role: str = Depends(require_user),
) -> dict:
    """Récupère le contenu d'une page d'un document PDF.

    Authentification requise (token user ou admin).

    Args:
        file_name: Nom du fichier PDF (e.g., "GCT_notes_exemples_50-2.pdf")
        page_number: Numéro de la page à récupérer (optionnel, 1-indexed)

    Returns:
        Dictionnaire contenant:
        - file_name: Nom du fichier
        - page_number: Numéro de la page
        - total_pages: Nombre total de pages
        - content: Texte extrait de la page
    """
    from app.utils.pdf_extractor import PDFExtractor
    from app.core.config import settings

    request_id = _generate_request_id()
    logger.info(f"[{request_id}] Retrieving content for {file_name} (page {page_number})")

    # Validation du nom de fichier (anti path traversal)
    if "/" in file_name or "\\" in file_name or file_name.startswith("."):
        logger.warning(f"[{request_id}] Suspicious file_name: {file_name}")
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    # Chemin sécurisé du fichier
    documents_dir = Path(settings.documents_dir)
    file_path = documents_dir / file_name

    # Vérifier que le fichier existe et est bien dans documents_dir
    try:
        file_path = file_path.resolve()
        documents_dir = documents_dir.resolve()
        if not str(file_path).startswith(str(documents_dir)):
            logger.warning(f"[{request_id}] Path traversal attempt: {file_path}")
            raise HTTPException(status_code=403, detail="Accès refusé.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{request_id}] Path resolution error: {exc}")
        raise HTTPException(status_code=400, detail="Chemin invalide.")

    if not file_path.exists():
        logger.warning(f"[{request_id}] File not found: {file_path}")
        # Fournir une liste de fichiers disponibles pour aider au débogage
        available_files = sorted([f.name for f in documents_dir.glob("*.pdf")])[:5]
        available_str = ", ".join(available_files) if available_files else "aucun"
        detail = f"Fichier '{file_name}' non trouvé. Fichiers disponibles: {available_str}..."
        raise HTTPException(status_code=404, detail=detail)

    try:
        extractor = PDFExtractor(str(documents_dir))
        pages = extractor.extract_text_from_pdf(file_path)
        total_pages = len(pages)

        # Si aucun numéro de page spécifié, retourner la première
        target_page = page_number if page_number is not None else 1

        # Vérifier que le numéro de page est valide (1-indexed)
        if target_page < 1 or target_page > total_pages:
            logger.warning(f"[{request_id}] Invalid page number: {target_page}/{total_pages}")
            raise HTTPException(
                status_code=400,
                detail=f"Numéro de page invalide. Le document contient {total_pages} pages.",
            )

        page_content = pages[target_page - 1]["text"]

        logger.info(f"[{request_id}] Returned page {target_page}/{total_pages} ({len(page_content)} chars)")
        return {
            "file_name": file_name,
            "page_number": target_page,
            "total_pages": total_pages,
            "content": page_content,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"[{request_id}] Error retrieving document content: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la lecture du document : {exc}",
        )
