#!/usr/bin/env python3
"""
Validate that every spec_clause referenced in the project bible resolves
to a clause_id in the clauses registry.

Sources checked:
  - deviations[].spec_clause
  - compliant_checks[].spec_clause
  - spec_defects[].location (extracted clause references)
  - registers.cx_test_register[].spec_clause
  - addendum_3.changes[].reference (normalized format)
"""

import os
import re
import sys
import yaml

BIBLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project_bible.yaml")

# Regex to match clause references: "XX XX XX Part X.X.X[.L]"
CLAUSE_REF_RE = re.compile(r'\b(\d{2}\s\d{2}\s\d{2}\s+Part\s+[\d]+(?:\.[\d]+)*(?:\.[A-Z])?)\b')

# Regex for bare "Part X.X.X[.L]" (relative, needs section prefix)
# Negative lookbehind ensures we don't match "NBC Part 4", "DBR Section 3.1", etc.
BARE_PART_RE = re.compile(r'(?<!\d\s)(?<![A-Z] )Part\s+([\d]+(?:\.[\d]+)*(?:\.[A-Z])?)\b')


def collect_clause_ids(bible):
    """Collect all clause_ids from the clauses block."""
    ids = set()
    clauses = bible.get("clauses", {})
    for section_data in clauses.values():
        for part in section_data.get("parts", []):
            for article in part.get("articles", []):
                for para in article.get("paragraphs", []):
                    ids.add(para["clause_id"])
    return ids


def collect_required_refs(bible):
    """Collect all spec_clause references from the bible."""
    required = set()
    sources = {}  # track where each ref came from

    # 1. deviations
    for dev in bible.get("deviations", []):
        ref = dev["spec_clause"]
        required.add(ref)
        sources.setdefault(ref, []).append(f"deviation:{dev['check_id']}")

    # 2. compliant_checks
    for chk in bible.get("compliant_checks", []):
        ref = chk["spec_clause"]
        required.add(ref)
        sources.setdefault(ref, []).append(f"compliant:{chk['check_id']}")

    # 3. spec_defects (parse location field)
    for defect in bible.get("spec_defects", []):
        loc = defect["location"]
        section = defect["section"]

        # Find full references (with section prefix)
        full_refs = CLAUSE_REF_RE.findall(loc)
        for ref in full_refs:
            # Normalize whitespace
            ref = re.sub(r'\s+', ' ', ref)
            required.add(ref)
            sources.setdefault(ref, []).append(f"defect:{defect['defect_id']}")

        # Find bare "Part X.X.X" references and prefix with section
        # Remove already-matched full refs from the string to avoid double-matching
        remaining = loc
        for fr in full_refs:
            remaining = remaining.replace(fr, "")

        bare_matches = BARE_PART_RE.findall(remaining)
        for bm in bare_matches:
            full_ref = f"{section} Part {bm}"
            # Skip non-spec references like "NBC Part 4"
            if not re.match(r'\d{2} \d{2} \d{2}', section):
                continue
            required.add(full_ref)
            sources.setdefault(full_ref, []).append(f"defect:{defect['defect_id']}(relative)")

    # 4. cx_test_register
    for test in bible.get("registers", {}).get("cx_test_register", []):
        ref = test["spec_clause"]
        required.add(ref)
        sources.setdefault(ref, []).append(f"cx_test:{test['test_id']}")

    # 5. addendum_3.changes
    for change in bible.get("addendum_3", {}).get("changes", []):
        ref_raw = change["reference"]
        # Normalize: "Section 26 33 53, Part 2.3.4" → "26 33 53 Part 2.3.4"
        normalized = re.sub(r'Section\s+(\d{2}\s\d{2}\s\d{2}),\s*Part', r'\1 Part', ref_raw)
        required.add(normalized)
        sources.setdefault(normalized, []).append(f"addendum_3")

    return required, sources


def resolve_ref(ref, clause_ids):
    """Check if a reference resolves to a clause_id.
    
    Exact match first, then check if ref is a parent prefix of any clause_id.
    E.g. "23 81 23 Part 2.2.1" resolves if "23 81 23 Part 2.2.1.A" exists.
    """
    if ref in clause_ids:
        return True
    # Check as parent prefix
    prefix = ref + "."
    return any(cid.startswith(prefix) for cid in clause_ids)


def main():
    with open(BIBLE_PATH, "r") as f:
        bible = yaml.safe_load(f)

    if "clauses" not in bible:
        print("ERROR: No 'clauses' block found in project_bible.yaml")
        return 1

    clause_ids = collect_clause_ids(bible)
    required, sources = collect_required_refs(bible)

    print(f"Clause IDs defined:        {len(clause_ids)}")
    print(f"Spec clause refs found:    {len(required)}")
    print()

    resolved = set()
    unresolved = set()

    for ref in sorted(required):
        if resolve_ref(ref, clause_ids):
            resolved.add(ref)
        else:
            unresolved.add(ref)

    print(f"Resolved:                  {len(resolved)}")
    print(f"Unresolved:                {len(unresolved)}")
    print()

    if unresolved:
        print("UNRESOLVED REFERENCES:")
        for ref in sorted(unresolved):
            src_list = sources.get(ref, ["unknown"])
            print(f"  ✗ {ref}")
            for s in src_list:
                print(f"      from: {s}")
        print()
        print(f"FAIL: {len(unresolved)} unresolved clause reference(s)")
        return 1
    else:
        print("✓ 100% clause resolution achieved!")
        print()

        # Bonus: validate defect embeddings
        print("--- Defect Embedding Checks ---")
        defect_checks = [
            ("DEF-001", "26 33 53 Part 2.1.2.A", "N+2"),
            ("DEF-002a", "26 33 53 Part 2.3.1.E", "10.0 minutes"),
            ("DEF-002b", "26 33 53 Part 3.4.2.C", "12 minutes"),
            ("DEF-003a", "26 05 00 Part 1.4.3.B", "IEC"),
            ("DEF-003b", "26 13 26 Part 1.2.1", "UL"),
            ("DEF-004", "23 81 23 Part 2.2.4.C", "5.2"),
            ("DEF-005", "26 32 13 Part 3.2.1.F", "adequate ventilation"),
            ("DEF-006", "21 22 00 Part 1.2.1", "2008"),
            ("DEF-007", "26 32 13 Part 2.3.8.C", "2.0 hours"),
        ]

        # Find clause text by clause_id
        clause_texts = {}
        for section_data in bible["clauses"].values():
            for part in section_data.get("parts", []):
                for article in part.get("articles", []):
                    for para in article.get("paragraphs", []):
                        clause_texts[para["clause_id"]] = para["text"]

        all_pass = True
        for label, cid, keyword in defect_checks:
            text = clause_texts.get(cid, "")
            if keyword.lower() in text.lower():
                print(f"  ✓ {label}: '{keyword}' found in {cid}")
            else:
                print(f"  ✗ {label}: '{keyword}' NOT found in {cid}")
                all_pass = False

        print()
        if all_pass:
            print("✓ All defect embeddings verified!")
        else:
            print("WARN: Some defect embedding checks failed")

        return 0


if __name__ == "__main__":
    sys.exit(main())
