"""Tests unitaires de la couche de récupération (retrieval).

Ces tests mockent la collection ChromaDB et le service d'embedding : ils ne
nécessitent ni ChromaDB ni le modèle E5 réel. Les tests contre la vraie
collection se trouvent dans test_retrieval_integration.py.
"""
import numpy as np
import pytest
import sentence_transformers as st

from app.ingest.embeddings import E5EmbeddingService
from app.retrieval import Retriever

REQUIRED_KEYS = [
    "text",
    "score",
    "distance",
    "doc_id",
    "file_name",
    "file_path",
    "page_number",
    "chunk_index",
    "chunk_id",
]

ARABIC_QUESTION = "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة؟"


class FakeEmbedder:
    """Enregistre les textes/prefixes envoyés et renvoie des embeddings factices."""

    def __init__(self):
        self.captured = []

    def embed_texts(self, texts, prefix=""):
        self.captured.append({"texts": list(texts), "prefix": prefix})
        return np.zeros((len(texts), 8), dtype="float32")


class FakeStore:
    """Simule la réponse ChromaDB de ``ChromaStore.query``."""

    def __init__(self, response=None):
        self.response = response or {
            "ids": [["doc:doc_p1_c0"]],
            "documents": [["texte du chunk"]],
            "metadatas": [
                [
                    {
                        "doc_id": "doc",
                        "file_name": "doc.pdf",
                        "file_path": "data/doc.pdf",
                        "page_number": 1,
                        "chunk_index": 0,
                        "chunk_id": "doc_p1_c0",
                    }
                ]
            ],
            "distances": [[0.2]],
        }
        self.calls = []

    def query(self, query_embeddings, n_results=5, include=None):
        self.calls.append({"n_results": n_results, "include": include})
        return self.response

    def space(self):
        return "cosine"


def _make_retriever(response=None):
    embedder = FakeEmbedder()
    store = FakeStore(response)
    retriever = Retriever(embedding_service=embedder, store=store)
    return retriever, embedder, store


def test_embedding_model_is_single_configured_source():
    from app.core.config import settings

    assert settings.embedding_model == "intfloat/multilingual-e5-small"
    # L'ingestion et le retrieval instancient E5EmbeddingService() sans argument.
    assert E5EmbeddingService().model_name == settings.embedding_model


def test_retrieve_returns_results_for_arabic_question():
    retriever, _, _ = _make_retriever()

    results = retriever.retrieve(ARABIC_QUESTION, top_k=5)

    assert len(results) == 1
    assert results[0]["text"] == "texte du chunk"
    assert results[0]["distance"] == 0.2
    assert results[0]["score"] == pytest.approx(0.8)  # similarité = 1 - distance (cosine)


def test_retrieve_results_contain_all_required_metadata():
    retriever, _, _ = _make_retriever()

    results = retriever.retrieve(ARABIC_QUESTION)

    assert set(REQUIRED_KEYS).issubset(results[0].keys())
    assert results[0]["doc_id"] == "doc"
    assert results[0]["file_name"] == "doc.pdf"
    assert results[0]["page_number"] == 1
    assert results[0]["chunk_index"] == 0
    assert results[0]["chunk_id"] == "doc_p1_c0"


def test_retrieve_respects_top_k():
    response = {
        "ids": [[f"doc:{i}" for i in range(3)]],
        "documents": [[f"chunk {i}" for i in range(3)]],
        "metadatas": [[{"doc_id": "doc"} for _ in range(3)]],
        "distances": [[0.1, 0.2, 0.3]],
    }
    retriever, _, store = _make_retriever(response)

    results = retriever.retrieve(ARABIC_QUESTION, top_k=5)

    assert store.calls[-1]["n_results"] == 5
    assert len(results) <= 5


def test_retrieve_rejects_empty_question():
    retriever, _, _ = _make_retriever()

    with pytest.raises(ValueError):
        retriever.retrieve("")
    with pytest.raises(ValueError):
        retriever.retrieve("   ")


