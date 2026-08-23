"""Test manuel de la couche de récupération (retrieval) sur la collection ChromaDB.

Exécute de vraies questions arabes contre la collection ``gct_documents``
existante (chunks + metadata + distance/similarité). N'appelle PAS Ollama.

Usage:
    ./venv/Scripts/python.exe scripts/test_retrieval.py                # questions d'exemple
    ./venv/Scripts/python.exe scripts/test_retrieval.py "ma question"   # une question donnée

Les questions d'exemple ne sont que des démonstrations : elles ne font pas
partie du système, qui accepte n'importe quelle question en entrée.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval import retrieve

# Questions d'exemple (démo uniquement, aucune réponse attendue hardcodée).
SAMPLE_QUESTIONS = [
    "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟",
    "ما هي مهام اللجنة الفنية للصيانة؟",
    "كيف يتم تكوين اللجنة الفنية؟",
    "ما هي صلاحيات رئيس اللجنة الفنية؟",
]


def print_question_results(question: str, results) -> None:
    print("=" * 72)
    print(f"QUESTION:\n{question}\n")
    print(f"TOP RESULTS ({len(results)}):\n")
    if not results:
        print("  (aucun résultat)")
        return
    for i, r in enumerate(results, start=1):
        print(f"{i}. {r['file_name']}")
        print(f"   page: {r['page_number']} | chunk_index: {r['chunk_index']}")
        print(f"   distance: {r['distance']:.4f} | score (similarité): {r['score']:.4f}")
        print(f"   {r['text'][:200]}")
        print()


def main() -> None:
    top_k = 5
    questions = sys.argv[1:] or SAMPLE_QUESTIONS

    for question in questions:
        try:
            results = retrieve(question, top_k=top_k)
        except ValueError as exc:
            print(f"Question invalide: {exc}")
            continue
        print_question_results(question, results)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
