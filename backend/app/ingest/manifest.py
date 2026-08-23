import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class IngestionManifest:
    """Simple JSON manifest to track indexed documents and avoid unnecessary reindexing."""

    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.manifest_path.exists():
            return {}

        try:
            with self.manifest_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _save(self, state: Dict[str, Dict[str, Any]]) -> None:
        """Écrit le manifest de façon atomique (temp + rename).

        Si le processus est interrompu pendant l'écriture, seul le fichier
        temporaire est corrompu ; le manifest original reste intact.
        """
        import os
        import tempfile

        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.manifest_path.parent),
            suffix=".tmp",
            prefix=".manifest_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            # Replace atomiquement (sur la plupart des filesystems).
            os.replace(tmp_path, str(self.manifest_path))
        except BaseException:
            # Nettoyage en cas d'erreur (fichier temporaire abandonné).
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _file_key(file_path: str | Path) -> str:
        return str(Path(file_path).resolve())

    @staticmethod
    def compute_file_hash(file_path: str | Path) -> str:
        hasher = hashlib.sha256()
        with Path(file_path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_record(self, file_path: str | Path) -> Optional[Dict[str, Any]]:
        return self._load().get(self._file_key(file_path))

    def should_index(self, file_path: str | Path) -> bool:
        record = self.get_record(file_path)
        if not record:
            return True

        current_hash = self.compute_file_hash(file_path)
        return record.get("file_hash") != current_hash

    def mark_indexed(
        self,
        file_path: str | Path,
        doc_id: str,
        chunk_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        state = self._load()
        file_key = self._file_key(file_path)
        state[file_key] = {
            "file_path": str(file_path),
            "file_hash": self.compute_file_hash(file_path),
            "doc_id": doc_id,
            "chunk_count": chunk_count,
            "last_indexed_at": int(time.time()),
            "metadata": metadata or {},
        }
        self._save(state)
