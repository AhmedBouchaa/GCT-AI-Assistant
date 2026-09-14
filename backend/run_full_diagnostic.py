import json
import time
import requests
import sys
import os
from pathlib import Path

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def safe_print(text):
    # Print text, but if it contains non-ASCII, we will show a warning and the repr
    try:
        print(text)
    except UnicodeEncodeError:
        print(f"[Non-ASCII text, length={len(text)}] {repr(text)}")

def test_utf8_transmission():
    url = "http://127.0.0.1:8000/api/debug/test-encoding"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result = {
        "test": "utf8_transmission",
        "request_payload": payload,
        "request_payload_repr": repr(json.dumps(payload, ensure_ascii=False)),
        "http_status": None,
        "response_time": None,
        "decoded_question": None,
        "body_length": None,
        "body_hex": None,
        "utf8_intact": None,
        "error": None
    }
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        elapsed = time.time() - start
        result["http_status"] = response.status_code
        result["response_time"] = elapsed
        if response.status_code == 200:
            result_json = response.json()
            result["decoded_question"] = result_json.get('utf8', {}).get('decoded')
            result["body_length"] = result_json.get('body_length')
            result["body_hex"] = result_json.get('body_hex')
            decoded = result_json.get('utf8', {}).get('decoded')
            if decoded and question in decoded:
                result["utf8_intact"] = True
            else:
                result["utf8_intact"] = False
        else:
            result["error"] = response.text
    except Exception as e:
        result["error"] = str(e)
    return result

def test_direct_retriever():
    from app.retrieval import retrieve
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    start = time.time()
    results = retrieve(question, top_k=5)
    elapsed = time.time() - start
    result = {
        "test": "direct_retriever",
        "question": question,
        "question_repr": repr(question),
        "retrieval_time": elapsed,
        "num_results": len(results),
        "results": []
    }
    for i, r in enumerate(results):
        result["results"].append({
            "index": i+1,
            "filename": r.get('file_name'),
            "score": r.get('score'),
            "document_id": r.get('doc_id'),
            "chunk_id": r.get('chunk_id'),
            "text_snippet": (r.get('text', '')[:100] + ('...' if len(r.get('text', '')) > 100 else '')),
            "text_snippet_repr": repr((r.get('text', '')[:100] + ('...' if len(r.get('text', '')) > 100 else '')))
        })
    return result

def test_direct_rag_service():
    from app.rag import RAGService
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    rag = RAGService()
    start = time.time()
    result_obj = rag.answer(question, top_k=5)
    elapsed = time.time() - start
    # We will not store the full answer text in the result to avoid non-ASCII in the terminal when printing the result dict.
    # Instead, we will store a snippet and its repr.
    answer = result_obj.get('answer', '')
    result = {
        "test": "direct_rag_service",
        "question": question,
        "question_repr": repr(question),
        "rag_service_time": elapsed,
        "answer_snippet": answer[:100] + ('...' if len(answer) > 100 else ''),
        "answer_snippet_repr": repr(answer[:100] + ('...' if len(answer) > 100 else '')),
        "answer_length": len(answer),
        "num_sources": len(result_obj.get('sources', [])),
        "sources": []
    }
    for i, s in enumerate(result_obj.get('sources', [])):
        result["sources"].append({
            "index": i+1,
            "filename": s.get('file_name'),
            "page": s.get('page_number'),
            "score": s.get('score'),
            "chunk_id": s.get('chunk_id')
        })
    return result

def test_api_debug_ask():
    url = "http://127.0.0.1:8000/api/debug/ask-debug"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result = {
        "test": "api_debug_ask",
        "request_payload": payload,
        "http_status": None,
        "response_time": None,
        "received_question": None,
        "received_question_repr": None,
        "received_question_language": None,
        "direct_retriever_results": [],
        "rag_service_sources": [],
        "sources_match": None,
        "rag_service_answer_truncated": None,
        "rag_service_answer_truncated_repr": None,
        "rag_service_answer_language": None,
        "error": None
    }
    # Simple language detection
    def detect_language(text):
        if not text:
            return "unknown"
        arabic_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
        total_chars = len(text)
        if total_chars == 0:
            return "unknown"
        arabic_ratio = arabic_chars / total_chars
        if arabic_ratio > 0.5:
            return "ar"
        french_chars = sum(1 for c in text if c in "àâäéèêëîïôöùûüÿæœçÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÆŒÇ")
        if french_chars > 0:
            return "fr"
        latin_chars = sum(1 for c in text if ('a' <= c.lower() <= 'z'))
        if latin_chars > 0:
            return "en"
        return "unknown"
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        elapsed = time.time() - start
        result["http_status"] = response.status_code
        result["response_time"] = elapsed
        if response.status_code == 200:
            result_json = response.json()
            result["received_question"] = result_json.get('question')
            result["received_question_repr"] = repr(result_json.get('question'))
            result["received_question_language"] = detect_language(result.get('received_question'))
            result["direct_retriever_results"] = [
                {"filename": r.get('file_name'), "score": r.get('score')}
                for r in result_json.get('direct_retriever', [])
            ]
            result["rag_service_sources"] = [
                {"filename": s.get('file_name'), "score": s.get('score')}
                for s in result_json.get('rag_service_sources', [])
            ]
            result["sources_match"] = result_json.get('sources_match')
            result["rag_service_answer_truncated"] = result_json.get('rag_service_answer')[:100] + ('...' if len(result_json.get('rag_service_answer', '')) > 100 else '')
            result["rag_service_answer_truncated_repr"] = repr(result["rag_service_answer_truncated"])
            result["rag_service_answer_language"] = detect_language(result.get('rag_service_answer_truncated'))
        else:
            result["error"] = response.text
    except Exception as e:
        result["error"] = str(e)
    return result

