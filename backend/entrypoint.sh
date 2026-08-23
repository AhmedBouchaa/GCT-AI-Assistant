#!/bin/sh
# Peuple le volume /app/data (ChromaDB, documents, manifest, tessdata OCR) à
# partir du snapshot de l'image au premier démarrage, puis lance le serveur.
#
# Utilise un fichier marqueur (.seeded) pour distinguer « premier démarrage »
# de « corruption partielle ».  Un AND/OR sur la présence des fichiers ne
# peut pas faire la différence : le marqueur est la seule source fiable.
set -e

SEEDED_MARKER="/app/data/.seeded"

if [ ! -f "$SEEDED_MARKER" ]; then
  echo "[entrypoint] Première initialisation — copie du snapshot vers /app/data..."
  mkdir -p /app/data
  cp -r /app/data-seed/. /app/data/
  touch "$SEEDED_MARKER"
fi

exec "$@"
