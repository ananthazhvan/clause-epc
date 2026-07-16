#!/usr/bin/env python3
"""M4b - evidence adjudication (second AI layer).

M4 joins compiled rules to extracted claims deterministically. Everything it
could not resolve (MISSING_EVIDENCE / NOT_ADDRESSED / NEEDS_REVIEW) is handed
to an independent reviewer pass that reads the ENTIRE submittal package and
hunts for evidence rule by rule - the way a human reviewer re-reads the whole
package when the compliance matrix is silent.

Trust model: the model proposes, the code disposes. A verdict is only
upgraded when the model returns a verbatim quote that provably exists in the
submittal text (whitespace-normalised substring check). No verified quote,
no verdict change. Every upgrade carries its evidence: page, quote, reason.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import llm, pool

UNRESOLVED = {"MISSING_EVIDENCE", "NOT_ADDRESSED", "NEEDS_REVIEW"}
VALID = {"COMPLY", "DEVIATION", "NOT_ENOUGH_INFORMATION"}
BATCH = 25

SYSTEM = (
    "You are a senior construction submittal reviewer. You receive "
    "specification requirements that an automated matcher could not resolve, "
    "plus the full text of one vendor submittal package. For each requirement "
    "search the whole package for evidence.\n"
    "Return ONLY a JSON array, one object per rule_id, with fields: rule_id, "
    'verdict ("COMPLY" | "DEVIATION" | "NOT_ENOUGH_INFORMATION"), page '
    "(integer), quote (a sentence or table row copied VERBATIM, "
    "character-for-character, from the package text that proves the verdict), "
    "reason (under 30 words).\n"
    "Hard rules: the quote must exist verbatim in the package text. Check "
    "footnotes and small print - a footnote can contradict a compliance "
    "matrix. If no explicit evidence exists, verdict is "
    "NOT_ENOUGH_INFORMATION with an empty quote. Never guess or paraphrase."
)


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def parse_array(text):
    text = re.sub(r"^```[a-z]*|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        v = json.loads(text)
        return v if isinstance(v, list) else []
    except Exception:
        pass
    a, b = text.find("["), text.rfind("]")
    if a >= 0 and b > a:
        try:
            v = json.loads(text[a:b + 1])
            return v if isinstance(v, list) else []
        except Exception:
            pass
    return []


def doc_pages(out, pkg):
    for p in glob.glob(os.path.join(out, "doc_*.json")):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        t = d.get("transmittal")
        if not isinstance(t, dict):
            continue
        vals = [str(v) for v in t.values()]
        if pkg in vals or any(pkg in v for v in vals):
            return d.get("pages") or []
    return []


def adjudicate(path, out):
    f = json.load(open(path))
    pkg, section = f.get("package"), f.get("section")
    open_rules = [r for r in f.get("results", []) if r.get("verdict") in UNRESOLVED]
    if not open_rules:
        return f"{pkg}: nothing unresolved"
    pages = doc_pages(out, pkg)
    if not pages:
        return f"{pkg}: SKIP - source document text not found"
    full = "\n\n".join(f"[page {p.get('page')}]\n{p.get('text', '')}" for p in pages)
    nfull = norm(full)
    comply = dev = 0
    for i in range(0, len(open_rules), BATCH):
        chunk = open_rules[i:i + BATCH]
        rules_json = [{
            "rule_id": r.get("rule_id"),
            "parameter": r.get("parameter"),
            "requirement": {k: (r.get("requirement") or {}).get(k)
                            for k in ("operator", "value", "unit", "quote", "condition")},
        } for r in chunk]
        user = (f"Submittal package {pkg} (specification section {section}).\n"
                f"Unresolved requirements:\n{json.dumps(rules_json, indent=1)}\n\n"
                f"FULL PACKAGE TEXT:\n{full}")
        try:
            raw = llm.call(SYSTEM, user)
        except Exception as e:
            return f"{pkg}: LLM unavailable ({e}) - adjudication skipped"
        by_id = {r.get("rule_id"): r for r in chunk}
        for a in parse_array(raw):
            if not isinstance(a, dict):
                continue
            r = by_id.get(a.get("rule_id"))
            if r is None:
                continue
            v = str(a.get("verdict", "")).upper().replace(" ", "_")
            q = str(a.get("quote") or "").strip()
            verified = len(q) >= 12 and norm(q) in nfull
            if v in ("COMPLY", "DEVIATION") and verified:
                r["verdict"] = v
                r["reason"] = (r.get("reason") or "")
                r["adjudication"] = {
                    "page": a.get("page"),
                    "quote": q[:400],
                    "reason": str(a.get("reason", ""))[:300],
                    "evidence_verified": True,
                }
                if v == "COMPLY":
                    comply += 1
                else:
                    dev += 1
            else:
                r.setdefault("adjudication", {
                    "reason": str(a.get("reason", ""))[:300],
                    "evidence_verified": False,
                })
    counts = {}
    for r in f.get("results", []):
        counts[r.get("verdict")] = counts.get(r.get("verdict"), 0) + 1
    if isinstance(f.get("summary"), dict):
        f["summary"] = counts
    f["adjudication_summary"] = {
        "unresolved_before": len(open_rules),
        "resolved_comply": comply,
        "resolved_deviation": dev,
        "still_open": len(open_rules) - comply - dev,
    }
    with open(path, "w") as fh:
        json.dump(f, fh, indent=1)
    return (f"{pkg}: {len(open_rules)} unresolved -> {comply} comply, "
            f"{dev} deviation, {len(open_rules) - comply - dev} still open")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.out, "verdicts_*.json")))
    if not files:
        sys.exit("no verdicts_*.json found - run m4_verify.py first")
    lines = pool.pmap(lambda p: adjudicate(p, args.out), files, workers=args.workers)
    tot_c = tot_d = tot_o = 0
    for ln in lines:
        print(ln)
        m = re.search(r"(\d+) unresolved -> (\d+) comply, (\d+) deviation, (\d+) still open", str(ln))
        if m:
            tot_c += int(m.group(2))
            tot_d += int(m.group(3))
            tot_o += int(m.group(4))
    print(f"adjudication: +{tot_c} comply, +{tot_d} deviation, {tot_o} remain open "
          f"(every upgrade carries a verbatim, verified quote)")


if __name__ == "__main__":
    main()
