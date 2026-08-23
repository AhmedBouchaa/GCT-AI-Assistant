#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

# The raw response from the API
response = {
    "question": "?? ?? ???? ?????? ?????? ?????? ??????? ??????? ?????? ??????? ??????",
    "answer": "La réunion de la commission de contrôle de la direction administrative de Qabis a été organisée par le Groupe chimique tunisien. La composition de cette commission est la suivante :\n\n- Président : Amal Al-Daridi (Directeur de la unité de production d'acide phosphorique)\n- Membre : Balal Al-Daridi (Directeur de la maintenance)\n- Membre : Balal Al-Tarabulusi (Directeur du département de la sécurité industrielle)\n- Membre : Waled Al-Jalasi (Directeur de la maintenance des équipements)\n- Membre : Krim Al-Majri (Directeur des affaires sociales)\n\nLa réunion a eu lieu à la direction administrative de Qabis et les minutes ont été transmises à la direction des affaires légales de Qabis. (Source 1, page 1)",
    "sources": [
        {
            "file_name": "GCT_notes_exemples_50-11.pdf",
            "page_number": 1,
            "score": 0.8110452890396118
        },
        {
            "file_name": "GCT_notes_exemples_50-35.pdf",
            "page_number": 1,
            "score": 0.8106026649475098
        }
    ]
}

print("="*100)
print("BACKEND RESPONSE ANALYSIS")
print("="*100)

print("\n1. QUESTION ENCODING ISSUE:")
print(f"   Received: {response['question']}")
print(f"   This is corrupted UTF-8 — Arabic text rendered as ??")
print(f"   Expected: من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟")

print("\n2. RETRIEVED DOCUMENTS:")
for i, source in enumerate(response['sources'][:2], 1):
    print(f"   {i}. {source['file_name']}: score={source['score']:.10f}")

print("\n3. CRITICAL ISSUE: WRONG ANSWER")
print("   The question asks about 'محمد بن علي' (president of technical committee for")
print("   heavy equipment maintenance in Qabis) from document 50-2.pdf")
print("")
print("   The backend retrieved:")
print("   - 50-11.pdf (admin control commission)")
print("   - 50-35.pdf (??)")
print("")
print("   These are WRONG documents. The correct document is 50-2.pdf")
print("")
print("   The answer mentions 'Amal Al-Daridi', 'Balal Al-Daridi', etc.")
print("   These are WRONG names. The correct president is 'محمد بن علي'")

print("\n4. ROOT CAUSE:")
print("   → The retrieval returned wrong documents (50-11, 50-35 instead of 50-2)")
print("   → This caused the LLM to generate a completely incorrect answer")
print("   → The encoding corruption (?) indicates potential character encoding issues")

print("\n5. WHAT SHOULD HAVE HAPPENED:")
print("   ✗ Retrieve 50-2.pdf as #1 result (should be top match)")
print("   ✓ Extract: 'رئيس محمد بن علي' (President: Muhammad bin Ali)")
print("   ✓ Answer in Arabic (same language as question)")
print("   ✓ Return correct source: 50-2.pdf, page 1")

