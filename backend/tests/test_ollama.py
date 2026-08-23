"""Tests unitaires du service LLM Ollama (client mocké, aucun serveur requis).

Les tests d'intégration réels (serveur Ollama + modèle installé) sont dans
test_ollama_integration.py et sont ignorés si Ollama est injoignable.
"""
import pytest

from app.core.config import settings
from app.llm import OllamaClient, OllamaError, OllamaUnavailableError


class FakeResponse:
    def __init__(self, text):
        self.response = text


class FakeClient:
    """Simule ollama.Client : enregistre les appels et peut lever des erreurs."""

    def __init__(self, text="bonjour"):
        self.text = text
        self.fail = None
        self.calls = []

    def generate(self, **kwargs):
        if self.fail is not None:
            raise self.fail
        self.calls.append(kwargs)
        return FakeResponse(self.text)

    def list(self):
        return {"models": [type("M", (), {"model": "mistral:latest"})()]}


def _client_with_fake(fake):
    client = OllamaClient()
    client._get_client = lambda: fake
    return client


def test_config_loaded_correctly():
    # Modèle détecté sur le serveur local installé.
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "mistral:latest"
    assert settings.ollama_keep_alive == "1m"
    assert settings.ollama_num_ctx == 4096


def test_client_can_be_instantiated():
    client = OllamaClient()
    assert client.base_url == "http://localhost:11434"
    assert client.model == "mistral:latest"
    assert client.keep_alive == "1m"
    assert client.num_ctx == 4096

    custom = OllamaClient(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5-coder:7b",
        keep_alive="5m",
        num_ctx=2048,
    )
    assert custom.base_url == "http://127.0.0.1:11434"
    assert custom.model == "qwen2.5-coder:7b"
    assert custom.keep_alive == "5m"
    assert custom.num_ctx == 2048


def test_generate_sends_prompt_model_and_options():
    fake = FakeClient()
    client = _client_with_fake(fake)

    text = client.generate(
        "Explique le RAG en une phrase.",
        system_prompt="Sois concis.",
        temperature=0.2,
        num_predict=16,
    )

    assert text == "bonjour"
    call = fake.calls[-1]
    assert call["model"] == "mistral:latest"
    assert call["prompt"] == "Explique le RAG en une phrase."
    assert call["system"] == "Sois concis."
    assert call["keep_alive"] == "1m"
    assert call["options"] == {"temperature": 0.2, "num_ctx": 4096, "num_predict": 16}


def test_generate_passes_keep_alive_to_ollama():
    fake = FakeClient()
    client = _client_with_fake(fake)
    client.generate("Test prompt")

    assert len(fake.calls) == 1
    assert fake.calls[0]["keep_alive"] == "1m"


def test_generate_passes_num_ctx_in_options():
    fake = FakeClient()
    client = _client_with_fake(fake)
    client.generate("Test prompt")

    assert len(fake.calls) == 1
    assert "num_ctx" in fake.calls[0]["options"]
    assert fake.calls[0]["options"]["num_ctx"] == 4096


def test_custom_keep_alive_and_num_ctx_overrides():
    fake = FakeClient()
    custom = OllamaClient(keep_alive="2m", num_ctx=8192)
    custom._get_client = lambda: fake

    custom.generate("Test prompt", temperature=0.5)

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["keep_alive"] == "2m"
    assert call["options"]["num_ctx"] == 8192
    assert call["options"]["temperature"] == 0.5


def test_generate_rejects_empty_prompt():
    client = _client_with_fake(FakeClient())

    with pytest.raises(ValueError):
        client.generate("")
    with pytest.raises(ValueError):
        client.generate("   ")


def test_unavailable_server_raises_clear_error():
    fake = FakeClient()
    fake.fail = ConnectionError("connexion refusée")
    client = _client_with_fake(fake)

    with pytest.raises(OllamaUnavailableError) as exc_info:
        client.generate("Bonjour")

    assert "Ollama" in str(exc_info.value)


def test_http_error_is_ollama_error_not_unavailable():
    import ollama

    fake = FakeClient()
    fake.fail = ollama.ResponseError("model not found", 404)
    client = _client_with_fake(fake)
    client._ollama = ollama  # pour que la classification reconnaisse ResponseError

    with pytest.raises(OllamaError) as exc_info:
        client.generate("Bonjour")
    # Ce n'est PAS une erreur d'indisponibilité, c'est une erreur HTTP du serveur.
    assert not isinstance(exc_info.value, OllamaUnavailableError)


def test_list_models():
    client = _client_with_fake(FakeClient())
    assert client.list_models() == ["mistral:latest"]


def test_config_has_ollama_timeout():
    assert hasattr(settings, "ollama_timeout")
    assert isinstance(settings.ollama_timeout, int)
    assert settings.ollama_timeout > 0


def test_timeout_error_is_classified_as_unavailable():
    import httpx

    fake = FakeClient()
    fake.fail = httpx.ReadTimeout("read timeout")
    client = _client_with_fake(fake)
    client._ollama = __import__("ollama")

    with pytest.raises(OllamaUnavailableError) as exc_info:
        client.generate("Bonjour")

    assert "Timeout" in str(exc_info.value)


def test_client_passes_timeout_to_ollama():
    """Vérifie que le timeout de config est passé au constructeur ollama.Client."""
    import ollama as real_ollama

    captured = {}

    class FakeOllamaClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def generate(self, **kwargs):
            return FakeResponse("ok")

        def list(self):
            return {"models": []}

    original_client = real_ollama.Client
    real_ollama.Client = FakeOllamaClient
    try:
        client = OllamaClient()
        client._get_client()
        assert "timeout" in captured
        assert captured["timeout"] == settings.ollama_timeout
    finally:
        real_ollama.Client = original_client

