#!/usr/bin/env python3
"""M15 - supply-chain risk and alerting.

Joins three sources that never meet in real projects: the PO register (what
was bought, when, with what lead time), the schedule (when each item is
actually needed on site, with how much float), and any live logistics fields
present on the register (current location / ETA from a visibility feed).

Deterministic core: forward-pass the schedule, compute projected arrival vs
need-by date per PO, classify LATE / AT_RISK / WATCH / ON_TRACK, and emit
alerts with the number of days left to act. Optional AI layer: an executive
brief written from the computed alerts (never the other way around).
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def tokens(s):
    return {t.rstrip("s") if len(t) > 3 else t
            for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) > 2}


def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.date.fromisoformat(s) if fmt == "%Y-%m-%d" else datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def forward_pass(acts):
    es = {a["activity_id"]: 0.0 for a in acts}
    dur = {a["activity_id"]: float(a.get("duration_days") or 0) for a in acts}
    preds = {a["activity_id"]: [p.strip() for p in (a.get("predecessors") or "").split(";") if p.strip()] for a in acts}
    for _ in range(len(acts) + 1):
        changed = False
        for aid in es:
            v = max((es[p] + dur[p] for p in preds[aid] if p in es), default=0.0)
            if v > es[aid]:
                es[aid] = v
                changed = True
        if not changed:
            break
    return es


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join("workspace", "corpus"))
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    reg = os.path.join(args.corpus, "registers")
    po_path = os.path.join(reg, "po_register.csv")
    sc_path = os.path.join(reg, "schedule.csv")
    if not (os.path.exists(po_path) and os.path.exists(sc_path)):
        sys.exit("po_register.csv / schedule.csv not found - nothing to analyse")
    pos = list(csv.DictReader(open(po_path)))
    acts = list(csv.DictReader(open(sc_path)))
    es = forward_pass(acts)
    act_tok = {a["activity_id"]: tokens(a.get("name")) for a in acts}
    act_by_id = {a["activity_id"]: a for a in acts}
    starts = [parse_date(p.get("order_date")) for p in pos]
    starts = [d for d in starts if d]
    if not starts:
        os.makedirs(args.out, exist_ok=True)
        json.dump({"items": [], "alerts": [],
                   "note": "po_register.csv has no parseable order_date - fill the "
                           "order_date column (YYYY-MM-DD) to enable supply-chain risk"},
                  open(os.path.join(args.out, "supply_risk.json"), "w"), indent=1)
        print("  S9: no parseable order_date in po_register.csv - wrote an empty "
              "supply_risk.json and moved on (fill order_date to enable this analysis)")
        return
    day0 = min(starts)

    def iso(day):
        return (day0 + datetime.timedelta(days=int(round(day)))).isoformat()

    po_by_act = {}
    for _aid, _a in act_by_id.items():
        _nm = _a.get("name") or ""
        for _m in re.finditer(r"(\d{10})((?:/\d{2})+)?", _nm):
            _base = _m.group(1)
            po_by_act.setdefault(_base, _aid)
            for _suf in re.findall(r"/(\d{2})", _m.group(2) or ""):
                po_by_act.setdefault(_base[:-2] + _suf, _aid)

    items, alerts, unlinked = [], [], []
    for p in pos:
        od = parse_date(p.get("order_date"))
        lead_days = float(p.get("lead_time_weeks") or 0) * 7
        ptok = tokens(p.get("equipment_tag", "")) | tokens(p.get("item_description", ""))
        fam = next((t for t in re.split(r"[^a-z]+", (p.get("equipment_tag") or "").lower()) if len(t) >= 2), None)
        podig = re.sub(r"\D", "", p.get("po_number") or "")[-10:]
        direct = po_by_act.get(podig)
        best, score = None, 0
        for aid, at in act_tok.items():
            sc = len(ptok & at)
            aname = (act_by_id[aid].get("name") or "").lower()
            idtok = {t.rstrip("s") for t in re.split(r"[^a-z]+", aid.lower()) if t}
            if fam and (fam in idtok or fam in at):
                sc += 2
                if "procure" in aname or "deliver" in aname:
                    sc += 3
                elif "install" in aname or "mount" in aname:
                    sc += 1
            if sc > score:
                best, score = aid, sc
        matched = direct or (best if score >= 2 else None)
        eta = parse_date(p.get("eta") or p.get("current_eta") or "")
        arrival = (eta - day0).days if eta else ((od - day0).days + lead_days if od else None)
        rec = {
            "po": p.get("po_number"), "item": p.get("item_description"),
            "vendor": p.get("vendor"), "spec_section": p.get("spec_section"),
            "value_inr": p.get("value_inr"), "delivery_status": p.get("delivery_status"),
            "location": p.get("current_location") or None,
        }
        if matched is None or arrival is None:
            rec["status"] = "UNLINKED"
            unlinked.append(rec)
            continue
        a = act_by_id[matched]
        need = es[matched]
        margin = need - arrival
        flt = float(a.get("float_days") or 0)
        critical = (a.get("critical_path") or "").strip().lower() in ("yes", "true", "1", "y")
        status = ("RECEIVED" if (p.get("delivery_status") or "").upper() == "DELIVERED"
                  else "LATE" if margin < 0
                  else "AT_RISK" if margin < 14
                  else "WATCH" if margin < 35 else "ON_TRACK")
        rec.update({
            "activity": matched, "activity_name": a.get("name"),
            "needed_on_site": iso(need), "projected_arrival": iso(arrival),
            "margin_days": int(round(margin)), "float_days": int(flt),
            "critical_path": critical, "status": status,
        })
        items.append(rec)
        if status in ("LATE", "AT_RISK"):
            over = -margin if margin < 0 else 0
            alerts.append({
                "severity": "HIGH" if critical or over > flt else "MEDIUM",
                "po": rec["po"], "item": rec["item"], "vendor": rec["vendor"],
                "activity": matched, "activity_name": a.get("name"),
                "needed_on_site": rec["needed_on_site"],
                "projected_arrival": rec["projected_arrival"],
                "margin_days": rec["margin_days"],
                "days_to_act": max(0, int(round(margin + flt))),
                "schedule_float_absorbs": bool(margin < 0 and over <= flt),
            })
    alerts.sort(key=lambda x: x["margin_days"])
    counts = {}
    for r in items:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    doc = {
        "project_start": day0.isoformat(), "summary": counts,
        "items": sorted(items, key=lambda r: r["margin_days"]),
        "alerts": alerts, "unlinked": unlinked,
    }
    if alerts and not args.no_llm:
        try:
            from common import llm
            brief = llm.call(
                "You are a project supply-chain controller. Write a terse "
                "markdown brief (max 180 words) from the alert JSON you are "
                "given: lead with the single worst exposure, name POs and "
                "activities exactly as given, state days and dates plainly, "
                "end with the one action per HIGH alert. No preamble.",
                json.dumps(alerts[:12], indent=1))
            doc["brief_md"] = brief.strip()
        except Exception as e:
            print(f"brief skipped ({e})")
    with open(os.path.join(args.out, "supply_risk.json"), "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"supply risk: {len(items)} POs linked to schedule, "
          f"{len(alerts)} alerts ({counts.get('LATE', 0)} late, "
          f"{counts.get('AT_RISK', 0)} at risk), {len(unlinked)} unlinked")


if __name__ == "__main__":
    main()
