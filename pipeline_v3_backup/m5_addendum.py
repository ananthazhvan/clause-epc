"""M5 - Addendum precedence layer + blast wave.

Deterministic by design, like M4: an addendum is a legal instrument, so
applying it must not involve guessing. ADD-003 uses structured actions
(DELETE 'x' and INSERT 'y'); this parser handles that contract language
directly. An unstructured addendum would route through the M2 LLM
extractor + verbatim-quote checker instead (same machinery, same audit
trail) - that path exists in m2_rules.py and is not duplicated here.

Pipeline:
  1. Parse out/doc_addendum_3.json -> change orders (with page provenance).
  2. Amend matching rules -> out/post/rulebook_*.json (original value kept,
     amended_by recorded - the rulebook is a ledger, not a mutation).
  3. Re-run the deterministic verifier (M4) against amended rulebooks
     -> out/post/verdicts_*.json.
  4. Diff pre vs post verdicts -> verdict flips.
  5. Walk the registers: POs ordered before the addendum against amended
     sections -> INVALID; Cx tests whose acceptance criteria still test
     the deleted value -> STALE.
  6. Write out/blast_wave.json. Zero LLM calls.
"""
import csv
import json
import os
import re
import shutil

import m4_verify

ADDENDUM_ID = "ADD-003"
ADDENDUM_DOC = "out/doc_addendum_3.json"
REGISTERS = "../clause_corpus/registers"

CHANGE_RE = re.compile(
    r"Reference: Section (\d{2} \d{2} \d{2}), Part ([\d.A-Z]+)\s*\n"
    r"Action: DELETE '([^']+)' and INSERT '([^']+)'\s*\n"
    r"Clause: (.*?)(?=\nReference:|\nMeridian|\Z)",
    re.S,
)
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def first_num(s):
    m = NUM_RE.search(s)
    return float(m.group()) if m else None


def nums_in(s):
    return [float(x) for x in NUM_RE.findall(s)]


def parse_addendum():
    doc = json.load(open(ADDENDUM_DOC))
    date = None
    changes = []
    for page in doc["pages"]:
        text = page["text"]
        m = re.search(r"Date:\s*(\d{2}-\d{2}-\d{4})", text)
        if m and not date:
            d, mo, y = m.group(1).split("-")
            date = f"{y}-{mo}-{d}"
        for sec, part, dele, ins, desc in CHANGE_RE.findall(text):
            changes.append({
                "addendum": ADDENDUM_ID,
                "section": sec,
                "clause": f"{sec} Part {part}",
                "delete": dele,
                "insert": ins,
                "description": " ".join(desc.split()),
                "page": page.get("page"),
            })
    if not changes:
        raise SystemExit("M5: no structured changes parsed from addendum - "
                         "route this document through the M2 LLM path.")
    return date, changes


def amend_rulebooks(changes, date):
    os.makedirs("out/post", exist_ok=True)
    amendments = []
    for path in sorted(os.listdir("out")):
        if not (path.startswith("rulebook_") and path.endswith(".json")):
            continue
        rb = json.load(open(f"out/{path}"))
        for rule in rb["rules"]:
            for ch in changes:
                if not rule["source_clause"].startswith(ch["clause"]):
                    continue
                old, new = first_num(ch["delete"]), first_num(ch["insert"])
                rv = m4_verify.parse_number(rule.get("value"))
                applied = False
                if old is not None and rv is not None and abs(rv - old) < 1e-9:
                    rule["original_value"], rule["value"] = rule["value"], new
                    applied = True
                elif isinstance(rule.get("value"), str) and ch["delete"] in rule["value"]:
                    rule["original_value"] = rule["value"]
                    rule["value"] = rule["value"].replace(ch["delete"], ch["insert"])
                    applied = True
                if applied:
                    rule["amended_by"] = ADDENDUM_ID
                    rule["amended_on"] = date
                    amendments.append({
                        "rule_id": rule["rule_id"],
                        "parameter": rule["parameter"],
                        "from": rule["original_value"],
                        "to": rule["value"],
                        "clause": ch["clause"],
                        "addendum": ADDENDUM_ID,
                    })
        with open(f"out/post/{path}", "w") as f:
            json.dump(rb, f, indent=1)
    return amendments


def rerun_verifier():
    for path in sorted(os.listdir("out")):
        if path.startswith("claims_") and path.endswith(".json"):
            m4_verify.verify_package(f"out/{path}", "out/post")


def diff_verdicts():
    flips = []
    for path in sorted(os.listdir("out/post")):
        if not (path.startswith("verdicts_") and path.endswith(".json")):
            continue
        post = json.load(open(f"out/post/{path}"))
        pre = json.load(open(f"out/{path}"))
        pre_map = {r["rule_id"]: r for r in pre["results"]}
        for r in post["results"]:
            p = pre_map.get(r["rule_id"])
            if p and p["verdict"] != r["verdict"]:
                flips.append({
                    "package": post["package"],
                    "rule_id": r["rule_id"],
                    "parameter": r["requirement"]["parameter"],
                    "verdict_before": p["verdict"],
                    "verdict_after": r["verdict"],
                    "reason_after": r["reason"],
                })
    return flips


def walk_registers(changes, date):
    sections = {c["section"] for c in changes}
    pos = []
    for row in csv.DictReader(open(f"{REGISTERS}/po_register.csv")):
        if row["spec_section"] in sections and row["order_date"] < date:
            pos.append({**row, "ledger_status": "INVALID",
                        "ledger_reason": f"ordered {row['order_date']} against a "
                                          f"requirement amended by {ADDENDUM_ID} on {date}"})
    stale = []
    for row in csv.DictReader(open(f"{REGISTERS}/cx_test_register.csv")):
        sec = row["spec_clause"][:8]
        if sec not in sections:
            continue
        crit = row["acceptance_criteria"]
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
                                                f"'{ch['delete']}' superseded by {ADDENDUM_ID}"})
                break
    return pos, stale


def main():
    date, changes = parse_addendum()
    print(f"M5: parsed {len(changes)} change(s) from {ADDENDUM_ID} dated {date}")
    amendments = amend_rulebooks(changes, date)
    print(f"M5: amended {len(amendments)} rule(s):")
    for a in amendments:
        print(f"   {a['rule_id']}: {a['from']} -> {a['to']}")
    rerun_verifier()
    flips = diff_verdicts()
    pos, stale = walk_registers(changes, date)
    wave = {
        "addendum": ADDENDUM_ID, "date": date, "changes": changes,
        "rule_amendments": amendments, "verdict_flips": flips,
        "pos_invalidated": pos, "cx_tests_stale": stale,
        "summary": {"changes": len(changes), "rules_amended": len(amendments),
                     "verdict_flips": len(flips), "pos_invalidated": len(pos),
                     "cx_tests_stale": len(stale)},
    }
    with open("out/blast_wave.json", "w") as f:
        json.dump(wave, f, indent=1)
    print("\nBLAST WAVE SUMMARY")
    for k, v in wave["summary"].items():
        print(f"  {k}: {v}")
    for fl in flips:
        print(f"  FLIP {fl['package']} {fl['rule_id']}: "
              f"{fl['verdict_before']} -> {fl['verdict_after']}")
    for p in pos:
        print(f"  PO INVALID: {p['po_number']} ({p['item_description'][:40]})")
    for t in stale:
        print(f"  CX STALE: {t['test_id']} ({t['spec_clause']})")


if __name__ == "__main__":
    main()
