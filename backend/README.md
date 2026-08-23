# GCT AI Assistant - Backend

Assistant IA métier local pour le Groupe Chimique Tunisien (GCT).

## Structure du Projet

```
backend/
├── app/                    # Application principale
│   ├── api/               # Routes et endpoints API (auth, schemas, routes)
│   ├── core/              # Configuration et utilitaires centraux
│   ├── rag/               # Logique RAG (Retrieval-Augmented Generation)
│   ├── llm/               # Interface avec Ollama
│   ├── ingest/            # Pipeline d'ingestion (extraction, OCR, chunking, embeddings, ChromaDB)
│   ├── retrieval/         # Logique de récupération (E5 + ChromaDB)
│   └── utils/             # Utilitaires divers (PDF extraction)
├── data/                  # Données
│   ├── documents/         # Documents métier à indexer
│   └── chroma/            # Base de données vectorielle
├── tests/                 # Tests unitaires et d'intégration
├── scripts/               # Scripts utilitaires
├── docs/                  # Documentation
├── venv/                  # Environnement virtuel Python
├── requirements.txt       # Dépendances Python
├── .env.example          # Exemple de configuration
└── .gitignore            # Fichiers ignorés par Git
```

## Installation

1. Créer l'environnement virtuel :
```bash
python -m venv venv
```

2. Activer l'environnement :
```bash
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer l'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

## Technologies

- **FastAPI**: Framework web ASGI pour l'API REST
- **Ollama**: LLM local (Mistral)
- **ChromaDB**: Base de données vectorielle
- **Sentence Transformers**: Embeddings (intfloat/multilingual-e5-small, 384 dimensions)
- **Tesseract OCR**: Reconnaissance optique de caractères (ara, fra, eng)