def test_retrieve_uses_e5_query_prefix():
    # Le retriever délègue le préfixe au service d'embedding : il doit passer
    # `prefix="query:"` (l'application du préfixe est testée ci-dessous).
    retriever, embedder, _ = _make_retriever()

    retriever.retrieve(ARABIC_QUESTION)

    assert embedder.captured[-1]["prefix"] == "query:"


def test_e5_service_prepends_query_prefix(monkeypatch):
    # Vérifie que E5EmbeddingService préfixe réellement les textes par "query:".
    captured = []

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            pass

        def encode(self, texts, **kwargs):
            captured.extend(texts)
            return np.zeros((len(texts), 8), dtype="float32")

    monkeypatch.setattr(st, "SentenceTransformer", FakeSentenceTransformer)

    service = E5EmbeddingService("fake-model")
    service.embed_texts([ARABIC_QUESTION], prefix="query:")

    assert captured == [f"query:{ARABIC_QUESTION}"]


def test_e5_embedding_service_does_not_reload_model(monkeypatch):
    # Vérifie que E5EmbeddingService charge le modèle une seule fois et le réutilise.
    calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            calls.append(model_name)

        def encode(self, texts, **kwargs):
            return np.zeros((len(texts), 8), dtype="float32")

    # E5EmbeddingService._get_model fait `from sentence_transformers import SentenceTransformer`
    # à chaque appel : on patche l'attribut du module pour compter les constructions.
    monkeypatch.setattr(st, "SentenceTransformer", FakeSentenceTransformer)

    service = E5EmbeddingService("fake-model")
    service.embed_texts(["a"], prefix="query:")
    service.embed_texts(["b"], prefix="query:")

    assert len(calls) == 1


class FailingQueryStore:
    """Simule une panne ChromaDB lors de la requête (lecture)."""

    def query(self, query_embeddings, n_results=5, include=None):
        raise RuntimeError("base vectorielle indisponible")

    def space(self):
        return "cosine"


def test_chromadb_query_failure_raises_runtime_error():
    embedder = FakeEmbedder()
    store = FailingQueryStore()
    retriever = Retriever(embedding_service=embedder, store=store)

    with pytest.raises(RuntimeError, match="base vectorielle"):
        retriever.retrieve("une question", top_k=5)


def test_dimension_validation_passes_when_matching(tmp_path):
    from app.ingest.store import ChromaStore

    store = ChromaStore(
        persist_directory=tmp_path,
        collection_name="test_dim",
        expected_dimension=8,
    )
    store._validate_dimension(np.zeros((1, 8), dtype="float32"))
    assert store._dimension_checked is True


def test_dimension_validation_fails_when_mismatched(tmp_path):
    from app.ingest.store import ChromaStore, DimensionMismatchError

    store = ChromaStore(
        persist_directory=tmp_path,
        collection_name="test_dim",
        expected_dimension=384,
    )

    with pytest.raises(DimensionMismatchError, match="384"):
        store._validate_dimension(np.zeros((1, 8), dtype="float32"))


def test_dimension_validation_skipped_when_not_configured(tmp_path):
    from app.ingest.store import ChromaStore

    store = ChromaStore(
        persist_directory=tmp_path,
        collection_name="test_dim",
        expected_dimension=None,
    )
    store._validate_dimension(np.zeros((1, 8), dtype="float32"))
    assert store._dimension_checked is False


# =====================================================================
# Tests du pipeline hybride (extraction + réordonnancement par décision)
# =====================================================================

from app.retrieval.retriever import extract_decision_identifiers, _matches_any_decision


