# -*- coding: utf-8 -*-
"""Test the HARD-SIGNAL relevance model against ALL 23 tests WITHOUT touching selector.py.

Hard-signal model:
  - A candidate with an EXPLICIT CONTRADICTION on a requested hard fact is
    auto-EXCLUDED (decision mismatch, date mismatch, committee mismatch).
  - A candidate with a POSITIVE HARD MATCH is auto-INCLUDED
    (decision match, date match, committee match, entity match).
  - Everything else falls back to the linear score vs threshold.
  - Missing metadata is NEUTRAL (never a mismatch).

This is a monkeypatch of RelevanceSelector.select only; _compute_relevance,
weights, threshold and QueryAnalyzer are untouched.
"""
import importlib
import sys

import tests.test_relevance.test_selector as testmod
import app.relevance.selector as selmod
from app.relevance.models import RelevantDoc

MATCH_KEYS = ("decision_number_match", "date_match", "committee_match", "entity_match")
MISMATCH_KEYS = ("decision_number_mismatch", "date_mismatch", "committee_mismatch")


def hard_select(self, query_intent, candidates):
    if not candidates:
        return []
    relevant = []
    for candidate in candidates:
        score, flags, reasons = self._compute_relevance(query_intent, candidate)

        has_match = any(flags.get(k) for k in MATCH_KEYS)
        has_mismatch = any(flags.get(k) for k in MISMATCH_KEYS)

        if has_mismatch:
            continue  # explicit contradiction -> reject outright
        if has_match:
            score = max(score, self._RELEVANCE_THRESHOLD)
            flags["hard_match"] = True
            reasons.append("Hard match: auto-included on deterministic signal")
        elif score < self._RELEVANCE_THRESHOLD:
            continue

        relevant.append(RelevantDoc(
            text=candidate.text, score=candidate.score, distance=candidate.distance,
            doc_id=candidate.doc_id, file_name=candidate.file_name, file_path=candidate.file_path,
            page_number=candidate.page_number, chunk_index=candidate.chunk_index,
            chunk_id=candidate.chunk_id, decision_number=candidate.decision_number,
            decision_year=candidate.decision_year, publication_date=candidate.publication_date,
            committee_type=candidate.committee_type, entities=candidate.entities,
            relevance_score=score, match_flags=flags, reasons=reasons,
        ))
    return relevant


def run_with(select_impl, label):
    orig = selmod.RelevanceSelector.select
    selmod.RelevanceSelector.select = select_impl
    try:
        passed, failed = [], []
        for name in sorted(n for n in dir(testmod) if n.startswith("test_")):
            try:
                getattr(testmod, name)()
                passed.append(name)
            except AssertionError:
                failed.append(name)
            except Exception as e:
                failed.append(name)
    finally:
        selmod.RelevanceSelector.select = orig
    print("\n=== %s ===" % label)
    print("  passed=%d failed=%d" % (len(passed), len(failed)))
    for f in failed:
        print("    FAIL: %s" % f)
    return passed, failed


def main():
    # 1. baseline (current production)
    base_pass, base_fail = run_with(None, "BASELINE (production selector, unmodified)")

    # 2. hard-signal model on CURRENT weights/threshold
    run_with(hard_select, "HARD-SIGNAL model, weights=(0.1,0.4,0.5) thr=0.35")

    # 3. hard-signal + neutral-metadata base (base=0.5 instead of 0.0)
    #    We simulate by patching _compute_metadata_match too.
    orig_mm = selmod.RelevanceSelector._compute_metadata_match

    def neutral_mm(self, query_intent, candidate):
        score, flags, reasons = orig_mm(self, query_intent, candidate)
        # if no signal at all was set, metadata is missing -> neutral 0.5
        signal_keys = (MATCH_KEYS + MISMATCH_KEYS +
                       ("entity_match",))
        if not any(k in flags for k in signal_keys):
            score = 0.5
            flags["metadata_missing_neutral"] = True
            reasons.append("Metadata missing: neutral (not a mismatch)")
        return score, flags, reasons

    selmod.RelevanceSelector._compute_metadata_match = neutral_mm
    try:
        run_with(hard_select, "HARD-SIGNAL + neutral-missing-metadata base=0.5")
    finally:
        selmod.RelevanceSelector._compute_metadata_match = orig_mm


if __name__ == "__main__":
    main()