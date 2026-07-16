"""M8 - Margin erosion ledger (stack-up analysis).

A single accepted deviation looks harmless. Accepted together, they stack.
This module reads the post-addendum verdicts and computes, deterministically:

  1. A margin for every numeric rule with governing numeric evidence:
     signed % distance between what the contract demands and what the
     vendor actually offers (oriented so negative = worse than spec).
  2. Thin margins: rules that PASS but with < 2% headroom - the ones a
     hot day or a manufacturing tolerance will eat.
  3. Per-package concession stack: if every open deviation were accepted
     as-is, the compound performance giveaway vs contract.
  4. UPS efficiency money: extra losses (kW) implied by accepting the
     measured efficiency instead of the spec value, computed from the
     module ratings in po_register.csv. The frontend multiplies by a
     user-controlled tariff, so the rupee figure is live, not baked.

Run: python3 m8_margin.py   (writes out/margins.json)
"""
import csv
import datetime
import glob
import json
import os
import re

REG = os.path.join(os.environ.get("CLAUSE_CORPUS", "../clause_corpus"), "registers")


def signed_margin(op, req, claim):
    if not isinstance(req, (int, float)) or not isinstance(claim, (int, float)) or req == 0:
        return None
    if op in (">=", ">"):
        return (claim - req) / abs(req)
    if op in ("<=", "<"):
        return (req - claim) / abs(req)
    if op == "==":
        return -abs(claim - req) / abs(req)
    return None


def main(out="out"):
    ledger = []
    for path in sorted(glob.glob(os.path.join(out, "post", "verdicts_*.json"))):
        v = json.load(open(path))
        for r in v["results"]:
            req, gov = r["requirement"], r.get("governing_claim") or {}
            m = signed_margin(req.get("operator"), req.get("value"), gov.get("value"))
            if m is None:
                continue
            ledger.append({
                "package": v["package"], "section": v["section"],
                "rule_id": r["rule_id"], "parameter": r["parameter"],
                "operator": req["operator"], "required": req["value"],
                "offered": gov["value"], "unit": req.get("unit"),
                "margin_pct": round(m * 100, 2),
                "verdict": r["verdict"],
                "source_clause": req.get("source_clause"),
                "spec_page": req.get("page"), "evidence_page": gov.get("page"),
                "amended_by": req.get("amended_by"),
            })

    thin = sorted([e for e in ledger if 0 <= e["margin_pct"] < 2.0],
                  key=lambda e: e["margin_pct"])
    negative = sorted([e for e in ledger if e["margin_pct"] < 0],
                      key=lambda e: e["margin_pct"])

    # --- per-package concession stack -----------------------------------
    stacks = {}
    for e in negative:
        s = stacks.setdefault(e["package"], {"package": e["package"],
                                              "section": e["section"],
                                              "items": [], "compound_factor": 1.0})
        s["items"].append(e)
        s["compound_factor"] *= (1 + e["margin_pct"] / 100)
    for s in stacks.values():
        s["compound_erosion_pct"] = round((1 - s["compound_factor"]) * 100, 2)
        del s["compound_factor"]

    # --- UPS efficiency -> energy loss (money screen, tariff applied in UI)
    pos = list(csv.DictReader(open(f"{REG}/po_register.csv")))
    ups_pos = [p for p in pos if p["spec_section"] == "26 33 53"
               and "ups" in p["item_description"].lower()]
    fleet_kw = 0
    for p in ups_pos:
        mm = re.search(r"(\d+)\s*kW", p["item_description"])
        if mm:
            fleet_kw += int(mm.group(1))
    energy = []
    for e in negative:
        if "efficiency" not in e["parameter"] or e["unit"] != "%":
            continue
        load_frac = 1.0 if "100" in e["parameter"] else 0.75 if "75" in e["parameter"] else 0.5
        req_eff, off_eff = e["required"] / 100, e["offered"] / 100
        if off_eff <= 0:
            continue
        loss_kw = fleet_kw * load_frac * (1 / off_eff - 1 / req_eff)
        energy.append({
            "rule_id": e["rule_id"], "package": e["package"],
            "parameter": e["parameter"], "load_point": f"{int(load_frac*100)}%",
            "required_eff_pct": e["required"], "offered_eff_pct": e["offered"],
            "fleet_kw": fleet_kw, "extra_loss_kw": round(loss_kw, 1),
            "extra_kwh_per_year": round(loss_kw * 8760),
        })

    result = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "checked_rules": len(ledger),
        "ledger": sorted(ledger, key=lambda e: e["margin_pct"]),
        "thin_margins": thin,
        "negative_margins": negative,
        "concession_stacks": sorted(stacks.values(),
                                    key=lambda s: -s["compound_erosion_pct"]),
        "energy_penalty": {
            "note": "extra UPS losses if measured efficiency is accepted in "
                    "place of the spec value; fleet kW parsed from "
                    "po_register.csv item descriptions; rupee cost = "
                    "extra_kwh_per_year x tariff chosen in the UI",
            "assumptions": {"hours_per_year": 8760,
                            "load_profile": "continuous at stated load point"},
            "rows": energy,
        },
    }
    os.makedirs(out, exist_ok=True)
    json.dump(result, open(os.path.join(out, "margins.json"), "w"), indent=1)
    print(f"M8: {len(ledger)} numeric margins ({len(thin)} thin, "
          f"{len(negative)} negative) -> out/margins.json")


if __name__ == "__main__":
    main()
