#!/usr/bin/env python3
"""Generate realistic connector sample exports from the canonical corpus
registers, so the demo can show live P6/SAP/logistics ingestion WITHOUT
inventing project data: the samples are exact re-encodings of
clause_corpus/registers/*.csv in each vendor's wire format. Converting them
back through connectors/* reproduces the canonical registers (roundtrip
property - verified by --check).

Usage: python3 connectors/make_samples.py [--corpus ../clause_corpus] [--check]
"""
import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connectors import p6xml, sap_odata  # noqa: E402

START = date(2026, 1, 5)  # project mobilisation - matches the corpus timeline
H = 8  # hours per day

# crew assignment by activity family - display-only enrichment (P6 exports
# carry resource assignments; the canonical register has no resource column,
# so these ride along as an extra 'resources' column after conversion)
CREWS = [("CIV", "Civil Crew", 6), ("UPS", "Electrical Engineer", 4),
         ("GEN", "Mechanical Fitter", 4), ("SWGR", "Electrical Engineer", 3),
         ("CRAH", "HVAC Technician", 4), ("FIRE", "Fire-Protection Fitter", 3),
         ("ELEC", "Electrical Crew", 5), ("CX", "Commissioning Agent", 2)]


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def schedule_to_p6(rows):
    """Forward-pass planned dates from durations+logic, then emit P6 XML."""
    obj = {r["activity_id"]: 1000 + i for i, r in enumerate(rows)}
    es = {}
    dur = {r["activity_id"]: float(r["duration_days"]) for r in rows}
    preds = {r["activity_id"]: [p for p in r["predecessors"].split(";") if p] for r in rows}
    for r in rows:  # rows are already in dependency order in the corpus
        a = r["activity_id"]
        es[a] = max((es[p] + dur[p] for p in preds[a] if p in es), default=0.0)
    acts, rels, assigns = [], [], []
    res_ids = {}
    for name in {c[1] for c in CREWS}:
        res_ids[name] = 9000 + len(res_ids)
    rid = 5000
    for r in rows:
        a = r["activity_id"]
        s = START + timedelta(days=es[a])
        f = START + timedelta(days=es[a] + dur[a])
        acts.append(
            f"    <Activity>\n"
            f"      <Id>{escape(a)}</Id>\n"
            f"      <ObjectId>{obj[a]}</ObjectId>\n"
            f"      <Name>{escape(r['name'])}</Name>\n"
            f"      <PlannedDuration>{float(r['duration_days']) * H:g}</PlannedDuration>\n"
            f"      <PlannedStartDate>{s.isoformat()}T08:00:00</PlannedStartDate>\n"
            f"      <PlannedFinishDate>{f.isoformat()}T17:00:00</PlannedFinishDate>\n"
            f"      <TotalFloat>{float(r['float_days']) * H:g}</TotalFloat>\n"
            f"    </Activity>")
        for p in preds[a]:
            rels.append(
                f"    <Relationship>\n"
                f"      <ObjectId>{rid}</ObjectId>\n"
                f"      <PredecessorActivityObjectId>{obj[p]}</PredecessorActivityObjectId>\n"
                f"      <SuccessorActivityObjectId>{obj[a]}</SuccessorActivityObjectId>\n"
                f"      <Type>Finish to Start</Type>\n"
                f"      <Lag>0</Lag>\n"
                f"    </Relationship>")
            rid += 1
        for fam, crew, n in CREWS:
            if fam in a:
                for _ in range(n):
                    assigns.append(
                        f"    <ResourceAssignment>\n"
                        f"      <ObjectId>{rid}</ObjectId>\n"
                        f"      <ActivityObjectId>{obj[a]}</ActivityObjectId>\n"
                        f"      <ResourceObjectId>{res_ids[crew]}</ResourceObjectId>\n"
                        f"    </ResourceAssignment>")
                    rid += 1
                break
    resources = "\n".join(
        f"    <Resource>\n      <ObjectId>{i}</ObjectId>\n      <Name>{escape(n)}</Name>\n    </Resource>"
        for n, i in sorted(res_ids.items(), key=lambda kv: kv[1]))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<APIBusinessObjects xmlns="http://xmlns.oracle.com/Primavera/P6/V21.12/API/BusinessObjects">\n'
        "  <Project>\n"
        "    <Id>MERIDIAN-DC</Id>\n"
        "    <Name>Project Meridian - 12MW Data Centre, Chennai</Name>\n"
        + "\n".join(acts) + "\n" + "\n".join(rels) + "\n" + resources + "\n" + "\n".join(assigns) + "\n"
        "  </Project>\n"
        "</APIBusinessObjects>\n")


