#!/usr/bin/env python3
"""
DOCUMENT CONTENT DIAGNOSTIC
Analysis only - no modifications, no re-indexing
Determine whether document content/language characteristics explain the ranking difference
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
from app.core.config import settings
from app.ingest.store import ChromaStore

print("="*100)
print("DOCUMENT CONTENT DIAGNOSTIC")
print("="*100)

# ============================================================================
# PART 1: EXTRACT AND COMPARE DOCUMENT CONTENTS
# ============================================================================
print("\nPART 1: DOCUMENT CONTENT ANALYSIS")
print("="*100)

store = ChromaStore(
    persist_directory=settings.chroma_persist_directory,
    collection_name=settings.chroma_collection_name,
)
collection = store._get_collection()

# Get both documents
doc_50_2 = collection.get(
    where={'file_name': 'GCT_notes_exemples_50-2.pdf'},
    include=['documents', 'embeddings', 'metadatas']
)

doc_50_22 = collection.get(
    where={'file_name': 'GCT_notes_exemples_50-22.pdf'},
    include=['documents', 'embeddings', 'metadatas']
)

text_50_2 = doc_50_2['documents'][0] if doc_50_2['documents'] else ""
text_50_22 = doc_50_22['documents'][0] if doc_50_22['documents'] else ""

print("\n" + "-"*100)
print("DOCUMENT 50-2 (GCT_notes_exemples_50-2.pdf)")
print("-"*100)
print(f"Length: {len(text_50_2)} characters")
print(f"Metadata: {doc_50_2['metadatas'][0] if doc_50_2['metadatas'] else {}}")
print(f"\nFull text:\n{text_50_2}\n")

print("\n" + "-"*100)
print("DOCUMENT 50-22 (GCT_notes_exemples_50-22.pdf)")
print("-"*100)
print(f"Length: {len(text_50_22)} characters")
print(f"Metadata: {doc_50_22['metadatas'][0] if doc_50_22['metadatas'] else {}}")
print(f"\nFull text:\n{text_50_22}\n")

# ============================================================================
# PART 2: DOCUMENT EMBEDDING COMPARISON
# ============================================================================
print("\n" + "="*100)
print("PART 2: DOCUMENT EMBEDDING COMPARISON")
print("="*100)

emb_50_2 = np.array(doc_50_2['embeddings'][0])
emb_50_22 = np.array(doc_50_22['embeddings'][0])

# Direct comparison
doc_to_doc_sim = np.dot(emb_50_2, emb_50_22)
doc_to_doc_dist = np.linalg.norm(emb_50_2 - emb_50_22)

print(f"\nEmbedding dimensions:")
print(f"  50-2:  {len(emb_50_2)}")
print(f"  50-22: {len(emb_50_22)}")

print(f"\nL2 norms:")
print(f"  50-2:  {np.linalg.norm(emb_50_2):.6f}")
print(f"  50-22: {np.linalg.norm(emb_50_22):.6f}")

print(f"\nDocument-to-document similarity:")
print(f"  Cosine similarity: {doc_to_doc_sim:.10f}")
print(f"  Euclidean distance: {doc_to_doc_dist:.10f}")

print(f"\nInterpretation:")
print(f"  The two documents are {doc_to_doc_sim:.4f} similar in embedding space")
if doc_to_doc_sim > 0.95:
    print(f"  → Very similar embeddings (both describe same type of content)")
elif doc_to_doc_sim > 0.85:
    print(f"  → Highly similar embeddings")
elif doc_to_doc_sim > 0.70:
    print(f"  → Moderately similar embeddings")
else:
    print(f"  → Somewhat different embeddings")

# ============================================================================
# PART 3: QUERY GEOMETRY ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("PART 3: QUERY GEOMETRY ANALYSIS")
print("="*100)

from app.ingest.embeddings import E5EmbeddingService

embedding_service = E5EmbeddingService()

# French query
french_q = 'Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis ?'
french_emb_array = embedding_service.embed_texts([french_q], prefix="query:")
french_emb = french_emb_array[0]

# Arabic query
arabic_q = 'من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟'
arabic_emb_array = embedding_service.embed_texts([arabic_q], prefix="query:")
arabic_emb = arabic_emb_array[0]

print(f"\nFRENCH QUERY SIMILARITIES:")
french_sim_50_2 = np.dot(french_emb, emb_50_2)
french_sim_50_22 = np.dot(french_emb, emb_50_22)
french_diff = french_sim_50_22 - french_sim_50_2

print(f"  Query → 50-2:  {french_sim_50_2:.10f}")
print(f"  Query → 50-22: {french_sim_50_22:.10f}")
print(f"  Difference:    {french_diff:+.10f}")
print(f"  Margin:        {abs(french_diff):.10f} ({abs(french_diff)*1000:.4f} milliunits)")

print(f"\nARABIC QUERY SIMILARITIES:")
arabic_sim_50_2 = np.dot(arabic_emb, emb_50_2)
arabic_sim_50_22 = np.dot(arabic_emb, emb_50_22)
arabic_diff = arabic_sim_50_22 - arabic_sim_50_2

print(f"  Query → 50-2:  {arabic_sim_50_2:.10f}")
print(f"  Query → 50-22: {arabic_sim_50_22:.10f}")
print(f"  Difference:    {arabic_diff:+.10f}")
print(f"  Margin:        {abs(arabic_diff):.10f} ({abs(arabic_diff)*1000:.4f} milliunits)")

# ============================================================================
# PART 4: LANGUAGE CONTENT ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("PART 4: LANGUAGE CONTENT ANALYSIS")
print("="*100)

# Count Arabic vs French/Latin characters
def analyze_script(text):
    arabic_count = sum(1 for c in text if '؀' <= c <= 'ۿ')
    latin_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    total = len(text)
    return arabic_count, latin_count, total

ar_50_2, la_50_2, tot_50_2 = analyze_script(text_50_2)
ar_50_22, la_50_22, tot_50_22 = analyze_script(text_50_22)

print(f"\nDOCUMENT 50-2 script composition:")
print(f"  Arabic characters: {ar_50_2} ({100*ar_50_2/tot_50_2:.1f}%)")
print(f"  Latin characters:  {la_50_2} ({100*la_50_2/tot_50_2:.1f}%)")
print(f"  Total characters:  {tot_50_2}")

print(f"\nDOCUMENT 50-22 script composition:")
print(f"  Arabic characters: {ar_50_22} ({100*ar_50_22/tot_50_22:.1f}%)")
print(f"  Latin characters:  {la_50_22} ({100*la_50_22/tot_50_22:.1f}%)")
print(f"  Total characters:  {tot_50_22}")

# French query is entirely French/Latin
print(f"\nFRENCH QUERY script:")
fr_latin = sum(1 for c in french_q if 'a' <= c.lower() <= 'z')
print(f"  Latin characters: {fr_latin} (100%)")

print(f"\nARABIC QUERY script:")
ar_arabic = sum(1 for c in arabic_q if '؀' <= c <= 'ۿ')
print(f"  Arabic characters: {ar_arabic} (100%)")

# ============================================================================
# PART 5: KEY TERMINOLOGY ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("PART 5: KEY TERMINOLOGY ANALYSIS")
print("="*100)

key_terms = {
    'president_french': ['président', 'Président'],
    'president_arabic': ['رئيس'],
    'commission': ['commission', 'Commission', 'لجنة'],
    'technical': ['technique', 'technique', 'فنية'],
    'maintenance': ['maintenance', 'صيانة'],
    'equipment': ['équipements', 'معدات'],
    'heavy': ['lourds', 'ثقيلة'],
    'qabis': ['Qabis', 'قابس', 'Gabès'],
}

print(f"\nTERMINOLOGY MATCH ANALYSIS:\n")

for term_category, terms in key_terms.items():
    print(f"{term_category}:")
    for term in terms:
        count_50_2 = text_50_2.count(term)
        count_50_22 = text_50_22.count(term)
        count_fr_q = french_q.count(term)
        count_ar_q = arabic_q.count(term)

        indicator = ""
        if term_category.startswith('president'):
            if count_50_22 > count_50_2:
                indicator = " ← 50-22 favored by French query terms"
            elif count_50_2 > count_50_22:
                indicator = " ← 50-2 favored by French query terms"

        if count_50_2 > 0 or count_50_22 > 0:
            print(f"  '{term}': 50-2={count_50_2}, 50-22={count_50_22}{indicator}")

# ============================================================================
# PART 6: STATISTICAL INTERPRETATION
# ============================================================================
print("\n" + "="*100)
print("PART 6: SCORE GAP INTERPRETATION")
print("="*100)

# Get all 5 documents for context
all_docs = ['GCT_notes_exemples_50-2.pdf', 'GCT_notes_exemples_50-22.pdf',
            'GCT_notes_exemples_50-37.pdf', 'GCT_notes_exemples_50-29.pdf',
            'GCT_notes_exemples_50-6.pdf']

french_scores = []
for doc_file in all_docs:
    result = collection.get(where={'file_name': doc_file}, include=['embeddings'])
    if result['embeddings'] is not None and len(result['embeddings']) > 0:
        doc_emb = np.array(result['embeddings'][0])
        score = np.dot(french_emb, doc_emb)
        french_scores.append((doc_file, score))

french_scores.sort(key=lambda x: x[1], reverse=True)

print(f"\nAll French query scores (ranked):")
for i, (doc, score) in enumerate(french_scores, 1):
    print(f"  {i}. {doc}: {score:.10f}")

print(f"\nScore gaps analysis:")
for i in range(len(french_scores) - 1):
    gap = french_scores[i][1] - french_scores[i+1][1]
    print(f"  {french_scores[i][0]} → {french_scores[i+1][0]}: {gap:.10f}")

# The gap between 50-22 (#1) and 50-2 (#2)
gap_top_to_second = french_scores[0][1] - french_scores[1][1]
gap_second_to_third = french_scores[1][1] - french_scores[2][1]

print(f"\nCritical gaps:")
print(f"  #1 (50-22) to #2 (50-2):   {gap_top_to_second:.10f}")
print(f"  #2 (50-2)  to #3 (50-37):  {gap_second_to_third:.10f}")

print(f"\nInterpretation:")
if gap_top_to_second < 0.002:
    print(f"  The gap is EXTREMELY SMALL (< 0.002)")
    print(f"  This cluster of documents is essentially tied in relevance")
elif gap_top_to_second < 0.005:
    print(f"  The gap is VERY SMALL (< 0.005)")
else:
    print(f"  The gap is MODERATE")

print(f"\n  Relative gap comparison:")
print(f"  (#1 to #2) / (#2 to #3) = {gap_top_to_second / gap_second_to_third:.2f}x")
if gap_top_to_second / gap_second_to_third < 0.5:
    print(f"  → The #1-#2 gap is SMALLER than #2-#3")
    print(f"  → The ranking is on the edge of a tie")

# ============================================================================
# PART 7: FINAL ASSESSMENT
# ============================================================================
print("\n" + "="*100)
print("PART 7: ROOT-CAUSE ASSESSMENT")
print("="*100)

print("""
CLASSIFICATION FRAMEWORK:

