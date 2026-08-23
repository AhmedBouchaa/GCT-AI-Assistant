#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.core.config import settings
from app.ingest.embeddings import E5EmbeddingService
from app.ingest.store import ChromaStore
from app.retrieval.retriever import retrieve
import numpy as np

print("="*80)
print("EMBEDDING & RETRIEVAL DIAGNOSTIC")
print("="*80)

# Configuration
print("\n1. CONFIGURATION")
print(f"Embedding model: {settings.embedding_model}")
print(f"Collection: {settings.chroma_collection_name}")

# Queries
arabic_q = 'من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟'
french_q = 'Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis ?'

print(f"\n2. QUERIES")
print(f"Arabic length: {len(arabic_q)} chars")
print(f"French length: {len(french_q)} chars")

# Embed queries
service = E5EmbeddingService()
arabic_emb = service.embed_texts([f"query: {arabic_q}"], prefix="")[0]
french_emb = service.embed_texts([f"query: {french_q}"], prefix="")[0]

print(f"\n3. EMBEDDINGS")
print(f"Arabic embedding dim: {len(arabic_emb)}")
print(f"French embedding dim: {len(french_emb)}")
print(f"Arabic L2 norm: {np.linalg.norm(arabic_emb):.6f}")
print(f"French L2 norm: {np.linalg.norm(french_emb):.6f}")

# ChromaDB query
store = ChromaStore(
    persist_directory=settings.chroma_persist_directory,
    collection_name=settings.chroma_collection_name,
)
collection = store._get_collection()

arabic_res = collection.query(query_embeddings=[arabic_emb], n_results=5, include=['metadatas', 'distances'])
french_res = collection.query(query_embeddings=[french_emb], n_results=5, include=['metadatas', 'distances'])

print(f"\n4. CHROMADB RESULTS")
print(f"\nArabic top 5:")
for i, (dist, meta) in enumerate(zip(arabic_res['distances'][0], arabic_res['metadatas'][0])):
    print(f"  {i+1}. {meta['file_name']}: {1-dist:.10f}")

print(f"\nFrench top 5:")
for i, (dist, meta) in enumerate(zip(french_res['distances'][0], french_res['metadatas'][0])):
    print(f"  {i+1}. {meta['file_name']}: {1-dist:.10f}")

# Retriever function
print(f"\n5. RETRIEVER FUNCTION RESULTS")
print(f"\nArabic retrieve():")
ar = retrieve(arabic_q, top_k=5)
for i, r in enumerate(ar[:3]):
    print(f"  {i+1}. {r['file_name']}: {r['score']:.10f}")

print(f"\nFrench retrieve():")
fr = retrieve(french_q, top_k=5)
for i, r in enumerate(fr[:3]):
    print(f"  {i+1}. {r['file_name']}: {r['score']:.10f}")

# Stored document check
print(f"\n6. STORED DOCUMENT VERIFICATION")
doc50_2 = collection.get(where={'file_name': 'GCT_notes_exemples_50-2.pdf'}, include=['documents', 'embeddings'])
if doc50_2['documents']:
    text = doc50_2['documents'][0]
    print(f"50-2 text length: {len(text)}")
    print(f"Contains 'محمد بن علي': {'محمد بن علي' in text}")

# Manual similarity check
if doc50_2['embeddings']:
    stored = np.array(doc50_2['embeddings'][0])
    ar_sim = np.dot(arabic_emb, stored)
    fr_sim = np.dot(french_emb, stored)
    print(f"\n7. MANUAL COSINE SIMILARITY TO 50-2")
    print(f"Arabic: {ar_sim:.10f} (distance: {1-ar_sim:.10f})")
    print(f"French: {fr_sim:.10f} (distance: {1-fr_sim:.10f})")
    print(f"Difference: {ar_sim - fr_sim:.10f}")
