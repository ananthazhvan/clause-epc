#!/usr/bin/env python3
"""M13 - data-centre facility profile (deterministic, no LLM).

Scans the parsed documents + registers for the declarations that make this a
DATA CENTRE project rather than generic construction: availability ratings
(Uptime Institute Tier / TIA-942 Rated), redundancy topologies (N+1 / 2N /
2N+1), the standards the spec invokes (TIA-942, BICSI, ASHRAE, NFPA, IEC),
PUE targets, standby fuel autonomy, and 5-level commissioning coverage.

Every finding carries its quote + document + page. Nothing is inferred beyond
what the uploaded documents actually say; where the registers corroborate a
topology claim (unit counts on POs), that is reported as corroboration.
"""
import argparse
import csv
import datetime
import glob
import json
import os
import re

STANDARDS = [
    ("ANSI/TIA-942 (data centre infrastructure)", r"TIA[\s-]?942"),
    ("Uptime Institute Tier topology", r"Uptime\s+Institute"),
    ("BICSI 002 (DC design best practice)", r"BICSI(?:[\s-]?002)?"),
    ("ASHRAE TC 9.9 thermal guidelines", r"ASHRAE"),
    ("NFPA 75/76 (IT equipment fire protection)", r"NFPA\s*7[56]\b"),
    ("NFPA 110 (emergency/standby power)", r"NFPA\s*110\b"),
    ("NFPA 2001 (clean-agent suppression)", r"NFPA\s*2001\b"),
    ("IEC 62040 (UPS)", r"IEC\s*62040"),
    ("IEEE 519 (harmonics)", r"IEEE\s*519"),
    ("ISO 8528 (generator sets)", r"ISO\s*8528"),
    ("EN 50600 / ISO-IEC 22237", r"EN\s*50600|ISO/?IEC\s*22237"),
]

SYSTEM_BY_DIV = {"21": "fire suppression", "22": "plumbing", "23": "cooling / HVAC",
                 "25": "controls / BMS", "26": "electrical power",
                 "27": "telecom / structured cabling", "28": "fire alarm & security",
                 "33": "site utilities"}

RED_RE = re.compile(r"\b(2N\+1|2N|N\+1|N\+2)\b")
TIER_RE = re.compile(r"\b(?:Tier|Rated)[\s-]*(IV|III|II|I|[1-4])\b")
PUE_RE = re.compile(r"\bPUE\b[^0-9\n]{0,30}([0-9]\.[0-9]{1,2})")
FUEL_RE = re.compile(r"(\d{1,3})\s*(?:hours?|hrs?)[^.\n]{0,50}?fuel|fuel[^.\n]{0,60}?(\d{1,3})\s*(?:hours?|hrs?)", re.I)
DENS_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*kW\s*(?:/|per)\s*rack", re.I)
CONC_RE = re.compile(r"concurrently\s+maintainable|fault[\s-]tolerant|single\s+points?\s+of\s+failure", re.I)
ROMAN = {"1": "I", "2": "II", "3": "III", "4": "IV"}


def norm_tier(tok):
    tok = tok.upper()
    return "Tier " + ROMAN.get(tok, tok)


def doc_div(name, text):
    m = re.search(r"spec[_ ](\d{2})[_ ]\d{2}[_ ]\d{2}", name)
    if m:
        return m.group(1)
    m = re.search(r"\bSECTION\s+(\d{2})\s\d{2}\s\d{2}\b", text[:4000])
    return m.group(1) if m else None


