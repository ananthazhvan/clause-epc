"""M5b - Project graph builder.

Builds the requirements-ledger graph that the UI renders and M6 walks.
Every node and edge is derived from pipeline artifacts and corpus
registers - nothing is invented. Zero LLM calls.

Node types: section, clause (only clauses that produced rules), package,
po, activity, cx, addendum.
Edge types: contains (section->clause), addresses (package->clause,
carries worst verdict), supplies (po->section), schedules (po->activity),
precedes (activity->activity), verifies (cx->clause/section),
amends (addendum->clause).
"""
import csv
import glob
import json
import os

REGISTERS = "../clause_corpus/registers"
SEVERITY = {"DEVIATION": 4, "NEEDS_REVIEW": 3, "MISSING_EVIDENCE": 2,
            "COMPLY": 1, "NOT_ADDRESSED": 0}
# Deterministic keyword bridge between PO equipment and schedule activities.
SECTION_ACTIVITY_KEYWORD = {
    "26 33 53": "ups", "26 32 13": "generator",
    "23 81 23": "crah", "21 22 00": "fire",
}


def worst(a, b):
    return a if SEVERITY.get(a, -1) >= SEVERITY.get(b, -1) else b


def main(out="out"):
    nodes, edges = {}, []

    def add(nid, ntype, label, status=None, **meta):
        if nid in nodes:
            if status:
                nodes[nid]["status"] = worst(nodes[nid].get("status"), status)
            return nodes[nid]
        nodes[nid] = {"id": nid, "type": ntype, "label": label,
                      "status": status, "meta": meta}
        return nodes[nid]

    # Sections + clauses from rulebooks (post-addendum = current reality).
    for path in sorted(glob.glob(f"{out}/post/rulebook_*.json")):
        rb = json.load(open(path))
        sec = rb["section"]
        add(f"sec:{sec}", "section", sec)
        for r in rb["rules"]:
            cl = r["source_clause"]
            n = add(f"cl:{cl}", "clause", cl.split(" Part ")[-1],
                    section=sec, rules=0)
            n["meta"]["rules"] += 1
            if r.get("amended_by"):
                n["meta"]["amended_by"] = r["amended_by"]
            e = (f"sec:{sec}", f"cl:{cl}", "contains")
            if e not in edges:
                edges.append(e)

    # Packages + addresses edges with worst verdict (post-addendum).
    pkg_secs = {}
    for path in sorted(glob.glob(f"{out}/post/verdicts_*.json")):
        v = json.load(open(path))
        pkg, sec = v["package"], v["section"]
        pkg_secs[pkg] = sec
        counts = {}
        for r in v["results"]:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        add(f"pkg:{pkg}", "package", pkg, section=sec, verdicts=counts)
        per_clause = {}
        for r in v["results"]:
            if r["verdict"] == "NOT_ADDRESSED":
                continue
            cl = r["requirement"]["source_clause"]
            per_clause[cl] = worst(per_clause.get(cl), r["verdict"])
            if "false_comply" in r["flags"]:
                per_clause[cl] = "DEVIATION"
        for cl, verdict in per_clause.items():
            if f"cl:{cl}" in nodes:
                nodes[f"cl:{cl}"]["status"] = worst(nodes[f"cl:{cl}"]["status"], verdict)
                edges.append((f"pkg:{pkg}", f"cl:{cl}", "addresses", verdict))
        pn = nodes[f"pkg:{pkg}"]
        pn["status"] = max(per_clause.values(), key=lambda s: SEVERITY[s], default="COMPLY")

    # Blast wave overlays.
    wave = {}
    if os.path.exists(f"{out}/blast_wave.json"):
        wave = json.load(open(f"{out}/blast_wave.json"))
        add("add:ADD-003", "addendum", wave["addendum"], status="AMENDS",
            date=wave["date"], summary=wave["summary"])
        for ch in wave["changes"]:
            for nid in list(nodes):
                if nid.startswith("cl:") and nid[3:].startswith(ch["clause"]):
                    edges.append(("add:ADD-003", nid, "amends"))
    invalid_pos = {p["po_number"] for p in wave.get("pos_invalidated", [])}
    stale_cx = {t["test_id"] for t in wave.get("cx_tests_stale", [])}

    # POs.
    activities = list(csv.DictReader(open(f"{REGISTERS}/schedule.csv")))
    for row in csv.DictReader(open(f"{REGISTERS}/po_register.csv")):
        status = "INVALID" if row["po_number"] in invalid_pos else row["delivery_status"]
        add(f"po:{row['po_number']}", "po", row["po_number"], status=status,
            section=row["spec_section"], vendor=row["vendor"],
            value_inr=int(row["value_inr"]), lead_time_weeks=int(row["lead_time_weeks"]),
            delivery=row["delivery_status"], item=row["item_description"])
        edges.append((f"po:{row['po_number']}", f"sec:{row['spec_section']}", "supplies"))
        kw = SECTION_ACTIVITY_KEYWORD.get(row["spec_section"])
        if kw:
            for act in activities:
                if kw in act["name"].lower():
                    edges.append((f"po:{row['po_number']}", f"act:{act['activity_id']}", "schedules"))

    # Schedule activities.
    for row in activities:
        add(f"act:{row['activity_id']}", "activity", row["name"],
            status="CRITICAL" if row["critical_path"] == "True" else None,
            float_days=int(row["float_days"]), duration=int(row["duration_days"]),
            critical=row["critical_path"] == "True")
        for pred in filter(None, row["predecessors"].split(";")):
            edges.append((f"act:{pred.strip()}", f"act:{row['activity_id']}", "precedes"))

    # Cx tests.
    for row in csv.DictReader(open(f"{REGISTERS}/cx_test_register.csv")):
        status = "STALE" if row["test_id"] in stale_cx else row["status"]
        add(f"cx:{row['test_id']}", "cx", row["test_id"], status=status,
            clause=row["spec_clause"], level=row["level"],
            criteria=row["acceptance_criteria"])
        target = f"cl:{row['spec_clause']}"
        if target not in nodes:
            target = f"sec:{row['spec_clause'][:8]}"
        if target in nodes:
            edges.append((f"cx:{row['test_id']}", target, "verifies"))

    graph = {
        "nodes": list(nodes.values()),
        "edges": [{"s": e[0], "t": e[1], "type": e[2],
                   **({"status": e[3]} if len(e) > 3 else {})} for e in edges],
    }
    with open(f"{out}/graph.json", "w") as f:
        json.dump(graph, f, indent=1)
    from collections import Counter
    print("graph nodes:", dict(Counter(n['type'] for n in graph['nodes'])))
    print("graph edges:", dict(Counter(e['type'] for e in graph['edges'])))
    print(f"-> {out}/graph.json")


if __name__ == "__main__":
    main()