def test_api_ask():
    url = "http://127.0.0.1:8000/api/v1/ask"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question, "top_k": 5}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result = {
        "test": "api_v1_ask",
        "request_payload": payload,
        "http_status": None,
        "response_time": None,
        "answer_snippet": None,
        "answer_snippet_repr": None,
        "answer_length": None,
        "question_returned": None,
        "question_returned_repr": None,
        "num_sources": None,
        "sources": [],
        "error": None
    }
    # Simple language detection
    def detect_language(text):
        if not text:
            return "unknown"
        arabic_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
        total_chars = len(text)
        if total_chars == 0:
            return "unknown"
        arabic_ratio = arabic_chars / total_chars
        if arabic_ratio > 0.5:
            return "ar"
        french_chars = sum(1 for c in text if c in "àâäéèêëîïôöùûüÿæœçÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÆŒÇ")
        if french_chars > 0:
            return "fr"
        latin_chars = sum(1 for c in text if ('a' <= c.lower() <= 'z'))
        if latin_chars > 0:
            return "en"
        return "unknown"
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        elapsed = time.time() - start
        result["http_status"] = response.status_code
        result["response_time"] = elapsed
        if response.status_code == 200:
            result_json = response.json()
            result["answer_snippet"] = result_json.get('answer', '')[:100] + ('...' if len(result_json.get('answer', '')) > 100 else '')
            result["answer_snippet_repr"] = repr(result["answer_snippet"])
            result["answer_length"] = len(result_json.get('answer', ''))
            result["question_returned"] = result_json.get('question')
            result["question_returned_repr"] = repr(result_json.get('question'))
            result["num_sources"] = len(result_json.get('sources', []))
            result["sources"] = [
                {
                    "filename": s.get('file_name'),
                    "page": s.get('page_number'),
                    "score": s.get('score'),
                    "chunk_id": s.get('chunk_id')
                }
                for s in result_json.get('sources', [])
            ]
        else:
            result["error"] = response.text
    except Exception as e:
        result["error"] = str(e)
    return result

def inspect_document_content():
    from app.utils.pdf_extractor import PDFExtractor
    from pathlib import Path
    extractor = PDFExtractor('data/documents')
    result = {
        "test": "document_inspection",
        "documents_checked": [],
        "safety_committee_found_in": [],
        "tarik_bin_othman_found_in": [],
        "ahmed_elfiqih_found_in": []
    }
    for doc_num in [16, 19, 20, 31, 36]:
        pdf_path = Path(f'data/documents/GCT_notes_exemples_50-{doc_num}.pdf')
        if pdf_path.exists():
            pages = extractor.extract_text_from_pdf(pdf_path)
            doc_info = {
                "document": pdf_path.name,
                "num_pages": len(pages),
                "pages_with_safety_committee_and_date": [],
                "pages_with_tarik_bin_othman": [],
                "pages_with_ahmed_elfiqih": []
            }
            for page in pages:
                text = page['text']
                if 'لجنة السلامة' in text and 'أمان' in text and '20' in text and 'أكتوبر' in text:
                    doc_info["pages_with_safety_committee_and_date"].append(page['page_number'])
                if 'طارق بن عثمان' in text:
                    doc_info["pages_with_tarik_bin_othman"].append(page['page_number'])
                if 'أحمد الفقيه' in text:
                    doc_info["pages_with_ahmed_elfiqih"].append(page['page_number'])
            result["documents_checked"].append(doc_info)
            if doc_info["pages_with_safety_committee_and_date"]:
                result["safety_committee_found_in"].append(pdf_path.name)
            if doc_info["pages_with_tarik_bin_othman"]:
                result["tarik_bin_othman_found_in"].append(pdf_path.name)
            if doc_info["pages_with_ahmed_elfiqih"]:
                result["ahmed_elfiqih_found_in"].append(pdf_path.name)
        else:
            result["documents_checked"].append({
                "document": pdf_path.name,
                "error": "File not found"
            })
    return result

