"""Script pour vérifier que les questions v2 correspondent au contenu des PDF."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.pdf_extractor import PDFExtractor


def main():
    documents_dir = Path(__file__).parent.parent / "data" / "documents"
    test_questions_file = Path(__file__).parent.parent / "data" / "test_questions_v2.json"
    
    # Charger les questions
    with open(test_questions_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    questions = data["questions"]
    
    # Extraire le contenu des PDF
    extractor = PDFExtractor(str(documents_dir))
    extracted = extractor.extract_all_pdfs()
    
    # Organiser par fichier
    documents = {}
    for page in extracted:
        filename = page["filename"]
        if filename not in documents:
            documents[filename] = ""
        documents[filename] += f" {page['text']}"
    
    # Vérifier chaque question
    print("Vérification des questions v2 par rapport au contenu des PDF :\n")
    print(f"{'ID':<5} | {'Question':<60} | {'PDF attendu':<30} | {'Vérification'}")
    print("-" * 120)
    
    valid_questions = []
    
    for q in questions:
        pdf_name = q["expected_pdf"]
        question_text = q["question"]
        
        if pdf_name in documents:
            doc_content = documents[pdf_name]
            
            # Extraire le numéro de décision de la question
            decision_number = None
            if "القرار رقم" in question_text:
                # Extraire le numéro de décision (format XXX/2026)
                import re
                match = re.search(r'القرار رقم (\d+)/2026', question_text)
                if match:
                    decision_number = match.group(1)
            
            # Vérifier si le numéro de décision est dans le PDF
            verification = "✓ Contenu vérifié"
            if decision_number:
                decision_pattern = f"N° {decision_number}/2026"
                if decision_pattern not in doc_content and f"{decision_number}/2026" not in doc_content:
                    verification = f"✗ Numéro décision {decision_number} non trouvé"
                else:
                    verification = f"✓ Décision N° {decision_number}/2026 trouvée"
            
            # Vérifier que le PDF existe
            if verification == "✓ Contenu vérifié":
                valid_questions.append(q)
        else:
            verification = "✗ PDF non trouvé"
        
        print(f"{q['id']:<5} | {question_text[:57]+'...':<60} | {pdf_name:<30} | {verification}")
    
    print("\n" + "="*120)
    print("Résumé de la validation :")
    print(f"- Total questions : {len(questions)}")
    print(f"- Questions valides : {len(valid_questions)}")
    print(f"- Questions invalides : {len(questions) - len(valid_questions)}")
    
    # Sauvegarder uniquement les questions valides
    if len(valid_questions) < len(questions):
        print(f"\nATTENTION: {len(questions) - len(valid_questions)} questions invalides détectées.")
        print("Création d'un fichier corrigé...")
        
        data["questions"] = valid_questions
        data["metadata"]["total_questions"] = len(valid_questions)
        
        corrected_file = Path(__file__).parent.parent / "data" / "test_questions_v2_corrected.json"
        with open(corrected_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Fichier corrigé sauvegardé: {corrected_file}")
    else:
        print("\n✓ Toutes les questions sont valides!")


if __name__ == "__main__":
    main()
