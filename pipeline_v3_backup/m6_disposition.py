"""M6 - Disposition engine.

For every open deviation (post-addendum verdicts = current contract
reality), walk the project graph and price the decision:

  deviation -> section -> POs (value, lead time, delivery status)
            -> schedule activities (float, critical path)
            -> downstream Cx tests

reorder_slip_days = lead_time_weeks * 7 - min_float_days (clamped at 0).
If slip > 0 the reorder eats through all schedule float and lands on the
critical path - that many days of project delay.

Recommendations are decision support with the math shown, never verdicts:
engineers close NCRs, CLAUSE drafts them. Zero LLM calls.

Outputs: out/dispositions.json (per-package, severity-ranked queue) and
out/ncr_register.csv (the QMS audit trail the PS asks for).
"""
import csv
import glob
import json

REGISTERS = "../clause_corpus/registers"
SECTION_ACTIVITY_KEYWORD = {
    "26 33 53": "ups", "26 32 13": "generator",
    "23 81 23": "crah", "21 22 00": "fire",
}


def main(out="out"):
    pos = list(csv.DictReader(open(f"{REGISTERS}/po_register.csv")))
    acts = list(csv.DictReader(open(f"{REGISTERS}/schedule.csv")))
    cx = list(csv.DictReader(open(f"{REGISTERS}/cx_test_register.csv")))
    wave = json.load(open(f"{out}/blast_wave.json"))
    stale_cx = {t["test_id"] for t in wave.get("cx_tests_stale", [])}
    invalid_pos = {p["po_number"] for p in wave.get("pos_invalidated", [])}

    ncr_rows, packages = [], []
    seq = 0
    for path in sorted(glob.glob(f"{out}/post/verdicts_*.json")):
        v = json.load(open(path))
        pkg, sec = v["package"], v["section"]
        sec_pos = [p for p in pos if p["spec_section"] == sec]
        kw = SECTION_ACTIVITY_KEYWORD.get(sec)
        sec_acts = [a for a in acts if kw and kw in a["name"].lower()]
        min_float = min((int(a["float_days"]) for a in sec_acts), default=None)
        lead_weeks = max((int(p["lead_time_weeks"]) for p in sec_pos), default=0)
        value_inr = sum(int(p["value_inr"]) for p in sec_pos)
        delivered = all(p["delivery_status"] == "DELIVERED" for p in sec_pos) if sec_pos else False
        sec_cx = [t for t in cx if t["spec_clause"].startswith(sec)]

        findings = [r for r in v["results"] if r["verdict"] == "DEVIATION"
                    or "false_comply" in r["flags"]]
        reviews = [r for r in v["results"] if r["verdict"] == "NEEDS_REVIEW"]
        items = []
        for r in findings:
            seq += 1
            slip = max(0, lead_weeks * 7 - (min_float if min_float is not None else 0)) if sec_pos else 0
            gov = r.get("governing_claim") or {}
            options = [
                {"option": "REJECT_AND_REORDER",
                 "math": f"lead time {lead_weeks} wk = {lead_weeks*7} d vs "
                          f"{min_float if min_float is not None else 'n/a'} d schedule float "
                          f"-> {slip} d onto the critical path",
                 "schedule_slip_days": slip,
                 "cost_exposure_inr": value_inr,
                 "note": "equipment already DELIVERED - reorder also strands "
                         f"\u20b9{value_inr:,} of delivered plant" if delivered else None},
                {"option": "USE_AS_IS_CONCESSION",
                 "math": "0 d slip; requires engineering concession with margin "
                          "stack-up check across all accepted deviations in this package",
                 "schedule_slip_days": 0,
                 "requires": "client + consultant signoff; margin analysis"},
                {"option": "VENDOR_REMEDIATION",
                 "math": "vendor rectifies/retests at factory or site; typical "
                          "4-8 wk, absorbed by float if <"
                          f"{min_float if min_float is not None else 'n/a'} d",
                 "schedule_slip_days": None},
            ]
            recommended = ("USE_AS_IS_CONCESSION_REVIEW" if slip > 0 else
                           "VENDOR_REMEDIATION" if delivered else "REJECT_AND_REORDER")
            ncr_id = f"NCR-{seq:03d}"
            item = {
                "ncr_id": ncr_id, "package": pkg, "section": sec,
                "rule_id": r["rule_id"],
                "parameter": r["requirement"]["parameter"],
                "verdict": r["verdict"], "flags": r["flags"],
                "requirement": {k: r["requirement"].get(k) for k in
                                 ("operator", "value", "unit", "condition",
                                  "source_clause", "quote", "page")},
                "evidence": {k: gov.get(k) for k in
                              ("value", "unit", "condition", "quote", "page", "location")},
                "reason": r["reason"],
                "amended_by": next((a["addendum"] for a in wave.get("rule_amendments", [])
                                     if a["rule_id"] == r["rule_id"]), None),
                "blast": {
                    "pos": [{"po": p["po_number"],
                              "status": "INVALID" if p["po_number"] in invalid_pos
                                         else p["delivery_status"],
                              "value_inr": int(p["value_inr"])} for p in sec_pos],
                    "activities": [{"id": a["activity_id"], "float_days": int(a["float_days"]),
                                     "critical": a["critical_path"] == "True"}
                                    for a in sec_acts[:6]],
                    "cx_tests": [{"id": t["test_id"],
                                   "status": "STALE" if t["test_id"] in stale_cx else t["status"]}
                                  for t in sec_cx[:8]],
                },
                "options": options,
                "recommended": recommended,
            }
            items.append(item)
            ncr_rows.append({
                "ncr_id": ncr_id, "package": pkg, "spec_clause":
                    r["requirement"]["source_clause"],
                "parameter": r["requirement"]["parameter"],
                "description": r["reason"][:220],
                "severity": "MAJOR" if "false_comply" in r["flags"] else "MINOR",
                "recommended_disposition": recommended,
                "schedule_slip_if_rejected_days": slip,
                "cost_exposure_inr": value_inr,
                "status": "OPEN",
            })
        severity = (sum(3 for i in items if "false_comply" in i["flags"])
                    + 2 * len(items) + len(reviews)
                    + (5 if any(i["amended_by"] for i in items) else 0))
        packages.append({
            "package": pkg, "section": sec, "severity_score": severity,
            "open_ncrs": len(items), "needs_review": len(reviews),
            "value_inr": value_inr, "lead_time_weeks": lead_weeks,
            "min_float_days": min_float, "delivered": delivered,
            "items": items,
        })
    packages.sort(key=lambda p: -p["severity_score"])
    with open(f"{out}/dispositions.json", "w") as f:
        json.dump({"queue": packages}, f, indent=1)
    with open(f"{out}/ncr_register.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ncr_rows[0].keys()))
        w.writeheader()
        w.writerows(ncr_rows)
    print(f"M6: {len(ncr_rows)} NCR(s) drafted -> {out}/ncr_register.csv")
    for p in packages:
        print(f"  {p['package']}: severity {p['severity_score']}, "
              f"{p['open_ncrs']} NCR(s), {p['needs_review']} review(s)")


if __name__ == "__main__":
    main()