def verify_expected_answer():
    from app.utils.pdf_extractor import PDFExtractor
    from pathlib import Path
    extractor = PDFExtractor('data/documents')
    result = {
        "test": "verify_expected_answer",
        "question": "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟",
        "expected_name": "أحمد الفقيه",
        "found_in_documents": [],
        "contexts": []
    }
    for doc_num in [16, 19, 20, 31, 36]:
        pdf_path = Path(f'data/documents/GCT_notes_exemples_50-{doc_num}.pdf')
        if pdf_path.exists():
            pages = extractor.extract_text_from_pdf(pdf_path)
            for page in pages:
                text = page['text']
                if 'أحمد الفقيه' in text:
                    result["found_in_documents"].append(pdf_path.name)
                    result["contexts"].append({
                        "document": pdf_path.name,
                        "page": page['page_number'],
                        "context": text[:200]
                    })
    if not result["found_in_documents"]:
        result["note"] = "Did not find 'أحمد الفقيه' in any of the retrieved documents."
    return result

def compare_stages():
    # This is a placeholder; we will construct the table from the other results
    result = {
        "test": "compare_stages",
        "note": "Please construct the table from the outputs of the previous sections."
    }
    return result

def test_french():
    url = "http://127.0.0.1:8000/api/v1/ask"
    question = "Qui est le président de la commission de sécurité et de sûreté industrielle du complexe de Gabès le 20 أكتوبر 2026 ?"
    payload = {"question": question, "top_k": 5}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result = {
        "test": "french_question",
        "request_payload": payload,
        "http_status": None,
        "response_time": None,
        "answer_snippet": None,
        "answer_snippet_repr": None,
        "answer_length": None,
        "num_sources": None,
        "sources": [],
        "error": None
    }
    # Simple language detection
    def detect_language(text):
        if not text:
            return "unknown"
        arabic_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
        total_chars = len(text)
        if total_chars == 0:
            return "unknown"
        arabic_ratio = arabic_chars / total_chars
        if arabic_ratio > 0.5:
            return "ar"
        french_chars = sum(1 for c in text if c in "àâäéèêëîïôöùûüÿæœçÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÆŒÇ")
        if french_chars > 0:
            return "fr"
        latin_chars = sum(1 for c in text if ('a' <= c.lower() <= 'z'))
        if latin_chars > 0:
            return "en"
        return "unknown"
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        elapsed = time.time() - start
        result["http_status"] = response.status_code
        result["response_time"] = elapsed
        if response.status_code == 200:
            result_json = response.json()
            result["answer_snippet"] = result_json.get('answer', '')[:100] + ('...' if len(result_json.get('answer', '')) > 100 else '')
            result["answer_snippet_repr"] = repr(result["answer_snippet"])
            result["answer_length"] = len(result_json.get('answer', ''))
            result["num_sources"] = len(result_json.get('sources', []))
            result["sources"] = [
                {
                    "filename": s.get('file_name'),
                    "page": s.get('page_number'),
                    "score": s.get('score')
                }
                for s in result_json.get('sources', [])
            ]
        else:
            result["error"] = response.text
    except Exception as e:
        result["error"] = str(e)
    return result

def performance_test():
    url = "http://127.0.0.1:8000/api/v1/ask"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question, "top_k": 5}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result = {
        "test": "performance",
        "first_request": {},
        "second_request": {}
    }
    # First request
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        elapsed = time.time() - start
        result["first_request"]["time"] = elapsed
        result["first_request"]["status"] = response.status_code
    except Exception as e:
        result["first_request"]["error"] = str(e)
    # Second request
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        elapsed = time.time() - start
        result["second_request"]["time"] = elapsed
        result["second_request"]["status"] = response.status_code
    except Exception as e:
        result["second_request"]["error"] = str(e)
    return result

def main():
    # We assume the server is already running. If not, we could start it, but let's assume it's running.
    # We'll try to connect to the health endpoint to see if it's up.
    health_url = "http://127.0.0.1:8000/api/v1/health"
    try:
        health_response = requests.get(health_url, timeout=5)
        if health_response.status_code != 200:
            print("Server is not responding correctly. Please start the server and try again.")
            return
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        print("Please start the server and try again.")
        return

    print("Running diagnostic tests...")
    results = []
    results.append(test_utf8_transmission())
    results.append(test_direct_retriever())
    results.append(test_direct_rag_service())
    results.append(test_api_debug_ask())
    results.append(test_api_ask())
    results.append(inspect_document_content())
    results.append(verify_expected_answer())
    results.append(compare_stages())
    results.append(test_french())
    results.append(performance_test())

    # Write results to a file
    output_file = Path('diagnostic_results.json')
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Diagnostic tests completed. Results written to {output_file}")
    # Print a short summary
    for res in results:
        test_name = res.get('test', 'unknown test')
        status = res.get('http_status', 'N/A')
        if isinstance(status, int):
            print(f"- {test_name}: HTTP {status}")
        else:
            print(f"- {test_name}: {status}")

    # Also, we can output the JSON content for the user to see
    print("\n" + "="*60)
    print("JSON OUTPUT:")
    print("="*60)
    with output_file.open('r', encoding='utf-8') as f:
        print(f.read())

if __name__ == "__main__":
    main()