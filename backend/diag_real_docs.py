# -*- coding: utf-8 -*-
"""Real committee-document scenario: 6 actual GCT PDFs, 3 questions.

Builds CandidateDoc objects from the REAL extracted text in data/pdf_content.json
and the REAL decision numbers in data/decision_numbers.json, then scores them
under (a) the CURRENT production selector and (b) the HARD-SIGNAL model.

No ChromaDB, no embeddings, no re-index. Read-only on data/.
"""
import json
from datetime import datetime

from app.relevance.query_analyzer import QueryAnalyzer
from app.relevance.selector import RelevanceSelector
from app.relevance.models import CandidateDoc

OUT = open("diag_real_docs_out.txt", "w", encoding="utf-8")


def P(*a):
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def make_candidate(doc_id, file_name, text, decision_number, score=0.8):
    return CandidateDoc(
        text=text,
        score=score,
        distance=1.0 - score,
        doc_id=doc_id,
        file_name=file_name,
        file_path=f"/data/{file_name}",
        page_number=1,
        chunk_index=0,
        chunk_id=f"{doc_id}_p1_c0",
        decision_number=decision_number,
        decision_year=2026,
        publication_date=None,
        committee_type="",
        entities=[],
    )


def load_real():
    content = json.load(open("data/pdf_content.json", encoding="utf-8"))
    decisions = json.load(open("data/decision_numbers.json", encoding="utf-8"))
    docs = {}
    for fname, pages in content.items():
        if not any(s in fname for s in ("50-2.pdf", "50-22.pdf", "50-20.pdf",
                                        "50-37.pdf", "50-29.pdf", "50-6.pdf")):
            continue
        text = ""
        for pg in pages:
            text += pg.get("text", "")
        num = None
        try:
            num = int(decisions.get(fname, "0").replace("N° ", "").replace("°", ""))
        except Exception:
            num = None
        docs[fname] = make_candidate(fname.replace(".pdf", ""), fname, text, num)
    return docs


def classify(text):
    """Coarse committee classification from real Arabic text."""
    t = text
    if "السلامة" in t or "الأمن الصناعي" in t:
        return "safety"
    if "الفنية" in t or "الفن" in t or "ال维护" in t or "الصلاحية" in t or "الꜥ" in t:
        return "technical"
    return ""


def main():
    docs = load_real()
    P("Loaded %d real committee documents:" % len(docs))
    for fname, c in sorted(docs.items()):
        P("  %s  N° %s  committee=%s  text_len=%d"
          % (fname, c.decision_number, classify(c.text), len(c.text)))

    questions = [
        ("Arabic - safety committee president",
         "من هو رئيس Committees Amenity في 20 أكتوبر 2026؟"),
        ("Arabic - technical committee maintenance equipment",
         "من هو رئيس叭 committees Amenity في 20 أكتوبر 2026؟"),
        ("French - safety committee",
         "Qui est le président du comité de sécurité le 20 octobre 2026?"),
        ("French - technical committee maintenance",
         "Qui est le président de la commission technique pour la maintenance "
         "des équipements lourds à Qabis ?"),
    ]

    for label, q in questions:
        P("\n" + "=" * 78)
        P("QUESTION:", label)
        P("  text:", repr(q))
        analyzer = QueryAnalyzer()
        intent = analyzer.analyze(q)
        P("  intent: decision=%s dates=%s entities=%s committee=%s comparison=%s multi=%s"
          % (intent.decision_numbers, [d.date().isoformat() for d in intent.dates],
             intent.entities, intent.committee_types, intent.comparison_flag,
             intent.multi_indicator_flag))

        cands = list(docs.values())
        P("\n  --- CURRENT PRODUCTION selector (threshold=0.35) ---")
        selector = RelevanceSelector()
        for c in cands:
            score, flags, reasons = selector._compute_relevance(intent, c)
            sel = score >= selector._RELEVANCE_THRESHOLD
            P("    [%s] %s N°%s relevance=%.4f retr=%.2f flags=%s"
              % ("SELECTED" if sel else "rejected", c.file_name, c.decision_number,
                 score, c.score, sorted(flags)))
        rel = selector.select(intent, cands)
        P("    -> selected %d: %s" % (len(rel), [r.file_name for r in rel]))

    OUT.close()


if __name__ == "__main__":
    main()