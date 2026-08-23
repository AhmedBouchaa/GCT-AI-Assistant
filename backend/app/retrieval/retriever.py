"""Couche de récupération (retrieval) sur la collection ChromaDB existante.

Pipeline :
    question utilisateur
        -> extraction des identifiants de décision (si présents)
        -> préfixe E5 ``query:``
        -> embedding (intfloat/multilingual-e5-small, instance réutilisée, 384 dims)
        -> recherche des candidats dans la collection ChromaDB active (``gct_documents_v2``)
        -> réordonnancement hybride (priorité aux chunks contenant le numéro de décision exact)
        -> résultats top-k : texte + metadata + distance brute + score de similarité

Sémantique des scores (IMPORTANT, ne pas confondre distance et similarité) :
ChromaDB renvoie une DISTANCE (espace configuré sur la collection, ici cosinus).
Pour l'espace cosine, la distance vaut ``1 - similarité_cosinus`` : plus elle
est PETITE, plus le chunk est proche. On expose donc deux champs distincts :
  - ``distance`` : valeur brute renvoyée par ChromaDB (plus petit = mieux) ;
  - ``score``    : similarité dérivée ``1 - distance`` pour l'espace cosine
                   (plus grand = mieux).

L'embedding est préfixé par ``query:`` (la même convention de préfixe que
l'ingestion, qui utilise ``passage:`` côté documents). Le modèle est chargé une
seule fois par processus et réutilisé entre les requêtes.
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.ingest.embeddings import E5EmbeddingService
from app.ingest.store import ChromaStore

logger = logging.getLogger(__name__)

_QUERY_PREFIX = "query:"

_DECISION_PATTERNS = [
    # Formes avec slash : N° 010/2026, 010/2026, numéro 10/2026, القرار رقم 010/2026, etc.
    re.compile(
        r"(?:N°|N\s*°|numéro|numero|décision|decision|القرار\s*رقم|القرار\s*عدد|العدد\s*:|عدد)?\s*(\d{1,4})\s*/\s*(\d{4})",
        re.IGNORECASE,
    ),
    # Formes arabes avec "لسنة" ou "سنة" : القرار عدد 010 لسنة 2026
    re.compile(
        r"(?:القرار\s*رقم|القرار\s*عدد|العدد\s*:|عدد|رقم)\s*(\d{1,4})\s+(?:لسنة|سنة)\s+(\d{4})",
        re.IGNORECASE,
    ),
]


def extract_decision_identifiers(query: str) -> List[Tuple[int, int]]:
    """Extrait les identifiants de décision (numéro, année) présents dans une requête.

    Reconnaît les formats français, arabes et numériques standards :
    - ``N° 010/2026``, ``N°010/2026``, ``010/2026``, ``10/2026``
    - ``numéro 010/2026``, ``numéro 10/2026``, ``decision 010/2026``
    - ``القرار عدد 010 لسنة 2026``, ``القرار رقم N° 010/2026``, ``العدد: N° 010/2026``
    """
    if not query:
        return []

    extracted: List[Tuple[int, int]] = []
    seen = set()
    for pat in _DECISION_PATTERNS:
        for match in pat.finditer(query):
            num_str, year_str = match.group(1), match.group(2)
            try:
                num_int = int(num_str)
                year_int = int(year_str)
            except ValueError:
                continue
            key = (num_int, year_int)
            if key not in seen:
                seen.add(key)
                extracted.append(key)
    return extracted


def _matches_any_decision(text: str, decision_ids: List[Tuple[int, int]]) -> bool:
    """Vérifie si le texte d'un chunk contient au moins un des identifiants recherchés."""
    if not text or not decision_ids:
        return False
    for num_int, year_int in decision_ids:
        # Correspondance avec "010/2026", "10/2026", "0010/2026", "N° 010/2026", "010 لسنة 2026", etc.
        pat = rf"(?:N°\s*|N\s*°\s*|numéro\s*|numero\s*|العدد\s*:\s*N°\s*|العدد\s*:\s*|\b)0*{num_int}\s*(?:/|\s+(?:لسنة|سنة)\s*)\s*{year_int}\b"
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _default_persist_directory() -> str:
    from app.core.config import settings  # import différé : évite la dépendance au module config

    return settings.chroma_persist_directory


def _default_collection_name() -> str:
    from app.core.config import settings

    return settings.chroma_collection_name


def _similarity_from_distance(distance: float, space: str) -> Optional[float]:
    """Convertit la distance ChromaDB en similarité, selon l'espace de la collection.

    Espace cosine : distance = 1 - similarité_cosinus. Pour tout autre espace
    (l2, ip), la conversion n'est pas directe et on renvoie ``None``.
    """
    if space == "cosine":
        return 1.0 - distance
    return None