def test_extract_decision_identifiers_all_formats():
    """Vérifie l'extraction des identifiants dans tous les formats supportés."""
    test_cases = [
        ("N° 010/2026", [(10, 2026)]),
        ("N°010/2026", [(10, 2026)]),
        ("010/2026", [(10, 2026)]),
        ("10/2026", [(10, 2026)]),
        ("numéro 010/2026", [(10, 2026)]),
        ("numéro 10/2026", [(10, 2026)]),
        ("decision 010/2026", [(10, 2026)]),
        ("decision numéro 010/2026", [(10, 2026)]),
        ("décision numéro 010/2026", [(10, 2026)]),
        ("القرار عدد 010 لسنة 2026", [(10, 2026)]),
        ("القرار رقم N° 010/2026", [(10, 2026)]),
        ("العدد: N° 010/2026", [(10, 2026)]),
        ("N° 001/2026", [(1, 2026)]),
        ("1/2026", [(1, 2026)]),
    ]
    for text, expected in test_cases:
        assert extract_decision_identifiers(text) == expected, f"Échec pour: {text}"


def test_extract_decision_identifiers_multiple_and_empty():
    assert extract_decision_identifiers("") == []
    assert extract_decision_identifiers("Question générale sans numéro") == []
    
    query = "من هو رئيس اللجنة حسب القرار رقم N° 006/2026 و القرار N° 007/2026؟"
    assert extract_decision_identifiers(query) == [(6, 2026), (7, 2026)]


def test_matches_any_decision_patterns():
    dec_ids = [(10, 2026)]
    assert _matches_any_decision("العدد: N° 010/2026 تعيين اللجنة", dec_ids) is True
    assert _matches_any_decision("قرار رقم 10/2026 صادر بتاريخ", dec_ids) is True
    assert _matches_any_decision("القرار عدد 010 لسنة 2026", dec_ids) is True
    assert _matches_any_decision("Décision numéro 010/2026", dec_ids) is True
    # Ne doit pas matcher d'autres numéros
    assert _matches_any_decision("العدد: N° 002/2026 تعيين اللجنة", dec_ids) is False
    assert _matches_any_decision("Texte sans aucun numéro", dec_ids) is False


def test_retrieve_prioritizes_exact_decision_match():
    """Vérifie qu'un chunk contenant le numéro exact est remonté au rang 1."""
    response = {
        "ids": [["doc:1", "doc:2", "doc:3"]],
        "documents": [[
            "Modèle type générique sans numéro",  # dense dist 0.1
            "Contenu de la décision N° 010/2026 pour la maintenance",  # dense dist 0.25 (cible)
            "Autre décision N° 002/2026",  # dense dist 0.3
        ]],
        "metadatas": [[
            {"doc_id": "doc1", "file_name": "50-1.pdf", "page_number": 1, "chunk_index": 0, "chunk_id": "doc1_p1_c0"},
            {"doc_id": "doc2", "file_name": "50-10.pdf", "page_number": 1, "chunk_index": 0, "chunk_id": "doc2_p1_c0"},
            {"doc_id": "doc3", "file_name": "50-2.pdf", "page_number": 1, "chunk_index": 0, "chunk_id": "doc3_p1_c0"},
        ]],
        "distances": [[0.1, 0.25, 0.3]],
    }
    retriever, _, _ = _make_retriever(response)

    results = retriever.retrieve("Quel est l'objet selon la décision N° 010/2026 ?", top_k=3)

    assert len(results) == 3
    # Le document 50-10 (cible) doit être au rang 1 malgré une distance dense plus grande
    assert results[0]["file_name"] == "50-10.pdf"
    assert results[0]["chunk_id"] == "doc2_p1_c0"
    assert results[0]["distance"] == 0.25
    assert results[0]["score"] == pytest.approx(0.75)

    # Les autres candidats restent disponibles après
    assert results[1]["file_name"] == "50-1.pdf"
    assert results[2]["file_name"] == "50-2.pdf"


