import json, urllib.request, urllib.error
q = "من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟"
data = json.dumps({"question": q, "top_k": 5}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8000/api/v1/ask", data=data,
    headers={"Content-Type": "application/json", "Authorization": "Bearer dev-admin-gct"})
print("Calling /api/v1/ask ... (timeout 60s)")
try:
    resp = urllib.request.urlopen(req, timeout=60)
    j = json.load(resp)
    print("status", resp.status)
    print("answer:", j.get("answer","")[:300])
    print("sources:", [(s.get("file_name"), s.get("score")) for s in (j.get("sources") or [])][:3])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:600])
except Exception as e:
    import traceback; traceback.print_exc()