A. E5-small language-dependent representation issue
   → The model produces systematically different query embeddings for Arabic vs French
   → This causes the ranking difference

B. Document content/language characteristics
   → 50-22 and 50-2 have different textual properties
   → The French query naturally aligns better with 50-22
   → This is a property of the documents, not the model

C. Both effects contribute
   → The documents differ in ways that slightly favor 50-22 for French queries
   → AND E5-small has language-dependent representation

D. Evidence insufficient
   → Cannot determine root cause from available analysis

EVIDENCE ASSESSMENT:
""")

print(f"\n1. Language composition of documents:")
print(f"   50-2:  {100*ar_50_2/tot_50_2:.1f}% Arabic, {100*la_50_2/tot_50_2:.1f}% Latin")
print(f"   50-22: {100*ar_50_22/tot_50_22:.1f}% Arabic, {100*la_50_22/tot_50_22:.1f}% Latin")
if abs((100*la_50_2/tot_50_2) - (100*la_50_22/tot_50_22)) > 5:
    print(f"   → SIGNIFICANT DIFFERENCE in Latin character ratio")
else:
    print(f"   → SIMILAR script composition")

print(f"\n2. Document embedding similarity:")
print(f"   50-2 ↔ 50-22 cosine sim: {doc_to_doc_sim:.6f}")
if doc_to_doc_sim > 0.90:
    print(f"   → Documents are NEARLY IDENTICAL in embedding space")
else:
    print(f"   → Documents have meaningful embedding differences")

print(f"\n3. French query score margin:")
print(f"   50-22 - 50-2: {french_diff:+.10f}")
print(f"   Magnitude: {abs(french_diff)*1000:.4f} milliunits")
if abs(french_diff) < 0.0015:
    print(f"   → Extremely marginal (essentially noise/tie)")
else:
    print(f"   → Measurable but still very small")

print(f"\n4. Ranking pattern consistency:")
print(f"   Arabic: ALL variants rank 50-2 #1")
print(f"   French: ALL variants rank 50-22 #1")
print(f"   → Perfect language-based split suggests model effect")

print(f"\n5. Geometric analysis:")
print(f"   French query alignment with 50-22: {french_sim_50_22:.6f}")
print(f"   French query alignment with 50-2:  {french_sim_50_2:.6f}")
print(f"   Arabic query alignment with 50-22: {arabic_sim_50_22:.6f}")
print(f"   Arabic query alignment with 50-2:  {arabic_sim_50_2:.6f}")

arabic_50_2_advantage = arabic_sim_50_2 - arabic_sim_50_22
french_50_22_advantage = french_sim_50_22 - french_sim_50_2

print(f"\n   Arabic: 50-2 is {arabic_50_2_advantage:.10f} BETTER than 50-22")
print(f"   French: 50-22 is {french_50_22_advantage:.10f} BETTER than 50-2")
print(f"   → The advantage FLIPS based on query language")

print(f"\n" + "="*100)
print("FINAL CLASSIFICATION")
print("="*100)

if abs((100*la_50_2/tot_50_2) - (100*la_50_22/tot_50_22)) > 10 and abs(french_diff) > 0.001:
    print("\nCLASSIFICATION: B (Document content/language characteristics)")
    print("Reason: Documents have significantly different Latin character ratios,")
    print("        and French query naturally aligns better with the more-Latin document.")
elif abs(french_diff) < 0.0015 and doc_to_doc_sim > 0.95:
    print("\nCLASSIFICATION: A (E5-small model behavior)")
    print("Reason: Documents are nearly identical, margin is extremely small,")
    print("        and the ranking FLIPS based on query language.")
elif abs(french_diff) < 0.005:
    print("\nCLASSIFICATION: C (Both effects contribute)")
    print("Reason: Margin is very small, documents may have minor differences,")
    print("        but the consistent language-based split suggests model effect dominates.")
else:
    print("\nCLASSIFICATION: D (Evidence insufficient)")
    print("Reason: Data is ambiguous regarding primary cause.")

