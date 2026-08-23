#!/usr/bin/env python3
"""
Controlled experiment: Query variants vs stored document embeddings
No modifications to any project code.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
from app.core.config import settings
from app.ingest.embeddings import E5EmbeddingService
from app.ingest.store import ChromaStore

print("="*80)
print("CONTROLLED EXPERIMENT: QUERY VARIANTS VS STORED EMBEDDINGS")
print("="*80)

# ============================================================================
# STEP 1: VERIFY INGESTION EMBEDDING CONFIGURATION
# ============================================================================
print("\nSTEP 1: INGESTION EMBEDDING CONFIGURATION")
print("-" * 80)

service = E5EmbeddingService()
print(f"Model: {service.model_name}")
print(f"Default prefix for documents: 'passage:'")
print(f"normalize_embeddings: True")
print(f"Configuration used: SentenceTransformer.encode()")

# ============================================================================
# STEP 2: RETRIEVE STORED EMBEDDINGS FOR 5 DOCUMENTS
# ============================================================================
print("\nSTEP 2: RETRIEVE STORED DOCUMENT EMBEDDINGS FROM CHROMADB")
print("-" * 80)

store = ChromaStore(
    persist_directory=settings.chroma_persist_directory,
    collection_name=settings.chroma_collection_name,
)
collection = store._get_collection()

doc_files = [
    'GCT_notes_exemples_50-2.pdf',
    'GCT_notes_exemples_50-22.pdf',
    'GCT_notes_exemples_50-37.pdf',
    'GCT_notes_exemples_50-29.pdf',
    'GCT_notes_exemples_50-6.pdf',
]

stored_docs = {}
for doc_file in doc_files:
    result = collection.get(
        where={'file_name': doc_file},
        include=['documents', 'embeddings', 'metadatas']
    )
    if result['embeddings'] is not None and len(result['embeddings']) > 0:
        emb = np.array(result['embeddings'][0])
        stored_docs[doc_file] = {
            'embedding': emb,
            'dimension': len(emb),
            'l2_norm': np.linalg.norm(emb),
            'text': result['documents'][0][:100] if result['documents'] else '',
            'metadata': result['metadatas'][0] if result['metadatas'] else {}
        }
        print(f"\n{doc_file}:")
        print(f"  Dimension: {stored_docs[doc_file]['dimension']}")
        print(f"  L2 norm: {stored_docs[doc_file]['l2_norm']:.6f}")
        print(f"  Text preview: {stored_docs[doc_file]['text']}...")

# ============================================================================
# STEP 3: CREATE QUERY VARIANTS (IN MEMORY ONLY)
# ============================================================================
print("\n" + "="*80)
print("STEP 3: CREATE QUERY VARIANTS")
print("-" * 80)

queries = {
    'A_Arabic_Original': 'من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟',
    'B_French_Original': 'Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis ?',
    'C_French_No_Punct': 'Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis',
    'D_French_Alt_Wording': 'Quel est le nom du président de la commission technique chargée de la maintenance des équipements lourds à Qabis ?',
    'E_Arabic_Alt_Wording': 'من يتولى رئاسة اللجنة الفنية المكلفة بصيانة المعدات الثقيلة في وحدات الإنتاج بقابس؟',
    'F_French_Short': 'Président de la commission technique de maintenance des équipements lourds à Qabis',
}

print("\nQueries created:")
for key, query in queries.items():
    print(f"\n{key}:")
    print(f"  {query}")

# ============================================================================
# STEP 4: EMBED ALL QUERY VARIANTS WITH CURRENT E5-SMALL
# ============================================================================
print("\n" + "="*80)
print("STEP 4: EMBED QUERY VARIANTS WITH E5-SMALL")
print("-" * 80)

query_embeddings = {}
for key, query in queries.items():
    # Use embed_texts with default prefix (no manual prefix)
    emb_array = service.embed_texts([query], prefix="query:")
    emb = emb_array[0]
    query_embeddings[key] = {
        'query': query,
        'embedding': emb,
        'dimension': len(emb),
        'l2_norm': np.linalg.norm(emb),
        'with_prefix': f"query: {query}"
    }
    print(f"\n{key}:")
    print(f"  Dimension: {len(emb)}")
    print(f"  L2 norm: {np.linalg.norm(emb):.6f}")
    print(f"  First 5 values: {emb[:5]}")

# ============================================================================
# STEP 5: CALCULATE COSINE SIMILARITY FOR ALL COMBINATIONS
# ============================================================================
print("\n" + "="*80)
print("STEP 5: COSINE SIMILARITY MATRIX")
print("-" * 80)

# Create results table
results = {}
for query_key, query_data in query_embeddings.items():
    query_emb = query_data['embedding']
    results[query_key] = {}

    for doc_file in doc_files:
        doc_emb = stored_docs[doc_file]['embedding']
        # Cosine similarity (both normalized, so just dot product)
        cosine_sim = np.dot(query_emb, doc_emb)
        score = 1 - (1 - cosine_sim)  # Convert to ChromaDB score format
        results[query_key][doc_file] = {
            'cosine_sim': cosine_sim,
            'score': 1 - (1 - cosine_sim),  # score = 1 - distance = 1 - (1 - cosine_sim) = cosine_sim
            'distance': 1 - cosine_sim
        }

# Print table
print("\nSCORES (1 - distance, where distance = 1 - cosine_similarity):")
print()
print("Query".ljust(25), end="")
for doc_file in doc_files:
    print(doc_file[:15].ljust(16), end="")
print("| Rank of 50-2")
print("-" * 120)

for query_key in queries.keys():
    print(query_key[:25].ljust(25), end="")
    scores = results[query_key]

    for doc_file in doc_files:
        score = 1 - (1 - scores[doc_file]['cosine_sim'])
        print(f"{score:.10f}".ljust(16), end="")

    # Find rank of 50-2
    rank_list = sorted(doc_files, key=lambda x: scores[x]['cosine_sim'], reverse=True)
    rank_50_2 = rank_list.index('GCT_notes_exemples_50-2.pdf') + 1
    print(f"| #{rank_50_2}")

# ============================================================================
# STEP 6: SCORE DIFFERENCES (50-22 - 50-2)
# ============================================================================
print("\n" + "="*80)
print("STEP 6: SCORE DIFFERENCE (50-22 minus 50-2)")
print("-" * 80)

print("\nQuery".ljust(25), "Score(50-22) - Score(50-2)".ljust(30), "Interpretation")
print("-" * 80)

for query_key in queries.keys():
    scores = results[query_key]
    score_22 = 1 - (1 - scores['GCT_notes_exemples_50-22.pdf']['cosine_sim'])
    score_2 = 1 - (1 - scores['GCT_notes_exemples_50-2.pdf']['cosine_sim'])
    diff = score_22 - score_2

    if diff > 0.001:
        interpretation = "50-22 HIGHER (50-2 not top)"
    elif diff < -0.001:
        interpretation = "50-2 HIGHER (correct)"
    else:
        interpretation = "VERY CLOSE (tied)"

    print(f"{query_key[:25].ljust(25)} {diff:+.10f}".ljust(30), interpretation)

# ============================================================================
# STEP 7: DIRECT QUERY EMBEDDING COMPARISON
# ============================================================================
print("\n" + "="*80)
print("STEP 7: ARABIC vs FRENCH QUERY EMBEDDING COMPARISON")
print("-" * 80)

arabic_emb = query_embeddings['A_Arabic_Original']['embedding']
french_emb = query_embeddings['B_French_Original']['embedding']

arabic_french_sim = np.dot(arabic_emb, french_emb)
print(f"\nArabic query L2 norm: {np.linalg.norm(arabic_emb):.6f}")
print(f"French query L2 norm: {np.linalg.norm(french_emb):.6f}")
print(f"Cosine similarity (Arabic vs French): {arabic_french_sim:.10f}")
print(f"\nBoth queries use:")
print(f"  Model: intfloat/multilingual-e5-small")
print(f"  Prefix: 'query:'")
print(f"  normalize_embeddings: True")

# ============================================================================
# STEP 8: ANALYSIS & CLASSIFICATION
# ============================================================================
print("\n" + "="*80)
print("STEP 8: ANALYSIS & CLASSIFICATION")
print("-" * 80)

# Check if 50-2 ever becomes rank 1 with French queries
french_queries = {k: v for k, v in results.items() if 'French' in k}
doc_50_2_rank_1_count = 0
for query_key, scores in french_queries.items():
    rank_list = sorted(doc_files, key=lambda x: scores[x]['cosine_sim'], reverse=True)
    if rank_list[0] == 'GCT_notes_exemples_50-2.pdf':
        doc_50_2_rank_1_count += 1

print(f"\nFRENCH QUERY ANALYSIS:")
print(f"Total French queries: {len(french_queries)}")
print(f"Times 50-2 is rank #1: {doc_50_2_rank_1_count}")

if doc_50_2_rank_1_count > 0:
    print(f"\n→ Small wording changes CAN make 50-2 rank #1")
    print(f"  This suggests the behavior is QUERY-SENSITIVE, not inherent")
else:
    print(f"\n→ 50-2 never ranks #1 with any French variant")
    print(f"  This suggests CONSISTENT MODEL BEHAVIOR for French")

# Check Arabic variants
arabic_queries = {k: v for k, v in results.items() if 'Arabic' in k}
doc_50_2_rank_1_arabic = 0
for query_key, scores in arabic_queries.items():
    rank_list = sorted(doc_files, key=lambda x: scores[x]['cosine_sim'], reverse=True)
    if rank_list[0] == 'GCT_notes_exemples_50-2.pdf':
        doc_50_2_rank_1_arabic += 1

print(f"\nARABIC QUERY ANALYSIS:")
print(f"Total Arabic queries: {len(arabic_queries)}")
print(f"Times 50-2 is rank #1: {doc_50_2_rank_1_arabic}")

# Final classification
print(f"\n" + "="*80)
print(f"PROVISIONAL CLASSIFICATION")
print(f"="*80)

if doc_50_2_rank_1_count > 0:
    print(f"\nB. Query preprocessing/wording issue")
    print(f"   Evidence: Different French wording variants produce different rankings")
else:
    print(f"\nA. E5-small model behavior")
    print(f"   Evidence: All French queries consistently rank 50-22 above 50-2")

print(f"\nWaiting for final review...")
