"""Couche de génération RAG : retrieval -> contexte -> Ollama -> réponse ancrée.

Réutilise UNIQUEMENT la couche de récupération existante (``app.retrieval.retrieve``)
et le client Ollama local (``app.generation.ollama_client``). N'introduit ni
chunking, ni modèle d'embedding, ni base vectorielle supplémentaire.

Flux :
    question
        -> retrieve()  (couche existante, E5 + ChromaDB, instance lazy partagée)
        -> construction du contexte [Document]/[Page]/[Similarité]/[texte]
        -> prompt système ancré (anti-hallucination) + prompt utilisateur
        -> Ollama / mistral:latest (local)
        -> réponse + sources dédupliquées

Contraintes respectées :
- réponse STRICTEMENT fondée sur le contexte récupéré ;
- si le contexte est vide (ou le score insuffisant), message « non trouvé »
  explicite SANS interroger Ollama ;
- même langue que la question ;
- mention de la source (document + page) quand c'est possible.
"""
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from app.core.config import settings
from app.generation.ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaUnavailableError,
)
from app.retrieval.retriever import extract_decision_identifiers

logger = logging.getLogger(__name__)

# Caractères arabes (plage Unicode de base + extensions).
_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")


def _is_arabic(text: str) -> bool:
    """Indique si un texte contient des caractères arabes."""
    return bool(_ARABIC_RE.search(text or ""))


# Prompt système (français, « Arabic/French-friendly ») : assistant interne GCT.
# Imposé en tant qu'instruction de rôle ; garanti l'ancrage sur le contexte.
SYSTEM_PROMPT = (
    "Vous êtes un assistant interne du Groupe Chimique Tunisien (GCT). "
    "Votre rôle est de répondre aux questions des collaborateurs à partir des "
    "documents internes fournis.\n"
    "Règles strictes :\n"
    "1. Répondez UNIQUEMENT à partir du CONTEXTE fourni ci-dessous.\n"
    "2. N'inventez jamais de noms, dates, numéros, procédures ou règles absents "
    "du contexte ; n'utilisez aucune connaissance externe.\n"
    "3. Si le contexte ne permet pas de répondre, dites explicitement que "
    "l'information n'a pas été trouvée dans les documents fournis.\n"
    "4. Répondez dans la MÊME langue que la question de l'utilisateur.\n"
    "5. Soyez concis et professionnel.\n"
    "6. Lorsque c'est possible, citez le document source (nom du fichier et page).\n"
)

# Messages « non trouvé » : adaptés à la langue de la question.
NOT_FOUND_MESSAGE_AR = (
    "لم أجد هذه المعلومة في الوثائق المقدمة. يمكنك طرح سؤال آخر إذا رغبت."
)
NOT_FOUND_MESSAGE_FR = (
    "Je ne trouve pas cette information dans les documents fournis. "
    "N'hésitez pas à poser une autre question."
)


def not_found_message(question: str) -> str:
    """Retourne le message « non trouvé » dans la langue de la question."""
    return NOT_FOUND_MESSAGE_AR if _is_arabic(question) else NOT_FOUND_MESSAGE_FR


def build_context(results: List[Dict[str, Any]]) -> str:
    """Formate les chunks récupérés en blocs normalisés.

    Chaque bloc respecte le format imposé :
        [Document: nom_fichier]
        [Page: numéro_page]
        [Similarité: score]
        [texte]
    """
    blocks = []
    for index, result in enumerate(results, start=1):
        file_name = result.get("file_name", "")
        page_number = result.get("page_number")
        score = result.get("score")
        text = result.get("text", "")
        similarity = f"{score:.4f}" if isinstance(score, (int, float)) else "—"
        page = page_number if page_number is not None else "?"
        blocks.append(
            f"[Document: {file_name}]\n"
            f"[Page: {page}]\n"
            f"[Similarité: {similarity}]\n"
            f"[Texte {index}] :\n{text}"
        )
    return "\n\n".join(blocks)


def build_user_prompt(question: str, results: List[Dict[str, Any]]) -> str:
    """Assemble le prompt utilisateur : contexte récupéré + question."""
    context = build_context(results)
    return (
        f"CONTEXTE :\n{context}\n\n"
        f"QUESTION :\n{question}\n\n"
        "RÉPONSE :"
    )


