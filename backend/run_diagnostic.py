import json
import time
import requests
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def safe_print(text):
    # Only print ASCII characters, replace non-ASCII with ?
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ASCII representation
        print(text.encode('ascii', 'replace').decode('ascii'))

def test_utf8_transmission():
    url = "http://127.0.0.1:8000/api/debug/test-encoding"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }

    # We'll return a dictionary with the results
    result_dict = {
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
        result_dict["http_status"] = response.status_code
        result_dict["response_time"] = elapsed
        if response.status_code == 200:
            result = response.json()
            result_dict["decoded_question"] = result.get('utf8', {}).get('decoded')
            result_dict["body_length"] = result.get('body_length')
            result_dict["body_hex"] = result.get('body_hex')
            # Check if the question is intact
            decoded = result.get('utf8', {}).get('decoded')
            if decoded and question in decoded:
                result_dict["utf8_intact"] = True
            else:
                result_dict["utf8_intact"] = False
        else:
            result_dict["error"] = response.text
    except Exception as e:
        result_dict["error"] = str(e)
    return result_dict

def test_direct_retriever():
    from app.retrieval import retrieve
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    start = time.time()
    results = retrieve(question, top_k=5)
    elapsed = time.time() - start
    result_dict = {
        "test": "direct_retriever",
        "question": question,
        "question_repr": repr(question),
        "retrieval_time": elapsed,
        "num_results": len(results),
        "results": []
    }
    for i, r in enumerate(results):
        result_dict["results"].append({
            "index": i+1,
            "filename": r.get('file_name'),
            "score": r.get('score'),
            "document_id": r.get('doc_id'),
            "chunk_id": r.get('chunk_id'),
            "text_snippet": (r.get('text', '')[:200] + ('...' if len(r.get('text', '')) > 200 else ''))
        })
    return result_dict

def test_direct_rag_service():
    from app.rag import RAGService
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    rag = RAGService()
    start = time.time()
    result = rag.answer(question, top_k=5)
    elapsed = time.time() - start
    # Simple language detection for the purpose of this script
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
    result_dict = {
        "test": "direct_rag_service",
        "question": question,
        "question_repr": repr(question),
        "rag_service_time": elapsed,
        "answer": result.get('answer'),
        "answer_language": detect_language(result.get('answer')),
        "num_sources": len(result.get('sources', [])),
        "sources": []
    }
    for i, s in enumerate(result.get('sources', [])):
        result_dict["sources"].append({
            "index": i+1,
            "filename": s.get('file_name'),
            "page": s.get('page_number'),
            "score": s.get('score'),
            "chunk_id": s.get('chunk_id')
        })
    return result_dict

def test_api_debug_ask():
    url = "http://127.0.0.1:8000/api/debug/ask-debug"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result_dict = {
        "test": "api_debug_ask",
        "request_payload": payload,
        "http_status": None,
        "response_time": None,
        "received_question": None,
        "received_question_language": None,
        "direct_retriever_results": [],
        "rag_service_sources": [],
        "sources_match": None,
        "rag_service_answer_truncated": None,
        "rag_service_answer_language": None,
        "error": None
    }
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        elapsed = time.time() - start
        result_dict["http_status"] = response.status_code
        result_dict["response_time"] = elapsed
        if response.status_code == 200:
            result = response.json()
            result_dict["received_question"] = result.get('question')
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
                french_chars = sum(1 for c in text if c in "àâäéèêëîïôôùûüÿæœçÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÆŒÇ")
                if french_chars > 0:
                    return "fr"
                latin_chars = sum(1 for c in text if ('a' <= c.lower() <= 'z'))
                if latin_chars > 0:
                    return "en"
                return "unknown"
            result_dict["received_question_language"] = detect_language(result.get('question'))
            result_dict["direct_retriever_results"] = [
                {"filename": r.get('file_name'), "score": r.get('score')}
                for r in result.get('direct_retriever', [])
            ]
            result_dict["rag_service_sources"] = [
                {"filename": s.get('file_name'), "score": s.get('score')}
                for s in result.get('rag_service_sources', [])
            ]
            result_dict["sources_match"] = result.get('sources_match')
            result_dict["rag_service_answer_truncated"] = result.get('rag_service_answer')
            result_dict["rag_service_answer_language"] = detect_language(result.get('rag_service_answer'))
        else:
            result_dict["error"] = response.text
    except Exception as e:
        result_dict["error"] = str(e)
    return result_dict

def test_api_ask():
    url = "http://127.0.0.1:8000/api/v1/ask"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question, "top_k": 5}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result_dict = {
        "test": "api_v1_ask",
        "request_payload": payload,
        "http_status": None,
        "response_time": None,
        "answer": None,
        "answer_language": None,
        "question_returned": None,
        "num_sources": None,
        "sources": [],
        "error": None
    }
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        elapsed = time.time() - start
        result_dict["http_status"] = response.status_code
        result_dict["response_time"] = elapsed
        if response.status_code == 200:
            result = response.json()
            result_dict["answer"] = result.get('answer')
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
            result_dict["answer_language"] = detect_language(result.get('answer'))
            result_dict["question_returned"] = result.get('question')
            result_dict["num_sources"] = len(result.get('sources', []))
            result_dict["sources"] = [
                {
                    "filename": s.get('file_name'),
                    "page": s.get('page_number'),
                    "score": s.get('score'),
                    "chunk_id": s.get('chunk_id')
                }
                for s in result.get('sources', [])
            ]
        else:
            result_dict["error"] = response.text
    except Exception as e:
        result_dict["error"] = str(e)
    return result_dict

