"""Logique RAG (Retrieval-Augmented Generation) : retrieval + Ollama -> réponse + sources."""

from .prompts import NOT_FOUND_MESSAGE, SYSTEM_PROMPT, build_user_prompt
from .service import (
    RAGError,
    RAGGenerationError,
    RAGRetrievalError,
    RAGService,
    RAGUnavailableError,
)

__all__ = [
    "RAGService",
    "RAGError",
    "RAGRetrievalError",
    "RAGGenerationError",
    "RAGUnavailableError",
    "NOT_FOUND_MESSAGE",
    "SYSTEM_PROMPT",
    "build_user_prompt",
]
