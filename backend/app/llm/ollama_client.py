"""Service LLM local générique via Ollama.

Ce module est volontairement générique et isolé du domaine GCT : il ne connaît
ni les PDF, ni ChromaDB, ni le retrieval, ni les questions de benchmark. Son
unique rôle est : prompt -> serveur Ollama local -> réponse générée.

Utilise le client Python ``ollama`` (``ollama.Client``) installé dans
l'environnement. Le timeout HTTP est configurable via ``settings.ollama_timeout``
et passe au ``httpx.Client`` sous-jacent (``ollama.Client(**kwargs)``).
"""
from typing import List, Optional

from app.core.config import settings


class OllamaError(Exception):
    """Le serveur Ollama a répondu avec une erreur (HTTP anormale, modèle inconnu...)."""


class OllamaUnavailableError(OllamaError):
    """Le serveur Ollama est injoignable (arrêté, connexion refusée, timeout)."""


class OllamaClient:
    """Client minimal vers un serveur Ollama local.

    Ne contient aucune logique métier : uniquement prompt -> réponse.
    Le timeout HTTP est pass ``httpx.Client`` via le constructeur.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        keep_alive: Optional[str] = None,
        num_ctx: Optional[int] = None,
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.keep_alive = keep_alive if keep_alive is not None else settings.ollama_keep_alive
        self.num_ctx = num_ctx if num_ctx is not None else settings.ollama_num_ctx
        self._client = None
        self._ollama = None

    def _get_client(self):
        if self._client is None:
            import ollama

            self._ollama = ollama
            self._client = ollama.Client(
                host=self.base_url,
                timeout=settings.ollama_timeout,
            )
        return self._client

    def list_models(self) -> List[str]:
        """Noms des modèles actuellement installés sur le serveur local."""
        try:
            response = self._get_client().list()
        except Exception as exc:
            raise self._classify_error(exc) from exc
        return [item.model for item in response["models"]]

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        num_predict: Optional[int] = None,
    ) -> str:
        """Envoie ``prompt`` à Ollama et retourne le texte généré.

        Args:
            prompt: Prompt utilisateur (non vide).
            system_prompt: Prompt système optionnel (instructions de rôle).
            temperature: Température d'échantillonnage (0.0 = déterministe).
            num_predict: Nombre maximal de tokens à générer (défaut: Ollama).

        Raises:
            ValueError: si ``prompt`` est vide.
            OllamaError: si le serveur renvoie une erreur HTTP.
            OllamaUnavailableError: si le serveur est injoignable.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Le prompt ne peut pas être vide.")

        options = {"temperature": temperature}
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx
        if num_predict is not None:
            options["num_predict"] = num_predict

        generate_kwargs = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "options": options,
        }
        if self.keep_alive is not None:
            generate_kwargs["keep_alive"] = self.keep_alive

        try:
            response = self._get_client().generate(**generate_kwargs)
        except Exception as exc:
            raise self._classify_error(exc) from exc
        return response.response

    def _classify_error(self, exc: Exception) -> OllamaError:
        """Classe une exception en erreur Ollama (HTTP) ou serveur injoignable."""
        if self._ollama is not None and isinstance(exc, self._ollama.ResponseError):
            return OllamaError(
                f"Ollama a renvoyé une erreur HTTP sur {self.base_url} "
                f"(modèle '{self.model}') : {exc}"
            )
        # Timeout httpx → indisponible (même classe que connexion refusée).
        try:
            import httpx

            if isinstance(exc, httpx.TimeoutException):
                return OllamaUnavailableError(
                    f"Timeout après {settings.ollama_timeout}s — "
                    f"Ollama sur {self.base_url} (modèle '{self.model}') : {exc}"
                )
        except ImportError:
            pass
        return OllamaUnavailableError(
            f"Impossible de contacter Ollama sur {self.base_url} "
            f"(modèle '{self.model}') : {exc}"
        )
