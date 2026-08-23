"""Configuration de l'application."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration principale de l'application."""
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    # Modèle installé sur le serveur local détecté (general-purpose). Ajuster
    # via .env (OLLAMA_MODEL) si d'autres modèles sont installés.
    ollama_model: str = "mistral:latest"

    # Options runtime Ollama transmises à chaque génération :
    # - keep_alive : durée de maintien du modèle en mémoire après la réponse
    #   (ex: "1m" = 1 minute ; vide = défaut du serveur Ollama). Sur cette
    #   machine 8 Go, "1m" décharge mistral ~1 min après la réponse, libérant
    #   ~5 Go entre requêtes.
    # - num_ctx : fenêtre de contexte. 4096 est le minimum sûr pour le prompt
    #   RAG complet (~3198 tokens avec top_k=5) ; 2048 TRONQUE le contexte.
    ollama_keep_alive: Optional[str] = "1m"
    ollama_num_ctx: Optional[int] = 4096
    # - num_predict : max tokens to generate (reduced for faster generation on 8GB RAM)
    ollama_num_predict: Optional[int] = 128

    # Embeddings (source unique pour ingestion ET retrieval)
    embedding_model: str = "intfloat/multilingual-e5-small"
    # Dimension des embeddings du modèle configuré (utilisé pour la validation
    # ChromaDB : si la collection contient des embeddings de dimension différente,
    # une erreur claire est levée au lieu de résultats silencieusement invalides).
    embedding_dimension: int = 384

    # ChromaDB Configuration
    chroma_persist_directory: str = "./data/chroma"
    # Collection active (indexée avec embeddings e5-small, 384 dims).
    # Rollback possible : repasser à "gct_documents" (ancien index 1024 dims).
    chroma_collection_name: str = "gct_documents_v2"

    # Ingestion (documents PDF + manifest)
    documents_dir: str = "./data/documents"
    ingestion_manifest_path: str = "./data/ingestion_manifest.json"

    # OCR (Tesseract local) — langues + binaire
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ocr_languages: str = "ara+fra+eng"
    ocr_timeout: int = 120

    # Authentification locale (léger, Bearer token). Tokens via .env — jamais
    # dans le code. auth_enabled=False désactive l'auth (développement local).
    auth_enabled: bool = True
    auth_admin_token: str = ""
    auth_user_tokens: str = ""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    # CORS : liste d'origines séparées par des virgules (défaut : serveur de
    # développement frontend Vite). Vide = désactivé.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    # Ollama timeout (secondes) — protège contre les générations bloquées
    # (mémoire insuffisante, modèle en-thrashing sur 8 Go RAM).
    # httpx.Timeout s'applique à toutes les requêtes HTTP vers Ollama.
    ollama_timeout: int = 900

    # RAG Configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_retrieval: int = 5
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