def _ms(d):
    dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return f"/Date({int(dt.timestamp() * 1000)})/"


def po_to_sap(rows):
    """po_register.csv -> OData v2 payload (API_PURCHASEORDER_PROCESS_SRV shape)."""
    results = []
    for r in rows:
        odate = date.fromisoformat(r["order_date"])
        ddate = odate + timedelta(weeks=int(r["lead_time_weeks"]))
        results.append({
            "__metadata": {"type": "API_PURCHASEORDER_PROCESS_SRV.A_PurchaseOrderType"},
            "PurchaseOrder": r["po_number"],
            "CompanyCode": "IN01",
            "Supplier": "V-" + str(abs(hash(r["vendor"])) % 100000).zfill(5),
            "SupplierName": r["vendor"],
            "DocumentCurrency": "INR",
            "CreationDate": _ms(odate),
            "to_PurchaseOrderItem": {"results": [{
                "PurchaseOrderItem": "00010",
                "Material": r["equipment_tag"],
                "PurchaseOrderItemText": r["item_description"],
                "OrderQuantity": "1",
                "NetPrice": r["value_inr"],
                "Currency": "INR",
                "ScheduleLineDeliveryDate": _ms(ddate),
                "YY1_SpecSection_PDH": r["spec_section"],
                "DeliveryStatus": r["delivery_status"],
            }]},
        })
    return {"d": {"results": results}}


def po_to_shipments(rows):
    """Visibility feed (FourKites/project44 style) for the in-transit POs.
    Statuses mirror the register - the sample must not rewrite project truth."""
    ships, n = [], 0
    for r in rows:
        n += 1
        odate = date.fromisoformat(r["order_date"])
        eta = odate + timedelta(weeks=int(r["lead_time_weeks"]))
        ships.append({
            "shipmentId": f"SH-VZ-{90000 + n}",
            "purchaseOrderNumber": r["po_number"],
            "equipmentType": "CONTAINER_40HC",
            "carrierName": "Vanguard Global Logistics",
            "currentStatus": r["delivery_status"],
            "lastUpdatedLocation": {"latitude": 13.0827, "longitude": 80.2707,
                                      "name": "Chennai Port" if r["delivery_status"] == "DELIVERED" else "Indian Ocean, en route Chennai",
                                      "timestamp": "2026-07-01T09:30:00Z"},
            "estimatedTimeOfArrival": eta.isoformat() + "T12:00:00Z",
        })
    return {"shipments": ships}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "clause_corpus"))
    ap.add_argument("--check", action="store_true", help="verify roundtrip equality")
    a = ap.parse_args()
    reg = os.path.join(a.corpus, "registers")
    outd = os.path.join(a.corpus, "connectors")
    os.makedirs(outd, exist_ok=True)
    sched = read_csv(os.path.join(reg, "schedule.csv"))
    pos = read_csv(os.path.join(reg, "po_register.csv"))

    xml_text = schedule_to_p6(sched)
    open(os.path.join(outd, "meridian_schedule_p6.xml"), "w").write(xml_text)
    json.dump(po_to_sap(pos), open(os.path.join(outd, "meridian_po_sap_odata.json"), "w"), indent=1)
    json.dump(po_to_shipments(pos), open(os.path.join(outd, "meridian_shipments_visibility.json"), "w"), indent=1)
    print(f"wrote 3 sample exports to {outd}")

    if a.check:
        text, note = p6xml.convert(xml_text.encode())
        got = list(csv.DictReader(text.splitlines()))
        assert len(got) == len(sched), "P6 roundtrip: row count mismatch"
        for g, w in zip(got, sched):
            for col in ("activity_id", "name", "duration_days", "predecessors", "float_days", "critical_path"):
                assert g[col] == w[col], f"P6 roundtrip mismatch {w['activity_id']}.{col}: {g[col]!r} != {w[col]!r}"
        print("P6 roundtrip OK -", note)
        text, note = sap_odata.convert(po_to_sap(pos))
        got = list(csv.DictReader(text.splitlines()))
        assert len(got) == len(pos), "SAP roundtrip: row count mismatch"
        for g, w in zip(got, pos):
            for col in ("po_number", "equipment_tag", "spec_section", "vendor", "item_description",
                        "value_inr", "order_date", "lead_time_weeks", "delivery_status"):
                assert g[col] == w[col], f"SAP roundtrip mismatch {w['po_number']}.{col}: {g[col]!r} != {w[col]!r}"
        print("SAP roundtrip OK -", note)


if __name__ == "__main__":
    main()
