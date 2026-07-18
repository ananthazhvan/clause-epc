"""M10 - Paperwork engine + spec linter.

The verdicts are deterministic; the paperwork is just prose around them.
This module drafts, with zero LLM calls:

  1. SPEC LINT - reads the compiled rulebooks + project docs + raw spec
     sections and flags defects in the specification itself:
       a. internal contradictions (same parameter, conflicting values)
       b. design-basis conflicts (DBR says one thing, spec another)
       b2. cross-section standards conflicts (umbrella IEC vs UL-only)
       c. unverifiable qualitative requirements ('adequate', 'sufficient')
       c2. text-level contradictions in raw spec (Part 2 vs Part 3 values)
       d. performance values with no operating conditions (e.g. bare COP)
       e. withdrawn/superseded standard editions (lookup table w/ source)
       f. requirements that collide with statutory codes (lookup table)
  2. RFI drafts - one per lint finding, quoting both sides.
  3. Returned-submittal letters - one per package with deviations,
     every item carrying clause + page on both documents.
  4. Client impact notice - from the ADD-003 blast wave.

Run: python3 m10_paperwork.py  (writes out/paperwork/*.md + out/lint.json
                                + out/paperwork_index.json)
"""
import csv
import datetime
import glob
import json
import os
import re

REG = os.path.join(os.environ.get("CLAUSE_CORPUS", "../clause_corpus"), "registers")
SPECS = os.path.join(os.environ.get("CLAUSE_CORPUS", "../clause_corpus"), "specs")

# Small, citable domain tables (a linter is allowed to know things).
WITHDRAWN_STANDARDS = [
    {"pattern": r"NFPA\s*2001\s*\(?\s*2008", "standard": "NFPA 2001 (2008 Edition)",
     "issue": "withdrawn edition - current edition is 2022", "lint": "withdrawn_standard"},
]
QUALITATIVE = r"\b(adequate|sufficient|appropriate|as required|good industry practice|to the satisfaction of)\b"


def all_text(obj, bucket):
    """Recursively harvest every string in a parsed-doc JSON."""
    if isinstance(obj, str):
        bucket.append(obj)
    elif isinstance(obj, list):
        for x in obj:
            all_text(x, bucket)
    elif isinstance(obj, dict):
        for x in obj.values():
            all_text(x, bucket)
    return bucket


def num(v):
    return v if isinstance(v, (int, float)) else None


