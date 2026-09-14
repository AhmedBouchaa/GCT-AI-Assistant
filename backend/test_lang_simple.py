import sys
sys.path.insert(0, 'D:/Ingenirie/Stage/GCT-AI-Assistant/backend')
from app.utils.language_detection import detect_language

question = 'من هو رئيس لجنة السلامة والأمن الصناعي بمركب قابس بتاريخ 20 اكتوبر 2026؟'
print('Question: {}'.format(question))
print('Detected language: {}'.format(detect_language(question)))

# Test other languages
print('French test: {}'.format(detect_language("Qui est le président")))
print('English test: {}'.format(detect_language("Who is the president")))