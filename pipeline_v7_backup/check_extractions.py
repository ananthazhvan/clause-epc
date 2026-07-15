#!/usr/bin/env python3
"""Honesty checker - zero LLM. NEVER weaken this file to make a run pass.

Verifies that every rule quote exists verbatim in its source clause and
every claim quote exists verbatim on its source page, and that page
numbers are valid. Nonzero exit on any failure.
"""
import glob
import json
import re
import sys


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def contains(text, quote):
    from common.quotecheck import contains as _c
    return _c(text, quote)


def main():
    failures = 0
    specs = {}
    for f in glob.glob("out/spec_*.json"):
        d = json.load(open(f))
        specs[d["section"]] = {c["clause_id"]: c for c in d["clauses"]}

    for f in sorted(glob.glob("out/rulebook_*.json")):
        d = json.load(open(f))
        n_bad = 0
        for r in d["rules"]:
            cl = specs.get(d["section"], {}).get(r["source_clause"])
            if cl is None:
                n_bad += 1
                print(f"FAIL source {r['rule_id']}: clause not found in parsed spec")
                continue
            if not contains(cl["text"], r["quote"]):
                n_bad += 1
                print(f"FAIL quote {r['rule_id']}: {r['quote'][:90]!r}")
        failures += n_bad
        print(f"{f}: {len(d['rules'])} rules, {n_bad} failures")

    for f in sorted(glob.glob("out/claims_*.json")):
        d = json.load(open(f))
        doc = json.load(open(f.replace("claims_", "doc_")))
        pages = {p["page"]: p["text"] for p in doc["pages"]}
        n_bad = 0
        for c in d["claims"]:
            if c.get("page") not in pages:
                n_bad += 1
                print(f"FAIL page {d['package']}: claim has invalid page {c.get('page')}")
                continue
            if not contains(pages[c["page"]], c["quote"]):
                n_bad += 1
                print(f"FAIL quote {d['package']} p{c['page']}: {c['quote'][:90]!r}")
        failures += n_bad
        print(f"{f}: {len(d['claims'])} claims, {n_bad} failures")

    if failures:
        print(f"CHECKER FAILED: {failures} failure(s). Fix extraction - never this checker.")
        sys.exit(1)
    print("CHECKER PASSED: every quote verified against its source document.")


if __name__ == "__main__":
    main()