def lint(out):
    findings = []
    rules = []
    for p in sorted(glob.glob(os.path.join(out, "rulebook_*.json"))):
        sec = json.load(open(p))
        rules += sec["rules"]

    # a. internal contradictions in compiled rules: same parameter, same
    #    operator, different numeric values (pre-addendum rulebooks)
    byparam = {}
    for r in rules:
        byparam.setdefault(r["parameter"], []).append(r)
    for param, rs in byparam.items():
        seen = {}
        for r in rs:
            v = num(r.get("value"))
            if v is None or r.get("operator") not in ("==", ">=", "<="):
                continue
            key = r["operator"]
            if key in seen and abs(num(seen[key]["value"]) - v) > 1e-9:
                a, b = seen[key], r
                findings.append({
                    "lint": "internal_contradiction", "parameter": param,
                    "a": {"clause": a["source_clause"], "page": a["page"],
                          "value": a["value"], "unit": a.get("unit"), "quote": a["quote"]},
                    "b": {"clause": b["source_clause"], "page": b["page"],
                          "value": b["value"], "unit": b.get("unit"), "quote": b["quote"]},
                    "summary": f"{param}: {a['source_clause']} says {a['value']}"
                               f"{a.get('unit') or ''} but {b['source_clause']} "
                               f"says {b['value']}{b.get('unit') or ''}",
                })
            seen.setdefault(key, r)

    # b. design-basis conflict: DBR redundancy text vs rulebook value
    dbr_path = os.path.join(out, "doc_design_basis_report.json")
    if os.path.exists(dbr_path):
        dbr = " ".join(all_text(json.load(open(dbr_path)), []))
        for r in rules:
            if "redundancy" not in r["parameter"]:
                continue
            rv = str(r.get("value") or "")
            m = re.search(r"N\s*\+\s*(\d)", rv)
            if not m:
                continue
            sys_kw = r["parameter"].split(".")[0]
            for dm in re.finditer(r"([^.]{0,80}\b" + sys_kw + r"\b[^.]{0,120}?N\s*\+\s*(\d)[^.]{0,60})", dbr, re.I):
                if dm.group(2) != m.group(1):
                    findings.append({
                        "lint": "design_basis_conflict", "parameter": r["parameter"],
                        "a": {"clause": "Design Basis Report", "quote": dm.group(1).strip()[:220]},
                        "b": {"clause": r["source_clause"], "page": r["page"],
                              "value": r["value"], "quote": r["quote"]},
                        "summary": f"Design basis says N+{dm.group(2)} for {sys_kw.upper()} "
                                   f"but {r['source_clause']} requires {rv}",
                    })
                    break

    # b2. cross-section standards conflict: umbrella electrical section
    #     mandates IEC certification for all gear, equipment section
    #     references a UL standard with no IEC equivalent
    umbrella = [r for r in rules if r["source_clause"].startswith("26 05 00")
                and re.search(r"standard|certification", r["parameter"])
                and "IEC" in str(r.get("value", ""))]
    if umbrella:
        for r in rules:
            if r["source_clause"].startswith("26 05 00"):
                continue
            if re.search(r"\bstandard\b", r["parameter"]) and \
                    "UL" in str(r.get("value", "")) and "IEC" not in str(r.get("value", "")):
                u = umbrella[0]
                findings.append({
                    "lint": "cross_section_standard_conflict", "parameter": r["parameter"],
                    "a": {"clause": u["source_clause"], "page": u["page"],
                          "value": u["value"], "quote": u["quote"]},
                    "b": {"clause": r["source_clause"], "page": r["page"],
                          "value": r["value"], "quote": r["quote"]},
                    "summary": f"{u['source_clause']} mandates IEC certification "
                               f"({u['value']}) but {r['source_clause']} requires "
                               f"'{r['value']}' with no IEC equivalent",
                })

    # c2 + f. text-level lints over the RAW spec sections (Part 3
    #     execution clauses are not always in the parsed-doc JSON)
    for p in sorted(glob.glob(os.path.join(SPECS, "spec_*.html"))):
        sec_name = os.path.basename(p)[5:-5].replace("_", " ")
        raw = open(p, encoding="utf-8", errors="ignore").read()
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))

        # c2. internal contradiction: battery/inverter runtime minutes
        #     stated with different values in different clauses
        rt = {}
        for sm in re.finditer(r"([^.]{0,140}\b(?:battery|inverter)\b[^.]{0,180}?\bminimum[^.]{0,60}?\b(\d{1,3})(?:\.0)?\s*minutes?\b[^.]{0,60})", text, re.I):
            v = int(sm.group(2))
            rt.setdefault(v, sm.group(1).strip()[:240])
        if len(rt) > 1:
            vals = sorted(rt)
            findings.append({
                "lint": "internal_contradiction", "section": sec_name,
                "a": {"clause": f"Section {sec_name} (Part 2)", "quote": rt[vals[0]]},
                "b": {"clause": f"Section {sec_name} (Part 3)", "quote": rt[vals[-1]]},
                "summary": f"section {sec_name} requires battery runtime of "
                           f"{vals[0]} minutes in one clause and {vals[-1]} "
                           f"minutes in another - a vendor can comply with one "
                           f"and fail the other",
            })

        # f. statutory collision: indoor day tanks vs NBC cap
        for sm in re.finditer(r"([^.]{0,140}\bday tanks?\b[^.]{0,220})", text, re.I):
            s = sm.group(1)
            vols = [int(x) for x in re.findall(r"(\d{3,5})\s*(?:L\b|litres?)\b(?!\s*per|/)", s, re.I)]
            big = [v for v in vols if v >= 1000]
            if big:
                lm_val = big[0]
                findings.append({
                    "lint": "code_conflict", "section": sec_name,
                    "a": {"clause": f"Section {sec_name}", "quote": s.strip()[:240]},
                    "summary": f"section {sec_name} sizes indoor day tanks at "
                               f"{lm_val} L, which collides with the NBC "
                               f"fire-safety cap on indoor fuel day tanks (< 1000 L)",
                })

    # c. qualitative requirements + e. withdrawn standards (parsed specs)
    for p in sorted(glob.glob(os.path.join(out, "doc_spec_*.json"))):
        sec_name = os.path.basename(p)[9:-5].replace("_", " ")
        text = " ".join(all_text(json.load(open(p)), []))
        for sm in re.finditer(r"([^.]{0,100}\bshall\b[^.]{0,160})", text):
            s = sm.group(1)
            qm = re.search(QUALITATIVE, s, re.I)
            if qm and not re.search(r"\d", s):
                findings.append({
                    "lint": "unverifiable_qualitative", "section": sec_name,
                    "a": {"clause": f"Section {sec_name}", "quote": s.strip()[:220]},
                    "summary": f"'{qm.group(0)}' requirement with no measurable "
                               f"criterion in section {sec_name}",
                })
        for w in WITHDRAWN_STANDARDS:
            for wm in re.finditer(r"([^.]{0,80}" + w["pattern"] + r"[^.]{0,80})", text):
                findings.append({
                    "lint": w["lint"], "section": sec_name,
                    "a": {"clause": f"Section {sec_name}", "quote": wm.group(1).strip()[:220]},
                    "summary": f"{w['standard']} referenced in section {sec_name}: {w['issue']}",
                })

    # d. bare performance values (COP/EER with no conditions)
    for r in rules:
        if re.search(r"\b(cop|eer)\b", r["parameter"]) and num(r.get("value")) is not None \
                and not r.get("condition"):
            findings.append({
                "lint": "missing_test_conditions", "parameter": r["parameter"],
                "a": {"clause": r["source_clause"], "page": r["page"],
                      "value": r["value"], "quote": r["quote"]},
                "summary": f"{r['source_clause']} specifies {r['parameter']} = "
                           f"{r['value']} with no operating conditions "
                           f"(entering water temp / airflow unstated) - unverifiable at Cx",
            })

    # dedupe by (lint, summary)
    seen, uniq = set(), []
    for f in findings:
        k = (f["lint"], f["summary"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def main(out="out"):
    today = datetime.date.today().isoformat()
    pdir = os.path.join(out, "paperwork")
    os.makedirs(pdir, exist_ok=True)
    pos = list(csv.DictReader(open(f"{REG}/po_register.csv")))
    sec_vendor = {p["spec_section"]: p["vendor"] for p in pos}
    docs = []

    # ---------- 1+2. lint + RFIs ----------------------------------------
    findings = lint(out)
    json.dump({"generated_at": today, "findings": findings},
              open(os.path.join(out, "lint.json"), "w"), indent=1)
    for i, f in enumerate(findings, 1):
        rid = f"RFI-DRAFT-{i:03d}"
        lines = [f"# {rid} - {f['lint'].replace('_', ' ').title()}", "",
                 f"**Date:** {today}   **Status:** DRAFT (auto-generated from lint finding, human to review before issue)", "",
                 f"**Subject:** {f['summary']}", "", "## Query", ""]
        a, b = f.get("a"), f.get("b")
        if a:
            lines += [f"> {a.get('clause','')}" + (f" (p{a['page']})" if a.get("page") else "") + f": \"{a.get('quote','')}\"", ""]
        if b:
            lines += [f"> {b.get('clause','')}" + (f" (p{b['page']})" if b.get("page") else "") + f": \"{b.get('quote','')}\"", ""]
        lines += ["Please confirm the governing requirement and issue a clarification "
                  "or addendum as appropriate. Until resolved, this item is held as a "
                  "specification defect and excluded from vendor non-conformance counts."]
        fn = f"{rid}.md"
        open(os.path.join(pdir, fn), "w").write("\n".join(lines))
        docs.append({"type": "rfi", "id": rid, "title": f["summary"][:110], "file": fn,
                     "lint": f["lint"]})

    # ---------- 3. returned-submittal letters ---------------------------
    for path in sorted(glob.glob(os.path.join(out, "post", "verdicts_*.json"))):
        v = json.load(open(path))
        devs = [r for r in v["results"] if r["verdict"] == "DEVIATION"]
        if not devs:
            continue
        vendor = sec_vendor.get(v["section"], "Vendor")
        pkg = v["package"]
        lines = [f"# Submittal Review Letter - {pkg}", "",
                 f"**To:** {vendor}   **Date:** {today}   "
                 f"**Disposition:** REVISE AND RESUBMIT", "",
                 f"**Status:** DRAFT (verdicts are machine-verified; letter text is templated; human to review before issue)", "",
                 f"Your submittal {pkg} for specification section {v['section']} has "
                 f"been reviewed against the compiled requirement ledger "
                 f"(post-Addendum 3). {len(devs)} item(s) do not conform. Each item "
                 f"below cites both documents; please respond item-by-item.", ""]
        for i, r in enumerate(devs, 1):
            req, g = r["requirement"], r.get("governing_claim") or {}
            fc = " **Your cover sheet stamps this item 'Comply'.**" if "false_comply" in r["flags"] else ""
            lines += [f"## Item {i} - {r['parameter']}",
                      f"- **Required** ({req['source_clause']}, spec p{req['page']}"
                      + (f", amended by {req['amended_by']}" if req.get("amended_by") else "")
                      + f"): \"{req['quote']}\"",
                      f"- **Offered** ({g.get('location','-')}, submittal p{g.get('page','-')}): "
                      + (f"\"{g['quote']}\"" if g.get("quote") else "no governing evidence found"),
                      f"- **Finding:** {r['reason']}{fc}", ""]
        lines += ["Please resubmit within 14 calendar days. Items may alternatively be "
                  "proposed for concession with supporting margin analysis."]
        fn = f"letter_{pkg}.md"
        open(os.path.join(pdir, fn), "w").write("\n".join(lines))
        docs.append({"type": "letter", "id": pkg, "file": fn,
                     "title": f"Revise & resubmit - {pkg} ({len(devs)} items) to {vendor}"})

    # ---------- 4. client impact notice ----------------------------------
    bw_path = os.path.join(out, "blast_wave.json")
    if os.path.exists(bw_path):
        w = json.load(open(bw_path))
        inv = w.get("pos_invalidated", [])
        total = sum(int(p["value_inr"]) for p in inv)
        lines = ["# Client Impact Notice - Addendum No. 3", "",
                 f"**Date:** {today}   **Ref:** {w.get('addendum','ADD-003')} dated {w.get('date','')}", "",
                 "**Status:** DRAFT (figures are machine-derived from the requirement ledger; human to review before issue)", "",
                 f"Addendum 3 changes {len(w.get('changes', []))} contract requirement(s). "
                 f"Automated re-verification of all submittal packages against the "
                 f"amended ledger shows:", "",
                 f"- {len(w.get('rule_amendments', []))} requirements amended",
                 f"- {len(w.get('verdict_flips', []))} review verdicts flipped",
                 f"- {len(inv)} purchase orders (INR {total:,}) now reference superseded values",
                 f"- {len(w.get('cx_tests_stale', []))} commissioning tests test the old values and are STALE", ""]
        for f_ in w.get("verdict_flips", []):
            lines.append(f"  - {f_['package']} / {f_['rule_id']}: "
                         f"{f_['verdict_before']} -> {f_['verdict_after']}")
        lines += ["", "We request confirmation of the commercial treatment of the "
                  "invalidated purchase orders and the revised commissioning criteria."]
        open(os.path.join(pdir, "impact_notice_ADD-003.md"), "w").write("\n".join(lines))
        docs.append({"type": "notice", "id": "ADD-003",
                     "file": "impact_notice_ADD-003.md",
                     "title": f"Client impact notice - ADD-003 ({len(inv)} POs, INR {total:,})"})

    json.dump({"generated_at": today, "documents": docs},
              open(os.path.join(out, "paperwork_index.json"), "w"), indent=1)
    print(f"S10: {len(findings)} lint findings, {len(docs)} documents -> out/paperwork/")


if __name__ == "__main__":
    main()
