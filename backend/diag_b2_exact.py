# -*- coding: utf-8 -*-
"""Diagnostic: run the EXACT failing test functions, capturing full per-candidate scoring.

Strategy: import the real test module, monkeypatch RelevanceSelector.select to log,
then call each failing test function. AssertionError is caught (the test still
runs its real assertions) but the logged data is preserved and written to a
UTF-8 file so Arabic survives the console.

This guarantees the questions and candidates are byte-identical to the test file.
"""
import traceback
from app.relevance.selector import RelevanceSelector

import tests.test_relevance.test_selector as testmod

FAILING = [
    "test_multi_document_relevance",
    "test_missing_metadata_fallback",
    "test_multilingual_arabic_question",
    "test_multilingual_french_question",
    "test_english_question",
    "test_candidate_ranking",
]

OUT = open("diag_b2_exact_out.txt", "w", encoding="utf-8")


def P(*args):
    line = " ".join(str(a) for a in args)
    OUT.write(line + "\n")
    OUT.flush()


captured = []


def make_capture(original_select):
    def wrapped_select(self, query_intent, candidates):
        captured.append({
            "phase": "select",
            "question": query_intent.raw_question,
            "decision_numbers": list(query_intent.decision_numbers),
            "dates": [d.date().isoformat() for d in query_intent.dates],
            "entities": list(query_intent.entities),
            "committee_types": list(query_intent.committee_types),
            "comparison": query_intent.comparison_flag,
            "multi": query_intent.multi_indicator_flag,
            "threshold": self._RELEVANCE_THRESHOLD,
            "n_candidates": len(candidates),
            "candidates": [],
            "selected": None,
        })
        cur = captured[-1]
        for c in candidates:
            score, flags, reasons = self._compute_relevance(query_intent, c)
            cur["candidates"].append({
                "text": c.text,
                "score": c.score,
                "decision_number": c.decision_number,
                "decision_year": c.decision_year,
                "publication_date": c.publication_date.date().isoformat() if c.publication_date else None,
                "committee_type": c.committee_type,
                "entities": list(c.entities),
                "relevance": score,
                "flags": dict(flags),
                "reasons": list(reasons),
            })
        result = original_select(self, query_intent, candidates)
        cur["selected"] = [
            {
                "text": r.text,
                "decision_number": r.decision_number,
                "publication_date": r.publication_date.date().isoformat() if r.publication_date else None,
                "committee_type": r.committee_type,
                "relevance": r.relevance_score,
                "flags": dict(r.match_flags),
            }
            for r in result
        ]
        return result

    return wrapped_select


def run():
    orig_select = RelevanceSelector.select
    RelevanceSelector.select = make_capture(orig_select)

    for name in FAILING:
        captured.clear()
        P("\n" + "=" * 78)
        P("TEST FUNCTION:", name)
        fn = getattr(testmod, name)
        try:
            fn()
            P("  RESULT: PASS (assertion succeeded)")
        except AssertionError as e:
            P("  RESULT: FAIL ->", str(e).strip())
        except Exception as e:
            P("  RESULT: ERROR ->", repr(e))
            traceback.print_exc()

        for c in captured:
            P("\n  Question:", repr(c["question"]))
            P("  Intent: decision_numbers=%s dates=%s" % (c["decision_numbers"], c["dates"]))
            P("          entities=%s" % (c["entities"],))
            P("          committee_types=%s comparison=%s multi=%s"
              % (c["committee_types"], c["comparison"], c["multi"]))
            P("  Threshold: %.4f   n_candidates=%d" % (c["threshold"], c["n_candidates"]))
            for i, cand in enumerate(c["candidates"]):
                sel = any(
                    s["text"] == cand["text"] and s.get("decision_number") == cand["decision_number"]
                    for s in (c["selected"] or [])
                )
                P("    [%s] cand%d relevance=%.4f (retrieval=%.2f) decision=%s/%s date=%s committee=%s entities=%s"
                  % ("SELECTED" if sel else "rejected", i, cand["relevance"], cand["score"],
                     cand["decision_number"], cand["decision_year"], cand["publication_date"],
                     cand["committee_type"], cand["entities"]))
                P("         flags=%s" % (cand["flags"],))
                P("         reasons=%s" % (cand["reasons"],))
            if c["selected"]:
                P("  Selected (%d):" % len(c["selected"]))
                for s in c["selected"]:
                    P("     - relevance=%.4f decision=%s date=%s committee=%s text=%r"
                      % (s["relevance"], s["decision_number"], s["publication_date"],
                         s["committee_type"], s["text"][:70]))
            else:
                P("  Selected: (none)")

    RelevanceSelector.select = orig_select
    OUT.close()


if __name__ == "__main__":
    run()