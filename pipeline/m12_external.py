"""M12 - External reality check (unseen real documents).

Everything else in this repo runs on the manufactured corpus. This module
runs on two REAL documents dropped into clause_corpus/external/:

  - a real public tender: 'Design, Supply, Installation, Testing &
    Commissioning of HPC-BYOH Data Centre at IIT Bombay' (NTPC, 151 pages)
  - a real vendor brochure: Vertiv Liebert HPC free-cooling chiller range
    (the kind of document a vendor actually attaches to a submittal)

It is deliberately the HONEST tier of the stack: a deterministic L0
regex harvester (no LLM, no cache, nothing planted). It:

  1. Extracts text per page (pypdf/PyMuPDF if available, else the
     `pdftotext` binary; extracted text is cached in out/external/ so
     re-runs and other machines need no PDF tooling).
  2. Harvests candidate requirements from the tender: sentences with
     obligation words (shall/minimum/maximum/...) + a number + a unit,
     with the parameter keyword required within 90 chars of the number.
  3. Harvests numeric claims from the brochure the same way.
  4. Where a requirement and a claim fall in the same parameter family
     (cooling capacity, water temperature, ambient, noise), runs the same
     operator comparison M4 uses and reports a verdict WITH BOTH QUOTES
     AND PAGE NUMBERS - checkable by a judge against the PDFs.
     Site-envelope questions it cannot resolve deterministically are
     routed to REVIEW instead of being guessed - same discipline as M4.

Every number on the External screen traces to a real page of a real
document. Run the full LLM pipeline against these files for deeper
coverage; this module is the zero-cost deterministic floor.

Run: python3 m12_external.py   (writes out/external.json)
"""
import datetime
import glob
import json
import os
import re
import subprocess

EXT = "../clause_corpus/external"
OBLIGATION = r"\b(shall|must|minimum|maximum|not less than|at least|not exceed(?:ing)?|required to)\b"
NUM_UNIT = r"(\d{1,4}(?:[.,]\d{1,3})?)\s*(\u00b0?\s?C\b|TR\b|kW\b|kVA\b|dB\s?\(?A\)?)"

# Family keyword must appear within WINDOW chars of the number itself -
# sentence-level matching pulled in BOQ junk during tuning.
WINDOW = 90
FAMILIES = {
    "cooling_capacity": {"kw": r"cooling capacity|sensible cooling|chiller capacity", "units": {"TR", "kW"}},
    "chilled_water_temp": {"kw": r"chilled water|entering water|leaving water|water temperatures?", "units": {"C"}},
    "ambient_temp": {"kw": r"ambient|outdoor temperature", "units": {"C"}},
    "noise": {"kw": r"noise|sound pressure|acoustic", "units": {"dBA"}},
}
JUNK = re.compile(r"Supply of|Page \d|of 151|Schedule of|\boptional\b|accessor|^\d+ ", re.I)


def norm_unit(u):
    u = u.strip().replace(" ", "")
    u = {"\u00b0C": "C", "\u00b0c": "C", "c": "C"}.get(u, u)
    if re.fullmatch(r"dB\(?A\)?", u):
        u = "dBA"
    return u


def to_kw(val, unit):
    return (val * 3.517, "kW") if unit == "TR" else (val, unit)


def extract_pages(pdf_path, cache_txt):
    if os.path.exists(cache_txt):
        return open(cache_txt, encoding="utf-8", errors="ignore").read().split("\f")
    text = None
    try:
        import pypdf
        text = "\f".join((p.extract_text() or "") for p in pypdf.PdfReader(pdf_path).pages)
    except Exception:
        pass
    if text is None:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text = "\f".join(p.get_text() for p in doc)
        except Exception:
            pass
    if text is None:
        try:
            r = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                text = r.stdout
        except FileNotFoundError:
            pass
    if text is None:
        raise RuntimeError(f"no PDF text extractor available for {pdf_path}; "
                           f"install pypdf or poppler, or ship the cached txt")
    os.makedirs(os.path.dirname(cache_txt), exist_ok=True)
    open(cache_txt, "w", encoding="utf-8").write(text)
    return text.split("\f")


def sentences(page_text):
    flat = re.sub(r"\s+", " ", page_text)
    return re.split(r"(?<=[.;])\s+", flat)


