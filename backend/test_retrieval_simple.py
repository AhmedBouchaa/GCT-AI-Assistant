# Test retrieval directly to see what it returns
from app.retrieval import retrieve
question = 'من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 أكتوبر 2026؟'
print('Testing retrieval for question:')
print(question.encode('utf-8'))
print()
results = retrieve(question, top_k=5)
print(f'Retrieved {len(results)} results:')
for i, r in enumerate(results):
    print(f'{i+1}. {r["file_name"]} (score: {r["score"]:.4f})')