class Retriever:
    """Récupère les chunks les plus pertinents pour une question utilisateur."""

    def __init__(
        self,
        persist_directory: Optional[str | Path] = None,
        collection_name: Optional[str] = None,
        embedding_service: Optional[Any] = None,
        store: Optional[ChromaStore] = None,
    ):
        """Construit un retriever sur une collection ChromaDB.

        ``store`` permet d'injecter un mock pour les tests ; sinon on construit
        un ``ChromaStore`` avec les valeurs données (ou la configuration par
        défaut). ``embedding_service`` permet aussi d'injecter un mock ; par
        défaut on réutilise ``E5EmbeddingService`` (modèle chargé une fois).
        """
        if store is not None:
            self._store = store
        else:
            persist_directory = persist_directory if persist_directory is not None else _default_persist_directory()
            collection_name = collection_name if collection_name is not None else _default_collection_name()
            from app.core.config import settings

            self._store = ChromaStore(
                persist_directory,
                collection_name,
                expected_dimension=settings.embedding_dimension,
            )
        self._embedding_service = (
            embedding_service if embedding_service is not None else E5EmbeddingService()
        )

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Recherche les ``top_k`` chunks les plus proches de ``query``.

        Pipeline hybride :
        1. Recherche dense E5 comme générateur de candidats.
        2. Si la requête contient des numéros de décision (ex: N° 010/2026),
           les chunks contenant exactement l'identifiant reçoivent la priorité,
           en conservant leur ordre dense entre eux.
        3. Si aucun numéro de décision n'est détecté, le comportement est
           strictement équivalent à la recherche dense pure.

        Retourne une liste de dictionnaires contenant :
        ``text``, ``score``, ``distance``, ``doc_id``, ``file_name``,
        ``file_path``, ``page_number``, ``chunk_index``, ``chunk_id``.

        Raises:
            ValueError: si ``query`` est vide.
            RuntimeError: si la requête ChromaDB ou l'embedding échoue
                (erreur propagée à la couche RAG qui la mappe en HTTP 500).
        """
        if not query or not query.strip():
            raise ValueError("La question ne peut pas être vide.")

        decision_ids = extract_decision_identifiers(query)

        # Si un identifiant de décision est présent, on élargit le pool de candidats
        # pour s'assurer que le chunk cible est inclus même s'il est mal classé en dense.
        if decision_ids:
            try:
                doc_count = self._store.count()
            except Exception:
                doc_count = 50
            candidate_k = min(doc_count, max(top_k * 4, 50)) if doc_count > 0 else max(top_k, 20)
        else:
            candidate_k = top_k

        query_embedding = self._embedding_service.embed_texts([query], prefix=_QUERY_PREFIX)

        try:
            result = self._store.query(query_embeddings=query_embedding, n_results=candidate_k)
        except Exception as exc:
            raise RuntimeError(
                f"Erreur lors de l'interrogation de la base vectorielle : {exc}"
            ) from exc

        items = self._format_results(result, self._store.space())

        # SNAPSHOT 1: résultats bruts immédiatement après _format_results (avant reranking)
        logger.debug(
            "[retriever] SNAPSHOT_1_raw_results query=%r top_k=%s candidate_k=%s count=%s",
            query, top_k, candidate_k, len(items)
        )
        for idx, item in enumerate(items, start=1):
            logger.debug(
                "[retriever]   RAW #%s file=%s page=%s score=%.4f dist=%.4f chunk_idx=%s chunk_id=%s",
                idx,
                item.get("file_name"),
                item.get("page_number"),
                item.get("score"),
                item.get("distance"),
                item.get("chunk_index"),
                item.get("chunk_id"),
            )

        # Si aucun identifiant n'est présent dans la requête : repli dense pur transparent
        if not decision_ids:
            logger.debug(
                "[retriever] No decision_ids - returning dense results (top %s)",
                top_k
            )
            return items[:top_k]

        # Réordonnancement hybride : priorité aux chunks contenant l'identifiant exact
        matching_items = []
        non_matching_items = []
        for item in items:
            if _matches_any_decision(item.get("text", ""), decision_ids):
                matching_items.append(item)
            else:
                non_matching_items.append(item)

        matching_items.sort(key=lambda x: x["distance"])
        non_matching_items.sort(key=lambda x: x["distance"])

        reranked = matching_items + non_matching_items

        # SNAPSHOT 2: résultats après reranking hybride
        logger.debug(
            "[retriever] SNAPSHOT_2_after_rerank query=%r decision_ids=%s "
            "matching=%s non_matching=%s final_count=%s",
            query, decision_ids, len(matching_items), len(non_matching_items), min(len(reranked), top_k)
        )
        for idx, item in enumerate(reranked[:top_k], start=1):
            logger.debug(
                "[retriever]   RERANKED #%s file=%s page=%s score=%.4f dist=%.4f chunk_idx=%s chunk_id=%s",
                idx,
                item.get("file_name"),
                item.get("page_number"),
                item.get("score"),
                item.get("distance"),
                item.get("chunk_index"),
                item.get("chunk_id"),
            )

        return reranked[:top_k]

    @staticmethod
    def _format_results(result: Dict[str, Any], space: str) -> List[Dict[str, Any]]:
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        items: List[Dict[str, Any]] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            metadata = metadata or {}
            items.append(
                {
                    "text": text,
                    "distance": float(distance),
                    "score": _similarity_from_distance(float(distance), space),
                    "doc_id": metadata.get("doc_id", ""),
                    "file_name": metadata.get("file_name", ""),
                    "file_path": metadata.get("file_path", ""),
                    "page_number": metadata.get("page_number"),
                    "chunk_index": metadata.get("chunk_index"),
                    "chunk_id": metadata.get("chunk_id", chunk_id),
                }
            )
        return items


_default_retriever: Optional[Retriever] = None


def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Fonction de commodité : réutilise un ``Retriever`` par défaut.

    Le modèle E5 est chargé une seule fois par processus et partagé entre
    toutes les requêtes (pas de rechargement à chaque appel).
    """
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = Retriever()
    return _default_retriever.retrieve(query, top_k=top_k)

