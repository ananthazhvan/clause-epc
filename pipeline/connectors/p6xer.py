"""Primavera P6 XER connector: native XER export -> canonical schedule.csv.

XER is P6's tab-delimited exchange format: %T <table>, %F <fields>, %R <row>.
We read TASK (+ TASKPRED for logic) and emit the canonical schedule register.
Duration and float columns are hour counts (8h working day). Deterministic,
zero LLM.
"""
import csv
import io

PRED_SEP = ";"


def _tables(text):
    tabs, fields, cur = {}, {}, None
    for line in text.splitlines():
        parts = line.split("\t")
        tag = parts[0]
        if tag == "%T":
            cur = parts[1].strip()
            tabs[cur] = []
        elif tag == "%F" and cur:
            fields[cur] = [f.strip() for f in parts[1:]]
        elif tag == "%R" and cur and fields.get(cur):
            tabs[cur].append(dict(zip(fields[cur], parts[1:])))
    return tabs


def sniff(data):
    head = data[:200000].decode("utf-8", errors="ignore")
    return head.startswith("ERMHDR") or "%T\tTASK" in head


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def convert(data):
    tabs = _tables(data.decode("utf-8", errors="ignore"))
    tasks = tabs.get("TASK") or []
    if not tasks:
        raise ValueError("no TASK table in XER")
    code_by_id = {t.get("task_id"): t.get("task_code") for t in tasks}
    preds = {}
    for p in tabs.get("TASKPRED") or []:
        c = code_by_id.get(p.get("task_id"))
        pc = code_by_id.get(p.get("pred_task_id"))
        if c and pc:
            preds.setdefault(c, []).append(pc)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["activity_id", "name", "duration_days", "predecessors", "float_days", "critical_path"])
    nfloat = 0
    for t in tasks:
        code = t.get("task_code") or ""
        dur = _num(t.get("target_drtn_hr_cnt"))
        fl = _num(t.get("total_float_hr_cnt"))
        if fl is not None:
            nfloat += 1
        w.writerow([code, t.get("task_name") or "",
                    round(dur / 8) if dur is not None else "",
                    PRED_SEP.join(preds.get(code, [])),
                    round(fl / 8) if fl is not None else "",
                    "YES" if fl is not None and fl <= 0 else "NO"])
    note = (f"{len(tasks)} activities, {sum(len(v) for v in preds.values())} logic links, "
            f"float carried on {nfloat} activities (XER hour counts / 8h day)")
    return buf.getvalue(), note
