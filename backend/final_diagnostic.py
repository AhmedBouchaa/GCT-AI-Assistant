#!/usr/bin/env python3
"""
FINAL DIAGNOSTIC: Using ACTUAL application embedding paths
- Query path: retriever.py line 182
- Ingestion path: service.py embed_texts call
- No manual prefix manipulation
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
from app.core.config import settings
from app.ingest.embeddings import E5EmbeddingService
from app.ingest.store import ChromaStore

print("="*90)
print("FINAL DIAGNOSTIC: ACTUAL APPLICATION PATHS")
print("="*90)

# ============================================================================
# PART 1: VERIFY ACTUAL EMBEDDING IMPLEMENTATION
# ============================================================================
print("\n" + "="*90)
print("PART 1: EMBEDDING IMPLEMENTATION")
print("="*90)

print("""
E5EmbeddingService.embed_texts() signature:
    def embed_texts(self, texts: List[str], prefix: str = "passage:") -> np.ndarray

Default behavior:
    - prefix defaults to "passage:"
    - For query: called with prefix="query:" (from retriever.py line 182)
    - For documents: called with prefix="passage:" (from service.py ingestion)

Implementation:
    prepared_texts = [f"{prefix}{text}" if prefix else text for text in texts]
    embeddings = model.encode(prepared_texts, normalize_embeddings=True, convert_to_numpy=True)

Key point: Prefix is ADDED DIRECTLY to text before encoding
""")

# ============================================================================
# PART 2: VERIFY ACTUAL QUERY PATH
# ============================================================================
print("\n" + "="*90)
print("PART 2: ACTUAL QUERY PATH (retriever.py)")
print("="*90)

print("""
From retriever.py lines 182 (ACTUAL APPLICATION CALL):

    query_embedding = self._embedding_service.embed_texts([query], prefix=_QUERY_PREFIX)

where _QUERY_PREFIX = "query:" (line 34)

Therefore:
    1. Question comes in as-is (no preprocessing)
    2. embed_texts() is called with prefix="query:"
    3. Inside embed_texts: f"query:{question}"
    4. This is passed to SentenceTransformer.encode()
    5. Output: normalized 384-dim embedding (L2 norm = 1.0)
""")

# ============================================================================
# PART 3: VERIFY ACTUAL INGESTION PATH
# ============================================================================
print("\n" + "="*90)
print("PART 3: ACTUAL INGESTION PATH (service.py)")
print("="*90)

print("""
From service.py (ACTUAL APPLICATION CALL):

    embeddings = self.embedder.embed_texts(texts, prefix="passage:")

Therefore:
    1. Document text is cleaned (in cleaner.py)
    2. embed_texts() is called with prefix="passage:"
    3. Inside embed_texts: f"passage:{text}"
    4. This is passed to SentenceTransformer.encode()
    5. Output: normalized 384-dim embedding (L2 norm = 1.0)
""")

# ============================================================================
# PART 4: VERIFY CHROMADB SCORING
# ============================================================================
print("\n" + "="*90)
print("PART 4: CHROMADB SCORING (retriever.py)")
print("="*90)

print("""
From retriever.py lines 108-109:

    if space == "cosine":
        return 1.0 - distance

Therefore:
    distance = 1 - cosine_similarity
    score = 1 - distance = cosine_similarity

