"""Tests de communication du client Ollama (couche de génération).

Les tests rapides mockent ``ollama.Client`` (aucun serveur Ollama requis) ;
le test ``heavy`` interroge le vrai serveur local (nécessite Ollama + RAM libre).
"""
import ollama
import pytest
import types

from app.generation.ollama_client import OllamaClient


class _FakeResponse:
    response = "رئيس اللجنة الفنية لصيانة المعدات الثقيلة هو محمد بن علي."


class _FakeClient:
    def __init__(self, host, timeout):
        self.host = host
        self.timeout = timeout
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse()

    def list(self):
        return {"models": [types.SimpleNamespace(model="mistral:latest")]}


@pytest.fixture
def fake_ollama(monkeypatch):
    """Remplace ``ollama.Client`` (module réel) par un faux client."""
    monkeypatch.setattr(ollama, "Client", _FakeClient)
    return _FakeClient


def test_generate_builds_expected_options(fake_ollama):
    client = OllamaClient()
    out = client.generate(
        "question ?",
        system_prompt="sys",
        temperature=0.1,
        num_predict=100,
    )
    assert out == _FakeResponse.response
    assert len(client._client.calls) == 1
    kwargs = client._client.calls[0]
    # Le client transmet le modèle, le prompt et les options à Ollama.
    assert kwargs["model"] == "mistral:latest"
    assert kwargs["prompt"] == "question ?"
    assert kwargs["system"] == "sys"
    assert kwargs["options"]["temperature"] == 0.1
    assert kwargs["options"]["num_predict"] == 100
    # num_ctx et keep_alive proviennent de la configuration.
    assert "num_ctx" in kwargs["options"]
    assert "keep_alive" in kwargs


def test_list_models(fake_ollama):
    client = OllamaClient()
    models = client.list_models()
    assert "mistral:latest" in models


@pytest.mark.heavy
def test_real_ollama_reachable():
    """Test lourd : le serveur Ollama local doit être joignable."""
    client = OllamaClient()
    models = client.list_models()
    assert isinstance(models, list)
    assert models  # au moins un modèle installé (ex: mistral:latest)
