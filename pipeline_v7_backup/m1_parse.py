#!/usr/bin/env python3
"""M1 - ingestion & parsing. Deterministic fast path, zero LLM.

Digital-native CSI-format specifications print clause identifiers in the
document body, so structure recovery is deterministic (cheaper, faster,
fully auditable). Documents that fail the structure confidence check can
be routed through LLM structuring with --allow-llm: same output schema,
clauses marked parse_mode="llm". That is the real-world path for messy
or non-CSI documents.

CONTAMINATION RULE: this pipeline reads ONLY rendered project documents.
It must never open project_bible.yaml, labels.json or curves_data.json -
those are evaluation ground truth for M9.
"""
import argparse
import glob
import json
import os
import re
import sys

import pypdf

CLAUSE_RE = re.compile(r"^(\d{2} \d{2} \d{2}) Part (\d+(?:\.\d+)*(?:\.[A-Z])?)\s+(.*)$")
ART_RE = re.compile(r"^\d\.\d+\s+[A-Za-z]")
PART_RE = re.compile(r"^PART \d - ")
FOOT_RE = re.compile(r"Page \d+ of \d+$")  # generic print footer
SPEC_NAME_RE = re.compile(r"^(?:spec_)?(\d{2})_(\d{2})_(\d{2})\.pdf$")

TRANSMITTAL_PATTERNS = [
    (r"^Reference Section:\s*(\d{2} \d{2} \d{2})", "reference_section"),
    (r"^Package ID:\s*(\S+)", "package_id"),
    (r"^Revision:\s*(R\d+)", "revision"),
    (r"^Reviewed Spec Revision:\s*(.+)$", "reviewed_spec_revision"),
    (r"^Date:\s*([\d-]+)", "date"),
]


def extract_pages(path):
    return [(p.extract_text() or "") for p in pypdf.PdfReader(path).pages]


def boilerplate_lines(pages):
    """Header/footer lines repeat verbatim across pages; detect them per
    document so any project's print furniture is skipped - no hardcoded
    project names, ever."""
    from collections import Counter
    cnt = Counter()
    for text in pages:
        for line in {raw.strip() for raw in text.split("\n") if raw.strip()}:
            cnt[line] += 1
    if len(pages) < 3:
        return set()
    thresh = max(3, len(pages) // 2 + 1)
    return {l for l, c in cnt.items() if c >= thresh and not CLAUSE_RE.match(l)}


def parse_spec_clauses(pages):
    boiler = boilerplate_lines(pages)
    clauses, cur = [], None
    for pageno, text in enumerate(pages, 1):
        for raw in text.split("\n"):
            line = raw.strip()
            if not line or FOOT_RE.search(line) or line in boiler:
                continue
            m = CLAUSE_RE.match(line)
            if m:
                cur = {
                    "clause_id": f"{m.group(1)} Part {m.group(2)}",
                    "page": pageno,
                    "text": m.group(3).strip(),
                }
                clauses.append(cur)
                continue
            if PART_RE.match(line) or ART_RE.match(line):
                cur = None
                continue
            if cur is not None:
                if cur["text"].endswith("-") and not cur["text"].endswith(" -") and (line[:1].islower() or line[:1].isdigit()):
                    cur["text"] += line  # rejoin PDF line-wrap hyphenation
                else:
                    cur["text"] += " " + line  # wrapped continuation line
    return clauses


def parse_transmittal(page1_text):
    fields = {}
    for pat, key in TRANSMITTAL_PATTERNS:
        m = re.search(pat, page1_text, re.MULTILINE)
        if m:
            fields[key] = m.group(1).strip()
    return fields


def llm_structure_pages(pages):
    """Real-world fallback: LLM converts unstructured spec pages to clause JSON."""
    from common import llm

    system = (
        "You convert construction specification pages into structured clauses. "
        'Output strict JSON only, as an object with the single key "clauses".'
    )
    clauses = []
    for pageno, text in enumerate(pages, 1):
        user = (
            f"Page {pageno} text:\n---\n{text}\n---\n"
            "Split this page into individual requirement clauses. Each clause object has "
            '"clause_id" (the identifier printed in the document - never invent numbering; '
            'use "" if none is printed) and "text" (the verbatim clause text). '
            'Return an object with the single key "clauses".'
        )
        content = llm.call(system, user)
        for c in json.loads(content).get("clauses", []):
            clauses.append({
                "clause_id": str(c.get("clause_id", "")),
                "page": pageno,
                "text": str(c.get("text", "")),
                "parse_mode": "llm",
            })
    return clauses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="path to corpus/rendered")
    ap.add_argument("--out", default="out")
    ap.add_argument("--allow-llm", action="store_true",
                    help="enable LLM structuring fallback for docs failing deterministic parse")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    banned = ["project_bible", "labels.json", "curves_data"]
    pdfs = sorted(glob.glob(os.path.join(args.corpus, "**", "*.pdf"), recursive=True))
    if not pdfs:
        sys.exit(f"no PDFs found in {args.corpus}")

    for path in pdfs:
        name = os.path.basename(path)
        if any(b in name for b in banned) or "_answer_key" in path:
            continue
        stem = name[:-4]
        pages = extract_pages(path)
        doc = {"doc": name, "pages": [{"page": i + 1, "text": t} for i, t in enumerate(pages)]}
        tm = parse_transmittal(pages[0])
        if tm.get("package_id"):
            doc["transmittal"] = tm
            stem = tm["package_id"]
        with open(os.path.join(args.out, f"doc_{stem}.json"), "w") as f:
            json.dump(doc, f, indent=1)

        m = SPEC_NAME_RE.match(name)
        if m:
            section = f"{m.group(1)} {m.group(2)} {m.group(3)}"
            clauses = parse_spec_clauses(pages)
            mode = "deterministic"
            if not clauses:
                if args.allow_llm:
                    clauses = llm_structure_pages(pages)
                    mode = "llm"
                else:
                    print(f"WARN {name}: 0 clauses parsed deterministically; "
                          f"rerun with --allow-llm to use LLM structuring", file=sys.stderr)
            spec_stem = section.replace(" ", "_")
            with open(os.path.join(args.out, f"spec_{spec_stem}.json"), "w") as f:
                json.dump({"section": section, "source_pdf": name,
                           "parse_mode": mode, "clauses": clauses}, f, indent=1)
            print(f"{name:30s} spec: {len(clauses)} clauses ({mode})")
        else:
            # Content-based spec detection: a document that carries clause
            # lines is a specification whatever its filename says.
            content_clauses = [] if doc.get("transmittal") else parse_spec_clauses(pages)
            section = None
            if len(content_clauses) >= 5:
                prefixes = [c["clause_id"][:8] for c in content_clauses
                            if re.match(r"^\d{2} \d{2} \d{2}", c["clause_id"])]
                if prefixes:
                    section = max(set(prefixes), key=prefixes.count)
            if section:
                spec_stem = section.replace(" ", "_")
                with open(os.path.join(args.out, f"spec_{spec_stem}.json"), "w") as f:
                    json.dump({"section": section, "source_pdf": name,
                               "parse_mode": "deterministic", "clauses": content_clauses}, f, indent=1)
                print(f"{name:30s} spec by content: {section}, {len(content_clauses)} clauses")
            else:
                extra = ""
                if doc.get("transmittal"):
                    extra = f"  transmittal: {doc['transmittal']}"
                print(f"{name:30s} {len(pages)} pages{extra}")


if __name__ == "__main__":
    main()
