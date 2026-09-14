"""
Diagnostic script to trace the current pipeline and test multi-document behavior.
This script is read-only and does not modify any existing code.
"""

import json
import os
import sys
from pathlib import Path

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.retrieval import retrieve
from app.rag import RAGService
from app.utils.pdf_extractor import PDFExtractor
from app.utils.language_detection import detect_language

# Initialize the PDF extractor for the documents directory
extractor = PDFExtractor('data/documents')

def load_document_text(doc_id):
    """Load the full text of a document given its doc_id (filename without extension)."""
    pdf_path = Path(f'data/documents/{doc_id}.pdf')
    if not pdf_path.exists():
        return None
    pages = extractor.extract_text_from_pdf(pdf_path)
    full_text = "\n".join([page['text'] for page in pages])
    return full_text

def check_relevance(text, keywords):
    """Check if any of the keywords (case-insensitive) are in the text."""
    if not text:
        return False
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False

def safe_print(text):
    """Print text safely, handling unicode characters."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Print a representation that is safe
        print(repr(text))

def test_question(question, expected_keywords=None, case_description=""):
    """Test a single question and return diagnostic information."""
    safe_print(f"\n{'='*60}")
    safe_print(f"Testing question: {repr(question)}")
    safe_print(f"Case: {case_description}")
    safe_print(f"{'='*60}")

    # Detect language
    lang = detect_language(question)
    print(f"\nDetected language: {lang}")

    # Step 1: Retrieval
    print("\n--- RETRIEVAL ---")
    try:
        results = retrieve(question, top_k=5)
        print(f"Retrieved {len(results)} documents:")
        retrieval_info = []
        for i, r in enumerate(results):
            filename = r['file_name']
            score = r['score']
            doc_id = r.get('doc_id', '')
            if not doc_id and filename:
                doc_id = Path(filename).stem
            print(f"  {i+1}. {filename} (score: {score:.4f})")
            # Load document text and check relevance
            text = load_document_text(doc_id)
            relevant = False
            if expected_keywords:
                relevant = check_relevance(text, expected_keywords)
            print(f"      Contains expected keywords? {relevant}")
            if text and len(text) > 200:
                print(f"      Text preview: {text[:200]}...")
            else:
                print(f"      Text preview: {text}")
            retrieval_info.append({
                "index": i+1,
                "filename": filename,
                "doc_id": doc_id,
                "score": score,
                "relevant": relevant
            })
    except Exception as e:
        print(f"Error during retrieval: {e}")
        results = []
        retrieval_info = []

    # Step 2: RAG Service
    print("\n--- RAG SERVICE ---")
    rag = RAGService()
    try:
        rag_result = rag.answer(question, top_k=5)
        print(f"Answer: {rag_result['answer'][:200]}...")
        print(f"Sources returned by RAG service:")
        for i, s in enumerate(rag_result['sources']):
            print(f"  {i+1}. {s['file_name']} (page: {s['page_number']}, score: {s['score']:.4f})")
    except Exception as e:
        print(f"Error during RAG service call: {e}")
        rag_result = {"answer": "", "sources": []}

    # Step 3: Context analysis (what is passed to the LLM)
    print("\n--- CONTEXT ANALYSIS ---")
    print("The RAG service builds context from the retrieved chunks (after deduplication by document).")
    print("It passes ALL retrieved chunks (up to top_k) to the LLM via the prompt.")
    print("The LLM receives:")
    print("  - System prompt (with language instructions)")
    print("  - User prompt: [CONTEXT] + [QUESTION] + [RÉPONSE :]")
    print("Where [CONTEXT] is the concatenation of all retrieved chunks with metadata.")

    # Return structured data for further analysis
    return {
        "question": question,
        "language": lang,
        "retrieved_results": retrieval_info,
        "rag_answer": rag_result.get('answer', ''),
        "rag_sources": rag_result.get('sources', [])
    }

def main():
    # Define test questions for different cases
    test_cases = [
        {
            "question": "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟",
            "expected_keywords": ["طارق بن عثمان", "رئيس", "لجنة السلامة", "20 أكتوبر 2026"],
            "case": "Single document (expected answer in one document)"
        },
        {
            "question": "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟",
            "expected_keywords": ["محمد بن علي", "رئيس", "اللجنة الفنية", "صيانة المعدات الثقيلة"],
            "case": "Single document (expected answer in one document)"
        },
        {
            "question": "ما هو عدد المرات التي تم فيها تجديد العقد مع شركة XYZ بين عامي 2020 و 2023؟",
            "expected_keywords": ["عقد", "شركة XYZ", "2020", "2023", "تجديد"],
            "case": "Possible multi-document (if information spans multiple years)"
        },
        {
            "question": "قارن بين رئيس اللجنة الأولى ورئيس اللجنة الثانية في عام 2025",
            "expected_keywords": ["رئيس", "اللجنة الأولى", "اللجنة الثانية", "2025", "مقارنة"],
            "case": "Comparison question (requires two documents)"
        },
        {
            "question": "ما هي الإجراءات المتخذة لسلامة العاملين في المجمع الكيميائي التونسي خلال جائحة كوفيد-19؟",
            "expected_keywords": ["إجراءات", "سلامة", "العاملين", "المجمع الكيميائي", "كوفيد-19"],
            "case": "Possible multi-document (if information spread across multiple notes)"
        }
    ]

    all_results = []
    for test in test_cases:
        result = test_question(
            test["question"],
            expected_keywords=test.get("expected_keywords"),
            case_description=test["case"]
        )
        all_results.append(result)

    # Write results to a file for later analysis
    output_path = Path('diagnostic_results.json')
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Diagnostic complete. Results written to {output_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()