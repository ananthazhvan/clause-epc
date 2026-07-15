#!/usr/bin/env python3
"""M3 - claim extractor: submittal pages -> claimed values with provenance (LLM, cached)."""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import llm, schemas  # noqa: E402

SYSTEM = (
    "You extract vendor claims from equipment submittal pages. "
    'Output strict JSON only, as an object with the single key "claims".'
)

USER_TMPL = """Submittal package {package}, page {page} of {total}. Referenced specification section: {section}.
Known specification parameters for this section (map to these when the match is clear):
{param_list}

Page text:
---
{text}
---
Extract EVERY statement of a technical parameter value as a claim object with fields:
"parameter", "value", "unit", "condition", "location", "quote", "confidence"
- CRITICAL: footnotes, numbered notes, compliance-matrix rows and transmittal header fields are claims too. If a table states one value and a footnote states a different value or a condition for the SAME parameter, output BOTH claims separately. Never merge, average, or resolve conflicts yourself.
- location: one of "table", "footnote", "compliance_matrix", "transmittal", "prose", "curve_caption"
- For a compliance-matrix row: value = the Response cell text verbatim (e.g. "Comply" or the stated value), location = "compliance_matrix", and quote = the clause id exactly as printed in that row (e.g. "26 33 53 Part 2.3.2.A")
- condition: verbatim condition text when stated (e.g. "under VFI mode when harmonic filters are active at 50% load"), else null
- parameter: use a name from the known parameter list when the match is clear; otherwise "unmapped." followed by a snake_case name - never force a wrong mapping
- confidence: 0.0 to 1.0; use below 0.7 when the mapping or the value is ambiguous (ambiguous items route to human review - that is correct behaviour)
- quote: the exact source line, copied verbatim from the page text
- If the page contains no parameter statements, return an empty list.
Return a JSON object with the single key "claims" containing the list (possibly empty)."""


def _quarantine(out_dir, label, items):
    with open(os.path.join(out_dir, "quarantine.jsonl"), "a") as f:
        for it in items:
            f.write(json.dumps({"label": label, "item": it}) + "\n")
    print(f"WARNING {label}: {len(items)} item(s) QUARANTINED (quote not verbatim after repair)")


def extract_package(doc_path, out_dir):
    doc = json.load(open(doc_path))
    pkg = doc["doc"].replace(".pdf", "")
    pkg_label = pkg
    section = (doc.get("transmittal") or {}).get("reference_section")
    if not section:
        sys.exit(f"{pkg}: transmittal reference_section not parsed - inspect {doc_path}")
    stem = section.replace(" ", "_")
    onto_path = os.path.join(out_dir, f"ontology_{stem}.json")
    if not os.path.exists(onto_path):
        sys.exit(f'{pkg}: run m2_rules.py --spec "{section}" first (missing {onto_path})')
    params = sorted(json.load(open(onto_path)).keys())
    claims = []
    total = len(doc["pages"])
    for p in doc["pages"]:
        user = USER_TMPL.format(package=pkg, page=p["page"], total=total, section=section,
                                param_list="\n".join("- " + x for x in params), text=p["text"])
        items, dropped = llm.get_checked_items(SYSTEM, user, "claims", schemas.CLAIM_FIELDS, f"{pkg} p{p['page']}", p["text"])
        if dropped:
            _quarantine(out_dir, f"{pkg_label} p{p['page']}", dropped)
        for c in items:
            c["page"] = p["page"]
        claims.extend(items)
        print(f"{pkg} page {p['page']}: {len(items)} claim(s)")
    pkg_id = (doc.get("transmittal") or {}).get("package_id") or pkg
    with open(os.path.join(out_dir, f"claims_{pkg_id}.json"), "w") as f:
        json.dump({"package": pkg_id, "section": section, "claims": claims}, f, indent=1)
    print(f"== {pkg}: {len(claims)} claims total")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", help="e.g. SUB-263353-01-R0")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    if a.all:
        for f in sorted(glob.glob(os.path.join(a.out, "doc_*.json"))):
            try:
                if "transmittal" not in json.load(open(f)):
                    continue
            except Exception:
                continue
            extract_package(f, a.out)
    elif a.package:
        extract_package(os.path.join(a.out, f"doc_{a.package}.json"), a.out)
    else:
        ap.error("use --package SUB-263353-01-R0 or --all")


if __name__ == "__main__":
    main()