def _log_retrieved(question: str, results: List[Dict[str, Any]], top_k: int) -> None:
    """Journal de diagnostic : liste les documents récupérés avant génération.

    Consigne CHAQUE résultat intégralement (file_name, page, chunk_id, score,
    distance) pour pouvoir comparer bit à bit avec retrieve() exécuté
    directement et repérer toute déviation (collection / modèle d'embedding).
    """
    logger.debug(
        "[generation] retrieve(question=%r, top_k=%s) -> %s résultat(s)",
        question,
        top_k,
        len(results),
    )
    for idx, r in enumerate(results, start=1):
        logger.debug(
            "[generation]   #%s  file=%s  page=%s  chunk_id=%s  "
            "score=%s  distance=%s",
            idx,
            r.get("file_name"),
            r.get("page_number"),
            r.get("chunk_id"),
            r.get("score"),
            r.get("distance"),
        )


class GenerationError(Exception):
    """Erreur applicative de la couche de génération (message propre, pas de traceback)."""


class GenerationRetrievalError(GenerationError):
    """Échec de la récupération des documents."""


class GenerationUnavailableError(GenerationError):
    """Serveur Ollama injoignable."""


class GenerationOllamaError(GenerationError):
    """Erreur de génération par le modèle Ollama (erreur HTTP/modèle)."""


