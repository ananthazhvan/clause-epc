"""Primavera P6 XML connector: schedule export -> canonical schedule.csv.

Oracle Primavera P6 is the dominant scheduling tool in EPC; its XML export
(APIBusinessObjects) carries activities, FS/SS/FF logic links, and resource
assignments. This adapter is deterministic stdlib XML parsing - no LLM.

What it reads (namespace-agnostic):
  Activity            Id, Name, ObjectId, PlannedDuration (hours),
                      PlannedStartDate/PlannedFinishDate, TotalFloat (hours)
  Relationship        PredecessorActivityObjectId, SuccessorActivityObjectId,
                      Type, Lag (hours)
  Resource            ObjectId, Name
  ResourceAssignment  ActivityObjectId, ResourceObjectId

Float: taken from TotalFloat when the export carries it; otherwise computed
here with a standard CPM forward/backward pass over finish-to-start logic.
The note returned with the CSV says which one happened - never pretend.
"""
import csv
import io

HOURS_PER_DAY = 8.0


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) and "}" in tag else tag


def sniff(data):
    head = data[:200000].decode("utf-8", errors="ignore")
    if "<APIBusinessObjects" in head or "Primavera" in head:
        return "<Activity" in head or "<Project" in head
    return "<Project" in head and "<Activity" in head


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _days_from_dates(start, finish):
    from datetime import date
    try:
        d0 = date.fromisoformat(str(start)[:10])
        d1 = date.fromisoformat(str(finish)[:10])
        return max((d1 - d0).days, 0)
    except ValueError:
        return None


def _fmt(x):
    if x is None:
        return ""
    r = round(x)
    return str(int(r)) if abs(x - r) < 1e-6 else str(round(x, 2))


def _cpm(acts, preds_by_act, lags):
    """Forward/backward pass over FS logic. Returns float_days per activity id.
    Raises ValueError on a relationship cycle (an honest failure, not a guess)."""
    order, seen, mark = [], set(), set()

    def visit(a):
        if a in seen:
            return
        if a in mark:
            raise ValueError("cycle detected in relationship logic")
        mark.add(a)
        for p in preds_by_act.get(a, ()):  # predecessors first
            if p in acts:
                visit(p)
        mark.discard(a)
        seen.add(a)
        order.append(a)

    for a in acts:
        visit(a)
    es, ef = {}, {}
    for a in order:
        es[a] = max((ef[p] + lags.get((p, a), 0.0) for p in preds_by_act.get(a, ()) if p in acts), default=0.0)
        ef[a] = es[a] + acts[a]
    end = max(ef.values(), default=0.0)
    succs = {}
    for a, ps in preds_by_act.items():
        for p in ps:
            succs.setdefault(p, []).append(a)
    lf, ls = {}, {}
    for a in reversed(order):
        lf[a] = min((ls[s] - lags.get((a, s), 0.0) for s in succs.get(a, ()) if a in acts and s in acts), default=end)
        ls[a] = lf[a] - acts[a]
    return {a: ls[a] - es[a] for a in acts}


def convert(data):
    """P6 XML bytes -> (canonical schedule.csv text, honest conversion note)."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(data.decode("utf-8", errors="ignore"))
    activities, rels, resources, assigns = [], [], {}, []
    for el in root.iter():
        t = _local(el.tag)
        if t == "Activity":
            activities.append({_local(c.tag): (c.text or "").strip() for c in el})
        elif t == "Relationship":
            rels.append({_local(c.tag): (c.text or "").strip() for c in el})
        elif t == "Resource":
            d = {_local(c.tag): (c.text or "").strip() for c in el}
            if d.get("ObjectId"):
                resources[d["ObjectId"]] = d.get("Name") or ("resource-" + d["ObjectId"])
        elif t == "ResourceAssignment":
            assigns.append({_local(c.tag): (c.text or "").strip() for c in el})
    if not activities:
        raise ValueError("no <Activity> elements found")

    by_obj = {a.get("ObjectId"): (a.get("Id") or a.get("ObjectId")) for a in activities if a.get("ObjectId")}
    durs, floats, names = {}, {}, {}
    for a in activities:
        aid = a.get("Id") or a.get("ObjectId") or ""
        names[aid] = a.get("Name", "")
        d = _num(a.get("PlannedDuration"))
        durs[aid] = (d / HOURS_PER_DAY) if d is not None else (
            _days_from_dates(a.get("PlannedStartDate"), a.get("PlannedFinishDate")) or 0)
        tf = _num(a.get("TotalFloat"))
        if tf is not None:
            floats[aid] = tf / HOURS_PER_DAY

    preds, lags, non_fs = {}, {}, 0
    for r in rels:
        p = by_obj.get(r.get("PredecessorActivityObjectId"))
        s = by_obj.get(r.get("SuccessorActivityObjectId"))
        if not p or not s:
            continue
        rtype = (r.get("Type") or "Finish to Start").lower()
        if not ("finish" in rtype and "start" in rtype) and rtype not in ("fs",):
            non_fs += 1  # treated as FS for float purposes - flagged in the note
        preds.setdefault(s, []).append(p)
        lg = _num(r.get("Lag"), 0.0) or 0.0
        lags[(p, s)] = lg / HOURS_PER_DAY

    float_src = "TotalFloat from the P6 export"
    if len(floats) < len(durs):
        floats = _cpm(durs, preds, lags)
        float_src = "computed by CPM forward/backward pass (export carried no TotalFloat)"

    res_by_act = {}
    for asg in assigns:
        aid = by_obj.get(asg.get("ActivityObjectId"))
        rname = resources.get(asg.get("ResourceObjectId"))
        if aid and rname:
            res_by_act.setdefault(aid, []).append(rname)

    buf = io.StringIO()
    cols = ["activity_id", "name", "duration_days", "predecessors", "float_days", "critical_path"]
    if res_by_act:
        cols.append("resources")
    w = csv.writer(buf)
    w.writerow(cols)
    for a in activities:
        aid = a.get("Id") or a.get("ObjectId") or ""
        fl = floats.get(aid, 0.0)
        row = [aid, names.get(aid, ""), _fmt(durs.get(aid, 0)), ";".join(preds.get(aid, [])),
               _fmt(fl), str(fl <= 1e-9)]
        if res_by_act:
            counts = {}
            for rn in res_by_act.get(aid, []):
                counts[rn] = counts.get(rn, 0) + 1
            row.append("; ".join(f"{n} x{c}" if c > 1 else n for n, c in sorted(counts.items())))
        w.writerow(row)

    note = (f"{len(activities)} activities, {len(rels)} logic links, "
            f"{len(assigns)} resource assignment(s); float {float_src}")
    if non_fs:
        note += f"; {non_fs} non-FS link(s) treated as FS for float"
    return buf.getvalue(), note