def clean_quote(line):
    return re.sub(r"\s+", " ", line).strip()[:220]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--corpus", default=os.environ.get("CLAUSE_CORPUS", ""))
    a = ap.parse_args()

    # third-party reference material (corpus/external/) is kept on file but
    # never counted as a project declaration - a tender or vendor brochure
    # from another project must not set THIS facility's tier.
    excl = set()
    if a.corpus:
        ext_dir = os.path.join(a.corpus, "external")
        for root, _, names in os.walk(ext_dir):
            for n in names:
                excl.add(os.path.splitext(n)[0].lower())

    docs = []
    for p in sorted(glob.glob(os.path.join(a.out, "doc_*.json"))):
        try:
            d = json.load(open(p))
            name = d.get("doc") or os.path.basename(p)[4:-5]
            if os.path.splitext(str(name))[0].lower() in excl:
                continue
            docs.append((name, d.get("pages") or []))
        except Exception:
            continue
    if not docs:
        print("no parsed documents found - run M1 first")
        raise SystemExit(1)

    stds, ratings, redund, metrics, resil = {}, [], [], [], []
    for name, pages in docs:
        full = "\n".join((pg.get("text") or "") for pg in pages)
        div = doc_div(name, full)
        system = SYSTEM_BY_DIV.get(div, "general / project-wide")
        for pg in pages:
            text, pno = pg.get("text") or "", pg.get("page", 0)
            for label, pat in STANDARDS:
                for _ in re.finditer(pat, text, re.I):
                    e = stds.setdefault(label, {"std": label, "mentions": 0, "sources": []})
                    e["mentions"] += 1
                    src = f"{name} p.{pno}"
                    if src not in e["sources"] and len(e["sources"]) < 6:
                        e["sources"].append(src)
            for line in text.split("\n"):
                m = TIER_RE.search(line)
                if m:
                    ratings.append({"rating": norm_tier(m.group(1)), "quote": clean_quote(line),
                                    "doc": name, "page": pno})
                m = RED_RE.search(line)
                if m:
                    redund.append({"system": system, "topology": m.group(1),
                                   "quote": clean_quote(line), "doc": name, "page": pno})
                m = PUE_RE.search(line)
                if m:
                    metrics.append({"name": "PUE target", "value": m.group(1),
                                    "quote": clean_quote(line), "doc": name, "page": pno})
                m = FUEL_RE.search(line)
                if m:
                    hrs = m.group(1) or m.group(2)
                    metrics.append({"name": "standby fuel autonomy", "value": hrs + " h",
                                    "quote": clean_quote(line), "doc": name, "page": pno})
                m = DENS_RE.search(line)
                if m:
                    metrics.append({"name": "design rack density", "value": m.group(1) + " kW/rack",
                                    "quote": clean_quote(line), "doc": name, "page": pno})
                m = CONC_RE.search(line)
                if m:
                    resil.append({"term": m.group(0).lower(), "quote": clean_quote(line),
                                  "doc": name, "page": pno})

    # dedupe redundancy claims by (system, topology); keep first quote, count rest
    seen, red_out = {}, []
    for r in redund:
        k = (r["system"], r["topology"])
        if k in seen:
            seen[k]["occurrences"] += 1
        else:
            r["occurrences"] = 1
            seen[k] = r
            red_out.append(r)

    # corroborate with the PO register: units actually ordered per division
    po_counts = {}
    po_path = os.path.join(a.corpus, "registers", "po_register.csv") if a.corpus else ""
    if po_path and os.path.exists(po_path):
        for row in csv.DictReader(open(po_path)):
            div = (row.get("spec_section") or "").strip()[:2]
            po_counts[div] = po_counts.get(div, 0) + 1
    for r in red_out:
        div = next((d for d, s in SYSTEM_BY_DIV.items() if s == r["system"]), None)
        if div and div in po_counts:
            r["corroboration"] = f"PO register: {po_counts[div]} line item(s) ordered under division {div}"
        else:
            r["corroboration"] = "no matching PO lines found - topology is declared, not yet corroborated"

    # commissioning levels (5-level Cx is data-centre practice)
    levels, cx_n = set(), 0
    cx_path = os.path.join(a.corpus, "registers", "cx_test_register.csv") if a.corpus else ""
    if cx_path and os.path.exists(cx_path):
        for row in csv.DictReader(open(cx_path)):
            cx_n += 1
            lv = (row.get("level") or "").strip().upper().replace("LV", "L").replace("LEVEL ", "L")
            if re.fullmatch(r"L[1-5]", lv):
                levels.add(lv)

    # declared rating = the highest tier mentioned, with its evidence
    order = {"Tier I": 1, "Tier II": 2, "Tier III": 3, "Tier IV": 4}
    declared = max((r["rating"] for r in ratings), key=lambda x: order.get(x, 0), default=None)
    basis = [r for r in ratings if r["rating"] == declared][:4]

    def has_sys(s):
        return any(r["system"] == s for r in red_out)

    checklist = [
        {"item": "availability rating declared", "status": "declared" if declared else "not found",
         "detail": declared or "no Tier / Rated level stated in the uploaded documents"},
        {"item": "electrical redundancy topology", "status": "declared" if has_sys("electrical power") else "not found",
         "detail": ", ".join(sorted({r["topology"] for r in red_out if r["system"] == "electrical power"})) or "-"},
        {"item": "cooling redundancy topology", "status": "declared" if has_sys("cooling / HVAC") else "not found",
         "detail": ", ".join(sorted({r["topology"] for r in red_out if r["system"] == "cooling / HVAC"})) or "-"},
        {"item": "standby fuel autonomy", "status": "declared" if any(m["name"] == "standby fuel autonomy" for m in metrics) else "not found",
         "detail": next((m["value"] for m in metrics if m["name"] == "standby fuel autonomy"), "-")},
        {"item": "PUE target", "status": "declared" if any(m["name"] == "PUE target" for m in metrics) else "not found",
         "detail": next((m["value"] for m in metrics if m["name"] == "PUE target"), "-")},
        {"item": "fire protection standard (NFPA 75/76/2001)", "status": "declared" if any("NFPA" in s for s in stds) else "not found",
         "detail": ", ".join(s for s in stds if "NFPA" in s) or "-"},
        {"item": "concurrent maintainability / fault tolerance language", "status": "declared" if resil else "not found",
         "detail": (resil[0]["quote"][:120] if resil else "-")},
        {"item": "5-level commissioning coverage", "status": ("declared" if levels else "not found"),
         "detail": (", ".join(sorted(levels)) + f" across {cx_n} tests") if levels else "-"},
    ]

    gaps = [c for c in checklist if c["status"] == "not found"]
    if declared and not any(m["name"] == "standby fuel autonomy" for m in metrics) and declared in ("Tier III", "Tier IV"):
        gaps.append({"item": "tier consistency", "status": "gap",
                     "detail": f"{declared} is declared but no standby fuel autonomy requirement was found - Tier III/IV practice expects one (typ. 72/96 h)"})

    out = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "tier": {"declared": declared, "basis": basis, "all_mentions": len(ratings)},
        "standards": sorted(stds.values(), key=lambda s: -s["mentions"]),
        "redundancy": red_out,
        "resilience_language": resil[:8],
        "metrics": metrics[:20],
        "commissioning": {"levels_seen": sorted(levels), "tests": cx_n},
        "checklist": checklist,
        "gaps": gaps,
    }
    with open(os.path.join(a.out, "facility.json"), "w") as f:
        json.dump(out, f, indent=1)

    print(f"documents scanned: {len(docs)}")
    print(f"availability rating: {declared or 'none declared'} ({len(ratings)} mention(s))")
    print(f"standards referenced: {len(stds)} ({', '.join(list(stds)[:4])}{'...' if len(stds) > 4 else ''})")
    print(f"redundancy claims: {len(red_out)} across {len({r['system'] for r in red_out})} system(s)")
    print(f"commissioning levels seen: {', '.join(sorted(levels)) or 'none'}")
    print(f"facility checklist: {sum(1 for c in checklist if c['status'] == 'declared')}/{len(checklist)} declared, {len(gaps)} gap(s)")
    print("facility.json written")


if __name__ == "__main__":
    main()
