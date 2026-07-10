"""EVAL HARNESS ONLY - measures M4 against the corpus answer key.

The pipeline itself (m1-m4) must NEVER read _answer_key/ or import this file.
Verdicts are compared against verdict_pre_addendum: M4 judges against the base
spec revision; addendum precedence lands with M5 and will be evaluated against
verdict_post_addendum then.

Scoring per labeled check:
  caught      ground truth DEVIATION, we said DEVIATION
  flagged     ground truth DEVIATION, we routed it to a human
              (NEEDS_REVIEW / MISSING_EVIDENCE)
  missed      ground truth DEVIATION, we said COMPLY or nothing
  ok          ground truth COMPLIANT, we said COMPLY / NOT_ADDRESSED
  false_alarm ground truth COMPLIANT, we said DEVIATION
"""
import argparse
import collections
import glob
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="../clause_corpus/_answer_key/labels.json")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    labels = json.load(open(a.labels))
    verdicts = {}
    for p in glob.glob(os.path.join(a.out, "verdicts_*.json")):
        v = json.load(open(p))
        verdicts[v["package"]] = v["results"]

    tallies = collections.defaultdict(collections.Counter)
    misses, false_alarms, out_of_scope = [], [], []

    for lab in labels:
        pkg = (lab.get("submittal_pdf") or "").replace(".pdf", "")
        clause = lab.get("spec_clause") or ""
        tier = lab.get("tier") or "OK"
        gt_dev = (lab.get("verdict_pre_addendum") or "").upper().startswith("DEV")
        if pkg not in verdicts or not clause:
            out_of_scope.append(lab["check_id"])
            continue
        rows = [r for r in verdicts[pkg] if r["requirement"]["source_clause"] == clause]
        # Rule-level disambiguation: several rules can live under one clause
        # (efficiency at 50/75/100% load). Match the label to the rule whose
        # parameter tokens best overlap the label explanation; clause-level
        # aggregate stays as fallback.
        if len(rows) > 1 and lab.get("explanation"):
            import re as _re
            exp = set(_re.findall(r"[a-z0-9]+", lab["explanation"].lower()))
            def _score(r):
                pt = set(_re.findall(r"[a-z0-9]+", r["parameter"].lower()))
                return len(pt & exp)
            best = max(_score(r) for r in rows)
            top = [r for r in rows if _score(r) == best]
            if best > 0 and len(top) < len(rows):
                rows = top
        row_verdicts = {r["verdict"] for r in rows}
        if "DEVIATION" in row_verdicts:
            pred = "DEVIATION"
        elif row_verdicts & {"NEEDS_REVIEW", "MISSING_EVIDENCE"}:
            pred = "FLAGGED"
        elif "COMPLY" in row_verdicts:
            pred = "COMPLY"
        else:
            pred = "NO_COVERAGE"

        if gt_dev:
            outcome = {"DEVIATION": "caught", "FLAGGED": "flagged"}.get(pred, "missed")
            if outcome == "missed":
                misses.append((lab["check_id"], pkg, clause, pred, lab.get("explanation", "")[:140]))
        else:
            outcome = "false_alarm" if pred == "DEVIATION" else "ok"
            if outcome == "false_alarm":
                false_alarms.append((lab["check_id"], pkg, clause, lab.get("explanation", "")[:140]))
        tallies[tier][outcome] += 1

    print("=== M4 vs answer key (pre-addendum ground truth) ===")
    for tier in sorted(tallies):
        print(f"  {tier}: {dict(tallies[tier])}")
    dev_total = sum(t["caught"] + t["flagged"] + t["missed"] for t in tallies.values())
    caught = sum(t["caught"] for t in tallies.values())
    flagged = sum(t["flagged"] for t in tallies.values())
    if dev_total:
        print(f"\n  hard recall (caught): {caught}/{dev_total} = {caught/dev_total:.0%}")
        print(f"  flag-inclusive recall: {(caught+flagged)}/{dev_total} = {(caught+flagged)/dev_total:.0%}")
    print(f"  false alarms: {len(false_alarms)}   out of scope for M4: {len(out_of_scope)} ({', '.join(out_of_scope[:8])}{'...' if len(out_of_scope) > 8 else ''})")
    if misses:
        print("\n=== MISSES (actionable) ===")
        for m in misses:
            print("  ", m)
    if false_alarms:
        print("\n=== FALSE ALARMS ===")
        for m in false_alarms:
            print("  ", m)


if __name__ == "__main__":
    main()
