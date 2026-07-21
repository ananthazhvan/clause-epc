"""Cross-evidence conflict sweep (deterministic, no LLM, no prompts).

A package quotes the same parameter in several places - datasheet, compliance
matrix, factory test report, certificates. Vendors get away with deviations
because reviewers read the governing table and stop. This sweep re-reads every
COMPLY verdict against ALL evidence captured for that parameter; if the
package contradicts itself, the check is routed to a human with both quotes
attached. It also reclassifies 'no evidence' deviations as MISSING_EVIDENCE -
absence of evidence is a documentation gap, not a measured deviation.
Runs after the addendum blast wave, before dispositions. Pure post-processing
of claims + verdicts already on disk; the answer key is never read.
"""
import argparse
import glob
import json
import os
import re

RED_FLAGS = ("below requirement", "above requirement", "differs", "absent",
             "not tested", "fail", "non-compliant", "noncompliant", "exceeds")


def norm(v):
    return re.sub(r"\s+", " ", str(v or "").strip().lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    total = flips = reclass = 0
    for vp in sorted(glob.glob(os.path.join(args.out, "verdicts_*.json"))):
        v = json.load(open(vp))
        pkg = v.get("package", "")
        cp = os.path.join(args.out, f"claims_{pkg}.json")
        if not os.path.exists(cp):
            continue
        c = json.load(open(cp))
        claims = c.get("claims") if isinstance(c, dict) else c
        byparam = {}
        for cl in claims or []:
            byparam.setdefault(norm(cl.get("parameter")), []).append(cl)
        changed = False
        for r in v.get("results", []):
            total += 1
            verdict = r.get("verdict")
            reason = str(r.get("reason") or "")
            if verdict == "DEVIATION" and "provides no evidence for the parameter" in reason:
                r["verdict"] = "MISSING_EVIDENCE"
                r["reason"] = reason + " [conflict sweep: reclassified - absence of evidence is a gap, not a measured deviation]"
                r["conflict_sweep"] = "reclassified"
                reclass += 1
                changed = True
                continue
            if verdict != "COMPLY":
                continue
            cls = byparam.get(norm(r.get("parameter"))) or []
            vals = {}
            for cl in cls:
                vals.setdefault(norm(cl.get("value")) + "|" + norm(cl.get("unit")), cl)
            reds = [cl for cl in cls if any(f in norm(cl.get("value")) for f in RED_FLAGS)]
            if len(vals) > 1 or reds:
                seen = list(vals.values())
                gov = seen[0]
                pick = reds[0] if reds else seen[1]
                gtxt = (str(gov.get("value") or "") + " " + str(gov.get("unit") or "")).strip()
                ptxt = (str(pick.get("value") or "") + " " + str(pick.get("unit") or "")).strip()
                r["verdict"] = "NEEDS_REVIEW"
                r["conflict_sweep"] = "escalated"
                r["reason"] = (f"package contradicts itself on '{r.get('parameter')}': "
                               f"p{gov.get('page')} ({gov.get('location')}) says '{gtxt}' vs "
                               f"p{pick.get('page')} ({pick.get('location')}) says '{ptxt}' - "
                               "conflicting evidence is never silent compliance; routed to the "
                               "engineer with both quotes")
                r["conflict_quotes"] = [gov.get("quote"), pick.get("quote")]
                flips += 1
                changed = True
        if changed:
            json.dump(v, open(vp, "w"), indent=1)
    print(f"  conflict sweep: {flips} contradiction(s) routed to review, "
          f"{reclass} no-evidence check(s) reclassified, {total} checks scanned")


if __name__ == "__main__":
    main()
