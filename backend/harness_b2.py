# -*- coding: utf-8 -*-
"""Configurable B2 scoring harness.

Runs EVERY test function in tests/test_relevance/test_selector.py against a
parametrised selector configuration (weights + threshold), without touching
the production selector.py or any test file.

For each configuration it reports:
  passed | failed | regressions | newly_fixed | threshold | weights
and a per-test PASS/FAIL table.

Usage:
  python harness_b2.py                       # sweep default grid
  python harness_b2.py --only 0.1,0.6,0.3,0.55  # single config
"""
import argparse
import importlib
import io
import sys
import traceback

import tests.test_relevance.test_selector as testmod

# capture per-test pass/fail under a given config
results = {}


def run_all(w_ret, w_meta, w_text, threshold):
    import app.relevance.selector as selmod
    old = (selmod.RelevanceSelector._RETRIEVAL_WEIGHT,
           selmod.RelevanceSelector._METADATA_WEIGHT,
           selmod.RelevanceSelector._TEXTUAL_WEIGHT,
           selmod.RelevanceSelector._RELEVANCE_THRESHOLD)
    selmod.RelevanceSelector._RETRIEVAL_WEIGHT = w_ret
    selmod.RelevanceSelector._METADATA_WEIGHT = w_meta
    selmod.RelevanceSelector._TEXTUAL_WEIGHT = w_text
    selmod.RelevanceSelector._RELEVANCE_THRESHOLD = threshold
    try:
        out = {}
        for name in sorted(n for n in dir(testmod) if n.startswith("test_")):
            fn = getattr(testmod, name)
            try:
                fn()
                out[name] = True
            except AssertionError:
                out[name] = False
            except Exception:
                out[name] = False
    finally:
        selmod.RelevanceSelector._RETRIEVAL_WEIGHT = old[0]
        selmod.RelevanceSelector._METADATA_WEIGHT = old[1]
        selmod.RelevanceSelector._TEXTUAL_WEIGHT = old[2]
        selmod.RelevanceSelector._RELEVANCE_THRESHOLD = old[3]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    # baseline = current production config
    BASE = (0.1, 0.4, 0.5, 0.35)
    base_res = run_all(*BASE)
    base_pass = {k for k, v in base_res.items() if v}
    base_fail = {k for k, v in base_res.items() if not v}

    print("BASELINE (current production): weights=(0.1,0.4,0.5) threshold=0.35")
    print("  passed=%d failed=%d" % (len(base_pass), len(base_fail)))
    print("  failing: %s" % ", ".join(sorted(base_fail)))

    if args.only:
        parts = [float(x) for x in args.only.split(",")]
        w_ret, w_meta, w_text, thr = parts
        res = run_all(w_ret, w_meta, w_text, thr)
        report(res, base_pass, base_fail, (w_ret, w_meta, w_text, thr))
        return

    # ---- grid sweep ----
    weight_grid = [round(x, 2) for x in (0.05, 0.1, 0.15, 0.2)]
    meta_grid = [round(x, 2) for x in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)]
    text_grid = [round(x, 2) for x in (0.3, 0.4, 0.5, 0.6)]
    thr_grid = [round(x, 2) for x in (0.15, 0.2, 0.25, 0.3, 0.35)]

    best = None
    rows = []
    for w_ret in weight_grid:
        for w_meta in meta_grid:
            for w_text in text_grid:
                for thr in thr_grid:
                    res = run_all(w_ret, w_meta, w_text, thr)
                    rows.append((res, (w_ret, w_meta, w_text, thr)))

    # sort by #passed desc, then #regressions asc
    def score(item):
        res, cfg = item
        p = sum(1 for v in res.values() if v)
        reg = len([k for k in base_pass if not res.get(k, False)])
        new = len([k for k in base_fail if res.get(k, False)])
        return (-p, reg, -new)

    rows.sort(key=score)
    print("\n=== TOP 25 CONFIGURATIONS (by #passed, then #regressions asc) ===")
    for res, cfg in rows[:25]:
        p = sum(1 for v in res.values() if v)
        reg = len([k for k in base_pass if not res.get(k, False)])
        new = len([k for k in base_fail if res.get(k, False)])
        tag = ""
        if reg == 0 and new == len(base_fail):
            tag = "  <-- PERFECT (fixes all, no regressions)"
        print("  passed=%2d failed=%d reg=%d newfix=%d  w=(%.2f,%.2f,%.2f) thr=%.2f%s"
              % (p, 23 - p, reg, new, cfg[0], cfg[1], cfg[2], cfg[3], tag))

    # full detail for the best config
    best_res, best_cfg = rows[0]
    print("\n=== DETAIL: best config w=(%.2f,%.2f,%.2f) thr=%.2f ==="
          % (best_cfg[0], best_cfg[1], best_cfg[2], best_cfg[3]))
    report(best_res, base_pass, base_fail, best_cfg)


def report(res, base_pass, base_fail, cfg):
    for name in sorted(res):
        v = res[name]
        if name in base_pass and not v:
            tag = "REGRESSION"
        elif name in base_fail and v:
            tag = "NEWFIX"
        elif v:
            tag = "pass"
        else:
            tag = "still-fail"
        print("  [%-9s] %s" % (tag, name))


if __name__ == "__main__":
    main()