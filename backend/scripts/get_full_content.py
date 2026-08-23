"""Script pour obtenir le contenu complet de PDF spécifiques."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.pdf_extractor import PDFExtractor


def main():
    documents_dir = Path(__file__).parent.parent / "data" / "documents"
    
    extractor = PDFExtractor(str(documents_dir))
    
    # Vérifier les PDF 16-25
    pdfs_to_check = [
        "GCT_notes_exemples_50-16.pdf",
        "GCT_notes_exemples_50-17.pdf", 
        "GCT_notes_exemples_50-18.pdf",
        "GCT_notes_exemples_50-19.pdf",
        "GCT_notes_exemples_50-20.pdf",
        "GCT_notes_exemples_50-21.pdf",
        "GCT_notes_exemples_50-22.pdf",
        "GCT_notes_exemples_50-23.pdf",
        "GCT_notes_exemples_50-24.pdf",
        "GCT_notes_exemples_50-25.pdf"
    ]
    
    for pdf_name in pdfs_to_check:
        pdf_path = Path(documents_dir) / pdf_name
        if pdf_path.exists():
            extracted = extractor.extract_text_from_pdf(pdf_path)
            print(f"\n{'='*80}")
            print(f"FICHIER: {pdf_name}")
            print(f"{'='*80}")
            for page in extracted:
                print(page['text'])
        else:
            print(f"\n{pdf_name} n'existe pas")


if __name__ == "__main__":
    main()