def test_retrieve_transparent_fallback_without_decision_id():
    """Sans numéro de décision, l'ordre dense est 100% préservé."""
    response = {
        "ids": [["doc:1", "doc:2", "doc:3"]],
        "documents": [["Texte A", "Texte B", "Texte C"]],
        "metadatas": [[
            {"doc_id": "doc1", "file_name": "50-1.pdf", "page_number": 1, "chunk_index": 0, "chunk_id": "doc1_p1_c0"},
            {"doc_id": "doc2", "file_name": "50-2.pdf", "page_number": 1, "chunk_index": 0, "chunk_id": "doc2_p1_c0"},
            {"doc_id": "doc3", "file_name": "50-3.pdf", "page_number": 1, "chunk_index": 0, "chunk_id": "doc3_p1_c0"},
        ]],
        "distances": [[0.15, 0.22, 0.35]],
    }
    retriever, _, _ = _make_retriever(response)

    results = retriever.retrieve("Question générale sans numéro", top_k=3)

    assert [r["file_name"] for r in results] == ["50-1.pdf", "50-2.pdf", "50-3.pdf"]
    assert [r["distance"] for r in results] == [0.15, 0.22, 0.35]


def test_retrieve_multiple_decision_identifiers_priority():
    """Quand plusieurs décisions sont demandées, toutes reçoivent la priorité."""
    response = {
        "ids": [["doc:1", "doc:2", "doc:3", "doc:4"]],
        "documents": [[
            "Document neutre",  # dist 0.05
            "Décision N° 007/2026",  # dist 0.20 (match)
            "Décision N° 006/2026",  # dist 0.15 (match, meilleur dense)
            "Décision N° 020/2026",  # dist 0.30
        ]],
        "metadatas": [[
            {"file_name": "neutre.pdf", "doc_id": "n"},
            {"file_name": "50-7.pdf", "doc_id": "7"},
            {"file_name": "50-6.pdf", "doc_id": "6"},
            {"file_name": "50-20.pdf", "doc_id": "20"},
        ]],
        "distances": [[0.05, 0.20, 0.15, 0.30]],
    }
    retriever, _, _ = _make_retriever(response)

    results = retriever.retrieve("Comparer la décision N° 006/2026 et la décision N° 007/2026", top_k=4)

    # Les deux documents correspondants sont en tête, ordonnés par score dense entre eux (50-6 puis 50-7)
    assert results[0]["file_name"] == "50-6.pdf"
    assert results[1]["file_name"] == "50-7.pdf"
    assert results[2]["file_name"] == "neutre.pdf"
    assert results[3]["file_name"] == "50-20.pdf"


def test_retrieve_never_exceeds_top_k():
    """Le nombre de résultats renvoyé ne dépasse jamais top_k."""
    response = {
        "ids": [[f"doc:{i}" for i in range(10)]],
        "documents": [[f"Document {i} avec décision N° 010/2026" for i in range(10)]],
        "metadatas": [[{"file_name": f"doc_{i}.pdf", "doc_id": f"id_{i}"} for i in range(10)]],
        "distances": [[0.1 * i for i in range(10)]],
    }
    retriever, _, _ = _make_retriever(response)

    results = retriever.retrieve("Selon la décision 010/2026", top_k=3)
    assert len(results) == 3


def test_retrieve_preserves_all_metadata_and_score_semantics():
    """Vérifie que toutes les clés de métadonnées et le calcul du score cosine sont préservés."""
    response = {
        "ids": [["doc:1"]],
        "documents": [["Contenu N° 008/2026"]],
        "metadatas": [[
            {
                "doc_id": "GCT_50-8",
                "file_name": "GCT_notes_exemples_50-8.pdf",
                "file_path": "data/documents/GCT_notes_exemples_50-8.pdf",
                "page_number": 1,
                "chunk_index": 0,
                "chunk_id": "GCT_50-8_p1_c0",
            }
        ]],
        "distances": [[0.18]],
    }
    retriever, _, _ = _make_retriever(response)

    results = retriever.retrieve("Détails de la décision N° 008/2026", top_k=1)
    res = results[0]

    assert res["doc_id"] == "GCT_50-8"
    assert res["file_name"] == "GCT_notes_exemples_50-8.pdf"
    assert res["file_path"] == "data/documents/GCT_notes_exemples_50-8.pdf"
    assert res["page_number"] == 1
    assert res["chunk_index"] == 0
    assert res["chunk_id"] == "GCT_50-8_p1_c0"
    assert res["distance"] == 0.18
    assert res["score"] == pytest.approx(0.82)