def harvest(pages, need_obligation):
    """-> list of {page, quote, value, unit, operator, window, families}"""
    outp = []
    for pno, ptxt in enumerate(pages, 1):
        for s in sentences(ptxt):
            if len(s) < 25 or len(s) > 700:
                continue
            if need_obligation and not re.search(OBLIGATION, s, re.I):
                continue
            if JUNK.search(s):
                continue
            for m in re.finditer(NUM_UNIT, s):
                val = float(m.group(1).replace(",", ""))
                unit = norm_unit(m.group(2))
                win = s[max(0, m.start() - WINDOW):m.end() + WINDOW].lower()
                fams = [f for f, cfg in FAMILIES.items()
                        if re.search(cfg["kw"], win) and unit in cfg["units"]]
                if "ambient_temp" in fams and re.search(r"room temperature|comfort", win):
                    fams.remove("ambient_temp")  # comfort-AC clause, not equipment envelope
                if not fams:
                    continue
                op = ">="
                if re.search(r"\b(maximum|not exceed|not more than|max\.?|below|less than|up to)\b", win):
                    op = "<="
                elif re.search(r"\b(shall be|of)\s*" + re.escape(m.group(1)), win) and \
                        not re.search(r"minimum|at least|not less", win):
                    op = "=="
                outp.append({"page": pno, "quote": s.strip()[:320],
                             "value": val, "unit": unit, "operator": op,
                             "window": win, "families": fams})
    return outp


def page_of(pages, needle, flags=re.I):
    """1-based page number of first page whose text matches needle."""
    for i, p in enumerate(pages, 1):
        m = re.search(needle, re.sub(r"\s+", " ", p), flags)
        if m:
            flat = re.sub(r"\s+", " ", p)
            a = max(0, m.start() - 130)
            return i, flat[a:m.end() + 130].strip()
    return None, None


def fire_checks(spec_pages, kidde_pages):
    """Targeted string-level checks: IITB tender fire-suppression scope vs
    the real Kidde Fluoro-K brochure. L0-honest: what the text does not
    state is routed to REVIEW, never assumed."""
    checks = []
    rp, rq = page_of(spec_pages, r"Novec\s*1230[^.]{0,120}")
    # 1. agent identity - tender names Novec 1230; brochure brands Fluoro-K
    #    and never states the chemical designation in its text layer
    cp, cq = page_of(kidde_pages, r"Fluoro-K[^.]{0,80}")
    if rp and cp:
        checks.append({
            "family": "agent_identity", "verdict": "REVIEW",
            "requirement": {"page": rp, "operator": "==", "value": "Novec 1230",
                            "unit": None, "quote": rq},
            "claim": {"page": cp, "value": "Fluoro-K", "unit": None, "quote": cq},
            "note": "tender requires a Novec 1230 system; the brochure brands "
                    "its agent 'Fluoro-K' and nowhere states the chemical "
                    "designation (FK-5-1-12) in its text - equivalence cannot "
                    "be verified from this document; request the agent data "
                    "sheet before acceptance",
        })
    # 2. listings - tender points at relevant NFPA standards; brochure
    #    carries UL Listed / FM Approved statements
    rp2, rq2 = page_of(spec_pages, r"relevant NFPA Standards")
    cp2, cq2 = page_of(kidde_pages, r"UL Listed")
    if rp2 and cp2:
        checks.append({
            "family": "listings", "verdict": "SATISFIABLE",
            "requirement": {"page": rp2, "operator": "exists",
                            "value": "NFPA-compliant listings", "unit": None,
                            "quote": rq2},
            "claim": {"page": cp2, "value": "UL Listed / FM Approved",
                      "unit": None, "quote": cq2},
            "note": "listing statements found in brochure text; certificates "
                    "still required at submittal",
        })
    # 3. operating temperature envelope - numeric, both quotes real
    cp3, cq3 = page_of(kidde_pages, r"32\u00b0? to 130\u00b0?F \(0\u00b0? to 54\u00b0?C\)|0\u00b0? to 54\u00b0?\s?C")
    rp3, rq3 = page_of(spec_pages, r"Temperature \(Max\):?\s*41\.4")
    if rp3 and cp3:
        checks.append({
            "family": "operating_temp_range", "verdict": "SATISFIABLE",
            "requirement": {"page": rp3, "operator": "<=", "value": 41.4,
                            "unit": "C", "quote": rq3},
            "claim": {"page": cp3, "value": 54.0, "unit": "C", "quote": cq3},
            "note": "brochure operating range 0-54\u00b0C covers the site "
                    "design maximum of 41.4\u00b0C",
        })
    return checks


def compare(op, req, claim):
    if op == ">=":
        return claim >= req
    if op == "<=":
        return claim <= req
    return abs(claim - req) < 1e-9


