#!/usr/bin/env python3
"""M5 - Addendum precedence layer + blast wave. Project-agnostic.

An addendum is a legal instrument, so applying it must not involve
guessing: the deterministic change grammar is

    Reference: Section NN NN NN, Part X.Y.Z
    Action: DELETE '<old>' and INSERT '<new>'
    Clause: <one-sentence description ending with a period.>

Any parsed document whose opening lines announce ADDENDUM and which
carries at least one structured action is treated as an addendum -
discovery is by content, never by filename or hardcoded ID. Multiple
addenda are applied cumulatively in date order; each produces its own
wave (rule amendments, verdict flips, invalidated POs, stale Cx tests).
An unstructured addendum routes through the M2 LLM path instead.

Zero LLM calls. The rulebook is a ledger, not a mutation: original
values are kept and amended_by/amended_on are recorded.
"""
import csv
import glob
import json
import os
import re

import m4_verify

OUT = "out"
REGISTERS = os.path.join(os.environ.get("CLAUSE_CORPUS", "../clause_corpus"), "registers")

CHANGE_RE = re.compile(
    r"Reference: Section (\d{2} \d{2} \d{2}), Part ([\d.A-Z]+)\s*\n"
    r"Action: DELETE '([^']+)' and INSERT '([^']+)'\s*\n"
    r"Clause: (.*?)(?=\nReference:|\Z)",
    re.S,
)
PROSE_ITEM_RE = re.compile(
    r"Item\s+\d+\s*[\u2014\u2013-]+\s*Section\s+(\d{2} \d{2} \d{2})\s*,\s*Clause\s+([\d.]+)", re.I)
PROSE_DELSUB_RE = re.compile(
    r"Delete\s+[\"\u201c](.+?)[\"\u201d]\s+and\s+(?:substitute|insert)\s+[\"\u201c](.+?)[\"\u201d]",
    re.I | re.S)


