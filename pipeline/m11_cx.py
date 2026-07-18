"""M11 - Commissioning package generator.

When an addendum amends a requirement, every commissioning test that
verifies the old value is silently wrong. This module:

  1. Cross-references the Cx test register with the amended rule ledger
     (out/blast_wave.json) and drafts an updated test procedure for every
     STALE test - old criterion struck through, new criterion substituted,
     provenance chain attached (rule id -> addendum clause -> date).
  2. Builds a commissioning readiness board: for each L4/L5 test, the
     open NCRs on the equipment it tests - a test whose equipment has
     undispositioned deviations cannot produce a valid pass.

Run: python3 m11_cx.py   (writes out/cx_packs.json + out/paperwork/cx_*.md)
"""
import csv
import datetime
import glob
import json
import os
import re

REG = os.path.join(os.environ.get("CLAUSE_CORPUS", "../clause_corpus"), "registers")
SECTION_KW = {"26 33 53": "ups", "26 32 13": "generator",
              "23 81 23": "crah", "21 22 00": "fire"}


def main(out="out"):
    today = datetime.date.today().isoformat()
    _cxp = next((p for p in (f"{REG}/cx_test_register.csv", f"{REG}/cx_register.csv") if os.path.exists(p)), None)
    cx = list(csv.DictReader(open(_cxp)))
    wave = json.load(open(os.path.join(out, "blast_wave.json")))
    stale = {t["test_id"]: t for t in wave.get("cx_tests_stale", [])}
    amendments = wave.get("rule_amendments", [])
    ncrs = []
    dp = os.path.join(out, "dispositions.json")
    if os.path.exists(dp):
        for q in json.load(open(dp))["queue"]:
            ncrs += q["items"]

    pdir = os.path.join(out, "paperwork")
    os.makedirs(pdir, exist_ok=True)
    packs, drafts = [], []

    for t in cx:
        sec = " ".join(t["spec_clause"].split()[:3])
        st = stale.get(t["test_id"])
        # amendments touching this test's spec section
        touching = [a for a in amendments if a["rule_id"].startswith(sec)]
        open_ncrs = [n for n in ncrs if n["section"] == sec]
        pack = {
            "test_id": t["test_id"], "level": t["level"], "system": t["system"],
            "spec_clause": t["spec_clause"], "status": t["status"],
            "acceptance_criteria": t["acceptance_criteria"],
            "ledger_status": "STALE" if st else "CURRENT",
            "open_ncrs_on_equipment": len(open_ncrs),
            "ready": (not st) and not open_ncrs,
        }
        if st:
            # substitute amended numeric values into the criteria text
            new_crit = t["acceptance_criteria"]
            subs = []
            for a in touching:
                frm, to = str(a["from"]), str(a["to"])
                frm_n = re.sub(r"\.0$", "", frm)
                pat = re.compile(r"\b" + re.escape(frm_n) + r"(\.0)?\b")
                if pat.search(new_crit):
                    new_crit = pat.sub(to, new_crit)
                    subs.append(a)
            pack["updated_criteria"] = new_crit
            pack["stale_reason"] = st.get("ledger_reason")
            pack["amendments_applied"] = subs
            # draft procedure
            fn = f"cx_{t['test_id']}.md"
            lines = [f"# Updated Test Procedure - {t['test_id']} ({t['system']})", "",
                     f"**Date:** {today}   **Level:** {t['level']}   "
                     f"**Spec clause:** {t['spec_clause']}", "",
                     "**Status:** DRAFT (values substituted mechanically from the "
                     "amended requirement ledger; human to countersign before execution)", "",
                     "## Why this procedure was regenerated",
                     f"- {st.get('ledger_reason', 'criteria reference superseded values')}",
                     "", "## Acceptance criteria",
                     f"- ~~{t['acceptance_criteria']}~~  (superseded)",
                     f"- **{new_crit}**", "", "## Provenance"]
            for a in subs or touching:
                lines.append(f"- Rule {a['rule_id']}: {a['from']} -> {a['to']} "
                             f"(amended by {wave.get('addendum','ADD-003')} "
                             f"dated {wave.get('date','')})")
            if open_ncrs:
                lines += ["", "## Blocockers"]
            if open_ncrs:
                lines[-1] = "## Blockers"
                lines += [f"- {n['ncr_id']}: {n['parameter']} ({n['verdict']})"
                          for n in open_ncrs[:10]]
                lines += ["", "This test cannot produce a valid pass until the "
                          "above NCRs are dispositioned."]
            open(os.path.join(pdir, fn), "w").write("\n".join(lines))
            drafts.append({"type": "cx_procedure", "id": t["test_id"], "file": fn,
                           "title": f"Updated Cx procedure - {t['test_id']} ({t['system']})"})
        packs.append(pack)

    # append drafts to the paperwork index
    idx_path = os.path.join(out, "paperwork_index.json")
    if os.path.exists(idx_path):
        idx = json.load(open(idx_path))
        idx["documents"] = [d for d in idx["documents"] if d["type"] != "cx_procedure"] + drafts
        json.dump(idx, open(idx_path, "w"), indent=1)

    result = {
        "generated_at": today,
        "tests": packs,
        "stale": sum(p["ledger_status"] == "STALE" for p in packs),
        "blocked": sum((not p["ready"]) and p["ledger_status"] == "CURRENT" for p in packs),
        "ready": sum(p["ready"] for p in packs),
    }
    json.dump(result, open(os.path.join(out, "cx_packs.json"), "w"), indent=1)
    print(f"S11: {len(packs)} Cx tests ({result['stale']} stale, "
          f"{result['ready']} ready) -> out/cx_packs.json, {len(drafts)} procedures drafted")


if __name__ == "__main__":
    main()
