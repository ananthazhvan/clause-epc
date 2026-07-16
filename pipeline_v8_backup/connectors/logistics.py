"""Logistics-visibility connector: shipment JSON -> enrich po_register.csv.

Real-time transport visibility platforms (FourKites, project44, etc.) publish
shipment feeds keyed by PO number. This adapter matches shipments to staged
po_register.csv rows by po_number and patches three columns on the matching
rows: delivery_status, current_location, eta. Extra columns ride along; the
pipeline's required PO columns are untouched. Deterministic, zero LLM.

Accepted shapes: {"shipments": [...]}, {"value": [...]}, {"data": [...]},
a bare list, or a single shipment object. A shipment needs a PO reference
(purchaseOrderNumber / poNumber / purchase_order) to be usable.
"""
import csv
import io


def _po_of(s):
    return s.get("purchaseOrderNumber") or s.get("poNumber") or s.get("purchase_order") or ""


def _shipments(obj):
    if isinstance(obj, dict):
        for key in ("shipments", "value", "data", "results"):
            if isinstance(obj.get(key), list):
                obj = obj[key]
                break
        else:
            obj = [obj]
    if not isinstance(obj, list):
        return []
    out = []
    for s in obj:
        if isinstance(s, dict) and (s.get("shipmentId") or s.get("shipment_id")) and _po_of(s):
            out.append(s)
    return out


def sniff(obj):
    return bool(_shipments(obj))


def _loc_of(s):
    loc = s.get("lastUpdatedLocation") or s.get("currentLocation") or s.get("location")
    if isinstance(loc, dict):
        lat, lon = loc.get("latitude"), loc.get("longitude")
        name = loc.get("name") or loc.get("city") or ""
        ts = loc.get("timestamp") or ""
        core = name or (f"{lat},{lon}" if lat is not None and lon is not None else "")
        return (core + (f" @ {ts}" if ts and core else "")).strip()
    return str(loc or "").strip()


def _eta_of(s):
    for k in ("estimatedTimeOfArrival", "eta", "estimatedArrival", "scheduledArrival"):
        if s.get(k):
            return str(s[k])
    dest = s.get("destination")
    if isinstance(dest, dict):
        for k in ("eta", "estimatedArrival", "scheduledArrival"):
            if dest.get(k):
                return str(dest[k])
    return ""


def merge(po_csv_text, obj):
    """(existing po_register.csv text, feed payload) -> (merged text, note)."""
    ships = _shipments(obj)
    if not ships:
        raise ValueError("no shipments with a PO reference found in feed")
    rd = csv.DictReader(io.StringIO(po_csv_text))
    rows = list(rd)
    cols = list(rd.fieldnames or [])
    if "po_number" not in cols:
        raise ValueError("staged po_register.csv has no po_number column")
    for extra in ("delivery_status", "current_location", "eta"):
        if extra not in cols:
            cols.append(extra)
    by_po = {}
    for s in ships:
        by_po.setdefault(str(_po_of(s)).strip(), s)
    matched_rows, matched_pos = 0, set()
    for r in rows:
        s = by_po.get(str(r.get("po_number", "")).strip())
        if not s:
            continue
        matched_rows += 1
        matched_pos.add(str(_po_of(s)).strip())
        status = s.get("currentStatus") or s.get("status")
        if status:
            r["delivery_status"] = str(status)
        loc = _loc_of(s)
        if loc:
            r["current_location"] = loc
        eta = _eta_of(s)
        if eta:
            r["eta"] = eta
    unmatched = sorted(set(by_po) - matched_pos)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    note = f"{len(ships)} shipment(s); {matched_rows} PO line(s) updated"
    if unmatched:
        shown = ", ".join(unmatched[:3]) + ("..." if len(unmatched) > 3 else "")
        note += f"; {len(unmatched)} shipment PO(s) not in the register ({shown})"
    return buf.getvalue(), note
