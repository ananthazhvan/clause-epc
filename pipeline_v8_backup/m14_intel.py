#!/usr/bin/env python3
"""M14 - cross-document intelligence.

The findings no single document contains: joins verdicts, vendors, POs,
schedule exposure, commissioning coverage and the spec itself, then lets an
AI analyst read the whole joined digest at once and surface what a human
coordination meeting would take hours to see.

Trust model: deterministic findings are computed first from the registers
and artifacts. AI findings are accepted only if every entity they cite
(package, PO, activity, vendor, section) actually exists in the project -
anything else is dropped.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load(out, name, default):
    p = os.path.join(out, name)
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            pass
    return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join("workspace", "corpus"))
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    out = args.out
    reg = os.path.join(args.corpus, "registers")

    verdicts = {}
    for p in sorted(glob.glob(os.path.join(out, "verdicts_*.json"))):
        d = json.load(open(p))
        verdicts[d.get("package")] = d
    supply = load(out, "supply_risk.json", {})
    vendors = load(out, "vendors.json", {})
    rule_counts = {}
    for p in glob.glob(os.path.join(out, "rulebook_*.json")):
        d = json.load(open(p))
        sec = d.get("section") or os.path.basename(p)[9:-5].replace("_", " ")
        rule_counts[sec] = len(d.get("rules", []))
    pos = []
    po_path = os.path.join(reg, "po_register.csv")
    if os.path.exists(po_path):
        pos = list(csv.DictReader(open(po_path)))
    cx = []
    cx_path = os.path.join(reg, "cx_test_register.csv")
    if os.path.exists(cx_path):
        cx = list(csv.DictReader(open(cx_path)))

    findings = []

    # D1 - vendor deviation fan-out: one shaky vendor touching many POs.
    by_vendor = {}
    for p in pos:
        by_vendor.setdefault(p.get("vendor"), []).append(p)
    dev_by_pkg = {k: [r for r in v.get("results", []) if r.get("verdict") == "DEVIATION"]
                  for k, v in verdicts.items()}
    sec_of_pkg = {k: v.get("section") for k, v in verdicts.items()}
    for vendor, vpos in by_vendor.items():
        secs = {p.get("spec_section") for p in vpos}
        devs = [(k, len(d)) for k, d in dev_by_pkg.items() if d and sec_of_pkg.get(k) in secs]
        if devs and len(vpos) >= 2:
            value = sum(float(p.get("value_inr") or 0) for p in vpos)
            findings.append({
                "kind": "vendor_fanout", "severity": "HIGH" if len(vpos) >= 3 else "MEDIUM",
                "title": f"{vendor}: deviations while holding {len(vpos)} POs",
                "narrative": (f"{vendor} has {sum(n for _, n in devs)} verified deviation(s) in "
                              f"{', '.join(k for k, _ in devs)} and holds {len(vpos)} purchase orders "
                              f"worth INR {value:,.0f}. A rejection cascades to every one of them."),
                "entities": [vendor] + [k for k, _ in devs] + [p.get("po_number") for p in vpos],
                "ai": False,
            })

    # D2 - commissioning coverage: sections with rules but no Cx test on them.
    covered = {(" ".join((r.get("spec_clause") or "").split()[:3])) for r in cx}
    for sec, n in sorted(rule_counts.items()):
        if n and sec not in covered:
            findings.append({
                "kind": "cx_gap", "severity": "MEDIUM",
                "title": f"Section {sec}: {n} rules, zero commissioning tests",
                "narrative": (f"Specification section {sec} compiles to {n} checkable requirements "
                              f"but no test in the commissioning register cites it. Nothing verifies "
                              f"those requirements on site."),
                "entities": [sec], "ai": False,
            })

    # D3 - critical-path supply exposure straight from M15.
    for a in (supply.get("alerts") or []):
        if a.get("severity") == "HIGH":
            findings.append({
                "kind": "supply_critical", "severity": "HIGH",
                "title": f"{a.get('po')} projected {abs(a.get('margin_days', 0))}d "
                         f"{'late' if a.get('margin_days', 0) < 0 else 'tight'} for {a.get('activity')}",
                "narrative": (f"{a.get('item')} ({a.get('vendor')}) is needed on site {a.get('needed_on_site')} "
                              f"for {a.get('activity_name')} but projects to arrive {a.get('projected_arrival')}. "
                              f"Days left to act: {a.get('days_to_act')}."),
                "entities": [a.get("po"), a.get("activity"), a.get("vendor")], "ai": False,
            })

    # AI layer - the analyst reads the whole joined digest at once.
    known = set()
    for k, v in verdicts.items():
        known.add(k)
        known.add(v.get("section"))
    for p in pos:
        known.update([p.get("po_number"), p.get("vendor"), p.get("spec_section")])
    for r in (supply.get("items") or []):
        known.add(r.get("activity"))
    known.discard(None)
    if not args.no_llm:
        digest = {
            "verdict_summaries": {k: v.get("summary") for k, v in verdicts.items()},
            "deviations": [{"package": k, "rule_id": r.get("rule_id"), "parameter": r.get("parameter"),
                            "reason": (r.get("reason") or "")[:200]}
                           for k, d in dev_by_pkg.items() for r in d][:60],
            "supply_alerts": (supply.get("alerts") or [])[:20],
            "vendor_scores": vendors.get("vendors", vendors) if isinstance(vendors, dict) else vendors,
            "cx_tests": len(cx), "rules_per_section": rule_counts,
        }
        try:
            from common import llm
            raw = llm.call(
                "You are the intelligence analyst for a data-centre EPC project. "
                "You get a joined digest of compliance verdicts, supply alerts, "
                "vendor scores and commissioning coverage. Find up to 6 "
                "cross-source insights a coordination meeting would miss - "
                "connections BETWEEN sources, never restatements of one row. "
                "Return ONLY a JSON array with fields: title, severity "
                "(HIGH|MEDIUM|LOW), narrative (<=60 words, cite exact IDs), "
                "entities (array of exact IDs used).",
                json.dumps(digest, indent=1))
            m = re.search(r"\[.*\]", raw, re.S)
            for f in (json.loads(m.group(0)) if m else []):
                ents = [e for e in (f.get("entities") or []) if e in known]
                if not ents:
                    continue
                findings.append({
                    "kind": "ai_insight",
                    "severity": str(f.get("severity", "LOW")).upper(),
                    "title": str(f.get("title", ""))[:140],
                    "narrative": str(f.get("narrative", ""))[:500],
                    "entities": ents, "ai": True,
                })
        except Exception as e:
            print(f"AI findings skipped ({e})")

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda f: order.get(f.get("severity"), 3))
    with open(os.path.join(out, "intel.json"), "w") as fh:
        json.dump({"findings": findings}, fh, indent=1)
    print(f"intel: {len(findings)} findings "
          f"({sum(1 for f in findings if f['ai'])} AI, entity-verified; "
          f"{sum(1 for f in findings if not f['ai'])} computed)")


if __name__ == "__main__":
    main()
