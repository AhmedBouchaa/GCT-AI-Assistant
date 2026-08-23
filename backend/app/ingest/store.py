from pathlib import Path
from typing import Any, Dict, List, Optional


class DimensionMismatchError(Exception):
    """La dimension des embeddings ne correspond pas à la collection ChromaDB."""


class ChromaStore:
    """Thin wrapper around ChromaDB for document chunk storage."""

    def __init__(
        self,
        persist_directory: str | Path,
        collection_name: str = "gct_documents",
        expected_dimension: Optional[int] = None,
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.expected_dimension = expected_dimension
        self._client = None
        self._collection = None
        self._dimension_checked = False

    def _get_client(self):
        import chromadb

        if self._client is None:
            self._client = chromadb.PersistentClient(path=str(self.persist_directory))
        return self._client

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def upsert_chunks(
        self,
        doc_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: Optional[Any] = None,
    ) -> None:
        """Ajoute une unité documentaire (ou, legacy, des chunks) dans la collection.

        Depuis la règle 1-PDF=1-unité : chaque entrée est une unité complète
        (``text`` = contenu intégral du PDF normalisé). ``chunk_id`` est
        conservé comme alias de compatibilité — après la bascule il vaut
        ``doc_id`` (une seule entrée par document) ; la compatibilité avec
        d'anciens chunks ``{doc_id}_p{page}_c{index}`` est préservée.

        Chaque entrée doit contenir au minimum:
        - ``chunk_id`` : alias stable de l'unité (actuellement ``doc_id``);
          l'identifiant final en base est ``{doc_id}:{chunk_id}``.
        - ``text`` : texte complet de l'unité.

        Metadata dérivées : ``doc_id``, ``file_name``, ``file_path``,
        ``chunk_index`` (0), ``page_number`` (1ère page utile), ``chunk_id``.
        """
        if not chunks:
            return

        collection = self._get_collection()
        ids = [f"{doc_id}:{chunk['chunk_id']}" for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "doc_id": chunk.get("doc_id", doc_id),
                "file_name": chunk.get("file_name", ""),
                "file_path": chunk.get("file_path", ""),
                "chunk_index": chunk.get("chunk_index"),
                "page_number": chunk.get("page_number"),
                "chunk_id": chunk.get("chunk_id", ""),
            }
            for chunk in chunks
        ]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def delete_doc(self, doc_id: str) -> None:
        collection = self._get_collection()
        existing = collection.get(where={"doc_id": doc_id}, include=[])
        ids = existing.get("ids", []) if isinstance(existing, dict) else []
        if ids:
            collection.delete(ids=ids)

    def space(self) -> str:
        """Espace de distance configuré pour la collection (ex: ``cosine``)."""
        collection = self._get_collection()
        metadata = collection.metadata or {}
        return metadata.get("hnsw:space", "cosine")

    def query(
        self,
        query_embeddings: Any,
        n_results: int = 5,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Recherche les chunks les plus proches d'un embedding de requête.

        Retourne la structure ChromaDB : ``ids``, ``documents``, ``metadatas``,
        ``distances`` (listes imbriquées, une entrée par requête).

        Si ``expected_dimension`` a été fourni au constructeur, vérifie la
        compatibilité dimension au premier appel (une seule fois).
        """
        collection = self._get_collection()
        self._validate_dimension(query_embeddings)
        return collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            include=include or ["documents", "metadatas", "distances"],
        )

    def _validate_dimension(self, query_embeddings: Any) -> None:
        """Vérifie (une seule fois) que la dimension des embeddings correspond.

        Compare la dimension du premier embedding de requête avec
        ``expected_dimension``.  Lève ``DimensionMismatchError`` en cas
        d'incohérence.  La vérification est faite au premier appel de
        ``query`` et jamais répétée.
        """
        if self._dimension_checked or self.expected_dimension is None:
            return
        self._dimension_checked = True

        try:
            import numpy as np

            emb = np.asarray(query_embeddings)
            actual_dim = int(emb.shape[-1]) if emb.ndim >= 1 else 0
        except Exception:
            return  # incapacité à déterminer la dimension → pas de blocage

        if actual_dim != self.expected_dimension:
            raise DimensionMismatchError(
                f"Dimension des embeddings ({actual_dim}) incompatible avec "
                f"la collection '{self.collection_name}' "
                f"(dimension attendue : {self.expected_dimension}). "
                "Vérifiez CHROMA_COLLECTION_NAME et EMBEDDING_MODEL."
            )

    def count(self) -> int:
        collection = self._get_collection()
        result = collection.get(include=[])
        ids = result.get("ids", []) if isinstance(result, dict) else []
        return len(ids)
