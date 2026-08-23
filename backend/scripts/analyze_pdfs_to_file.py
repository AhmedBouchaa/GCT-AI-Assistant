"""Script pour analyser le contenu des 50 PDF et écrire dans un fichier."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.pdf_extractor import PDFExtractor


def main():
    documents_dir = Path(__file__).parent.parent / "data" / "documents"
    output_file = Path(__file__).parent.parent / "data" / "pdf_content_analysis.txt"
    
    extractor = PDFExtractor(str(documents_dir))
    extracted = extractor.extract_all_pdfs()
    
    # Organiser par fichier
    documents = {}
    for page in extracted:
        filename = page["filename"]
        if filename not in documents:
            documents[filename] = ""
        documents[filename] += f"\n--- Page {page['page_number']} ---\n{page['text']}"
    
    # Écrire dans un fichier avec encodage UTF-8
    with open(output_file, 'w', encoding='utf-8') as f:
        for filename in sorted(documents.keys()):
            f.write(f"\n{'='*80}\n")
            f.write(f"FICHIER: {filename}\n")
            f.write(f"{'='*80}\n")
            f.write(documents[filename])
            f.write(f"\n{'='*80}\n")
    
    print(f"Contenu écrit dans {output_file}")


if __name__ == "__main__":
    main()
