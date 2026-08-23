"""Module d'extraction de texte depuis des fichiers PDF."""
from pathlib import Path
from typing import List, Dict
from pypdf import PdfReader


class PDFExtractor:
    """Classe responsable de l'extraction de texte depuis les fichiers PDF."""
    
    def __init__(self, documents_directory: str):
        """
        Initialise l'extracteur PDF avec le répertoire des documents.
        
        Args:
            documents_directory: Chemin vers le dossier contenant les fichiers PDF
        """
        self.documents_directory = Path(documents_directory)
    
    def get_pdf_files(self) -> List[Path]:
        """
        Récupère tous les fichiers PDF dans le répertoire de documents.
        
        Returns:
            Liste des chemins vers les fichiers PDF trouvés
        """
        if not self.documents_directory.exists():
            raise FileNotFoundError(
                f"Le répertoire {self.documents_directory} n'existe pas"
            )
        
        pdf_files = list(self.documents_directory.glob("*.pdf"))
        return pdf_files
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[Dict[str, any]]:
        """
        Extrait le texte page par page depuis un fichier PDF.
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Liste de dictionnaires contenant:
            - filename: nom du fichier
            - page_number: numéro de la page
            - text: texte extrait de la page
        """
        reader = PdfReader(str(pdf_path))
        extracted_pages = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            extracted_pages.append({
                "filename": pdf_path.name,
                "page_number": page_num,
                "text": text
            })
        
        return extracted_pages
    
    def extract_all_pdfs(self) -> List[Dict[str, any]]:
        """
        Extrait le texte de tous les fichiers PDF dans le répertoire.
        
        Returns:
            Liste de tous les dictionnaires (filename, page_number, text)
            pour tous les PDF trouvés
        """
        pdf_files = self.get_pdf_files()
        all_extracted = []
        
        for pdf_file in pdf_files:
            try:
                extracted = self.extract_text_from_pdf(pdf_file)
                all_extracted.extend(extracted)
            except Exception as e:
                print(f"Erreur lors de l'extraction de {pdf_file.name}: {e}")
        
        return all_extracted
