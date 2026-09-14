import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.rag import RAGService

def main():
    question = "من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 اكتوبر 2026؟"
    service = RAGService()
    try:
        result = service.answer(question, top_k=5, temperature=0.0, max_tokens=512)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    print(f"QUESTION: {result['question']}")
    print(f"ANSWER LANGUAGE: {result['answer'][:50]}")
    print(f"ANSWER: {result['answer'][:300]}")
    print("SOURCES:")
    for src in result['sources'][:3]:
        print(f"  {src['chunk_id']}: {src['file_name']} p.{src['page_number']} (score:{src['score']:.4f})")
    sys.exit(0)

if __name__ == "__main__":
    main()