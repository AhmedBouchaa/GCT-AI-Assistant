# -*- coding: utf-8 -*-
"""Exhaustive search over rule-based selector families.

For each configuration (how to treat each mismatch type, missing-metadata
policy, hard-match auto-include, threshold, weights), run ALL 23 tests and
report pass/fail. Goal: prove whether ANY uniform deterministic rule satisfies
all 23, or whether a subset of tests is mutually contradictory.

Does not modify selector.py or any test file.
"""
import itertools

import tests.test_relevance.test_selector as testmod
import app.relevance.selector as selmod
from app.relevance.models import RelevantDoc

MATCH_KEYS = ("decision_number_match", "date_match", "committee_match", "entity_match")
MISMATCH_KEYS = ("decision_number_mismatch", "date_mismatch", "committee_mismatch")

NAMES = [n for n in dir(testmod) if n.startswith("test_")]


def make_selector(mismatch_policy, missing_policy, hard_match, w_ret, w_meta, w_text, thr):
    """Return a select() implementation for the given policy."""

    def select(self, query_intent, candidates):
        if not candidates:
            return []
        relevant = []
        for candidate in candidates:
            score, flags, reasons = self._compute_relevance(query_intent, candidate)

            mismatches = [k for k in MISMATCH_KEYS if flags.get(k)]
            matches = [k for k in MATCH_KEYS if flags.get(k)]

            # missing-metadata detection: no match/mismatch/entity flag at all
            has_any_signal = bool(matches) or bool(mismatches) or flags.get("entity_match")

            if mismatches:
                if mismatch_policy == "hard_reject":
                    continue
                elif mismatch_policy == "soft_zero":
                    score = 0.0
                # "ignore" -> leave score as computed

            if not has_any_signal:
                if missing_policy == "neutral":
                    score = max(score, 0.5)
                elif missing_policy == "reject":
                    continue
                # "as_is" -> leave score

            if matches and hard_match:
                score = max(score, self._RELEVANCE_THRESHOLD)
                flags["hard_match"] = True
                reasons.append("Hard match: auto-included")

            if score < self._RELEVANCE_THRESHOLD:
                continue

            relevant.append(RelevantDoc(
                text=candidate.text, score=candidate.score, distance=candidate.distance,
                doc_id=candidate.doc_id, file_name=candidate.file_name, file_path=candidate.file_path,
                page_number=candidate.page_number, chunk_index=candidate.chunk_index,
                chunk_id=candidate.doc_id and candidate.chunk_id, decision_number=candidate.decision_number,
                decision_year=candidate.decision_year, publication_date=candidate.publication_date,
                committee_type=candidate.committee_type, entities=candidate.entities,
                relevance_score=score, match_flags=flags, reasons=reasons,
            ))
        return relevant

    return select


def run(select_impl):
    orig = selmod.RelevanceSelector.select
    selmod.RelevanceSelector.select = select_impl
    try:
        res = {}
        for name in NAMES:
            try:
                getattr(testmod, name)()
                res[name] = True
            except Exception:
                res[name] = False
    finally:
        selmod.RelevanceSelector.select = orig
    return res


def main():
    # baseline
    base = run(None)  # placeholder; real baseline from harness = 9 pass / 6 fail
    print("NOTE: baseline (production) = 9 passed / 6 failed:")
    print("   failing: test_candidate_ranking, test_english_question, test_missing_metadata_fallback,")
    print("            test_multi_document_relevance, test_multilingual_arabic_question, test_multilingual_french_question")

    policies = ["hard_reject", "soft_zero", "ignore"]
    missing_policies = ["neutral", "reject", "as_is"]
    thresholds = [0.15, 0.2, 0.25, 0.3, 0.35]
    weights = [(0.1, 0.4, 0.5), (0.05, 0.5, 0.45), (0.1, 0.5, 0.4), (0.05, 0.6, 0.35)]

    best = []
    total = 0
    for mismatch_policy, missing_policy, hard_match, thr, (wr, wm, wt) in itertools.product(
            policies, missing_policies, [True, False], thresholds, weights):
        total += 1
        selmod.RelevanceSelector._RETRIEVAL_WEIGHT = wr
        selmod.RelevanceSelector._METADATA_WEIGHT = wm
        selmod.RelevanceSelector._TEXTUAL_WEIGHT = wt
        selmod.RelevanceSelector._RELEVANCE_THRESHOLD = thr
        select_impl = make_selector(mismatch_policy, missing_policy, hard_match, wr, wm, wt, thr)
        res = run(select_impl)
        npass = sum(1 for v in res.values() if v)
        best.append((npass, mismatch_policy, missing_policy, hard_match, thr, (wr, wm, wt), res))

    best.sort(key=lambda x: -x[0])
    print("\nTotal configurations tested: %d" % total)
    print("\n=== TOP 15 ===")
    for npass, mp, msp, hm, thr, w, res in best[:15]:
        fails = [n for n in NAMES if not res[n]]
        print("  pass=%2d  mismatch=%-11s missing=%-8s hard_match=%-5s thr=%.2f w=%s"
              % (npass, mp, msp, hm, thr, w))
        print("        fails: %s" % (fails if fails else "NONE"))

    top = best[0]
    print("\n=== BEST: pass=%d ===" % top[0])
    for n in NAMES:
        print("  [%s] %s" % ("PASS" if top[6][n] else "FAIL", n))

    # Does any config reach 23?
    perfect = [b for b in best if b[0] == 23]
    print("\nConfigurations reaching 23/23: %d" % len(perfect))
    if perfect:
        for b in perfect[:5]:
            print("   mismatch=%s missing=%s hard=%s thr=%.2f w=%s" % (b[1], b[2], b[3], b[4], b[5]))


if __name__ == "__main__":
    main()