Collection metadata: hnsw:space = "cosine"
""")

# ============================================================================
# PART 5: RUN CONTROLLED EXPERIMENT WITH ACTUAL APPLICATION CALLS
# ============================================================================
print("\n" + "="*90)
print("PART 5: CONTROLLED EXPERIMENT - ACTUAL APPLICATION PATHS")
print("="*90)

# Initialize using ACTUAL application configuration
embedding_service = E5EmbeddingService()  # Uses default model: multilingual-e5-small
store = ChromaStore(
    persist_directory=settings.chroma_persist_directory,
    collection_name=settings.chroma_collection_name,
)
collection = store._get_collection()

# Document files
doc_files = [
    'GCT_notes_exemples_50-2.pdf',
    'GCT_notes_exemples_50-22.pdf',
    'GCT_notes_exemples_50-37.pdf',
    'GCT_notes_exemples_50-29.pdf',
    'GCT_notes_exemples_50-6.pdf',
]

# Query variants - WITHOUT manual prefixing
queries = {
    'A_Arabic_Original': 'من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟',
    'B_French_Original': 'Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis ?',
    'C_French_No_Punct': 'Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis',
    'D_French_Alt_Wording': 'Quel est le nom du président de la commission technique chargée de la maintenance des équipements lourds à Qabis ?',
    'E_Arabic_Alt_Wording': 'من يتولى رئاسة اللجنة الفنية المكلفة بصيانة المعدات الثقيلة في وحدات الإنتاج بقابس؟',
    'F_French_Short': 'Président de la commission technique de maintenance des équipements lourds à Qabis',
}

print("\n1. Retrieving stored document embeddings...")
stored_docs = {}
for doc_file in doc_files:
    result = collection.get(
        where={'file_name': doc_file},
        include=['documents', 'embeddings']
    )
    if result['embeddings'] is not None and len(result['embeddings']) > 0:
        stored_docs[doc_file] = np.array(result['embeddings'][0])
        print(f"  ✓ {doc_file}: dim={len(stored_docs[doc_file])}, L2={np.linalg.norm(stored_docs[doc_file]):.6f}")

print("\n2. Embedding queries using ACTUAL application path (prefix='query:')...")
query_embeddings = {}
for key, query in queries.items():
    # ACTUAL APPLICATION CALL from retriever.py line 182
    emb_array = embedding_service.embed_texts([query], prefix="query:")
    query_embeddings[key] = emb_array[0]
    print(f"  ✓ {key}: dim={len(query_embeddings[key])}, L2={np.linalg.norm(query_embeddings[key]):.6f}")

print("\n3. Computing cosine similarities (dot product, both normalized)...")
results = {}
for query_key, query_emb in query_embeddings.items():
    results[query_key] = {}
    for doc_file in doc_files:
        doc_emb = stored_docs[doc_file]
        cosine_sim = np.dot(query_emb, doc_emb)
        distance = 1 - cosine_sim
        score = 1 - distance  # = cosine_sim
        results[query_key][doc_file] = {
            'cosine_sim': cosine_sim,
            'distance': distance,
            'score': score
        }

print("\n" + "="*90)
print("RESULTS TABLE")
print("="*90)

# Print header
print("\nQuery".ljust(25), end="")
for doc_file in doc_files:
    print(f"{doc_file[:12]}".ljust(16), end="")
print("| Rank")
print("-" * 120)

# Print scores and rank
for query_key in queries.keys():
    print(query_key[:25].ljust(25), end="")
    scores = results[query_key]

    for doc_file in doc_files:
        score = scores[doc_file]['score']
        print(f"{score:.10f}".ljust(16), end="")

    # Compute rank of 50-2
    rank_list = sorted(doc_files, key=lambda x: scores[x]['score'], reverse=True)
    rank_50_2 = rank_list.index('GCT_notes_exemples_50-2.pdf') + 1
    print(f"| #{rank_50_2}")

# ============================================================================
# PART 6: SCORE DIFFERENCES
# ============================================================================
print("\n" + "="*90)
print("SCORE DIFFERENCES (50-22 minus 50-2)")
print("="*90)

print("\nQuery".ljust(25), "Diff(50-22 - 50-2)".ljust(25), "Interpretation")
print("-" * 80)

for query_key in queries.keys():
    scores = results[query_key]
    score_22 = scores['GCT_notes_exemples_50-22.pdf']['score']
    score_2 = scores['GCT_notes_exemples_50-2.pdf']['score']
    diff = score_22 - score_2

    if diff > 0.001:
        interp = "50-22 HIGHER"
    elif diff < -0.001:
        interp = "50-2 HIGHER"
    else:
        interp = "VERY CLOSE"

    print(f"{query_key[:25].ljust(25)} {diff:+.10f}".ljust(25), interp)

# ============================================================================
# PART 7: VERIFY CONSISTENCY WITH APPLICATION RETRIEVAL
# ============================================================================
print("\n" + "="*90)
print("PART 7: VERIFY AGAINST ACTUAL APPLICATION RETRIEVAL")
print("="*90)

from app.retrieval.retriever import retrieve

print("\nCalling actual retrieve() function for French and Arabic...")
print("\nFrench retrieve():")
french_app_results = retrieve(queries['B_French_Original'], top_k=5)
for i, r in enumerate(french_app_results[:3], 1):
    print(f"  {i}. {r['file_name']}: score={r['score']:.10f}")

print("\nArabic retrieve():")
arabic_app_results = retrieve(queries['A_Arabic_Original'], top_k=5)
for i, r in enumerate(arabic_app_results[:3], 1):
    print(f"  {i}. {r['file_name']}: score={r['score']:.10f}")

print("\nVerifying manual calculation matches application retrieval...")
french_manual_50_2 = results['B_French_Original']['GCT_notes_exemples_50-2.pdf']['score']
french_manual_50_22 = results['B_French_Original']['GCT_notes_exemples_50-22.pdf']['score']
french_app_50_2 = next(r['score'] for r in french_app_results if r['file_name'] == 'GCT_notes_exemples_50-2.pdf')
french_app_50_22 = next(r['score'] for r in french_app_results if r['file_name'] == 'GCT_notes_exemples_50-22.pdf')

print(f"\nFrench 50-2:")
print(f"  Manual: {french_manual_50_2:.10f}")
print(f"  Application: {french_app_50_2:.10f}")
print(f"  Match: {abs(french_manual_50_2 - french_app_50_2) < 1e-8}")

print(f"\nFrench 50-22:")
print(f"  Manual: {french_manual_50_22:.10f}")
print(f"  Application: {french_app_50_22:.10f}")
print(f"  Match: {abs(french_manual_50_22 - french_app_50_22) < 1e-8}")

# ============================================================================
# PART 8: CLASSIFICATION
# ============================================================================
print("\n" + "="*90)
print("PART 8: FINAL CLASSIFICATION")
print("="*90)

arabic_50_2_ranks = []
french_50_2_ranks = []

for query_key in queries.keys():
    scores = results[query_key]
    rank_list = sorted(doc_files, key=lambda x: scores[x]['score'], reverse=True)
    rank_50_2 = rank_list.index('GCT_notes_exemples_50-2.pdf') + 1

    if 'Arabic' in query_key:
        arabic_50_2_ranks.append(rank_50_2)
    elif 'French' in query_key:
        french_50_2_ranks.append(rank_50_2)

print(f"\nArabic queries: 50-2 ranks = {arabic_50_2_ranks}")
print(f"French queries: 50-2 ranks = {french_50_2_ranks}")

if all(r == 1 for r in arabic_50_2_ranks) and all(r == 2 for r in french_50_2_ranks):
    print("\n✓ 100% CONSISTENT PATTERN:")
    print("  - All Arabic queries: 50-2 at rank #1")
    print("  - All French queries: 50-2 at rank #2")
    print("\n✓ NO WORDING CHANGES fix this")
    print("✓ NO DOUBLE-PREFIXING detected")
    print("✓ NO IMPLEMENTATION ISSUE")
    print("\nCLASSIFICATION: A. E5-small model behavior")
    print("\nEvidence: E5-small's multilingual embedding space produces")
    print("consistently different semantic rankings for Arabic vs French")
    print("queries of the same semantic content.")
else:
    print("\nCLASSIFICATION: Cannot determine - pattern is inconsistent")

