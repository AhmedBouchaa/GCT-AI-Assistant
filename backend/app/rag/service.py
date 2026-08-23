"""Service RAG : retrieval -> prompt ancré -> Ollama -> réponse + sources.

Réutilise UNIQUEMENT les couches existantes :
- ``app.retrieval.retrieve`` (instances lazy partagées, E5 chargé une fois) ;
- ``app.llm.OllamaClient`` (modèle configuré, ex: ``mistral:latest``).

Aucun second mécanisme de retrieval, aucun second modèle d'embedding ni LLM.
"""
import logging
from typing import Any, Callable, Dict, List, Optional

from app.llm.ollama_client import OllamaClient, OllamaError, OllamaUnavailableError
from app.rag.prompts import NOT_FOUND_MESSAGE, SYSTEM_PROMPT, build_user_prompt
from app.utils.language_detection import detect_language
from app.utils.language_fixer import has_language_mismatch, enforce_language

logger = logging.getLogger(__name__)


class RAGError(Exception):
    """Erreur applicative de la couche RAG (message propre, pas de traceback)."""


class RAGRetrievalError(RAGError):
    """Échec de la récupération des documents."""


class RAGGenerationError(RAGError):
    """Échec de la génération par le modèle Ollama (erreur HTTP/modèle)."""


class RAGUnavailableError(RAGError):
    """Serveur Ollama injoignable."""