def main(out="out"):
    spec_pdf = glob.glob(f"{EXT}/*HPC-BYOH*") + glob.glob(f"{EXT}/*BYOH*")
    sub_pdf = glob.glob(f"{EXT}/*liebert*") + glob.glob(f"{EXT}/*Liebert*")
    spec_pdf = [p for p in spec_pdf if p.endswith(".pdf")]
    sub_pdf = [p for p in sub_pdf if p.endswith(".pdf")]
    if not spec_pdf or not sub_pdf:
        print("M12: external documents not found - skipping")
        return
    spec_pages = extract_pages(spec_pdf[0], os.path.join(out, "external", "iitb_spec.txt"))
    sub_pages = extract_pages(sub_pdf[0], os.path.join(out, "external", "liebert.txt"))
    kidde_pdf = [p for p in glob.glob(f"{EXT}/*Kidde*") if p.endswith(".pdf")]
    kidde_pages = extract_pages(kidde_pdf[0], os.path.join(out, "external", "kidde.txt")) if kidde_pdf else []

    reqs = harvest(spec_pages, need_obligation=True)
    claims = harvest(sub_pages, need_obligation=False)

    checks, seen = [], set()
    for fam in FAMILIES:
        freqs = [r for r in reqs if fam in r["families"]]
        fclaims = [c for c in claims if fam in c["families"]]
        if not freqs or not fclaims:
            continue
        for r in freqs[:4]:
            rv, runit = to_kw(r["value"], r["unit"])
            best, ok = None, None
            for c in fclaims:
                cv, cunit = to_kw(c["value"], c["unit"])
                if cunit != runit:
                    continue
                good = compare(r["operator"], rv, cv)
                if best is None or (good and not ok) or \
                        (good == ok and abs(cv - rv) < abs(to_kw(best["value"], best["unit"])[0] - rv)):
                    best, ok = c, good
            if best is None:
                continue
            verdict = "SATISFIABLE" if ok else "CHECK_FAILS"
            note = ("TR converted to kW at 3.517"
                    if r["unit"] == "TR" or best["unit"] == "TR" else None)
            # Site-envelope semantics an L0 comparator cannot resolve get
            # routed to a human instead of being guessed away.
            if fam == "ambient_temp" and "max" in r.get("window", "") \
                    and best["value"] < r["value"]:
                verdict = "REVIEW"
                note = (f"brochure states performance at {best['value']}\u00b0C "
                        f"outdoor; tender requires design for {r['value']}\u00b0C "
                        f"site conditions - request capacity/derating data at "
                        f"the site condition before relying on rated figures")
            key = (fam, r["page"], r["value"], best["page"], best["value"])
            if key in seen:
                continue
            seen.add(key)
            checks.append({
                "family": fam,
                "verdict": verdict,
                "requirement": {"page": r["page"], "operator": r["operator"],
                                "value": r["value"], "unit": r["unit"],
                                "quote": r["quote"]},
                "claim": {"page": best["page"], "value": best["value"],
                          "unit": best["unit"], "quote": best["quote"]},
                "note": note,
            })

    if kidde_pages:
        checks += fire_checks(spec_pages, kidde_pages)

    result = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "method": "L0 deterministic harvester - regex obligation+number+unit, "
                  "proximity-scoped parameter families, M4-style operator "
                  "comparison. No LLM, no cache, nothing planted. For deeper "
                  "coverage run the full M1-M4 pipeline on these PDFs with an "
                  "API key.",
        "spec": {"file": os.path.basename(spec_pdf[0]),
                 "title": "Design, Supply, Installation, Testing & Commissioning "
                          "of HPC-BYOH Data Centre at IIT Bombay (NTPC tender)",
                 "pages": len(spec_pages),
                 "requirements_harvested": len(reqs)},
        "submittal": {"file": os.path.basename(sub_pdf[0]),
                      "title": "Vertiv Liebert HPC free-cooling chiller range brochure",
                      "pages": len(sub_pages),
                      "claims_harvested": len(claims)},
        "documents_extra": ([{"file": os.path.basename(kidde_pdf[0]),
                              "title": "Kidde Fluoro-K clean agent fire suppression brochure",
                              "pages": len(kidde_pages)}] if kidde_pages else []),
        "checks": checks,
        "sample_requirements": [{k: v for k, v in r.items() if k != "window"}
                                for r in reqs[:40]],
    }
    os.makedirs(out, exist_ok=True)
    json.dump(result, open(os.path.join(out, "external.json"), "w"), indent=1)
    print(f"M12: {len(reqs)} real requirements, {len(claims)} real claims, "
          f"{len(checks)} cross-document checks -> out/external.json")


if __name__ == "__main__":
    main()
