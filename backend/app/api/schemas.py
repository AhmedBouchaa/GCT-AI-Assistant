"""Schémas Pydantic pour l'API REST de l'assistant RAG GCT."""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    """Requête POST /api/v1/ask."""

    question: str = Field(..., description="Question de l'utilisateur.")
    top_k: int = Field(default=5, ge=1, le=20, description="Nombre de chunks à récupérer.")
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Température d'échantillonnage pour la génération.",
    )
    max_tokens: int = Field(
        default=512,
        ge=1,
        le=8192,
        description="Nombre maximal de tokens générés.",
    )

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("La question ne peut pas être vide.")
        return stripped


class Source(BaseModel):
    """Source d'une unité documentaire (compat: chunk_id alias doc_id)."""

    file_name: str
    page_number: Optional[int] = None
    score: Optional[float] = None
    chunk_id: Optional[str] = None


class AskResponse(BaseModel):
    """Réponse de POST /api/v1/ask."""

    question: str
    answer: str
    sources: List[Source]


class HealthResponse(BaseModel):
    """Réponse des endpoints de santé."""

    status: str
    model: Optional[str] = None


class DocumentIngestResponse(BaseModel):
    """Réponse de POST /api/v1/documents (ingestion d'un PDF)."""

    file_name: str
    status: str  # indexed | updated | skipped | ocr_required | failed
    pages: int
    chunks: int
    message: str
    ocr_pages: int = 0


class ChatSource(BaseModel):
    """Source d'un chunk utilisé pour répondre (endpoint /api/chat)."""

    file_name: str
    page_number: Optional[int] = None
    score: Optional[float] = None


class ChatRequest(BaseModel):
    """Requête POST /api/chat (couche de génération RAG)."""

    question: str = Field(..., description="Question de l'utilisateur.")
    top_k: int = Field(default=5, ge=1, le=20, description="Nombre de chunks à récupérer.")
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Température d'échantillonnage pour la génération.",
    )
    max_tokens: int = Field(
        default=512,
        ge=1,
        le=8192,
        description="Nombre maximal de tokens générés.",
    )

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("La question ne peut pas être vide.")
        return stripped


class ChatResponse(BaseModel):
    """Réponse de POST /api/chat (uniquement réponse + sources)."""

    answer: str
    sources: List[ChatSource]
