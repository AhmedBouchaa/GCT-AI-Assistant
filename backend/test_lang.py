import sys
sys.path.insert(0, 'D:/Ingenirie/Stage/GCT-AI-Assistant/backend')
from app.utils.language_detection import detect_language

question = 'من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 اكتوبر 2026؟'
print(f'Question: {question}')
print(f'Detected language: {detect_language(question)}')

# Test other languages
print(f'French test: {detect_language("Qui est le président")}')
print(f'English test: {detect_language("Who is the president")}')