# -*- coding: utf-8 -*-
from app.relevance.query_analyzer import QueryAnalyzer

def debug_entities():
    analyzer = QueryAnalyzer()
    question = "Quel président est meilleur, Ahmed ou Mohamed?"
    intent = analyzer.analyze(question)
    print(f"Question: {question}")
    print(f"Intent: {intent}")
    print(f"Entities: {intent.entities}")

if __name__ == "__main__":
    debug_entities()