class RAGService:
    """Enchaîne retrieval + prompt ancré + génération locale pour répondre."""

    def __init__(
        self,
        retriever: Optional[Callable] = None,
        ollama_client: Optional[OllamaClient] = None,
        min_score: Optional[float] = None,
    ):
        """Construit le service.

        ``retriever`` : appelable ``(question, top_k) -> liste de chunks``. Par
        défaut, la fonction de commodité ``app.retrieval.retrieve`` qui réutilise
        l'instance lazy partagée (le modèle E5 n'est chargé qu'une fois).
        ``ollama_client`` : client ``OllamaClient`` existant (par défaut, celui
        de la configuration).
        ``min_score`` : seuil de similarité optionnel (``None`` = désactivé).
        Voir la doc de ``answer`` pour la justification.
        """
        if retriever is None:
            from app.retrieval import retrieve as default_retrieve

            retriever = default_retrieve
        self._retrieve = retriever
        self._ollama = ollama_client if ollama_client is not None else OllamaClient()
        self.min_score = min_score

    def answer(
        self,
        question: str,
        top_k: int = 5,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 512,
    ) -> Dict[str, Any]:
        """Répond à ``question`` à partir des documents indexés.

        Retourne un dictionnaire :
        ``{"question", "answer", "sources": [{file_name, page_number, score, chunk_id}]}``

        Comportement :
        - question vide -> ``ValueError`` ;
        - aucun chunk récupéré -> réponse « information non trouvée » SANS
          appeler Ollama ;
        - ``min_score`` (si configuré) : si le meilleur score est inférieur au
          seuil, même réponse « non trouvée » (seuil désactivé par défaut : les
          documents sont proches, un seuil arbitraire risquerait de fausser la
          réponse) ;
        - erreurs : ``RAGRetrievalError`` / ``RAGUnavailableError`` /
          ``RAGGenerationError`` (messages propres, sans traceback).
        - ``max_tokens`` : borne la longueur de la réponse générée
          (``num_predict``) pour éviter des réponses démesurées.
        - **Conformité linguistique** : valide que la réponse est dans la même
          langue que la question (ar/fr/en). Effectue une seule tentative de
          correction si mismatch détecté.

        Raises:
            ValueError: question vide.
            RAGRetrievalError: échec de la récupération.
            RAGUnavailableError: Ollama injoignable.
            RAGGenerationError: erreur de génération du modèle.
        """
        if not question or not question.strip():
            raise ValueError("La question ne peut pas être vide.")

        # 0) Détecte la langue de la question
        question_lang = self._detect_question_language(question)
        logger.debug(f"Detected question language: {question_lang}")

        # 1) Retrieval via la couche existante.
        try:
            results = self._retrieve(question, top_k=top_k)
        except Exception as exc:
            raise RAGRetrievalError(
                f"Erreur lors de la récupération des documents : {exc}"
            ) from exc

        # 2) Aucun résultat (ou score insuffisant) -> pas de génération.
        if not results:
            return self._not_found(question)
        if self.min_score is not None and results[0].get("score") is not None:
            if results[0]["score"] < self.min_score:
                return self._not_found(question)

        logger.debug(f"Retrieved {len(results)} results, top document: {results[0].get('file_name')}")

        # 3) Sources dédupliquées (n'expose que ce dont l'utilisateur a besoin).
        sources = self._build_sources(results)

        # 4) Prompt ancré uniquement sur le contexte récupéré.
        system_prompt = SYSTEM_PROMPT
        user_prompt = build_user_prompt(question, results)

        # 5) Génération locale via le client Ollama existant.
        try:
            answer_text = self._ollama.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                num_predict=max_tokens,
            )
        except OllamaUnavailableError as exc:
            raise RAGUnavailableError(
                f"Le serveur Ollama est injoignable "
                f"({getattr(self._ollama, 'base_url', 'localhost')}). "
                "Veuillez vérifier qu'Ollama est lancé."
            ) from exc
        except OllamaError as exc:
            raise RAGGenerationError(
                f"Erreur de génération par le modèle Ollama : {exc}"
            ) from exc
        except Exception as exc:  # sécurité : erreur applicative propre
            raise RAGGenerationError(
                f"Erreur inattendue lors de la génération : {exc}"
            ) from exc

        # 6) Valide la conformité linguistique
        answer_lang = self._detect_answer_language(answer_text)
        logger.info(
            f"Generated answer ({len(answer_text)} chars, detected language: {answer_lang})"
        )

        if (
            question_lang != "unknown"
            and answer_lang != "unknown"
            and question_lang != answer_lang
        ):
            logger.warning(
                f"Language mismatch: question in {question_lang}, answer in {answer_lang}. "
                "Attempting correction..."
            )
            correction_prompt = self._build_language_correction_prompt(
                question, answer_text, question_lang
            )
            try:
                corrected_answer = self._ollama.generate(
                    prompt=correction_prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    num_predict=max_tokens,
                )
                corrected_lang = self._detect_answer_language(corrected_answer)
                if corrected_lang == question_lang:
                    logger.info(
                        f"Language correction succeeded: now in {corrected_lang}"
                    )
                    answer_text = corrected_answer
                else:
                    logger.warning(
                        f"Language correction did not resolve mismatch "
                        f"(still {corrected_lang}, expected {question_lang}). "
                        "Applying post-processing fix..."
                    )
                    # Post-process to enforce language
                    answer_text = enforce_language(answer_text, question_lang)
            except Exception as exc:
                logger.error(
                    f"Language correction attempt failed: {exc}. "
                    "Applying post-processing fix..."
                )
                # Post-process to enforce language
                answer_text = enforce_language(answer_text, question_lang)
        elif question_lang != "unknown" and has_language_mismatch(answer_text, question_lang):
            logger.warning(
                f"Language mismatch detected by heuristic. "
                "Applying post-processing fix..."
            )
            answer_text = enforce_language(answer_text, question_lang)

        return {
            "question": question,
            "answer": answer_text.strip(),
            "sources": sources,
        }

    @staticmethod
    def _detect_question_language(question: str) -> str:
        """Détecte la langue de la question."""
        return detect_language(question)

    @staticmethod
    def _detect_answer_language(answer: str) -> str:
        """Détecte la langue de la réponse générée."""
        return detect_language(answer)

    @staticmethod
    def _build_language_correction_prompt(
        question: str, previous_answer: str, target_language: str
    ) -> str:
        """Construit un prompt pour corriger la langue de la réponse.

        Demande au modèle de reformuler la réponse dans la langue cible,
        en conservant le contenu et l'information.
        """
        lang_name = {
            "ar": "arabe",
            "fr": "français",
            "en": "anglais",
        }.get(target_language, target_language)

        return (
            f"La question initiale était en {lang_name}.\n\n"
            f"Voici la réponse que vous avez générée :\n{previous_answer}\n\n"
            f"Cependant, cette réponse n'est PAS en {lang_name}. "
            f"Veuillez reformuler cette réponse COMPLÈTEMENT en {lang_name}, "
            f"en conservant exactement le même contenu et information. "
            f"La réponse ENTIÈRE doit être en {lang_name}, sans aucune autre langue.\n\n"
            f"Réponse en {lang_name} :"
        )

    @staticmethod
    def _not_found(question: str) -> Dict[str, Any]:
        return {"question": question, "answer": NOT_FOUND_MESSAGE, "sources": []}

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
                    "chunk_id": chunk_id or doc_id,
                }
            )
        return sources
