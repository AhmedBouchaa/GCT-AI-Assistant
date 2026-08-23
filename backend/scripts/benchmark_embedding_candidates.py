"""Benchmark expérimental de modèles d'embedding multilingues (NON destructif).

Compare plusieurs modèles d'embedding sur les 30 questions du benchmark
(data/test_questions_v2.json, lu en lecture seule) en utilisant la MÊME
méthodologie que scripts/benchmark_embeddings.py (retrieval plein document en
mémoire, cosine top-5) afin que les scores soient comparables.

Le benchmark PRODUCTION (scripts/benchmark_embeddings.py) n'est PAS modifié.

Utilisation (venv) :
    ./venv/Scripts/python.exe scripts/benchmark_embedding_candidates.py [--models m1,m2]

Conventions de préfixe : famille E5 -> "passage: " / "query: " ; les autres
modèles (MiniLM, mpnet) n'utilisent pas de préfixe.
"""
import argparse
import gc
import sys
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.pdf_extractor import PDFExtractor

# (nom modèle, dimensions, taille disque approx., préfixe document, préfixe requête)
CANDIDATES = [
    ("intfloat/multilingual-e5-large", 1024, "~2.2 Go", "passage: ", "query: "),
    ("intfloat/multilingual-e5-base", 768, "~0.5 Go", "passage: ", "query: "),
    ("intfloat/multilingual-e5-small", 384, "~0.12 Go", "passage: ", "query: "),
    ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 384, "~0.42 Go", "", ""),
]


def load_documents(documents_dir: Path) -> Dict[str, str]:
    extractor = PDFExtractor(str(documents_dir))
    documents: Dict[str, str] = {}
    for page in extractor.extract_all_pdfs():
        documents.setdefault(page["filename"], "")
        documents[page["filename"]] += f"\n{page['text']}"
    return documents


def load_questions(questions_file: Path) -> List[Dict]:
    import json

    with open(questions_file, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data["questions"]


def evaluate(doc_embeddings, doc_names, query_embeddings, questions):
    recall_1, recall_3, recall_5, reciprocal_ranks = [], [], [], []
    for i, question in enumerate(questions):
        sims = cosine_similarity(query_embeddings[i].reshape(1, -1), doc_embeddings)[0]
        order = np.argsort(sims)[::-1]
        retrieved = [doc_names[j] for j in order[:5]]
        expected = question["expected_pdf"]

        recall_1.append(1 if expected in retrieved[:1] else 0)
        recall_3.append(1 if expected in retrieved[:3] else 0)
        recall_5.append(1 if expected in retrieved[:5] else 0)
        rank = order.tolist().index(doc_names.index(expected)) + 1 if expected in doc_names else None
        reciprocal_ranks.append(1.0 / rank if rank and rank <= 5 else 0.0)

    return {
        "recall@1": np.mean(recall_1),
        "recall@3": np.mean(recall_3),
        "recall@5": np.mean(recall_5),
        "mrr": np.mean(reciprocal_ranks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark expérimental des embeddings.")
    parser.add_argument(
        "--models",
        default=None,
        help="Noms des modèles séparés par des virgules (défaut : tous les candidats).",
    )
    args = parser.parse_args()

    backend = Path(__file__).resolve().parent.parent
    documents_dir = backend / "data" / "documents"
    questions_file = backend / "data" / "test_questions_v2.json"

    if args.models:
        selected = {name: (dims, size, pdoc, pquery) for (name, dims, size, pdoc, pquery) in CANDIDATES if name in args.models.split(",")}
    else:
        selected = {name: (dims, size, pdoc, pquery) for (name, dims, size, pdoc, pquery) in CANDIDATES}
    if not selected:
        print("Aucun modèle sélectionné.")
        sys.exit(1)

    print("Chargement des documents...")
    documents = load_documents(documents_dir)
    doc_names = sorted(documents.keys())
    doc_texts = [documents[n] for n in doc_names]
    print(f"{len(documents)} documents.")

    print("Chargement des questions...")
    questions = load_questions(questions_file)
    question_texts = [q["question"] for q in questions]
    print(f"{len(questions)} questions.\n")

    results = []
    for model_name, (dims, size, prefix_doc, prefix_query) in selected.items():
        print(f"=== {model_name} (dims={dims}, {size}) ===")
        t0 = time.time()
        model = SentenceTransformer(model_name)
        t_load = time.time() - t0

        t0 = time.time()
        doc_emb = model.encode(
            [f"{prefix_doc}{t}" for t in doc_texts] if prefix_doc else doc_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        t_doc = time.time() - t0

        t0 = time.time()
        query_emb = model.encode(
            [f"{prefix_query}{q}" for q in question_texts] if prefix_query else question_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        t_query = time.time() - t0

        metrics = evaluate(doc_emb, doc_names, query_emb, questions)
        results.append(
            {
                "model": model_name,
                "dims": dims,
                "size": size,
                "load_s": round(t_load, 1),
                "embed_docs_s": round(t_doc, 1),
                "embed_queries_s": round(t_query, 1),
                **metrics,
            }
        )
        print(
            f"  chargement: {t_load:.1f}s | docs: {t_doc:.1f}s | requêtes: {t_query:.1f}s\n"
            f"  Recall@1={metrics['recall@1']:.3f}  Recall@3={metrics['recall@3']:.3f}  "
            f"Recall@5={metrics['recall@5']:.3f}  MRR={metrics['mrr']:.3f}\n"
        )

        del model
        gc.collect()

    print("=" * 88)
    print("TABLEAU COMPARATIF")
    print(f"{'Modèle':<50} {'Dim':<6} {'Taille':<9} {'Load_s':<7} {'R@1':<7} {'R@3':<7} {'R@5':<7} {'MRR':<7}")
    print("-" * 88)
    for r in results:
        print(
            f"{r['model']:<50} {r['dims']:<6} {r['size']:<9} {r['load_s']:<7} "
            f"{r['recall@1']:<7.3f} {r['recall@3']:<7.3f} {r['recall@5']:<7.3f} {r['mrr']:<7.3f}"
        )
    print("=" * 88)


if __name__ == "__main__":
    main()
