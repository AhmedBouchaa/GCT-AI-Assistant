"""Test d'intégration : requête réelle au serveur Ollama local.

Ignoré proprement si Ollama est injoignable (le reste de la suite ne dépend
pas de la disponibilité d'Ollama).

À exécuter avec le venv :
    ./venv/Scripts/python.exe -m pytest tests/test_ollama_integration.py -q
"""
import pytest

pytest.importorskip("ollama")

pytestmark = pytest.mark.heavy  # requiert un vrai serveur Ollama + modèle local (voir conftest.py)

from app.llm import OllamaClient, OllamaUnavailableError


def test_real_ollama_generation_with_installed_model():
    client = OllamaClient()

    try:
        models = client.list_models()
    except OllamaUnavailableError as exc:
        pytest.skip(f"Ollama injoignable : {exc}")

    assert client.model in models, (
        f"Le modèle configuré '{client.model}' n'est pas installé. "
        f"Modèles disponibles : {models}"
    )

    response = client.generate(
        "Dis uniquement: OK.",
        temperature=0.0,
        num_predict=8,
    )

    assert isinstance(response, str)
    assert response.strip()
