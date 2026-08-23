"""Script de test pour l'extraction de texte depuis des PDF."""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.pdf_extractor import PDFExtractor


def main():
    """Fonction principale de test."""
    # Configuration du chemin vers les documents
    documents_dir = Path(__file__).parent.parent / "data" / "documents"
    
    print(f"Répertoire des documents: {documents_dir}")
    print("-" * 50)
    
    # Initialisation de l'extracteur
    extractor = PDFExtractor(str(documents_dir))
    
    # Récupération des fichiers PDF
    pdf_files = extractor.get_pdf_files()
    print(f"Fichiers PDF trouvés: {len(pdf_files)}")
    
    if not pdf_files:
        print("Aucun fichier PDF trouvé dans le répertoire.")
        print("Veuillez placer un fichier PDF dans backend/data/documents/")
        return
    
    for pdf_file in pdf_files:
        print(f"\nTraitement de: {pdf_file.name}")
        print("-" * 50)
        
        # Extraction du texte
        extracted_pages = extractor.extract_text_from_pdf(pdf_file)
        
        print(f"Nombre de pages extraites: {len(extracted_pages)}")
        
        # Affichage du texte extrait pour chaque page
        for page in extracted_pages:
            print(f"\n--- Page {page['page_number']} ---")
            print(f"Texte extrait ({len(page['text'])} caractères):")
            print(page['text'][:200] + "..." if len(page['text']) > 200 else page['text'])
    
    print("\n" + "=" * 50)
    print("Test terminé avec succès!")


if __name__ == "__main__":
    main()
