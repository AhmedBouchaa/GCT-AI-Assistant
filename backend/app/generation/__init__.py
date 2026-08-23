"""Couche de génération RAG (retrieval -> contexte -> Ollama -> réponse ancrée).

Module autonome et parallèle à ``app.rag`` : réutilise UNIQUEMENT la couche de
récupération existante (``app.retrieval.retrieve``) et le client Ollama local.
N'introduit ni chunking, ni modèle d'embedding, ni base vectorielle supplémentaire.
"""
from .ollama_client import OllamaClient, OllamaError, OllamaUnavailableError
from .rag_service import (
    NOT_FOUND_MESSAGE_AR,
    NOT_FOUND_MESSAGE_FR,
    SYSTEM_PROMPT,
    GenerationError,
    GenerationOllamaError,
    GenerationRetrievalError,
    GenerationService,
    GenerationUnavailableError,
    build_context,
    build_user_prompt,
    not_found_message,
)

__all__ = [
    "OllamaClient",
    "OllamaError",
    "OllamaUnavailableError",
    "GenerationService",
    "GenerationError",
    "GenerationRetrievalError",
    "GenerationUnavailableError",
    "GenerationOllamaError",
    "SYSTEM_PROMPT",
    "NOT_FOUND_MESSAGE_AR",
    "NOT_FOUND_MESSAGE_FR",
    "not_found_message",
    "build_context",
    "build_user_prompt",
]
