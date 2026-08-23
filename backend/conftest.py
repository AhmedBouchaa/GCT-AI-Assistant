"""Configuration pytest du projet.

Les tests marqués ``heavy`` chargent de vrais modèles (E5-large dans PyTorch,
ou un LLM résident via le serveur Ollama) et nécessitent ~8 Go de RAM libre.
Sur cette machine (8 Go au total), E5 et mistral ne peuvent pas être chargés
simultanément : par défaut ces tests sont SKIPPÉS. Pour les exécuter :

    ./venv/Scripts/python.exe -m pytest --run-heavy tests/test_retrieval_integration.py -q
    ./venv/Scripts/python.exe -m pytest --run-heavy tests/test_ollama_integration.py -q

À lancer séparément (pas les deux d'affilée dans un même process) pour éviter
le manque de mémoire.
"""
import os

import pytest

# Les tests existants (ask, documents, health) s'exécutent SANS authentification
# afin de ne pas dépendre de tokens. Les tests d'authentification
# (tests/test_auth.py) activent l'auth via monkeypatch sur settings.
os.environ["AUTH_ENABLED"] = "false"


def pytest_addoption(parser):
    parser.addoption(
        "--run-heavy",
        action="store_true",
        help="Exécute les tests d'intégration lourds (vrais modèles E5 / Ollama).",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-heavy"):
        return
    skip_heavy = pytest.mark.skip(
        reason="test lourd (vrai modèle) : exécuter avec --run-heavy"
    )
    for item in items:
        if "heavy" in item.keywords:
            item.add_marker(skip_heavy)
