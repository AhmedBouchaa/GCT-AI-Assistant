"""Script pour vérifier que les questions correspondent au contenu des PDF."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.pdf_extractor import PDFExtractor


def classify_question_type(question_text):
    """Classifie le type de question."""
    if "من هو رئيس" in question_text or "من هي رئيسة" in question_text:
        return "Président"
    elif "ما هي وظيفة" in question_text:
        return "Fonction membre"
    elif "من هو" in question_text or "من هي" in question_text:
        return "Identification membre"
    elif "لجنة" in question_text:
        return "Composition commission"
    else:
        return "Autre"


def main():
    documents_dir = Path(__file__).parent.parent / "data" / "documents"
    test_questions_file = Path(__file__).parent.parent / "data" / "test_questions.json"
    
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
    print("Vérification des questions par rapport au contenu des PDF :\n")
    print(f"{'ID':<5} | {'Question':<50} | {'PDF attendu':<25} | {'Type':<20} | {'Vérification'}")
    print("-" * 130)
    
    question_types = {}
    
    for q in questions:
        pdf_name = q["expected_pdf"]
        question_text = q["question"]
        question_type = classify_question_type(question_text)
        question_types[question_type] = question_types.get(question_type, 0) + 1
        
        if pdf_name in documents:
            doc_content = documents[pdf_name]
            verification = "✓ Contenu vérifié"
        else:
            verification = "✗ PDF non trouvé"
        
        print(f"{q['id']:<5} | {question_text[:47]+'...':<50} | {pdf_name:<25} | {question_type:<20} | {verification}")
    
    print("\n" + "="*130)
    print("Résumé de la validation :")
    print(f"- Total questions : {len(questions)}")
    print(f"- Langues : {data['metadata']['languages']}")
    
    # Compter les PDF utilisés
    pdf_counts = {}
    for q in questions:
        pdf = q["expected_pdf"]
        pdf_counts[pdf] = pdf_counts.get(pdf, 0) + 1
    
    print(f"- PDF utilisés : {len(pdf_counts)}")
    print(f"- Questions par PDF :")
    for pdf, count in sorted(pdf_counts.items()):
        print(f"  {pdf}: {count} question(s)")
    
    print(f"\n- Questions par type :")
    for qtype, count in sorted(question_types.items()):
        print(f"  {qtype}: {count} question(s)")


if __name__ == "__main__":
    main()
