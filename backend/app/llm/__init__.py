"""Service LLM local générique via Ollama (aucune dépendance au domaine GCT)."""

from .ollama_client import OllamaClient, OllamaError, OllamaUnavailableError

__all__ = ["OllamaClient", "OllamaError", "OllamaUnavailableError"]
