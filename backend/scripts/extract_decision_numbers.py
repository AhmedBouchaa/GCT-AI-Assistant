"""Script pour extraire les numéros de décision de tous les PDF."""
import sys
import re
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
    
    # Extraire les numéros de décision
    decision_numbers = {}
    for filename, text in sorted(documents.items()):
        # Chercher le pattern N° XXX/2026
        match = re.search(r'N°\s*(\d+)/2026', text)
        if match:
            decision_num = match.group(1)
            decision_numbers[filename] = decision_num
            print(f"{filename}: N° {decision_num}/2026")
        else:
            print(f"{filename}: Pas de numéro de décision trouvé")
    
    # Sauvegarder pour référence
    import json
    output_file = Path(__file__).parent.parent / "data" / "decision_numbers.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(decision_numbers, f, ensure_ascii=False, indent=2)
    
    print(f"\nNuméros de décision sauvegardés dans {output_file}")


if __name__ == "__main__":
    main()
