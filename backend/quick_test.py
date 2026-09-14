import json
import time
import requests
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

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
        "received_question_language": None,
        "direct_retriever_results": [],
        "rag_service_sources": [],
        "sources_match": None,
        "rag_service_answer_truncated": None,
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
            result["rag_service_answer_truncated"] = result_json.get('rag_service_answer')
            result["rag_service_answer_language"] = detect_language(result.get('rag_service_answer_truncated'))
        else:
            result["error"] = response.text
    except Exception as e:
        result["error"] = str(e)
    return result

def test_french_question():
    url = "http://127.0.0.1:8000/api/v1/ask"
    question = "Qui est le président de la commission de sécurité et de sûreté industrielle du complexe de Gabès le 20 octobre 2026 ?"
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
        "answer": None,
        "answer_language": None,
        "num_sources": None,
        "sources": [],
        "error": None
    }
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
            result["answer"] = result_json.get('answer')
            result["answer_language"] = detect_language(result.get('answer'))
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

def main():
    # Start the server
    import subprocess
    server_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"
    ], cwd=os.path.dirname(os.path.abspath(__file__)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # Wait for server to be ready
        if wait_for_server("http://127.0.0.1:8000/api/v1/health", timeout=30):
            print("Server is ready")
            # Run tests
            results = []
            results.append(test_utf8_transmission())
            results.append(test_api_debug_ask())
            results.append(test_french_question())
            # Write results to file
            with open('quick_test_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            # Print a summary
            print("Tests completed. Results written to quick_test_results.json")
            for res in results:
                print(f"- {res.get('test', 'unknown test')}: status {res.get('http_status', 'error')}")
        else:
            print("Server did not become ready in time")
    finally:
        # Kill the server
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()