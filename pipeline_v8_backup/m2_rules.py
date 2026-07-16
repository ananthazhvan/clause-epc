#!/usr/bin/env python3
"""M2 - rule compiler: spec clauses -> machine-checkable rules (LLM, cached)."""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import llm, pool, schemas  # noqa: E402

SECTION_PREFIX = {
    "26 33 53": "ups.",
    "26 32 13": "gen.",
    "23 81 23": "crah.",
    "26 13 26": "swgr.",
    "21 22 00": "fire.",
    "26 05 00": "elec.",
}

SYSTEM = (
    "You compile construction specification clauses into machine-checkable rules. "
    'Output strict JSON only, as an object with the single key "rules".'
)

USER_TMPL = """Specification section {section}.
Clause {clause_id} (page {page}):
---
{text}
---
Extract every objectively checkable requirement in this clause as a rule object with fields:
"parameter", "operator", "value", "unit", "condition", "quote"
- parameter: snake_case with the domain prefix "{prefix}" (examples: {prefix}efficiency_50_load, {prefix}day_tank_capacity_l)
- operator: one of ">=", "<=", "==", "!=", "in", "exists", "absent", "range"
- value: a number for quantitative limits (no thousands separators, no units inside the number), a string for named/categorical requirements, or a two-element list [low, high] for range
- unit: engineering unit string (e.g. "%", "kW", "kVA", "L", "kg", "VDC", "deg C", "dBA", "m3/h"), or null
- condition: the measurement/operating condition copied VERBATIM from the clause when one is stated (e.g. "measured in VFI mode with harmonic filters active", "at 45 deg C ambient"). Use null only when no condition is stated. NEVER drop a stated condition.
- quote: the exact sentence from the clause supporting the rule, copied verbatim
- Purely administrative or procedural text (submittal procedures, reference lists, general scope statements) yields zero rules.
Return a JSON object with the single key "rules" containing the list (possibly empty)."""


def _quarantine(out_dir, label, items):
    with open(os.path.join(out_dir, "quarantine.jsonl"), "a") as f:
        for it in items:
            f.write(json.dumps({"label": label, "item": it}) + "\n")
    print(f"WARNING {label}: {len(items)} item(s) QUARANTINED (quote not verbatim after repair)")


def compile_section(spec_path, out_dir):
    spec = json.load(open(spec_path))
    section = spec["section"]
    prefix = SECTION_PREFIX.get(section, "misc.")
    rules = []

    def _compile_clause(cl):
        user = USER_TMPL.format(section=section, clause_id=cl["clause_id"],
                                page=cl["page"], text=cl["text"], prefix=prefix)
        return llm.get_checked_items(SYSTEM, user, "rules", schemas.RULE_FIELDS, cl["clause_id"], cl["text"])

    # scale-out: one independent LLM call per clause -> parallel map over the
    # key pool. Results come back in input order, so rule numbering is stable.
    w = pool.worker_count()
    if w > 1:
        print(f"  [scale-out: {w} parallel workers over {len(llm.keys())} API key(s)]")
    outs = pool.pmap(_compile_clause, spec["clauses"])
    for cl, (items, dropped) in zip(spec["clauses"], outs):
        if dropped:
            _quarantine(out_dir, cl["clause_id"], dropped)
        for n, r in enumerate(items, 1):
            r["rule_id"] = f"{cl['clause_id']}-R{n}"
            r["source_clause"] = cl["clause_id"]
            r["page"] = cl["page"]
            rules.append(r)
        print(f"{cl['clause_id']}: {len(items)} rule(s)")
    stem = section.replace(" ", "_")
    with open(os.path.join(out_dir, f"rulebook_{stem}.json"), "w") as f:
        json.dump({"section": section, "rules": rules}, f, indent=1)
    onto = {}
    for r in rules:
        onto.setdefault(r["parameter"], set()).add(r.get("unit") or "")
    with open(os.path.join(out_dir, f"ontology_{stem}.json"), "w") as f:
        json.dump({p: sorted(u - {""}) for p, u in sorted(onto.items())}, f, indent=1)
    print(f"== {section}: {len(rules)} rules, {len(onto)} distinct parameters")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help='section id, e.g. "26 33 53"')
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    if a.all:
        for f in sorted(glob.glob(os.path.join(a.out, "spec_*.json"))):
            compile_section(f, a.out)
    elif a.spec:
        stem = a.spec.replace(" ", "_")
        compile_section(os.path.join(a.out, f"spec_{stem}.json"), a.out)
    else:
        ap.error('use --spec "26 33 53" or --all')


if __name__ == "__main__":
    main()
