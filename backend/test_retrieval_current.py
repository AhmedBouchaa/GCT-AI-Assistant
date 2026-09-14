import sys
import os
sys.path.insert(0, '.')

from app.retrieval import retrieve

# Test Arabic question
question_ar = 'من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 اكتوبر 2026؟'
with open('ar_query.txt', 'w', encoding='utf-8') as f:
    f.write(question_ar)
results_ar = retrieve(question_ar, top_k=5)

with open('retrieval_results_ar.txt', 'w', encoding='utf-8') as f:
    f.write('Arabic question: {}\\n'.format(question_ar))
    for i, r in enumerate(results_ar, 1):
        f.write('{}. {} (score: {:.4f}, distance: {:.4f})\\n'.format(i, r['file_name'], r['score'], r['distance']))
        snippet = r['text'][:100].replace(chr(10), ' ')
        f.write('   Text: {}...\\n'.format(snippet))
    f.write('\\n')

# Test French question
question_fr = 'Qui est le président de la commission technique pour la maintenance des équipements lourds à Qabis ?'
with open('fr_query.txt', 'w', encoding='utf-8') as f:
    f.write(question_fr)
results_fr = retrieve(question_fr, top_k=5)

with open('retrieval_results_fr.txt', 'w', encoding='utf-8') as f:
    f.write('French question: {}\\n'.format(question_fr))
    for i, r in enumerate(results_fr, 1):
        f.write('{}. {} (score: {:.4f}, distance: {:.4f})\\n'.format(i, r['file_name'], r['score'], r['distance']))
        snippet = r['text'][:100].replace(chr(10), ' ')
        f.write('   Text: {}...\\n'.format(snippet))
    f.write('\\n')

print('Results written to files')