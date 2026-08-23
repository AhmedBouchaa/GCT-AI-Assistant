"""Tests d'intégration locale de la génération RAG (lourds).

Marqués ``heavy`` : skippés par défaut, lancer avec --run-heavy.

Deux niveaux :
- test_chat_endpoint_retrieves_correct_document : VRAI retrieval (E5 + ChromaDB
  gct_documents_v2) via l'endpoint POST /api/chat ; seul le client Ollama est
  mocké (pas de mistral nécessaire, donc exécutable sur cette machine 8 Go).
  Prouve que l'endpoint et le script de retrieve() direct utilisent BIEN la
  même récupération et renvoient GCT_notes_exemples_50-2.pdf en tête.
- test_full_rag_identifies_chairman : retrieval RÉEL + VRAI serveur Ollama
  (mistral:latest). Nécessite Ollama résident + ~8 Go de RAM.

    ./venv/Scripts/python.exe -m pytest --run-heavy tests/test_generation_integration.py -q
"""
from fastapi.testclient import TestClient

import pytest

from app.api import routes as routes_module
from app.core.config import settings
from app.generation import GenerationService
from main import app

pytestmark = pytest.mark.heavy

QUESTION_AR = (
    "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟"
)


class _RecordingOllama:
    """Client Ollama factice : enregistre le prompt, ne génère rien de réel.

    Permet de tester la récupération réelle via /api/chat SANS charger mistral.
    """

    def __init__(self):
        self.last_prompt = None

    def generate(self, prompt, system_prompt=None, temperature=0.2, num_predict=None):
        self.last_prompt = prompt
        return "RÉPONSE_SIMULÉE_POUR_TEST"


@pytest.mark.heavy
def test_chat_endpoint_retrieves_correct_document():
    """Regression : /api/chat doit récupérer GCT_notes_exemples_50-2.pdf en tête.

    Récupération RÉELLE (E5 + ChromaDB gct_documents_v2) ; Ollama mocké
    uniquement. Prouve que l'endpoint et retrieve() direct partagent la même
    collection / le même modèle / la même config (aucune déviation).
    """
    # Garde-fou : on s'assure d'utiliser la configuration attendue.
    assert settings.chroma_collection_name == "gct_documents_v2"
    assert settings.embedding_model == "intfloat/multilingual-e5-small"
    assert settings.embedding_dimension == 384

    fake_ollama = _RecordingOllama()
    # Service de génération avec retrieval RÉEL, Ollama factice.
    svc = GenerationService(ollama_client=fake_ollama)
    routes_module._get_generation_service = lambda: svc

    client = TestClient(app)
    resp = client.post("/api/chat", json={"question": QUESTION_AR, "top_k": 5})

    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"], "au moins une source attendue"
    # Le document principal doit être GCT_notes_exemples_50-2.pdf, en tête.
    assert body["sources"][0]["file_name"] == "GCT_notes_exemples_50-2.pdf"
    # Le contexte envoyé à Ollama doit contenir ce document, pas un autre.
    assert "GCT_notes_exemples_50-2.pdf" in (fake_ollama.last_prompt or "")
    assert "محمد بن علي" in (fake_ollama.last_prompt or "")


@pytest.mark.heavy
def test_full_rag_identifies_chairman():
    """Test fonctionnel imposé (réel) : la réponse doit identifier محمد بن علي."""
    svc = GenerationService()
    result = svc.answer(QUESTION_AR, top_k=5)

    assert "محمد بن علي" in result["answer"]
    assert result["sources"], "au moins une source attendue"
    assert any(
        s["file_name"] == "GCT_notes_exemples_50-2.pdf" for s in result["sources"]
    )
