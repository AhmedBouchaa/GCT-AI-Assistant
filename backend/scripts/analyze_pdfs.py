"""Script pour analyser le contenu des 50 PDF et créer les questions de benchmark."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.pdf_extractor import PDFExtractor


def main():
    documents_dir = Path(__file__).parent.parent / "data" / "documents"
    
    extractor = PDFExtractor(str(documents_dir))
    extracted = extractor.extract_all_pdfs()
    
    # Organiser par fichier
    documents = {}
    for page in extracted:
        filename = page["filename"]
        if filename not in documents:
            documents[filename] = ""
        documents[filename] += f"\n--- Page {page['page_number']} ---\n{page['text']}"
    
    # Afficher le contenu de chaque PDF
    for filename in sorted(documents.keys()):
        print(f"\n{'='*80}")
        print(f"FICHIER: {filename}")
        print(f"{'='*80}")
        print(documents[filename])
        print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
