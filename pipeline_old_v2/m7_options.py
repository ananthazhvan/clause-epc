"""M7 - Decision Clock (expiring options engine).

Every open finding is an option that expires. This module derives, from the
project registers alone (no LLM, no manual input):

  1. A project calendar via CPM forward pass over schedule.csv
     (durations + predecessors -> early start/finish for every activity).
  2. The calendar anchor is DERIVED, not assumed: the generator procurement
     activity (ACT-ELE-GEN-01, 'Procure and Deliver') must have started on
     the generator PO order date in po_register.csv. project_start =
     po_order_date - early_start_offset(procure activity).
  3. Per package:
     - need-on-site  = late start of the first install activity
     - last safe rejection date = need-on-site - reorder lead time
     - if expired: schedule slip a rejection would now cost
     - commissioning gate = early start of the first critical
       commissioning activity; concession decisions must close
       APPROVAL_LEAD_DAYS before it. This is the live countdown.

Run: python3 m7_options.py   (writes out/options.json)
"""
import csv
import datetime
import glob
import json
import os

REG = "../clause_corpus/registers"
SECTION_KW = {"26 33 53": "ups", "26 32 13": "generator",
              "23 81 23": "crah", "21 22 00": "fire"}
# Labeled assumption (the only one): calendar days a concession package
# typically needs for client + consultant signatures.
APPROVAL_LEAD_DAYS = 30


def parse_preds(s):
    return [p.strip() for p in (s or "").replace(";", ",").split(",") if p.strip()]


def cpm(acts):
    """Forward pass -> early start (day offset from project start)."""
    idx = {a["activity_id"]: a for a in acts}
    es = {}

    def visit(aid, stack=()):
        if aid in es:
            return es[aid]
        if aid in stack:  # cycle guard
            return 0
        a = idx.get(aid)
        if a is None:
            return 0
        preds = parse_preds(a["predecessors"])
        v = 0
        for p in preds:
            pa = idx.get(p)
            if pa:
                v = max(v, visit(p, stack + (aid,)) + int(pa["duration_days"]))
        es[aid] = v
        return v

    for a in acts:
        visit(a["activity_id"])
    return es


def main(out="out", today=None):
    today = today or datetime.date.today()
    acts = list(csv.DictReader(open(f"{REG}/schedule.csv")))
    pos = list(csv.DictReader(open(f"{REG}/po_register.csv")))
    es = cpm(acts)

    # --- derive the calendar anchor -------------------------------------
    proc = next(a for a in acts if "procure" in a["name"].lower()
                and "generator" in a["name"].lower())
    gen_pos = [p for p in pos if p["spec_section"] == "26 32 13"]
    anchor_order = min(datetime.date.fromisoformat(p["order_date"]) for p in gen_pos)
    project_start = anchor_order - datetime.timedelta(days=es[proc["activity_id"]])
    d = lambda off: project_start + datetime.timedelta(days=off)

    # --- commissioning gate (first critical commissioning activity) -----
    com = sorted((a for a in acts if a["activity_id"].startswith("ACT-COM")
                  and a["critical_path"] == "True"), key=lambda a: es[a["activity_id"]])
    gate_act = com[0] if com else None
    gate_date = d(es[gate_act["activity_id"]]) if gate_act else None

    disp = {}
    dp = os.path.join(out, "dispositions.json")
    if os.path.exists(dp):
        for q in json.load(open(dp))["queue"]:
            disp[q["package"]] = q

    cards = []
    for path in sorted(glob.glob(os.path.join(out, "post", "verdicts_*.json"))):
        v = json.load(open(path))
        pkg, sec = v["package"], v["section"]
        kw = SECTION_KW.get(sec)
        if not kw:
            continue
        installs = [a for a in acts if kw in a["name"].lower()
                    and "procure" not in a["name"].lower()]
        if not installs:
            continue
        first = min(installs, key=lambda a: es[a["activity_id"]])
        flo = int(first["float_days"])
        need_on_site = d(es[first["activity_id"]] + flo)  # late start
        sec_pos = [p for p in pos if p["spec_section"] == sec]
        lead_days = max((int(p["lead_time_weeks"]) for p in sec_pos), default=0) * 7
        value_inr = sum(int(p["value_inr"]) for p in sec_pos)
        last_safe = need_on_site - datetime.timedelta(days=lead_days)
        ttl = (last_safe - today).days
        # if rejected today, new delivery lands today+lead; slip vs late start
        slip = max(0, ((today + datetime.timedelta(days=lead_days)) - need_on_site).days)
        decide_by = (gate_date - datetime.timedelta(days=APPROVAL_LEAD_DAYS)) if gate_date else None
        q = disp.get(pkg, {})
        cards.append({
            "package": pkg, "section": sec,
            "vendor": sec_pos[0]["vendor"] if sec_pos else None,
            "open_findings": q.get("open_ncrs", 0),
            "needs_review": q.get("needs_review", 0),
            "value_inr": value_inr,
            "lead_time_days": lead_days,
            "install_activity": first["activity_id"],
            "need_on_site": need_on_site.isoformat(),
            "last_safe_rejection_date": last_safe.isoformat(),
            "reject_ttl_days": ttl,
            "reject_status": "OPEN" if ttl > 14 else "CLOSING" if ttl > 0 else "EXPIRED",
            "slip_if_rejected_today_days": slip,
            "commissioning_gate": gate_date.isoformat() if gate_date else None,
            "gate_activity": gate_act["activity_id"] if gate_act else None,
            "decide_concessions_by": decide_by.isoformat() if decide_by else None,
            "days_to_decide": (decide_by - today).days if decide_by else None,
        })

    cards.sort(key=lambda c: (c["days_to_decide"] if c["days_to_decide"] is not None else 9999,
                              -c["value_inr"]))
    result = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "today": today.isoformat(),
        "derivation": {
            "anchor": f"{proc['activity_id']} ({proc['name']}) began on the "
                      f"generator PO order date {anchor_order.isoformat()} "
                      f"(po_register.csv); its CPM offset is day {es[proc['activity_id']]}",
            "project_start": project_start.isoformat(),
            "commissioning_gate": f"{gate_act['activity_id']} early start" if gate_act else None,
            "approval_lead_days_assumption": APPROVAL_LEAD_DAYS,
        },
        "packages": cards,
    }
    os.makedirs(out, exist_ok=True)
    json.dump(result, open(os.path.join(out, "options.json"), "w"), indent=1)
    print(f"M7: decision clock for {len(cards)} packages -> out/options.json "
          f"(project start {project_start}, gate {gate_date})")


if __name__ == "__main__":
    main()
