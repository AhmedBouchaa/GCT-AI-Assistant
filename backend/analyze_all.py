# -*- coding: utf-8 -*-
"""Capture per-candidate scoring for ALL 23 tests under the CURRENT production selector.

Writes a UTF-8 report. Does not modify selector.py or any test.
"""
import traceback
from app.relevance.selector import RelevanceSelector
import tests.test_relevance.test_selector as testmod

OUT = open("analyze_all_out.txt", "w", encoding="utf-8")


def P(*a):
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


captured = []


def make_capture(orig):
    def wrapped(self, query_intent, candidates):
        captured.append({
            "question": query_intent.raw_question,
            "decision_numbers": list(query_intent.decision_numbers),
            "dates": [d.date().isoformat() for d in query_intent.dates],
            "entities": list(query_intent.entities),
            "committee_types": list(query_intent.committee_types),
            "comparison": query_intent.comparison_flag,
            "multi": query_intent.multi_indicator_flag,
            "threshold": self._RELEVANCE_THRESHOLD,
            "cands": [],
            "selected": None,
        })
        cur = captured[-1]
        for c in candidates:
            score, flags, reasons = self._compute_relevance(query_intent, c)
            # decompose metadata sub-components for insight
            md_score, md_flags, md_reasons = self._compute_metadata_match(query_intent, c)
            tx_score, tx_flags, tx_reasons = self._compute_textual_match(query_intent, c)
            cur["cands"].append({
                "text": c.text,
                "retrieval": c.score,
                "decision": c.decision_number,
                "year": c.decision_year,
                "date": c.publication_date.date().isoformat() if c.publication_date else None,
                "committee": c.committee_type,
                "entities": list(c.entities),
                "final": score,
                "metadata": md_score,
                "textual": tx_score,
                "flags": dict(flags),
                "reasons": list(reasons),
            })
        result = orig(self, query_intent, candidates)
        cur["selected"] = [(r.text, r.decision_number,
                            r.publication_date.date().isoformat() if r.publication_date else None,
                            r.relevance_score) for r in result]
        return result
    return wrapped


def main():
    orig = RelevanceSelector.select
    RelevanceSelector.select = make_capture(orig)
    names = sorted(n for n in dir(testmod) if n.startswith("test_"))
    for name in names:
        captured.clear()
        fn = getattr(testmod, name)
        P("\n" + "=" * 80)
        P("TEST:", name)
        try:
            fn()
            P("  ASSERTION: PASS")
        except AssertionError as e:
            P("  ASSERTION: FAIL ->", str(e).strip())
        except Exception as e:
            P("  ASSERTION: ERROR ->", repr(e))
        for c in captured:
            P("  Q:", repr(c["question"]))
            P("    intent: decision=%s dates=%s entities=%s committee=%s comparison=%s multi=%s"
              % (c["decision_numbers"], c["dates"], c["entities"], c["committee_types"],
                 c["comparison"], c["multi"]))
            P("    threshold=%.4f" % c["threshold"])
            for i, cd in enumerate(c["cands"]):
                sel = any(s[0] == cd["text"] and s[1] == cd["decision"] for s in (c["selected"] or []))
                P("    [%s] cand%d final=%.4f = 0.1*retr(%.2f) + 0.4*meta(%.4f) + 0.5*text(%.4f)"
                  % ("SELECTED" if sel else "rejected", i, cd["final"], cd["retrieval"],
                     cd["metadata"], cd["textual"]))
                P("         decision=%s/%s date=%s committee=%s entities=%s"
                  % (cd["decision"], cd["year"], cd["date"], cd["committee"], cd["entities"]))
                P("         flags=%s" % (cd["flags"],))
            P("    selected=%s" % ([(s[0][:50], s[1], s[2], round(s[3], 4)) for s in (c["selected"] or [])],))
    RelevanceSelector.select = orig
    OUT.close()


if __name__ == "__main__":
    main()