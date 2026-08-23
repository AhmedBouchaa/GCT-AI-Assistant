"""Tests d'intégration du retrieval contre la vraie collection ChromaDB.

Nécessite ``chromadb`` et la collection existante (``data/chroma``, 50 documents
déjà indexés par le pipeline d'ingestion). Le vrai modèle E5-large est chargé
une seule fois (fixture ``retriever``) et partagé entre les requêtes.

À exécuter avec le venv :
    ./venv/Scripts/python.exe -m pytest tests/test_retrieval_integration.py -q
"""
import pytest

pytest.importorskip("chromadb")

pytestmark = pytest.mark.heavy  # charge le vrai modèle E5-large (voir conftest.py)

from pathlib import Path

from app.ingest.store import ChromaStore
from app.retrieval import Retriever

BACKEND_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BACKEND_DIR / "data" / "chroma"
COLLECTION_NAME = "gct_documents_v2"

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


@pytest.fixture(scope="module")
def retriever():
    return Retriever(persist_directory=CHROMA_DIR, collection_name=COLLECTION_NAME)


def test_existing_collection_is_not_empty():
    store = ChromaStore(CHROMA_DIR, COLLECTION_NAME)
    assert store.count() > 0


def test_retrieve_real_arabic_question(retriever):
    results = retriever.retrieve(
        "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة؟",
        top_k=5,
    )

    assert 1 <= len(results) <= 5

    first = results[0]
    assert set(REQUIRED_KEYS).issubset(first.keys())
    assert first["text"]
    assert first["doc_id"]
    assert first["file_name"].endswith(".pdf")

    # Sémantique cosine : distance en [0, 2], score = 1 - distance.
    assert 0.0 <= first["distance"] <= 2.0
    assert first["score"] == pytest.approx(1.0 - first["distance"])