def inspect_document_content():
    from app.utils.pdf_extractor import PDFExtractor
    from pathlib import Path
    extractor = PDFExtractor('data/documents')
    result_dict = {
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
            result_dict["documents_checked"].append(doc_info)
            if doc_info["pages_with_safety_committee_and_date"]:
                result_dict["safety_committee_found_in"].append(pdf_path.name)
            if doc_info["pages_with_tarik_bin_othman"]:
                result_dict["tarik_bin_othman_found_in"].append(pdf_path.name)
            if doc_info["pages_with_ahmed_elfiqih"]:
                result_dict["ahmed_elfiqih_found_in"].append(pdf_path.name)
        else:
            result_dict["documents_checked"].append({
                "document": pdf_path.name,
                "error": "File not found"
            })
    return result_dict

def verify_expected_answer():
    # This is similar to the document inspection but focused on the expected answer
    from app.utils.pdf_extractor import PDFExtractor
    from pathlib import Path
    extractor = PDFExtractor('data/documents')
    result_dict = {
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
                    result_dict["found_in_documents"].append(pdf_path.name)
                    result_dict["contexts"].append({
                        "document": pdf_path.name,
                        "page": page['page_number'],
                        "context": text[:500]
                    })
    if not result_dict["found_in_documents"]:
        result_dict["note"] = "Did not find 'أحمد الفقيه' in any of the retrieved documents."
    return result_dict

def compare_stages():
    # This is a placeholder; we will construct the table from the other results
    result_dict = {
        "test": "compare_stages",
        "note": "Please construct the table from the outputs of the previous sections."
    }
    return result_dict

def test_french():
    url = "http://127.0.0.1:8000/api/v1/ask"
    question = "Qui est le président de la commission de sécurité et de sûreté industrielle du complexe de Gabès le 20 octobre 2026 ?"
    payload = {"question": question, "top_k": 5}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result_dict = {
        "test": "french_question",
        "request_payload": payload,
        "http_status": None,
        "response_time": None,
        "answer": None,
        "answer_language": None,
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
        result_dict["http_status"] = response.status_code
        result_dict["response_time"] = elapsed
        if response.status_code == 200:
            result = response.json()
            result_dict["answer"] = result.get('answer')
            result_dict["answer_language"] = detect_language(result.get('answer'))
            result_dict["num_sources"] = len(result.get('sources', []))
            result_dict["sources"] = [
                {
                    "filename": s.get('file_name'),
                    "page": s.get('page_number'),
                    "score": s.get('score')
                }
                for s in result.get('sources', [])
            ]
        else:
            result_dict["error"] = response.text
    except Exception as e:
        result_dict["error"] = str(e)
    return result_dict

def performance_test():
    url = "http://127.0.0.1:8000/api/v1/ask"
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
    payload = {"question": question, "top_k": 5}
    headers = {
        "Authorization": "Bearer dev-user-gct",
        "Content-Type": "application/json"
    }
    result_dict = {
        "test": "performance",
        "first_request": {},
        "second_request": {}
    }
    # First request
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        elapsed = time.time() - start
        result_dict["first_request"]["time"] = elapsed
        result_dict["first_request"]["status"] = response.status_code
    except Exception as e:
        result_dict["first_request"]["error"] = str(e)
    # Second request
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        elapsed = time.time() - start
        result_dict["second_request"]["time"] = elapsed
        result_dict["second_request"]["status"] = response.status_code
    except Exception as e:
        result_dict["second_request"]["error"] = str(e)
    return result_dict

def main():
    # Wait for the server to be ready
    print("Waiting for server to be ready...")
    time.sleep(5)

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
    with open('diagnostic_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Also print a simple ASCII summary
    print("Diagnostic tests completed. Results written to diagnostic_results.json")
    for res in results:
        print(f"- {res.get('test', 'unknown test')}")

if __name__ == "__main__":
    main()