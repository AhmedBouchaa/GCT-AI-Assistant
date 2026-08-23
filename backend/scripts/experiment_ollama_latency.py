"""Harness expérimental : mesure la latence du RAG /ask et teste les options Ollama.

NON destructif, n'utilise QUE du code existant en lecture :
- ``app.retrieval.retrieve`` (embedding e5-small, collection gct_documents_v2)
- ``app.rag.prompts`` (construction du prompt ancré, inchangée)

Teste des options OLLAMA côté requête (sans modifier l'environnement) :
- ``num_ctx`` (fenêtre de contexte)
- ``keep_alive`` (déchargement du modèle après la réponse)

Usage (venv) :
    ./venv/Scripts/python.exe scripts/experiment_ollama_latency.py --num-ctx 4096 --keep-alive "1m" \
        --question "Quel est l'objet de la decision concernant la maintenance des equipements lourds ?"
"""
import argparse
import time
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retrieval import retrieve


def main() -> None:
    parser = argparse.ArgumentParser(description="Mesure la latence /ask avec options Ollama.")
    parser.add_argument("--num-ctx", type=int, default=4096, help="Fenêtre de contexte (tokens).")
    parser.add_argument("--keep-alive", default=None, help="keep_alive Ollama (ex: 1m, 5m, None).")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--question",
        default="Quel est l'objet de la decision concernant la maintenance des equipements lourds ?",
    )
    args = parser.parse_args()

    import ollama

    print(f"Modèle : {settings.ollama_model} | num_ctx={args.num_ctx} | "
          f"keep_alive={args.keep_alive} | temp={args.temperature} | max_tokens={args.max_tokens}\n")

    # 1) Retrieval (e5-small, collection active)
    t0 = time.time()
    results = retrieve(args.question, top_k=args.top_k)
    t_retrieval = time.time() - t0
    print(f"[retrieval] {t_retrieval:.1f}s | {len(results)} chunk(s)")
    if not results:
        print("Aucun chunk -> pas de génération.")
        return

    # 2) Prompt ancré (même construction que la production)
    user_prompt = build_user_prompt(args.question, results)
    prompt_chars = len(user_prompt) + len(SYSTEM_PROMPT)
    est_tokens = prompt_chars // 3  # estimation conservatrice BPE (latin/arabe)
    print(f"[prompt] ~{prompt_chars} caractères -> ~{est_tokens} tokens estimés "
          f"(num_ctx={args.num_ctx})")
    if est_tokens >= args.num_ctx:
        print(f"[AVERTISSEMENT] le prompt estimé (~{est_tokens}) dépasse num_ctx={args.num_ctx} "
              "-> risque de troncature. Réduire top_k ou augmenter num_ctx.")
    for i, r in enumerate(results[:3], start=1):
        print(f"  source {i}: {r['file_name']} p{r['page_number']} score={r['score']:.3f}")

    # 3) Génération locale
    client = ollama.Client(host=settings.ollama_base_url)
    t0 = time.time()
    response = client.generate(
        model=settings.ollama_model,
        prompt=user_prompt,
        system=SYSTEM_PROMPT,
        options={
            "temperature": args.temperature,
            "num_predict": args.max_tokens,
            "num_ctx": args.num_ctx,
        },
        keep_alive=args.keep_alive,
    )
    t_generation = time.time() - t0
    print(f"[generation] {t_generation:.1f}s | tokens générés: {response.get('eval_count', '?')} "
          f"({response.get('eval_count', 0) / t_generation:.1f} tok/s si mesuré)")

    print(f"\n[total] {t_retrieval + t_generation:.1f}s\n")
    print("=== ANSWER ===")
    print(response.response.strip())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
