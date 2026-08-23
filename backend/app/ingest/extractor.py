from pathlib import Path
from typing import Any, Dict, List, Optional

from app.ingest.ocr import OCREngine
from app.utils.pdf_extractor import PDFExtractor as BasePDFExtractor


class DocumentExtractor:
    """Wrapper autour de l'extracteur PDF avec détection + OCR des pages scannées.

    Une page est marquée ``requires_ocr`` quand son texte est vide ou trop court
    (< 30 caractères). Si un moteur OCR est disponible, la page est rendue en
    image (PyMuPDF) puis passée à l'OCR : en cas de succès, ``requires_ocr``
    passe à ``False`` et le texte OCR remplace le texte vide. En cas d'échec,
    la page reste ``requires_ocr`` (comptée comme page OCR en échec).
    """

    def __init__(self, documents_dir: str | Path, ocr_engine: Optional[OCREngine] = None):
        self.documents_dir = Path(documents_dir)
        self._ocr_engine = ocr_engine

    def list_pdf_files(self) -> List[Path]:
        if not self.documents_dir.exists():
            return []
        return sorted(self.documents_dir.glob("*.pdf"))

    def extract_pages(self, pdf_path: str | Path) -> List[Dict[str, Any]]:
        extractor = BasePDFExtractor(str(self.documents_dir))
        extracted_pages = extractor.extract_text_from_pdf(Path(pdf_path))

        pages: List[Dict[str, Any]] = []
        for page in extracted_pages:
            text = (page.get("text") or "").strip()
            page_number = page.get("page_number")
            requires_ocr = not text or len(text) < 30
            ocr_used = False

            if requires_ocr and self._ocr_engine is not None and self._ocr_engine.is_available():
                ocr_text = self._render_and_ocr(pdf_path, page_number)
                if ocr_text:
                    text = ocr_text
                    requires_ocr = False
                    ocr_used = True

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                    "requires_ocr": requires_ocr,
                    "ocr": ocr_used,
                }
            )

        return pages

    def _render_and_ocr(self, pdf_path: str | Path, page_number: int) -> Optional[str]:
        """Rend la page en image puis applique l'OCR. Retourne le texte ou None."""
        try:
            import fitz  # PyMuPDF
            from PIL import Image

            document = fitz.open(str(pdf_path))
            try:
                pix = document[page_number - 1].get_pixmap(dpi=150)
            finally:
                document.close()
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return self._ocr_engine.extract_text_from_image(image)
        except Exception:
            return None
