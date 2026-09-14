# -*- coding: utf-8 -*-
"""Inspect real document metadata for the committee-document scenario.

Writes a UTF-8 report. Does not touch ChromaDB, embeddings, or any production file.
"""
import json

OUT = open("inspect_docs_out.txt", "w", encoding="utf-8")


def P(*a):
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def main():
    decision = json.load(open("data/decision_numbers.json", encoding="utf-8"))
    content = json.load(open("data/pdf_content.json", encoding="utf-8"))
    manifest = json.load(open("data/ingestion_manifest.json", encoding="utf-8"))

    P("decision_numbers records:", len(decision))
    P("pdf_content records:", len(content))
    P("manifest records:", len(manifest))

    P("\n=== pdf_content record structure (first record) ===")
    first_k = list(content)[0]
    P("key:", first_k)
    P(json.dumps(content[first_k], ensure_ascii=False, indent=2)[:1500])

    P("\n=== committee-related documents (decision_numbers map) ===")
    for k in sorted(decision):
        if "50-2" in k or "50-22" in k or "50-20" in k or "50-37" in k or "50-29" in k or "50-6" in k:
            P("  %s -> N° %s" % (k, decision[k]))

    P("\n=== full text of the 6 committee documents ===")
    for k in sorted(decision):
        if any(s in k for s in ("50-2.pdf", "50-22.pdf", "50-20.pdf",
                                "50-37.pdf", "50-29.pdf", "50-6.pdf")):
            rec = content.get(k, {})
            P("\n--- %s (N° %s) ---" % (k, decision.get(k)))
            if isinstance(rec, dict):
                for kk in rec:
                    vv = rec[kk]
                    if isinstance(vv, str):
                        P("  %s: %s" % (kk, vv[:600]))
                    else:
                        P("  %s: %r" % (kk, vv))
            else:
                P("  ", str(rec)[:800])

    OUT.close()


if __name__ == "__main__":
    main()