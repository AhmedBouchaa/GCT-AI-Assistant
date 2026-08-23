# Backend GCT AI Assistant (FastAPI + ChromaDB embarquée + Tesseract OCR).
#
# L'image embarque la base de connaissances existante (data/chroma,
# data/documents, manifest, tessdata) ; au premier démarrage l'entrée
# `entrypoint.sh` peuple le volume /app/data depuis un snapshot de l'image
# (aucun rebuild/migration de ChromaDB).
FROM python:3.12-slim

# Tesseract (binaire + langues ara/fra) pour l'OCR local
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-ara \
        tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Code + données de l'application (la base de connaissances est incluse)
COPY . /app

# Snapshot des données pour le peuplement du volume au premier démarrage
RUN mkdir -p /app/data-seed && cp -r /app/data/. /app/data-seed/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Configuration conteneur (surchargeable via environment)
ENV TESSERACT_CMD=/usr/bin/tesseract \
    OLLAMA_BASE_URL=http://ollama:11434 \
    CHROMA_PERSIST_DIRECTORY=./data/chroma \
    CHROMA_COLLECTION_NAME=gct_documents_v2 \
    DOCUMENTS_DIR=./data/documents \
    INGESTION_MANIFEST_PATH=./data/ingestion_manifest.json

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
