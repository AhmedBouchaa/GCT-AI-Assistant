"""Script pour résumer le contenu des 50 PDF."""
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
        documents[filename] += f" {page['text']}"
    
    # Afficher un résumé de chaque PDF
    for filename in sorted(documents.keys()):
        text = documents[filename].strip()
        print(f"\n{'='*80}")
        print(f"FICHIER: {filename}")
        print(f"Longueur: {len(text)} caractères")
        print(f"{'='*80}")
        # Afficher les 500 premiers caractères
        print(text[:500])
        if len(text) > 500:
            print("...")
        print(f"{'='*80}")


if __name__ == "__main__":
    main()
