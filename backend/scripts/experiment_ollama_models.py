"""Évaluation expérimentale de modèles Ollama (comparaison vs baseline mistral).

NON destructif : réutilise UNIQUEMENT le code de production en lecture
- ``app.retrieval.retrieve`` (e5-small, collection gct_documents_v2)
- ``app.rag.prompts`` (construction du prompt ancré, inchangée)
et appelle Ollama directement (``num_ctx=4096``, ``keep_alive``, même temp/max_tokens).
Ne modifie PAS ``RAGService`` ni la configuration de production.

Usage (venv) :
    ./venv/Scripts/python.exe scripts/experiment_ollama_models.py --model qwen2.5:3b
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retrieval import retrieve

# Questions fixes FR/AR/EN (même intention, parallèles ; aucune réponse attendue hardcodée).
DEFAULT_QUESTIONS = [
    {"lang": "FR", "question": "Quel est l'objet de la decision concernant la maintenance des equipements lourds ?"},
    {"lang": "AR", "question": "ما هو موضوع القرار المتعلق بصيانة المعدات الثقيلة؟"},
    {"lang": "EN", "question": "What is the subject of the decision concerning the maintenance of heavy equipment?"},
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Évalue un modèle Ollama pour le RAG GCT.")
    parser.add_argument("--model", required=True, help="Nom du modèle Ollama (ex: qwen2.5:3b).")
    parser.add_argument("--num-ctx", type=int, default=4096, help="Fenêtre de contexte (NE PAS réduire sous 4096).")
    parser.add_argument("--keep-alive", default="1m")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    import ollama

    client = ollama.Client(host=settings.ollama_base_url)
    options = {
        "temperature": args.temperature,
        "num_predict": args.max_tokens,
        "num_ctx": args.num_ctx,
    }
    print(f"Modèle : {args.model} | num_ctx={args.num_ctx} | keep_alive={args.keep_alive} | "
          f"temp={args.temperature} | max_tokens={args.max_tokens} | top_k={args.top_k}\n")

    # 1) Temps de chargement du modèle (petite génération d'échauffement)
    t0 = time.time()
    client.generate(
        model=args.model,
        prompt="Dis OK.",
        options={"num_predict": 4, "num_ctx": args.num_ctx},
        keep_alive=args.keep_alive,
    )
    t_load = time.time() - t0
    print(f"[load] {args.model} : {t_load:.1f}s\n")

    # 2) Évaluation par question (FR / AR / EN)
    rows = []
    for item in DEFAULT_QUESTIONS:
        q = item["question"]
        t0 = time.time()
        results = retrieve(q, top_k=args.top_k)
        t_retr = time.time() - t0
        prompt = build_user_prompt(q, results)
        if not results:
            print(f"[{item['lang']}] AUCUN CHUNK (pas de génération)")
            rows.append({"lang": item["lang"], "retrieval": t_retr, "generation": None, "total": t_retr, "tokens": 0, "tok_s": 0.0})
            continue

        t0 = time.time()
        resp = client.generate(
            model=args.model,
            prompt=prompt,
            system=SYSTEM_PROMPT,
            options=options,
            keep_alive=args.keep_alive,
        )
        t_gen = time.time() - t0
        n_tokens = resp.get("eval_count", 0)
        tok_s = n_tokens / t_gen if t_gen > 0 else 0.0
        answer = resp.response.strip()

        print(f"[{item['lang']}] retrieval={t_retr:.1f}s | generation={t_gen:.1f}s | "
              f"total={t_retr + t_gen:.1f}s | tokens={n_tokens} | {tok_s:.2f} tok/s")
        print(f"   sources : {[r['file_name'] for r in results[:5]]}")
        print(f"   ANSWER  : {answer[:400]}\n")
        rows.append({"lang": item["lang"], "retrieval": t_retr, "generation": t_gen,
                     "total": t_retr + t_gen, "tokens": n_tokens, "tok_s": tok_s, "answer": answer})

    # 3) Résumé
    print("=" * 70)
    print(f"RÉSUMÉ {args.model}")
    for r in rows:
        gen = f"{r['generation']:.1f}s ({r['tok_s']:.2f} tok/s, {r['tokens']} tok)" if r["generation"] else "n/a"
        print(f"  {r['lang']}: total={r['total']:.1f}s | generation={gen}")
    print("=" * 70)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
