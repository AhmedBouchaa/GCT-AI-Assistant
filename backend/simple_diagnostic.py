"""
Simple diagnostic script to trace the current pipeline without terminal output issues.
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

def test_question(question, expected_keywords=None, case_description=""):
    """Test a single question and return diagnostic information."""
    # Detect language
    lang = detect_language(question)

    # Step 1: Retrieval
    try:
        results = retrieve(question, top_k=5)
        retrieval_info = []
        for i, r in enumerate(results):
            filename = r['file_name']
            score = r['score']
            doc_id = r.get('doc_id', '')
            if not doc_id and filename:
                doc_id = Path(filename).stem
            text = load_document_text(doc_id)
            relevant = False
            if expected_keywords:
                relevant = check_relevance(text, expected_keywords)
            retrieval_info.append({
                "index": i+1,
                "filename": filename,
                "doc_id": doc_id,
                "score": score,
                "relevant": relevant,
                "text_preview": text[:200] if text and len(text) > 200 else text
            })
    except Exception as e:
        retrieval_info = [{"error": str(e)}]

    # Step 2: RAG Service
    rag = RAGService()
    try:
        rag_result = rag.answer(question, top_k=5)
        rag_answer = rag_result.get('answer', '')
        rag_sources = rag_result.get('sources', [])
    except Exception as e:
        rag_answer = f"Error: {str(e)}"
        rag_sources = []

    # Return structured data for further analysis
    return {
        "question": question,
        "language": lang,
        "retrieved_results": retrieval_info,
        "rag_answer": rag_answer,
        "rag_sources": rag_sources
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

    # Also create a human-readable summary
    summary_path = Path('diagnostic_summary.txt')
    with summary_path.open('w', encoding='utf-8') as f:
        f.write("GCT AI Assistant Diagnostic Report\n")
        f.write("=" * 50 + "\n\n")

        for i, result in enumerate(all_results):
            f.write(f"Test Case {i+1}: {result['question']}\n")
            f.write(f"Language: {result['language']}\n")
            f.write(f"Case: {test_cases[i]['case']}\n")
            f.write("\nRetrieved Documents:\n")
            for doc in result['retrieved_results']:
                if 'error' in doc:
                    f.write(f"  ERROR: {doc['error']}\n")
                else:
                    f.write(f"  {doc['index']}. {doc['filename']} (ID: {doc['doc_id']}, Score: {doc['score']:.4f})\n")
                    f.write(f"      Relevant: {doc['relevant']}\n")
                    f.write(f"      Preview: {doc['text_preview'][:100]}...\n")
            f.write("\nRAG Answer:\n")
            f.write(f"  {result['rag_answer'][:200]}...\n")
            f.write("\nSources Returned:\n")
            for i, source in enumerate(result['rag_sources']):
                f.write(f"  {i+1}. {source['file_name']} (page: {source['page_number']}, score: {source['score']:.4f})\n")
            f.write("\n" + "="*50 + "\n\n")

if __name__ == "__main__":
    main()