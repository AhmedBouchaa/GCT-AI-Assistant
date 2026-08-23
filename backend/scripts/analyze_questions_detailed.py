"""Analyse détaillée des 30 questions du benchmark."""
import json
from pathlib import Path
import re
from collections import Counter

# Charger les questions
test_questions_file = Path(__file__).parent.parent / "data" / "test_questions_v2.json"
with open(test_questions_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
questions = data["questions"]

print("="*80)
print("ANALYSE DÉTAILLÉE DES 30 QUESTIONS DU BENCHMARK")
print("="*80)

# 1. Analyse des numéros de décision
print("\n1. NUMÉROS DE DÉCISION EXTRAITS")
print("-" * 80)
decision_numbers = []
for q in questions:
    match = re.search(r'N°\s*(\d+)/2026', q['question'])
    if match:
        decision_numbers.append(match.group(1))

print(f"Nombre de questions avec numéro de décision : {len(decision_numbers)}/30")
print(f"Numéros : {', '.join(decision_numbers[:10])}...")

# 2. Analyse des mots-clés répétitifs
print("\n2. MOTS-CLÉS RÉPÉTITIFS")
print("-" * 80)
all_words = []
for q in questions:
    words = q['question'].split()
    all_words.extend(words)

word_counts = Counter(all_words)
print("Top 20 mots les plus fréquents :")
for word, count in word_counts.most_common(20):
    print(f"  {word}: {count}")

# 3. Analyse des types de questions
print("\n3. TYPES DE QUESTIONS")
print("-" * 80)
question_types = {
    "président": 0,
    "fonction": 0,
    "commission": 0,
    "comité": 0,
    "service": 0
}

for q in questions:
    text = q['question']
    if "من هو رئيس" in text or "من هي رئيسة" in text:
        question_types["président"] += 1
    if "ما هي وظيفة" in text:
        question_types["fonction"] += 1
    if "لجنة" in text:
        question_types["comité"] += 1
    if "مصلحة" in text:
        question_types["service"] += 1

for qtype, count in question_types.items():
    print(f"  {qtype}: {count}")

# 4. Analyse des commissions/services mentionnés
print("\n4. COMMISSIONS/SERVICES MENTIONNÉS")
print("-" * 80)
commissions = []
for q in questions:
    text = q['question']
    # Extraire les noms de commissions
    if "اللجنة الفنية لصيانة المعدات الثقيلة" in text:
        commissions.append("اللجنة الفنية لصيانة المعدات الثقيلة")
    elif "اللجنة التدريبية" in text:
        commissions.append("اللجنة التدريبية")
    elif "لجنة تقييم عروض" in text:
        commissions.append("لجنة تقييم عروض")
    elif "لجنة الجرد العام للمخزون" in text:
        commissions.append("لجنة الجرد العام للمخزون")
    elif "لجنة السلامة والأمن الصناعي" in text:
        commissions.append("لجنة السلامة والأمن الصناعي")
    elif "لجنة النظافة والبيئة الصناعية" in text:
        commissions.append("لجنة النظافة والبيئة الصناعية")
    elif "لجنة استلام التوريدات" in text:
        commissions.append("لجنة استلام التوريدات")

commission_counts = Counter(commissions)
for comm, count in commission_counts.items():
    print(f"  {comm}: {count}")

# 5. Analyse des noms propres
print("\n5. NOMS PROPRES EXTRAITS")
print("-" * 80)
names = []
for q in questions:
    text = q['question']
    # Patterns pour les noms arabes
    name_patterns = [
        r'محمد بن يوسف',
        r'منصور الغربي',
        r'عماد الزغلامي',
        r'سفيان بن يوسف',
        r'آمال الطرابلسي',
        r'رضا التومي',
        r'سامي الجلاصي',
        r'حاتم بوزيد',
        r'نور بن حسين',
        r'إيمان بن حسين',
        r'زياد الجربي',
        r'عمد الدريدي',
        r'مريم الطرابلسي',
        r'سفيان السلطاني',
        r'مريم بن سالم',
        r'آمال المسعودي',
        r'بلال الماجري',
        r'ليلى الفقية',
        r'أحمد بن حسين'
    ]
    for pattern in name_patterns:
        if pattern in text:
            names.append(pattern)

name_counts = Counter(names)
for name, count in name_counts.items():
    print(f"  {name}: {count}")

# 6. Analyse des lieux
print("\n6. LIEUX MENTIONNÉS")
print("-" * 80)
locations = []
for q in questions:
    text = q['question']
    if "قابس" in text:
        locations.append("قابس")
    if "مركب قابس" in text:
        locations.append("مركب قابس")
    if "الإدارة الجهوية بقابس" in text:
        locations.append("الإدارة الجهوية بقابس")
    if "وحدات الإنتاج بقابس" in text:
        locations.append("وحدات الإنتاج بقابس")

location_counts = Counter(locations)
for loc, count in location_counts.items():
    print(f"  {loc}: {count}")

# 7. Analyse de la similarité des questions
print("\n7. SIMILARITÉ DES QUESTIONS")
print("-" * 80)
print("Exemples de questions très similaires :")
similar_pairs = []
for i in range(len(questions)):
    for j in range(i+1, len(questions)):
        q1 = questions[i]['question']
        q2 = questions[j]['question']
        # Comparer les premiers mots
        words1 = q1.split()[:5]
        words2 = q2.split()[:5]
        if words1 == words2:
            similar_pairs.append((i+1, j+1, ' '.join(words1)))

print(f"Nombre de paires avec mêmes 5 premiers mots : {len(similar_pairs)}")
for i, j, prefix in similar_pairs[:5]:
    print(f"  Q{i} et Q{j}: {prefix}...")

# 8. Analyse discriminante
print("\n8. ÉLÉMENTS DISCRIMINANTS PAR QUESTION")
print("-" * 80)
for q in questions[:10]:
    print(f"\nQ{q['id']}: {q['question'][:60]}...")
    match = re.search(r'N°\s*(\d+)/2026', q['question'])
    if match:
        print(f"  → Discriminant principal: N° {match.group(1)}/2026")
    print(f"  → PDF attendu: {q['expected_pdf']}")

print("\n" + "="*80)
print("CONCLUSION DE L'ANALYSE")
print("="*80)
print("""
1. Les questions sont STRUCTURÉLLEMENT identiques
2. Le vocabulaire est très répétitif (من هو رئيس, اللجنة, بقابس, etc.)
3. Le SEUL élément discriminant est le numéro de décision (N° XXX/2026)
4. Les commissions sont les mêmes pour plusieurs questions
5. Les lieux sont identiques (قابس, مركب قابس)
6. Les noms propres sont peu nombreux et répétés
7. La similarité sémantique entre documents est EXTREMEMENT élevée

POURQUOI EMBEDDING-ONLY ÉCHOUE :
- Les embeddings capturent le sens global (commission, président, قابس)
- Tous les documents ont le même sens global
- Le numéro de décision est un identifiant, pas du sens sémantique
- Les embeddings ne peuvent pas distinguer "N° 006/2026" de "N° 007/2026"
- Les scores sont très proches (0.8963 vs 0.8896 = écart de 0.0067)

SOLUTION NÉCESSAIRE :
- Recherche exacte sur les numéros de décision
- Recherche lexicale sur les noms propres
- Métadonnées structurées
- Score hybride combinant sémantique + exact + métadonnées
""")
