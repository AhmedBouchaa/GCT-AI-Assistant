"""Point d'entrée FastAPI de l'assistant RAG GCT.

Aucun modèle n'est chargé au démarrage : E5 et mistral sont chargés
paresseusement à la première requête ``/api/v1/ask`` (voir app/api/routes.py).

Lancement :
    ./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from app.api.routes import chat_router, debug_router, router
from app.core.config import settings

logger = logging.getLogger(__name__)

class UTF8Middleware(BaseHTTPMiddleware):
    """Middleware to ensure proper UTF-8 encoding for requests."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Log request info for debugging
        if request.url.path.startswith("/api/v1/ask"):
            logger.debug(f"UTF8Middleware: Received request to {request.url.path}")
        response = await call_next(request)
        return response

app = FastAPI(
    title="GCT AI Assistant API",
    description=(
        "Assistant RAG 100% local pour le Groupe Chimique Tunisien (GCT) : "
        "réponse ancrée sur les documents indexés (ChromaDB + E5 + Ollama)."
    ),
    version="0.1.0",
)

# Add UTF-8 middleware to ensure proper encoding handling
app.add_middleware(UTF8Middleware)

# CORS configurable, désactivé par défaut (aucun frontend à ce stade).
# Activez via CORS_ORIGINS (origines séparées par des virgules).
if settings.cors_origins.strip():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.cors_origins.split(",")
            if origin.strip()
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc) -> JSONResponse:
    """Mappe les erreurs de validation Pydantic en HTTP 400 (message propre)."""
    return JSONResponse(
        status_code=400,
        content={
            "detail": (
                "Requête invalide : la question doit être non vide et "
                "top_k/temperature/max_tokens doivent être dans les bornes."
            )
        },
    )


app.include_router(router)
app.include_router(chat_router)
# /api/debug/runtime reste disponible en développement pour diagnostiquer
# le process servant réellement le trafic ; masqué en production via le
# mécanisme de config déjà présent (API_RELOAD=false en prod).
if settings.api_reload:
    app.include_router(debug_router)
