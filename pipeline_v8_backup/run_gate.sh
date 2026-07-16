#!/usr/bin/env bash
# Execution gate: one spec + one submittal end-to-end, then STOP for audit.
set -e
cd "$(dirname "$0")"
CORPUS=${1:-../corpus/rendered}

echo "== STEP 0: plumbing tests (mocked LLM, free) =="
python3 test_plumbing.py

echo "== STEP 1: M1 deterministic parse of ALL documents (free) =="
python3 m1_parse.py --corpus "$CORPUS" --out out
python3 - <<'EOF'
import glob, json
expected = {"26 05 00": 25, "26 33 53": 69, "26 32 13": 44,
            "26 13 26": 33, "23 81 23": 43, "21 22 00": 31}
got = {}
for f in glob.glob("out/spec_*.json"):
    d = json.load(open(f))
    got[d["section"]] = len(d["clauses"])
for sec, n in expected.items():
    assert got.get(sec) == n, f"M1 ACCEPTANCE FAIL {sec}: expected {n}, got {got.get(sec)}"
for f in glob.glob("out/doc_SUB-*.json"):
    t = json.load(open(f)).get("transmittal", {})
    assert t.get("reference_section"), f"M1 ACCEPTANCE FAIL: no reference_section in {f}"
print("M1 ACCEPTANCE PASS:", got, "total", sum(got.values()))
EOF

echo "== STEP 2: M2 rule compiler on section 26 33 53 ONLY (LLM) =="
python3 m2_rules.py --spec "26 33 53"

echo "== STEP 3: M3 claim extractor on SUB-263353-01-R0 ONLY (LLM) =="
python3 m3_claims.py --package SUB-263353-01-R0

echo "== STEP 4: honesty checker =="
python3 check_extractions.py

echo "== STEP 5: gate evidence (the footnote trap) =="
python3 - <<'EOF'
import json
rb = json.load(open("out/rulebook_26_33_53.json"))
print("--- rules compiled from clause 26 33 53 Part 2.2.2.B ---")
for r in rb["rules"]:
    if r["source_clause"].endswith("2.2.2.B"):
        print(json.dumps(r, indent=1))
cl = json.load(open("out/claims_SUB-263353-01-R0.json"))
print("--- claims about 50%-load efficiency ---")
for c in cl["claims"]:
    blob = (c["parameter"] + " " + str(c.get("condition")) + " " + c["quote"]).lower()
    if "eff" in blob and "50" in blob:
        print(json.dumps(c, indent=1))
print("EXPECTED: one rule >= 96.0 with the VFI/harmonic-filter condition;")
print("          TWO claims - 96.1 (table) AND 95.1 (footnote, with condition).")
EOF

echo "GATE COMPLETE. STOP HERE."
echo "Send back for audit: out/rulebook_26_33_53.json, out/claims_SUB-263353-01-R0.json,"
echo "cost_log.jsonl, and this full console output."
