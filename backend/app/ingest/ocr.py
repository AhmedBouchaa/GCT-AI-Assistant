"""Moteur OCR local (Tesseract) pour les pages scannées.

Utilisé par ``DocumentExtractor`` pour transformer une page sans texte
extractible (``requires_ocr``) en texte utilisable, avant le chunking.
Léger en RAM (~200-400 Mo), totalement local, langues ara+fra+eng.

Le binaire Tesseract est installé séparément (winget : UB-Mannheim.TesseractOCR)
et les données de langue (traineddata) vivent dans ``data/tessdata``
(ara, eng, fra, osd). Le moteur est chargé paresseusement : ``is_available()``
n'est vérifié que lorsqu'une page scannée est détectée.
"""
from pathlib import Path
from typing import Optional

from app.core.config import settings

# parents[2] = backend (ce module vit dans backend/app/ingest/).
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TESSDATA_DIR = BACKEND_DIR / "data" / "tessdata"
# Chemin par défaut de l'installation Tesseract (winget, machine scope).
DEFAULT_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class OCRError(Exception):
    """Échec de l'OCR d'une page (impossible ou texte vide)."""


class OCREngine:
    """OCR local via Tesseract (pytesseract). Lazy et léger."""

    def __init__(
        self,
        languages: Optional[str] = None,
        tesseract_cmd: Optional[str] = None,
        tessdata_dir: Optional[str | Path] = None,
        timeout: Optional[int] = None,
    ):
        self.languages = languages or settings.ocr_languages
        self.tesseract_cmd = tesseract_cmd or settings.tesseract_cmd or DEFAULT_TESSERACT_CMD
        self.tessdata_dir = Path(tessdata_dir or DEFAULT_TESSDATA_DIR)
        self.timeout = timeout if timeout is not None else settings.ocr_timeout
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Vérifie (une seule fois) que le binaire Tesseract et les traineddata
        des langues configurées sont présents. (``pytesseract.get_languages``
        étant peu fiable, on vérifie les fichiers directement.)"""
        if self._available is None:
            try:
                binary_ok = Path(self.tesseract_cmd).exists() or (
                    __import__("shutil").which(self.tesseract_cmd) is not None
                )
                present = {p.stem for p in self.tessdata_dir.glob("*.traineddata")}
                self._available = binary_ok and all(
                    lang in present for lang in self.languages.split("+")
                )
            except Exception:
                self._available = False
        return self._available

    def extract_text_from_image(self, image) -> str:
        """OCR une image (PIL.Image) et retourne le texte.

        Lève ``OCRError`` si Tesseract échoue, si le timeout est dépassé,
        ou si aucun texte n'est produit.
        """
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        try:
            text = pytesseract.image_to_string(
                image,
                lang=self.languages,
                config=f"--tessdata-dir {self.tessdata_dir}",
                timeout=self.timeout,
            )
        except Exception as exc:
            raise OCRError(f"Échec OCR : {exc}") from exc
        if not text or not text.strip():
            raise OCRError("OCR n'a produit aucun texte.")
        return text.strip()
