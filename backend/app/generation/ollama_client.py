"""Client de communication avec le serveur Ollama local pour la génération.

Ce module ne duplique PAS la logique de communication Ollama : il réexporte le
client générique déjà éprouvé (``app.llm.ollama_client``), unique source de
vérité pour le dialogue avec Ollama. Ce client est configurable via
``settings.ollama_base_url`` / ``settings.ollama_model`` / ``settings.ollama_*``
(URL et modèle non hardcodés, cohérents avec le reste de l'application).

Usage depuis la couche de génération :

    from app.generation.ollama_client import OllamaClient
    client = OllamaClient()            # lit settings.ollama_base_url / .ollama_model
    texte = client.generate(prompt, system_prompt=..., temperature=0.2)
"""
from app.llm.ollama_client import OllamaClient, OllamaError, OllamaUnavailableError

__all__ = ["OllamaClient", "OllamaError", "OllamaUnavailableError"]
