import requests
import json

# Test UTF-8 transmission
url = "http://127.0.0.1:8000/api/debug/test-encoding"
question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟"
payload = {"question": question}
headers = {
    "Authorization": "Bearer dev-user-gct",
    "Content-Type": "application/json"
}

print("Testing UTF-8 transmission...")
response = requests.post(url, headers=headers, json=payload, timeout=10)
if response.status_code == 200:
    result = response.json()
    utf8_result = result.get('utf8', {})
    decoded = utf8_result.get('decoded')
    print(f"Question sent: {repr(question)}")
    print(f"Question received: {repr(decoded)}")
    if question == decoded:
        print("UTF-8 transmission: OK")
    else:
        print("UTF-8 transmission: CORRUPTED")
        print(f"Expected: {repr(question)}")
        print(f"Got: {repr(decoded)}")
else:
    print(f"HTTP error: {response.status_code}")
    print(response.text)

# Test API with debug endpoint
print("\nTesting API debug endpoint...")
url = "http://127.0.0.1:8000/api/debug/ask-debug"
response = requests.post(url, headers=headers, json=payload, timeout=60)
if response.status_code == 200:
    result = response.json()
    print(f"Sources match: {result.get('sources_match')}")
    print(f"Retriever sources: {[s.get('file_name') for s in result.get('direct_retriever', [])]}")
    print(f"RAG service sources: {[s.get('file_name') for s in result.get('rag_service_sources', [])]}")
    print(f"RAG answer: {result.get('rag_service_answer', '')[:100]}...")
else:
    print(f"HTTP error: {response.status_code}")
    print(response.text)