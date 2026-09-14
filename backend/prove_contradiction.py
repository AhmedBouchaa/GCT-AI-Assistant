# -*- coding: utf-8 -*-
"""Prove the candidate_ranking vs irrelevant_high_similarity_rejection contradiction.

Both tests use a question that pins decision N° N/2026. One test demands that a
candidate with a DIFFERENT decision number be SELECTED; the other demands that a
candidate with a DIFFERENT decision number be REJECTED. No uniform deterministic
rule can satisfy both.

This script runs the two test functions under the BEST configuration found by
the exhaustive search (hard_reject mismatch + hard_match) and prints the exact
divergence.
"""
from app.relevance.selector import RelevanceSelector
from app.relevance.models import RelevantDoc
import tests.test_relevance.test_selector as testmod

MATCH_KEYS = ("decision_number_match", "date_match", "committee_match", "entity_match")
MISMATCH_KEYS = ("decision_number_mismatch", "date_mismatch", "committee_mismatch")


def best_select(self, query_intent, candidates):
    if not candidates:
        return []
    relevant = []
    for candidate in candidates:
        score, flags, reasons = self._compute_relevance(query_intent, candidate)
        mismatches = [k for k in MISMATCH_KEYS if flags.get(k)]
        matches = [k for k in MATCH_KEYS if flags.get(k)]
        if mismatches:
            continue  # hard_reject
        if matches:
            score = max(score, self._RELEVANCE_THRESHOLD)
        if score < self._RELEVANCE_THRESHOLD:
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


def show(test_name, fn, label):
    print("\n" + "=" * 72)
    print(label)
    print("TEST:", test_name)
    try:
        fn()
        print("  RESULT: PASS")
    except AssertionError as e:
        print("  RESULT: FAIL ->", str(e).strip())


def main():
    orig = RelevanceSelector.select
    RelevanceSelector.select = best_select
    try:
        show("test_irrelevant_high_similarity_rejection",
             testmod.test_irrelevant_high_similarity_rejection,
             "BEST CONFIG (hard_reject on decision mismatch)")
        show("test_candidate_ranking",
             testmod.test_candidate_ranking,
             "BEST CONFIG (hard_reject on decision mismatch)")
    finally:
        RelevanceSelector.select = orig

    # Now isolate the exact contradiction by hand
    print("\n" + "=" * 72)
    print("EXACT CONTRADICTION (independent of implementation):")
    print("""
  test_irrelevant_high_similarity_rejection:
    question = "Président de la commission technique N° 05/2026"
      -> intent.decision_numbers = [(5, 2026)]
    candidate with decision_number=99, year=2026
      -> decision_number_mismatch = True
    ASSERTION: len(relevant) == 1 AND relevant[0].decision_number == 5
      => the decision=99 candidate MUST be REJECTED.

  test_candidate_ranking:
    question = "Président de la commission de sécurité N° 10/2026"
      -> intent.decision_numbers = [(10, 2026)]
    candidate with decision_number=9, year=2026
      -> decision_number_mismatch = True
    ASSERTION: len(relevant) == 2 AND relevant[1].decision_number == 9
      => the decision=9 candidate MUST be SELECTED.

  Both candidates carry an explicit decision-number contradiction against the
  requested decision. One test demands rejection; the other demands selection.
  No uniform deterministic rule can satisfy both.
""")


if __name__ == "__main__":
    main()