class GenerationService:
    """Enchaîne retrieval + prompt ancré + génération locale pour répondre."""

    def __init__(
        self,
        retriever: Optional[Callable] = None,
        ollama_client: Optional[OllamaClient] = None,
        min_score: Optional[float] = None,
    ):
        """Construit le service.

        ``retriever`` : appelable ``(question, top_k) -> liste de chunks``. Par
        défaut, la fonction de commodité ``app.retrieval.retrieve`` (instance lazy
        partagée, E5 chargé une seule fois). ``ollama_client`` : client Ollama
        local (par défaut, celui de la configuration). ``min_score`` : seuil de
        similarité optionnel (``None`` = désactivé). Désactivé par défaut car les
        documents sont très proches les uns des autres ; un seuil arbitraire
        risquerait de fausser la réponse.
        """
        if retriever is None:
            from app.retrieval import retrieve as default_retrieve

            retriever = default_retrieve
        self._retrieve = retriever
        self._ollama = ollama_client if ollama_client is not None else OllamaClient()
        self.min_score = min_score
        # Journal de configuration active : permet de confirmer (dans les logs
        # du serveur) que la couche de génération utilise BIEN la même
        # collection / le même modèle / le même répertoire que la récupération
        # directe. Utile pour détecter un serveur démarré avec une config
        # périmée (singleton settings figé au démarrage).
        logger.info(
            "[generation] config active -> collection=%s | embedding_model=%s | "
            "embedding_dim=%s | chroma_persist=%s | ollama=%s/%s",
            settings.chroma_collection_name,
            settings.embedding_model,
            settings.embedding_dimension,
            settings.chroma_persist_directory,
            settings.ollama_base_url,
            settings.ollama_model,
        )

    def answer(
        self,
        question: str,
        top_k: int = 5,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 512,
    ) -> Dict[str, Any]:
        """Répond à ``question`` à partir des documents indexés.

        Retourne ``{"answer", "sources": [{file_name, page_number, score}]}``.

        Comportement :
        - question vide -> ``ValueError`` ;
        - aucun chunk récupéré -> message « non trouvé » SANS appeler Ollama ;
        - ``min_score`` (si configuré) : si le meilleur score est sous le seuil,
          même réponse « non trouvé » ;
        - erreurs mappées en ``GenerationRetrievalError`` / ``GenerationUnavailableError``
          / ``GenerationOllamaError`` (messages propres, sans traceback).
        """
        if not question or not question.strip():
            raise ValueError("La question ne peut pas être vide.")

        # 0) Journal de diagnostic (étape 1-2-9) : question reçue, top_k,
        # fonction de retrieve utilisée, et détection de reranking éventuel.
        decision_ids = extract_decision_identifiers(question)
        logger.debug(
            "[generation] question=%r (len=%s) top_k=%s retrieve=%s.%s "
            "decision_ids=%s",
            question,
            len(question),
            top_k,
            getattr(self._retrieve, "__module__", "?"),
            getattr(self._retrieve, "__qualname__", "?"),
            decision_ids,
        )
        # Si decision_ids n'est pas vide, le retriever applique un reranking
        # hybride (priorité aux chunks contenant l'identifiant exact). Sinon,
        # recherche dense pure — à consigner pour écarter cette piste.
        if decision_ids:
            logger.debug(
                "[generation] reranking hybride ACTIVÉ (decision_ids=%s) : "
                "l'ordre peut différer d'un retrieve() dense simple.",
                decision_ids,
            )

        # 1) Retrieval via la couche existante.
        try:
            results = self._retrieve(question, top_k=top_k)
        except Exception as exc:
            raise GenerationRetrievalError(
                f"Erreur lors de la récupération des documents : {exc}"
            ) from exc

        # SNAPSHOT 1: résultats immédiatement retournés par retrieve()
        logger.debug(
            "[generation] SNAPSHOT_1_post_retrieve question=%r top_k=%s count=%s",
            question, top_k, len(results)
        )
        for idx, r in enumerate(results, start=1):
            logger.debug(
                "[generation]   POST_RETRIEVE #%s file=%s page=%s score=%.4f dist=%.4f chunk_idx=%s chunk_id=%s",
                idx,
                r.get("file_name"),
                r.get("page_number"),
                r.get("score"),
                r.get("distance"),
                r.get("chunk_index"),
                r.get("chunk_id"),
            )

        # 2) Aucun résultat (ou score insuffisant) -> pas de génération.
        if not results:
            logger.info("[generation] retrieve() a renvoyé 0 résultat.")
            return self._not_found(question)
        if self.min_score is not None and isinstance(results[0].get("score"), (int, float)):
            if results[0]["score"] < self.min_score:
                return self._not_found(question)

        # 3) Sources dédupliquées (n'expose que ce dont l'utilisateur a besoin).
        sources = self._build_sources(results)

        # SNAPSHOT 2: sources après déduplication (avant prompt)
        logger.debug(
            "[generation] SNAPSHOT_2_post_dedup question=%r count=%s",
            question, len(sources)
        )
        for idx, s in enumerate(sources, start=1):
            logger.debug(
                "[generation]   DEDUP_SOURCE #%s file=%s page=%s score=%.4f chunk_id=%s",
                idx,
                s.get("file_name"),
                s.get("page_number"),
                s.get("score"),
                s.get("chunk_id"),
            )

        # 3bis) Journal de diagnostic (étapes 3-4-5) : documents réellement
        # récupérés AVANT Ollama, IDs de documents du contexte, et extrait du
        # contexte envoyé à Ollama. Permet de comparer avec retrieve() direct.
        _log_retrieved(question, results, top_k)
        logger.debug(
            "[generation] doc_ids du contexte Ollama = %s",
            [s.get("chunk_id") or (s.get("file_name"), s.get("page_number")) for s in sources],
        )

        # 4) Prompt ancré uniquement sur le contexte récupéré.
        system_prompt = SYSTEM_PROMPT
        user_prompt = build_user_prompt(question, results)

        # SNAPSHOT 3: documents exactement insérés dans le prompt Ollama
        logger.debug(
            "[generation] SNAPSHOT_3_ollama_context question=%r top_k=%s context_len=%s chars",
            question, top_k, len(user_prompt)
        )
        for idx, r in enumerate(results, start=1):
            text_preview = r.get("text", "")[:200].replace("\n", " ")
            logger.debug(
                "[generation]   OLLAMA_CONTEXT #%s file=%s page=%s score=%.4f text=%s",
                idx,
                r.get("file_name"),
                r.get("page_number"),
                r.get("score"),
                text_preview,
            )
        logger.debug(
            "[generation] CONTEXTE envoyé à Ollama (extrait) :\n%s",
            user_prompt[:1200],
        )

        # 5) Génération locale via le client Ollama existant.
        try:
            answer_text = self._ollama.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                num_predict=max_tokens,
            )
        except OllamaUnavailableError as exc:
            raise GenerationUnavailableError(
                f"Le serveur Ollama est injoignable "
                f"({getattr(self._ollama, 'base_url', 'localhost')}). "
                "Veuillez vérifier qu'Ollama est lancé."
            ) from exc
        except OllamaError as exc:
            raise GenerationOllamaError(
                f"Erreur de génération par le modèle Ollama : {exc}"
            ) from exc
        except Exception as exc:  # sécurité : erreur applicative propre
            raise GenerationOllamaError(
                f"Erreur inattendue lors de la génération : {exc}"
            ) from exc

        return {
            "answer": answer_text.strip(),
            "sources": sources,
        }

    @staticmethod
    def _not_found(question: str) -> Dict[str, Any]:
        return {"answer": not_found_message(question), "sources": []}

    @staticmethod
    def _build_sources(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Construit la liste de sources dédupliquée par document (compat chunk_id)."""
        seen = set()
        sources = []
        for result in results:
            doc_id = result.get("doc_id", "")
            chunk_id = result.get("chunk_id", "")
            # 1 unité par PDF : dedup par doc_id (chunk_id alias, fallback file/page).
            key = doc_id or chunk_id or (result.get("file_name", ""), result.get("page_number"))
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                {
                    "file_name": result.get("file_name", ""),
                    "page_number": result.get("page_number"),
                    "score": result.get("score"),
                }
            )
        return sources
