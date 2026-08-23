"""Test manuel de la connexion au serveur Ollama local.

Usage:
    ./venv/Scripts/python.exe scripts/test_ollama.py                 # modèle configuré
    ./venv/Scripts/python.exe scripts/test_ollama.py mistral:latest  # modèle explicite

Vérifie la connexion, liste les modèles installés, envoie un petit prompt de
test au modèle et affiche la réponse. N'utilise aucun document GCT ni
retrieval.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.llm import OllamaClient, OllamaUnavailableError


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else settings.ollama_model
    client = OllamaClient(model=model)

    print(f"Base URL : {client.base_url}")
    print(f"Modèle   : {client.model}")

    # 1) Connexion + liste des modèles installés
    try:
        models = client.list_models()
    except OllamaUnavailableError as exc:
        print(f"\n[ERREUR] Ollama injoignable sur {client.base_url} : {exc}")
        print("Vérifiez que le serveur Ollama est lancé (`ollama serve`).")
        sys.exit(1)
    print(f"Modèles installés : {models}")

    if client.model not in models:
        print(f"\n[ERREUR] le modèle '{client.model}' n'est pas installé.")
        print(f"Modèles disponibles : {models}")
        sys.exit(1)

    # 2) Petit prompt de test
    prompt = "Dis uniquement : OK."
    print(f"\nPrompt de test : {prompt!r}")
    try:
        response = client.generate(prompt, temperature=0.0, num_predict=8)
    except Exception as exc:  # noqa: BLE001 - rapport clair de toute erreur
        print(f"\n[ERREUR] génération impossible : {exc}")
        sys.exit(1)

    print(f"Réponse : {response.strip()!r}")
    print("\nConnexion Ollama OK.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
