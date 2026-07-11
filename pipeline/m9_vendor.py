"""M9 - Vendor trust ledger.

Every verified verdict is also a data point about the vendor who stamped
the cover sheet. This module aggregates the AS-SUBMITTED (pre-addendum)
verdicts per vendor:

  - checks run, deviations, false 'Comply' stamps (stamped Comply,
    disproven by their own document), needs-review, missing evidence
  - a trust score: 100 - weighted penalty (false-comply weighs 3x a
    plain deviation - lying about compliance is worse than deviating)
  - rupee exposure from po_register.csv
  - revision trend where a resubmittal exists (R0 -> R1)
  - a recommended review intensity for the vendor's next submittal

Run: python3 m9_vendor.py   (writes out/vendors.json)
"""
import csv
import datetime
import glob
import json
import os
import re

REG = "../clause_corpus/registers"


def main(out="out"):
    pos = list(csv.DictReader(open(f"{REG}/po_register.csv")))
    sec_vendor = {p["spec_section"]: p["vendor"] for p in pos}

    vendors = {}
    packages = []
    for path in sorted(glob.glob(os.path.join(out, "verdicts_*.json"))):
        v = json.load(open(path))
        pkg, sec = v["package"], v["section"]
        vendor = sec_vendor.get(sec, "Unknown")
        checks = [r for r in v["results"] if r["verdict"] != "NOT_ADDRESSED"]
        dev = sum(r["verdict"] == "DEVIATION" for r in checks)
        fc = sum("false_comply" in r["flags"] for r in checks)
        nr = sum(r["verdict"] == "NEEDS_REVIEW" for r in checks)
        mev = sum(r["verdict"] == "MISSING_EVIDENCE" for r in checks)
        rev = re.search(r"-R(\d+)$", pkg)
        packages.append({"package": pkg, "section": sec, "vendor": vendor,
                         "revision": int(rev.group(1)) if rev else 0,
                         "checks": len(checks), "deviations": dev,
                         "false_comply": fc, "needs_review": nr,
                         "missing_evidence": mev})
        agg = vendors.setdefault(vendor, {
            "vendor": vendor, "sections": set(), "packages": [],
            "checks": 0, "deviations": 0, "false_comply": 0,
            "needs_review": 0, "missing_evidence": 0, "exposure_inr": 0})
        agg["sections"].add(sec)
        agg["packages"].append(pkg)
        agg["checks"] += len(checks)
        agg["deviations"] += dev
        agg["false_comply"] += fc
        agg["needs_review"] += nr
        agg["missing_evidence"] += mev

    for p in pos:
        if p["vendor"] in vendors:
            vendors[p["vendor"]]["exposure_inr"] += int(p["value_inr"])

    rows = []
    for agg in vendors.values():
        c = max(1, agg["checks"])
        penalty = (3 * agg["false_comply"] + agg["deviations"]
                   + 0.25 * agg["missing_evidence"]) / (3 * c)
        score = round(max(0, 100 * (1 - penalty)))
        agg["sections"] = sorted(agg["sections"])
        agg["trust_score"] = score
        agg["false_comply_rate_pct"] = round(100 * agg["false_comply"] / c, 1)
        agg["deviation_rate_pct"] = round(100 * agg["deviations"] / c, 1)
        agg["review_intensity"] = ("FULL_VERIFICATION" if score < 70 else
                                   "TARGETED_SAMPLING" if score < 90 else
                                   "STANDARD")
        rows.append(agg)

    # revision trend (R0 -> R1 on the same submittal series)
    trends = []
    series = {}
    for p in packages:
        series.setdefault(p["package"].rsplit("-R", 1)[0], []).append(p)
    for base, revs in series.items():
        if len(revs) > 1:
            revs.sort(key=lambda p: p["revision"])
            a, b = revs[0], revs[-1]
            trends.append({
                "series": base, "vendor": a["vendor"],
                "from": a["package"], "to": b["package"],
                "deviations": [a["deviations"], b["deviations"]],
                "false_comply": [a["false_comply"], b["false_comply"]],
            })

    result = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "method": "aggregated from as-submitted (pre-addendum) verdicts; "
                  "trust = 100 - 100*(3*false_comply + deviations + "
                  "0.25*missing_evidence)/(3*checks)",
        "vendors": sorted(rows, key=lambda r: r["trust_score"]),
        "packages": packages,
        "revision_trends": trends,
    }
    os.makedirs(out, exist_ok=True)
    json.dump(result, open(os.path.join(out, "vendors.json"), "w"), indent=1)
    print(f"M9: {len(rows)} vendors scored -> out/vendors.json")


if __name__ == "__main__":
    main()
