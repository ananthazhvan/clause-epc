#!/usr/bin/env python3
"""M16 - ontology compiler: every artifact and feed -> one object graph.

Every real-world thing becomes an object with typed links, money, and
insights: SpecSection, Addendum, Submittal, Vendor, PurchaseOrder, Shipment,
Activity, CxTest, QualityIssue. Deterministic; runs last so it can fold in
everything the run produced. Output: out/ontology.json
"""
import argparse
import csv
import glob
import json
import os
import re

SEC_RE = re.compile(r"\b(\d{2} \d{2} \d{2})\b")


def jload(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def read_csv(path):
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def find_file(corpus, names):
    for name in names:
        hits = glob.glob(os.path.join(corpus, "**", name), recursive=True)
        hits = [h for h in hits if "_answer_key" not in h]
        if hits:
            return hits[0]
    return None


def digits(s):
    return re.sub(r"\D", "", str(s or ""))


def num(x):
    try:
        return float(re.sub(r"[^0-9.]", "", str(x)) or 0)
    except Exception:
        return 0.0


class Onto:
    def __init__(self):
        self.objects = {}
        self.links = []

    def obj(self, oid, otype, name, **kw):
        o = self.objects.get(oid)
        if not o:
            o = {"id": oid, "type": otype, "name": name, "status": "",
                 "props": {}, "money": {"value_inr": 0, "at_risk_inr": 0, "at_risk_why": []},
                 "insights": []}
            self.objects[oid] = o
        for k, v in kw.items():
            if k == "props":
                o["props"].update({k2: v2 for k2, v2 in v.items() if v2 not in (None, "")})
            elif v not in (None, ""):
                o[k] = v
        return o

    def link(self, s, t, rel):
        if s in self.objects and t in self.objects:
            key = (s, t, rel)
            if key not in {(l["s"], l["t"], l["rel"]) for l in self.links}:
                self.links.append({"s": s, "t": t, "rel": rel})

    def insight(self, oid, text, severity="info"):
        o = self.objects.get(oid)
        if o is not None and text and text not in [i["text"] for i in o["insights"]]:
            o["insights"].append({"severity": severity, "text": text})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    out, corpus = args.out, args.corpus
    O = Onto()

    # ---------------- spec sections + addenda (from parsed docs) ----------
    sections = set()
    for p in sorted(glob.glob(os.path.join(out, "spec_*.json"))):
        d = jload(p) or {}
        sec = d.get("section")
        if not sec:
            continue
        sections.add(sec)
        O.obj(f"section:{sec}", "section", f"Spec {sec}",
              props={"clauses": len(d.get("clauses") or []),
                     "source": d.get("source_pdf"), "parse_mode": d.get("parse_mode")})
    addenda = {}
    for p in sorted(glob.glob(os.path.join(out, "doc_*.json"))):
        d = jload(p) or {}
        name = os.path.basename(p)[4:-5]
        text0 = " ".join(pg.get("text", "") for pg in (d.get("pages") or [])[:2])
        if d.get("transmittal"):
            continue
        if name.upper().startswith("ADD") or "addendum no" in text0.lower():
            secs = sorted(set(SEC_RE.findall(text0)) & sections)
            addenda[name] = secs
            O.obj(f"add:{name}", "addendum", name, status="AMENDS",
                  props={"amends_sections": ", ".join(secs)})
            for s in secs:
                O.link(f"add:{name}", f"section:{s}", "amends")

    # ---------------- submittals (verdicts are the relationship) ----------
    sub_by_base = {}
    for p in sorted(glob.glob(os.path.join(out, "verdicts_*.json"))):
        pkg = os.path.basename(p)[9:-5]
        v = jload(p) or {}
        doc = jload(os.path.join(out, f"doc_{pkg}.json")) or {}
        tm = doc.get("transmittal") or {}
        sec = tm.get("reference_section") or (SEC_RE.findall(pkg.replace("-", " ")) or [""])[0]
        summ = v.get("summary") or {}
        dev, rev = summ.get("DEVIATION", 0), summ.get("NEEDS_REVIEW", 0)
        comp = summ.get("COMPLY", 0)
        status = ("DEVIATION" if dev else "NEEDS_REVIEW" if rev
                  else "COMPLY" if comp else "UNVERIFIED")
        O.obj(f"package:{pkg}", "package", pkg, status=status,
              props={"revision": tm.get("revision"), "date": tm.get("date"),
                     "reviewed_spec_revision": tm.get("reviewed_spec_revision"),
                     "section": sec, "verdicts": ", ".join(f"{k} {n}" for k, n in summ.items())})
        if sec:
            O.obj(f"section:{sec}", "section", f"Spec {sec}")
            rel = {"DEVIATION": "deviates_from", "COMPLY": "complies_with"}.get(status, "under_review_for")
            O.link(f"package:{pkg}", f"section:{sec}", rel)
        base = re.sub(r"-R\d+$", "", pkg)
        sub_by_base.setdefault(base, []).append((tm.get("revision") or "R0", pkg, sec, status))
        for aname, secs in addenda.items():
            if sec in secs and "addend" not in str(tm.get("reviewed_spec_revision", "")).lower():
                O.insight(f"package:{pkg}",
                          f"Reviewed against a superseded spec revision: {aname} amends "
                          f"section {sec} but the transmittal does not acknowledge it.", "warn")
                O.link(f"add:{aname}", f"package:{pkg}", "invalidates_review_of")
    for base, revs in sub_by_base.items():
        if len(revs) > 1:
            revs.sort()
            for _, pkg, _, _ in revs[:-1]:
                O.objects[f"package:{pkg}"]["status"] = "SUPERSEDED"
                O.link(f"package:{revs[-1][1]}", f"package:{pkg}", "supersedes")

    # ---------------- procurement: POs + vendors --------------------------
    po_csv = find_file(corpus, ["po_register.csv"])
    po_by_digits = {}
    vendors_json = jload(os.path.join(out, "vendors.json")) or {}
    for r in read_csv(po_csv) if po_csv else []:
        po = (r.get("po_number") or "").strip()
        if not po:
            continue
        vend = (r.get("vendor") or "").strip()
        sec = (r.get("spec_section") or "").strip()
        val = num(r.get("value_inr"))
        oid = f"po:{po}"
        po_by_digits[digits(po)] = oid
        O.obj(oid, "po", f"{po} \u00b7 {r.get('item_description') or r.get('equipment_tag') or ''}".strip(),
              status=(r.get("delivery_status") or "").strip(),
              props={"equipment_tag": r.get("equipment_tag"), "spec_section": sec,
                     "vendor": vend, "order_date": r.get("order_date"),
                     "lead_time_weeks": r.get("lead_time_weeks"),
                     "delivery_status": r.get("delivery_status"),
                     "eta": r.get("eta") or r.get("current_eta"),
                     "last_location": r.get("last_location") or r.get("location")})
        O.objects[oid]["money"]["value_inr"] = val
        if vend:
            vid = f"vendor:{vend}"
            O.obj(vid, "vendor", vend)
            O.link(vid, oid, "supplies")
        if sec:
            O.obj(f"section:{sec}", "section", f"Spec {sec}")
            O.link(oid, f"section:{sec}", "procured_against")

    # ---------------- SAP OData feed (extra PO detail) ---------------------
    for p in glob.glob(os.path.join(corpus, "**", "*.json"), recursive=True):
        if "_answer_key" in p:
            continue
        d = jload(p)
        rows = (((d or {}).get("d") or {}).get("results")) if isinstance(d, dict) else None
        if not rows or not isinstance(rows, list) or not (rows[0] or {}).get("PurchaseOrder"):
            continue
        for po in rows:
            oid = po_by_digits.get(digits(po.get("PurchaseOrder")))
            items = po.get("to_PurchaseOrderItem") or []
            it = items[0] if items else {}
            if not oid:
                pid = f"PO-{po.get('PurchaseOrder')}"
                oid = f"po:{pid}"
                po_by_digits[digits(pid)] = oid
                O.obj(oid, "po", f"{pid} \u00b7 {it.get('PurchaseOrderItemText', '')}")
            O.obj(oid, "po", O.objects[oid]["name"], props={
                "sap_supplier": po.get("SupplierName"), "sap_document_date": po.get("DocumentDate"),
                "material": it.get("Material"), "order_qty": it.get("OrderQuantity"),
                "plant": it.get("Plant"), "wbs": it.get("WBSElement"),
                "contract_delivery_date": it.get("ScheduleLineDeliveryDate")})
            if not O.objects[oid]["money"]["value_inr"]:
                O.objects[oid]["money"]["value_inr"] = num(it.get("NetPriceAmount")) * max(num(it.get("OrderQuantity")) or 1, 1)
            vend = po.get("SupplierName")
            if vend:
                O.obj(f"vendor:{vend}", "vendor", vend)
                O.link(f"vendor:{vend}", oid, "supplies")

    # ---------------- shipments (FourKites/project44-style feeds) ----------
    for p in glob.glob(os.path.join(corpus, "**", "*.json"), recursive=True):
        if "_answer_key" in p:
            continue
        d = jload(p)
        ships = (d or {}).get("shipments") if isinstance(d, dict) else None
        if not ships or not isinstance(ships, list) or not (ships[0] or {}).get("loadNumber"):
            continue
        for sh in ships:
            sid = f"ship:{sh.get('loadNumber')}"
            pos = sh.get("positionUpdates") or []
            last = pos[-1] if pos else {}
            status = sh.get("status") or ""
            if sh.get("exceptionCode"):
                status = sh.get("exceptionCode")
            org, dst = sh.get("origin") or {}, sh.get("destination") or {}
            O.obj(sid, "shipment", f"{sh.get('loadNumber')} \u00b7 {(sh.get('referenceNumbers') or {}).get('equipmentTag', '')}",
                  status=status,
                  props={"mode": sh.get("mode"), "carrier": (sh.get("carrier") or {}).get("name"),
                         "vessel": (sh.get("carrier") or {}).get("vesselName"),
                         "origin": org.get("city"), "destination": dst.get("city"),
                         "scheduled_eta": sh.get("scheduledDeliveryDateTime"),
                         "current_eta": sh.get("estimatedDeliveryDateTime") or sh.get("actualDeliveryDateTime"),
                         "last_position": last.get("locationDescription"),
                         "last_seen": last.get("dateTime"),
                         "delay_reason": sh.get("delayReasonDescription") or sh.get("exceptionDescription")},
                  geo={"lat": last.get("latitude", org.get("latitude")),
                       "lon": last.get("longitude", org.get("longitude")),
                       "origin": [org.get("latitude"), org.get("longitude")],
                       "destination": [dst.get("latitude"), dst.get("longitude")],
                       "trail": [[u.get("latitude"), u.get("longitude")] for u in pos]})
            ref = po_by_digits.get(digits((sh.get("referenceNumbers") or {}).get("purchaseOrder")))
            if ref:
                O.link(sid, ref, "delivers")
                if any(k in status.upper() for k in ("DELAY", "HOLD", "EXCEPTION")):
                    O.insight(ref, f"Shipment {sh.get('loadNumber')} is {status}: "
                                   f"{sh.get('delayReasonDescription') or sh.get('exceptionDescription') or ''}", "bad")

    # ---------------- schedule activities ---------------------------------
    sch_csv = find_file(corpus, ["schedule.csv"])
    for r in read_csv(sch_csv) if sch_csv else []:
        aid = (r.get("activity_id") or "").strip()
        if not aid:
            continue
        crit = str(r.get("critical_path", "")).strip().lower() in ("true", "1", "yes", "y")
        O.obj(f"act:{aid}", "activity", f"{aid} \u00b7 {r.get('name', '')}",
              status="CRITICAL" if crit else "",
              props={"duration_days": r.get("duration_days"), "float_days": r.get("float_days"),
                     "critical_path": str(crit).lower()})
    for r in read_csv(sch_csv) if sch_csv else []:
        aid = (r.get("activity_id") or "").strip()
        if not aid:
            continue
        for pred in re.split(r"[;,]", r.get("predecessors") or ""):
            pred = pred.strip()
            if pred and f"act:{pred}" in O.objects:
                O.link(f"act:{aid}", f"act:{pred}", "depends_on")

    # ---------------- supply risk (M15) ------------------------------------
    sup = jload(os.path.join(out, "supply_risk.json")) or {}
    for it in (sup.get("items") or []):
        oid = po_by_digits.get(digits(it.get("po_number") or it.get("po")))
        act = it.get("activity_id") or it.get("activity")
        st = (str(it.get("status") or "")).upper()
        if oid:
            O.obj(oid, "po", O.objects[oid]["name"], props={
                "supply_status": st, "days_to_act": it.get("days_to_act"),
                "need_date": it.get("need_date") or it.get("required_by")})
            if act and f"act:{act}" in O.objects:
                O.link(oid, f"act:{act}", "feeds")
            if st in ("LATE", "AT_RISK"):
                O.insight(oid, str(it.get("note") or f"Supply status {st} against the schedule."),
                          "bad" if st == "LATE" else "warn")

    # ---------------- cx tests --------------------------------------------
    cx_csv = find_file(corpus, ["cx_test_register.csv", "cx_register.csv"])
    for r in read_csv(cx_csv) if cx_csv else []:
        tid = (r.get("test_id") or "").strip()
        if not tid:
            continue
        O.obj(f"cx:{tid}", "cx", f"{tid} \u00b7 {r.get('system', '')}",
              status=(r.get("status") or "").strip(),
              props={"level": r.get("level"), "spec_clause": r.get("spec_clause"),
                     "acceptance_criteria": r.get("acceptance_criteria")})
        msec = SEC_RE.search(r.get("spec_clause") or "")
        if msec and f"section:{msec.group(1)}" in O.objects:
            O.link(f"cx:{tid}", f"section:{msec.group(1)}", "verifies")

    # ---------------- RFIs (requests for information) ----------------------
    rfi_csv = find_file(corpus, ["rfi_register.csv"])
    for r in read_csv(rfi_csv) if rfi_csv else []:
        rid = (r.get("rfi_id") or "").strip()
        if not rid:
            continue
        status = (r.get("status") or "").strip().upper()
        O.obj(f"rfi:{rid}", "rfi", f"{rid} \u00b7 {str(r.get('question', ''))[:70]}",
              status=status,
              props={"section": r.get("section"), "clause": r.get("clause"),
                     "question": r.get("question"), "answer": r.get("answer"),
                     "raised_by": r.get("raised_by")})
        sec = (r.get("section") or "").strip()
        if sec and f"section:{sec}" in O.objects:
            O.link(f"rfi:{rid}", f"section:{sec}", "questions")
            if status == "OPEN":
                O.insight(f"section:{sec}",
                          f"Open {rid}: {str(r.get('question', ''))[:100]}", "warn")
        pkg = (r.get("linked_package") or "").strip()
        if pkg and f"package:{pkg}" in O.objects:
            O.link(f"rfi:{rid}", f"package:{pkg}", "affects")
        if status == "OPEN":
            O.insight(f"rfi:{rid}",
                      "Unanswered - this requirement is ambiguous until the client responds.", "warn")

    # ---------------- quality issues (ACC-style feed) ----------------------
    for p in glob.glob(os.path.join(corpus, "**", "*.json"), recursive=True):
        if "_answer_key" in p:
            continue
        d = jload(p)
        rows = (d or {}).get("results") if isinstance(d, dict) else None
        if not rows or not isinstance(rows, list) or not (rows[0] or {}).get("displayId"):
            continue
        for q in rows:
            qid = f"qi:{q.get('displayId')}"
            attrs = {a.get("name"): a.get("value") for a in (q.get("customAttributes") or [])}
            O.obj(qid, "quality", f"{q.get('displayId')} \u00b7 {str(q.get('title', ''))[:70]}",
                  status=(q.get("status") or "").upper(),
                  props={"subtype": q.get("issueSubtypeName"), "location": q.get("locationDetails"),
                         "assigned_to": q.get("assignedToName"), "due": q.get("dueDate"),
                         "description": str(q.get("description") or "")[:220]})
            sec = attrs.get("Spec Section")
            if sec and f"section:{sec}" in O.objects:
                O.link(qid, f"section:{sec}", "raised_against")
            oid = po_by_digits.get(digits(attrs.get("Related PO")))
            if oid:
                O.link(qid, oid, "implicates")
                if (q.get("status") or "").lower() == "open":
                    O.insight(oid, f"Open quality issue {q.get('displayId')}: {str(q.get('title', ''))[:90]}", "warn")
            act = attrs.get("Activity")
            if act and f"act:{act}" in O.objects:
                O.link(qid, f"act:{act}", "blocks")
            cxr = attrs.get("Cx Test")
            if cxr and f"cx:{cxr}" in O.objects:
                O.link(qid, f"cx:{cxr}", "blocks")

    # ---------------- money at risk + vendor rollups -----------------------
    adj = {}
    for l in O.links:
        adj.setdefault(l["s"], []).append(l["t"])
        adj.setdefault(l["t"], []).append(l["s"])
    for oid, o in O.objects.items():
        if o["type"] != "po":
            continue
        why = []
        sec = o["props"].get("spec_section")
        if sec:
            for po2 in O.objects.values():
                if po2["type"] == "package" and po2["props"].get("section") == sec \
                        and po2["status"] == "DEVIATION":
                    why.append(f"linked submittal {po2['name']} deviates from spec {sec}")
        for nb in adj.get(oid, []):
            n = O.objects[nb]
            if n["type"] == "shipment" and any(k in n["status"].upper() for k in ("DELAY", "HOLD", "EXCEPTION")):
                why.append(f"shipment {n['name'].split(' ')[0]} is {n['status']}")
            if n["type"] == "quality" and n["status"] == "OPEN":
                why.append(f"open quality issue {n['name'].split(' ')[0]}")
        if (o["props"].get("supply_status") or "").upper() in ("LATE", "AT_RISK"):
            why.append(f"supply status {o['props']['supply_status']}")
        if why:
            o["money"]["at_risk_inr"] = o["money"]["value_inr"]
            o["money"]["at_risk_why"] = sorted(set(why))
    vtrust = vendors_json.get("vendors") if isinstance(vendors_json, dict) else None
    for oid, o in O.objects.items():
        if o["type"] != "vendor":
            continue
        pos = [O.objects[nb] for nb in adj.get(oid, []) if O.objects[nb]["type"] == "po"]
        o["money"]["value_inr"] = sum(p["money"]["value_inr"] for p in pos)
        o["money"]["at_risk_inr"] = sum(p["money"]["at_risk_inr"] for p in pos)
        secs = {p["props"].get("spec_section") for p in pos} - {None, ""}
        subs = [s for s in O.objects.values()
                if s["type"] == "package" and s["props"].get("section") in secs and s["status"] != "SUPERSEDED"]
        dev = sum(1 for s in subs if s["status"] == "DEVIATION")
        comp = sum(1 for s in subs if s["status"] == "COMPLY")
        o["props"].update({"po_count": len(pos), "submittals": len(subs),
                           "deviating_submittals": dev, "complying_submittals": comp,
                           "compliance_rate": (f"{comp}/{comp + dev}" if comp + dev else "n/a")})
        if isinstance(vtrust, list):
            for vt in vtrust:
                if str(vt.get("vendor", "")).lower() == o["name"].lower():
                    o["props"]["trust_notes"] = vt.get("note") or vt.get("trust") or ""
        if dev:
            o["status"] = "DEVIATION"
            O.insight(oid, f"{dev} live submittal(s) from this vendor deviate from spec; "
                           f"\u20b9{o['money']['at_risk_inr']:,.0f} of their supply is exposed.", "bad")
        for nb in adj.get(oid, []):
            for nb2 in adj.get(nb, []):
                n2 = O.objects[nb2]
                if n2["type"] == "shipment":
                    O.link(oid, nb2, "moves")

    # ---------------- addendum blast over live objects ---------------------
    for aname, secs in addenda.items():
        hit, val = set(), 0.0
        for s in secs:
            for oid, o in O.objects.items():
                if o["type"] == "package" and o["props"].get("section") == s and o["status"] != "SUPERSEDED":
                    hit.add(oid)
                if o["type"] == "po" and o["props"].get("spec_section") == s:
                    hit.add(oid)
                    val += o["money"]["value_inr"]
                    for nb in adj.get(oid, []):
                        n = O.objects[nb]
                        if n["type"] in ("shipment", "activity"):
                            hit.add(nb)
                            if n["type"] == "shipment" and "DELIVERED" not in n["status"].upper():
                                O.insight(nb, f"Cargo affected by {aname}: the spec it was built "
                                              f"against changed while this shipment is in motion.", "warn")
                                O.link(f"add:{aname}", nb, "affects_in_transit")
                if o["type"] == "cx" and s in str(o["props"].get("spec_clause", "")):
                    hit.add(oid)
        a = O.objects.get(f"add:{aname}")
        if a:
            a["props"]["objects_affected"] = len(hit)
            a["money"]["value_inr"] = val
            O.insight(f"add:{aname}", f"{aname} touches {len(hit)} live objects and "
                                      f"\u20b9{val:,.0f} of procurement.", "warn")

    # ---------------- fold in M14 entity-verified findings -----------------
    intel = jload(os.path.join(out, "intel.json")) or {}
    for f in (intel.get("findings") or []):
        ents = f.get("entities") or []
        sev = "bad" if str(f.get("severity", "")).upper() in ("HIGH", "CRITICAL") else "warn"
        txt = f"{f.get('title', '')}: {f.get('narrative', '')}"[:300]
        for oid, o in O.objects.items():
            short = oid.split(":", 1)[1]
            if any(str(e) and (str(e) in o["name"] or str(e) == short) for e in ents):
                O.insight(oid, txt, sev)

    # ---------------- certification readiness (evidence, not keywords) -----
    cxs = [o for o in O.objects.values() if o["type"] == "cx"]
    open_dev = [o for o in O.objects.values() if o["type"] == "package" and o["status"] == "DEVIATION"]
    open_qi = [o for o in O.objects.values() if o["type"] == "quality" and o["status"] == "OPEN"]
    reqs = []
    for label, prefixes in (("Component verification (L1-L3)", ("L1", "L2", "L3")),
                            ("Level 4 system tests witnessed", ("L4",)),
                            ("Level 5 integrated systems test", ("L5",))):
        sub = [c for c in cxs if str(c["props"].get("level", "")).upper().startswith(tuple(prefixes))]
        done = sum(1 for c in sub if c["status"].upper() in ("PASSED", "COMPLETE", "DONE", "READY"))
        fail = sum(1 for c in sub if c["status"].upper() == "FAILED")
        reqs.append({"requirement": label,
                     "status": "gap" if fail else ("proven" if sub and done == len(sub) else "in_progress"),
                     "evidence": f"{done}/{len(sub)} tests closed" + (f", {fail} failed" if fail else "")})
    reqs.append({"requirement": "No live spec deviations on installed equipment",
                 "status": "gap" if open_dev else "proven",
                 "evidence": (", ".join(o["name"] for o in open_dev[:4]) or "all live submittals comply or are superseded")})
    reqs.append({"requirement": "No open quality nonconformances",
                 "status": "gap" if open_qi else "proven",
                 "evidence": (", ".join(o["name"].split(" \u00b7 ")[0] for o in open_qi[:5]) or "QMS clean")})
    cert = {"target": "Tier III / Tier IV certification readiness",
            "note": ("Readiness is computed from evidence objects - commissioning tests, live "
                     "submittal verdicts, and open quality issues - never from keyword matches."),
            "requirements": reqs}

    # ---------------- totals + write ---------------------------------------
    objs = list(O.objects.values())
    total_val = sum(o["money"]["value_inr"] for o in objs if o["type"] == "po")
    total_risk = sum(o["money"]["at_risk_inr"] for o in objs if o["type"] == "po")
    tcount = {}
    for o in objs:
        tcount[o["type"]] = tcount.get(o["type"], 0) + 1
    onto = {"project": {"name": os.path.basename(os.path.abspath(corpus)),
                        "totals": {"objects": len(objs), "links": len(O.links),
                                   "procurement_value_inr": total_val,
                                   "value_at_risk_inr": total_risk}},
            "types": [{"type": t, "count": c} for t, c in sorted(tcount.items())],
            "objects": objs, "links": O.links, "cert": cert}
    with open(os.path.join(out, "ontology.json"), "w") as f:
        json.dump(onto, f, indent=1)
    print(f"  ontology: {len(objs)} objects \u00b7 {len(O.links)} links \u00b7 "
          f"\u20b9{total_val:,.0f} mapped, \u20b9{total_risk:,.0f} at risk -> out/ontology.json")


if __name__ == "__main__":
    main()
