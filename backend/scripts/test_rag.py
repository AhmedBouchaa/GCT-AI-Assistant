"""Test manuel du RAG complet : retrieval -> prompt ancré -> Ollama -> réponse + sources.

Usage:
    ./venv/Scripts/python.exe scripts/test_rag.py                  # questions d'exemple
    ./venv/Scripts/python.exe scripts/test_rag.py "une question"   # question donnée

N'implémente pas d'API : simple exécution en ligne de commande contre la
collection ChromaDB existante et le modèle Ollama configuré.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.rag import (
    RAGGenerationError,
    RAGRetrievalError,
    RAGService,
    RAGUnavailableError,
)

# Questions d'exemple (démo uniquement — aucune réponse attendue hardcodée).
SAMPLE_QUESTIONS = [
    "Quel est l'objet de la décision concernant la maintenance des équipements lourds ?",
    "ما هو موضوع القرار المتعلق بصيانة المعدات الثقيلة؟",
    "Quelle est la date de la décision sur la commission technique de maintenance ?",
]


def print_result(result) -> None:
    print("=" * 72)
    print("QUESTION")
    print("-" * 72)
    print(result["question"])
    print("\nANSWER")
    print("-" * 72)
    print(result["answer"])
    print("\nSOURCES")
    print("-" * 72)
    if not result["sources"]:
        print("  (aucune source)")
    for source in result["sources"]:
        print(f"Document : {source['file_name']}")
        print(f"Page     : {source['page_number']}")
        print(f"Score    : {source['score']}")
        print(f"Chunk    : {source['chunk_id']}")
        print()
    print(f"(modèle : {settings.ollama_model} | top_k : {len(result['sources']) or '?'})")


def main() -> None:
    top_k = 5
    questions = sys.argv[1:] or SAMPLE_QUESTIONS

    service = RAGService()

    for question in questions:
        try:
            result = service.answer(question, top_k=top_k, temperature=0.2)
        except ValueError as exc:
            print(f"Question invalide : {exc}")
            continue
        except RAGRetrievalError as exc:
            print(f"[ERREUR RETRIEVAL] {exc}")
            continue
        except RAGUnavailableError as exc:
            print(f"[ERREUR OLLAMA INJOIGNABLE] {exc}")
            continue
        except RAGGenerationError as exc:
            print(f"[ERREUR GÉNÉRATION] {exc}")
            continue
        print_result(result)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