def prose_to_structured(text):
    """Rewrite client-format addendum prose into the structured grammar so
    CHANGE_RE can parse it. Deterministic - no LLM."""
    marks = list(PROSE_ITEM_RE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        seg = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        ds = PROSE_DELSUB_RE.search(seg)
        if not ds:
            continue
        old = " ".join(ds.group(1).split()).replace("'", "")
        new = " ".join(ds.group(2).split()).replace("'", "")
        dm = re.search(r"Revised clause reads:\s*(.+?)(?:\n\s*\n|\Z)", seg, re.S)
        desc = " ".join((dm.group(1) if dm else seg[:200]).split())
        out.append("Reference: Section %s, Part %s\n"
                   "Action: DELETE '%s' and INSERT '%s'\n"
                   "Clause: %s" % (m.group(1), m.group(2), old, new, desc))
    return "\n".join(out)


ADD_HEAD_RE = re.compile(r"\bADDENDUM\b\s*(?:NO\.?\s*)?([A-Za-z0-9-]*)", re.I)
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def first_num(s):
    m = NUM_RE.search(s)
    return float(m.group()) if m else None


def clean_desc(s):
    """Trim print furniture: keep description lines up to the last one that
    ends like a sentence (headers/footers don't)."""
    lines = [l.strip() for l in s.strip().split("\n") if l.strip()]
    while len(lines) > 1 and not re.search(r"[.:;]$", lines[-1]):
        lines.pop()
    return " ".join(" ".join(lines).split())


def discover_addenda():
    adds = []
    for path in sorted(glob.glob(os.path.join(OUT, "doc_*.json"))):
        doc = json.load(open(path))
        pages = doc.get("pages", [])
        if not pages or doc.get("transmittal"):
            continue
        head = "\n".join(pages[0].get("text", "").split("\n")[:6])
        hm = ADD_HEAD_RE.search(head)
        if not hm:
            continue
        changes, date = [], None
        for page in pages:
            text = page.get("text", "")
            dm = re.search(r"Date:\s*(\d{2})-(\d{2})-(\d{4})", text)
            if dm and not date:
                date = f"{dm.group(3)}-{dm.group(2)}-{dm.group(1)}"
            dm2 = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", text)
            if dm2 and not date:
                date = dm2.group(1)
            body = text if CHANGE_RE.search(text) else prose_to_structured(text)
            for sec, part, dele, ins, desc in CHANGE_RE.findall(body):
                changes.append({
                    "section": sec,
                    "clause": f"{sec} Part {part}",
                    "delete": dele,
                    "insert": ins,
                    "description": clean_desc(desc),
                    "page": page.get("page"),
                })
        if not changes:
            print(f"S6: {doc.get('doc')} announces an addendum but carries no "
                  "structured actions - route it through the M2 LLM path.")
            continue
        token = hm.group(1).strip("-")
        if token.isdigit():
            aid = f"ADD-{int(token):03d}"
        elif token:
            aid = token.upper() if token.upper().startswith("ADD") else f"ADD-{token.upper()}"
        else:
            aid = os.path.basename(path)[4:-5].upper()
        for c in changes:
            c["addendum"] = aid
        adds.append({"id": aid, "date": date or "9999-12-31",
                     "doc": doc.get("doc"), "changes": changes})
    adds.sort(key=lambda a: (a["date"], a["id"]))
    return adds


def read_register(name):
    p = os.path.join(REGISTERS, name)
    if not os.path.exists(p):
        return None
    return list(csv.DictReader(open(p)))


def load_rulebooks():
    rbs = {}
    for path in sorted(glob.glob(os.path.join(OUT, "rulebook_*.json"))):
        rbs[os.path.basename(path)] = json.load(open(path))
    return rbs


def write_rulebooks(rbs):
    os.makedirs(f"{OUT}/post", exist_ok=True)
    for name, rb in rbs.items():
        with open(f"{OUT}/post/{name}", "w") as f:
            json.dump(rb, f, indent=1)


def amend(rbs, changes, aid, date):
    amendments = []
    for name, rb in rbs.items():
        for rule in rb["rules"]:
            for ch in changes:
                if not rule["source_clause"].startswith(ch["clause"]):
                    continue
                old, new = first_num(ch["delete"]), first_num(ch["insert"])
                rv = m4_verify.parse_number(rule.get("value"))
                before = rule.get("value")
                applied = False
                if old is not None and rv is not None and abs(rv - old) < 1e-9:
                    rule.setdefault("original_value", rule["value"])
                    rule["value"] = new
                    applied = True
                elif isinstance(rule.get("value"), str) and ch["delete"] in rule["value"]:
                    rule.setdefault("original_value", rule["value"])
                    rule["value"] = rule["value"].replace(ch["delete"], ch["insert"])
                    applied = True
                if applied:
                    rule["amended_by"] = aid
                    rule["amended_on"] = date
                    amendments.append({
                        "rule_id": rule["rule_id"],
                        "parameter": rule["parameter"],
                        "from": before,
                        "to": rule["value"],
                        "clause": ch["clause"],
                        "addendum": aid,
                    })
    return amendments


def verdicts_map(dirpath):
    out = {}
    for path in sorted(glob.glob(os.path.join(dirpath, "verdicts_*.json"))):
        v = json.load(open(path))
        for r in v["results"]:
            out[(v["package"], r["rule_id"])] = r
    return out


def rerun_verifier():
    for path in sorted(glob.glob(os.path.join(OUT, "claims_*.json"))):
        m4_verify.verify_package(path, f"{OUT}/post")


    m4_verify.apply_coverage(f"{OUT}/post")
def walk_registers(changes, date, aid):
    sections = {c["section"] for c in changes}
    pos, stale = [], []
    po_rows = read_register("po_register.csv")
    if po_rows is None:
        print("S6: note - po_register.csv not uploaded; PO impact not assessed")
        po_rows = []
    for row in po_rows:
        if row.get("spec_section") in sections and row.get("order_date", "") < date:
            pos.append({**row, "ledger_status": "INVALID",
                        "ledger_reason": f"ordered {row['order_date']} against a "
                                          f"requirement amended by {aid} on {date}"})
    cx_rows = read_register("cx_test_register.csv") or read_register("cx_register.csv")
    if cx_rows is None:
        print("S6: note - cx_test_register.csv not uploaded; Cx impact not assessed")
        cx_rows = []
    for row in cx_rows:
        sec = row.get("spec_clause", "")[:8]
        if sec not in sections:
            continue
        crit = row.get("acceptance_criteria", "")
        for ch in (c for c in changes if c["section"] == sec):
            m = re.search(r"(-?\d+(?:\.\d+)?)\s*([%\u00b0A-Za-z]*)", ch["delete"])
            if not m:
                continue
            old, unit = float(m.group(1)), m.group(2)
            # The deleted value must appear WITH its unit in the acceptance
            # criteria ('96.0%' or '10\u00b0C') - a bare number match would make
            # 'verification step 10' stale on a 10\u00b0C change.
            hit = any(abs(float(n.group(1)) - old) < 1e-9
                      and n.group(2).lower().startswith(unit[:1].lower() if unit else "")
                      and (not unit or n.group(2))
                      for n in re.finditer(r"(-?\d+(?:\.\d+)?)\s*([%\u00b0A-Za-z]*)", crit))
            if hit:
                stale.append({**row, "ledger_status": "STALE",
                              "ledger_reason": f"acceptance criteria still tests "
                                                f"'{ch['delete']}' superseded by {aid}"})
                break
    return pos, stale


def main():
    adds = discover_addenda()
    rbs = load_rulebooks()
    os.makedirs(f"{OUT}/post", exist_ok=True)

    if not adds:
        write_rulebooks(rbs)
        rerun_verifier()
        wave = {"addendum": None, "date": None, "changes": [],
                "rule_amendments": [], "verdict_flips": [],
                "pos_invalidated": [], "cx_tests_stale": [], "waves": [],
                "summary": {"addenda": 0, "changes": 0, "rules_amended": 0,
                             "verdict_flips": 0, "pos_invalidated": 0,
                             "cx_tests_stale": 0}}
        with open(f"{OUT}/blast_wave.json", "w") as f:
            json.dump(wave, f, indent=1)
        print("S6: no addendum found among the uploaded documents - "
              "post-state equals pre-state. Upload the addendum PDF when one "
              "is issued and run again.")
        return

    baseline = verdicts_map(OUT)
    waves = []
    for a in adds:
        print(f"S6: applying {a['id']} dated {a['date']} "
              f"({len(a['changes'])} change(s)) from {a['doc']}")
        amendments = amend(rbs, a["changes"], a["id"], a["date"])
        for am in amendments:
            print(f"   {am['rule_id']}: {am['from']} -> {am['to']}")
        write_rulebooks(rbs)
        rerun_verifier()
        post = verdicts_map(f"{OUT}/post")
        flips = []
        for key, r in post.items():
            b = baseline.get(key)
            if b and b["verdict"] != r["verdict"]:
                flips.append({
                    "package": key[0], "rule_id": key[1],
                    "parameter": r["requirement"]["parameter"],
                    "verdict_before": b["verdict"],
                    "verdict_after": r["verdict"],
                    "reason_after": r["reason"],
                    "addendum": a["id"],
                })
        baseline = post
        pos, stale = walk_registers(a["changes"], a["date"], a["id"])
        waves.append({
            "addendum": a["id"], "date": a["date"], "doc": a["doc"],
            "changes": a["changes"], "rule_amendments": amendments,
            "verdict_flips": flips, "pos_invalidated": pos,
            "cx_tests_stale": stale,
            "summary": {"changes": len(a["changes"]),
                         "rules_amended": len(amendments),
                         "verdict_flips": len(flips),
                         "pos_invalidated": len(pos),
                         "cx_tests_stale": len(stale)},
        })

    latest = waves[-1]

    def allof(k):
        return [x for w in waves for x in w[k]]

    wave = {
        "addendum": latest["addendum"], "date": latest["date"],
        "changes": allof("changes"),
        "rule_amendments": allof("rule_amendments"),
        "verdict_flips": allof("verdict_flips"),
        "pos_invalidated": allof("pos_invalidated"),
        "cx_tests_stale": allof("cx_tests_stale"),
        "waves": waves,
        "summary": {"addenda": len(waves),
                     "changes": len(allof("changes")),
                     "rules_amended": len(allof("rule_amendments")),
                     "verdict_flips": len(allof("verdict_flips")),
                     "pos_invalidated": len(allof("pos_invalidated")),
                     "cx_tests_stale": len(allof("cx_tests_stale"))},
    }
    with open(f"{OUT}/blast_wave.json", "w") as f:
        json.dump(wave, f, indent=1)
    print("\nBLAST WAVE SUMMARY")
    for k, v in wave["summary"].items():
        print(f"  {k}: {v}")
    for fl in wave["verdict_flips"]:
        print(f"  FLIP {fl['package']} {fl['rule_id']}: "
              f"{fl['verdict_before']} -> {fl['verdict_after']}")
    for p in wave["pos_invalidated"]:
        print(f"  PO INVALID: {p.get('po_number')} ({p.get('item_description', '')[:40]})")
    for t in wave["cx_tests_stale"]:
        print(f"  CX STALE: {t.get('test_id')} ({t.get('spec_clause')})")


if __name__ == "__main__":
    main()
