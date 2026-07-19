"""SAP S/4HANA OData connector: purchase-order JSON -> canonical po_register.csv.

SAP's API_PURCHASEORDER_PROCESS_SRV OData service is the standard way EPC
procurement data leaves SAP. This adapter accepts the common payload shapes:
  - OData v2: {"d": {"results": [ ...PO objects... ]}} (or a single PO under "d")
  - OData v4: {"value": [ ...PO objects... ]}
  - a bare list of PO objects
Line items may sit under to_PurchaseOrderItem.results / to_PurchaseOrderItem /
Items / items. Dates may be OData /Date(ms)/ or ISO strings.

spec_section comes from a custom field (SAP convention: YY1_* in-app extension
fields, e.g. YY1_SpecSection_PDH) or any key matching *spec*section*. Rows
without one are staged with the column empty and counted in the note - CLAUSE
never guesses a spec section. Deterministic, zero LLM.
"""
import csv
import io
import re
from datetime import datetime, timezone

COLS = ["po_number", "equipment_tag", "spec_section", "vendor", "item_description",
        "value_inr", "order_date", "lead_time_weeks", "delivery_status"]

_SPEC_KEY = re.compile(r"spec.?section", re.I)
_MS_DATE = re.compile(r"/Date\((-?\d+)\)/")


def _po_list(obj):
    if isinstance(obj, dict):
        d = obj.get("d")
        if isinstance(d, dict):
            if isinstance(d.get("results"), list):
                obj = d["results"]
            elif d.get("PurchaseOrder"):
                obj = [d]
        elif isinstance(d, list):
            obj = d
        elif isinstance(obj.get("value"), list):
            obj = obj["value"]
        elif obj.get("PurchaseOrder"):
            obj = [obj]
    if not isinstance(obj, list):
        return []
    out = []
    for p in obj:
        if not isinstance(p, dict):
            continue
        if p.get("PurchaseOrder"):
            out.append(p)
        elif p.get("EBELN"):  # raw EKKO/EKPO field names from a table-level extract
            out.append({
                "PurchaseOrder": p.get("EBELN"),
                "Supplier": str(p.get("LIFNR") or ""),
                "CreationDate": p.get("BEDAT") or p.get("AEDAT"),
                "DocumentCurrency": p.get("WAERS"),
                "to_PurchaseOrderItem": [{
                    "Material": p.get("MATNR"),
                    "OrderQuantity": p.get("MENGE"),
                    "NetPrice": p.get("NETPR"),
                    "PurchaseOrderItemText": p.get("TXZ01"),
                    "ScheduleLineDeliveryDate": p.get("EINDT"),
                    "DeliveryStatus": p.get("STATUS"),
                }],
            })
    return out


def sniff(obj):
    return bool(_po_list(obj))


def _date(v):
    """OData /Date(ms)/ or ISO string -> date object (or None)."""
    if not v:
        return None
    m = _MS_DATE.search(str(v))
    if m:
        return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).date()
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _items(po):
    for key in ("to_PurchaseOrderItem", "Items", "items", "to_PurchaseOrderItemTP"):
        v = po.get(key)
        if isinstance(v, dict) and isinstance(v.get("results"), list):
            return v["results"]
        if isinstance(v, list):
            return v
    return [{}]  # header-only payload -> one row from header fields


def _spec_section(*dicts):
    for d in dicts:
        for k, v in d.items():
            if _SPEC_KEY.search(k) and isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def convert(obj):
    """SAP OData payload -> (canonical po_register.csv text, honest note)."""
    pos = _po_list(obj)
    if not pos:
        raise ValueError("no PurchaseOrder objects found in payload")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLS)
    rows, missing_spec, foreign_ccy = 0, 0, set()
    for po in pos:
        vendor = po.get("SupplierName") or po.get("Supplier") or ""
        odate = _date(po.get("CreationDate") or po.get("PurchaseOrderDate"))
        for it in _items(po):
            spec = _spec_section(it, po)
            if not spec:
                missing_spec += 1
            qty = _num(it.get("OrderQuantity"))
            qty = 1 if qty is None else qty
            price = _num(it.get("NetPrice") or it.get("NetPriceAmount"))
            value = round(qty * price) if price is not None else ""
            ccy = (it.get("Currency") or it.get("DocumentCurrency")
                   or po.get("DocumentCurrency") or "INR").upper()
            if ccy != "INR":
                foreign_ccy.add(ccy)
            ddate = _date(it.get("ScheduleLineDeliveryDate") or it.get("DeliveryDate"))
            lead = ""
            if odate and ddate:
                lead = max((ddate - odate).days, 0) // 7
            status = (it.get("DeliveryStatus") or po.get("DeliveryStatus")
                      or po.get("PurchasingProcessingStatusName") or "ORDERED")
            w.writerow([po.get("PurchaseOrder", ""),
                        it.get("Material") or it.get("MaterialNumber") or "",
                        spec, vendor,
                        it.get("PurchaseOrderItemText") or it.get("Description") or "",
                        value, odate.isoformat() if odate else "", lead, status])
            rows += 1
    note = f"{len(pos)} purchase order(s), {rows} line item(s)"
    if missing_spec:
        note += (f"; {missing_spec} line(s) have no spec-section field "
                 "(add a YY1_SpecSection custom field in SAP or edit the CSV) - left empty, never guessed")
    if foreign_ccy:
        note += f"; non-INR currencies present ({', '.join(sorted(foreign_ccy))}) - values NOT converted"
    return buf.getvalue(), note
