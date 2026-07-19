"""CLAUSE AI server v4 - Python stdlib only, zero dependencies.

Run from the pipeline/ directory:  python3 app/server.py [port]

v4 architecture - EMPTY UNTIL FED:
  The server boots with no project. Every data endpoint returns 409
  until documents are uploaded from the hub and the REAL pipeline has
  run against them. Nothing the UI shows is pre-parsed or shipped:
  every artifact is rebuilt by runner.py from the uploaded documents.
  The only cache in the system is the LLM response cache (.cache/),
  keyed by sha256(model + prompt) - it saves API spend, never truth.

  POST /api/upload         - stage documents. Classified by CONTENT,
                             never by filename: specification /
                             submittal / addendum / register /
                             reference / project document.
                             Ground-truth files (bible, labels,
                             answer key) are refused - contamination
                             rule. Unrecognized CSV columns are an
                             honest error, not a guess.
  POST /api/run            - run the real pipeline (runner.py),
                             streaming to out/run.log
  GET  /api/run/log?offset - tail the run log + per-stage status
  GET  /api/project        - loaded / running / staged state
  POST /api/project/reset  - clear artifacts + staged documents
  GET/POST /api/llm/config - reads/writes pipeline/.env (the same
                             file the pipeline modules read); change
                             the model or key here and the next run
                             uses it - new model means cache misses
                             means real LLM calls that take real time
  POST /api/llm/test       - live round-trip test of that endpoint
"""
import base64
import csv
import datetime
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

PIPELINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(PIPELINE, "app", "static")
OUT = os.path.join(PIPELINE, "out")
WORKSPACE = os.path.join(PIPELINE, "workspace")
STAGE = os.path.join(WORKSPACE, "corpus")
ENV_PATH = os.path.join(PIPELINE, ".env")
MIME = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
        ".json": "application/json", ".svg": "image/svg+xml"}

STARTED_AT = datetime.datetime.now().isoformat(timespec="seconds")
ACTIVITY = deque(maxlen=200)
ACT_LOCK = threading.Lock()
RUN = {"proc": None}
GUIDES = {"LOCAL_LLM.md", "CORPUS_FORMAT.md", "README.md", "DESIGN_SPEC.md",
          "M7_M12_NOTES.md", "SCALABILITY.md"}

# Data endpoints that require a loaded project (top path segment).
GATED = {"summary", "graph", "queue", "paperwork", "cx", "node",
         "packages", "verdicts", "ncr", "supply", "ontology"}

# Ground truth is never read by the pipeline (contamination rule).
BANNED = ("project_bible", "labels.json", "curves_data", "answer_key", "violations_key", "evaluation.md")


# ------------------------------------------------------------------ .env
def read_env():
    vals = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def split_keys(raw):
    """Accept keys as a list, or a string separated by commas/newlines."""
    if isinstance(raw, list):
        return [str(k).strip() for k in raw if str(k).strip()]
    return [k.strip() for k in re.split(r"[,\s]+", str(raw or "")) if k.strip()]


def write_env(base_url, model, api_keys, workers=0):
    """api_keys: list of keys. The first is also written as DEEPSEEK_API_KEY
    for backward compatibility; the full pool goes to DEEPSEEK_API_KEYS and
    common/llm.py rotates over it (scale-out)."""
    lines = [
        "# CLAUSE LLM configuration - written by the Settings screen,",
        "# read directly by the pipeline modules (common/llm.py) and runner.py.",
        "# NEVER commit this file.",
        f"DEEPSEEK_BASE_URL={base_url}",
        f"DEEPSEEK_MODEL={model}",
    ]
    if api_keys:
        lines.append(f"DEEPSEEK_API_KEY={api_keys[0]}")
        lines.append("DEEPSEEK_API_KEYS=" + ",".join(api_keys))
    if workers:
        lines.append(f"CLAUSE_WORKERS={int(workers)}")
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


def env_keys(env):
    return split_keys(env.get("DEEPSEEK_API_KEYS", "")) or split_keys(env.get("DEEPSEEK_API_KEY", ""))


def llm_config(masked=True):
    env = read_env()
    out = {"base_url": env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
           "model": env.get("DEEPSEEK_MODEL", ""),
           "configured": bool(env.get("DEEPSEEK_MODEL")),
           "source": ".env"}
    keys = env_keys(env)
    out["keys_count"] = len(keys)
    try:
        out["workers"] = int(env.get("CLAUSE_WORKERS", "0") or 0)
    except ValueError:
        out["workers"] = 0
    if masked:
        out["api_keys_masked"] = [
            (k[:4] + "\u2026" + k[-4:]) if len(k) > 8 else "set" for k in keys]
        out["api_key_masked"] = out["api_keys_masked"][0] if keys else ""
    else:
        out["api_keys"] = keys
        out["api_key"] = keys[0] if keys else ""
    return out


def llm_test(cfg):
    base = (cfg.get("base_url") or "").rstrip("/")
    if not base:
        return {"ok": False, "error": "no base URL configured"}
    url = base + "/chat/completions"
    payload = {"model": cfg.get("model") or "",
               "messages": [{"role": "user",
                             "content": "Reply with exactly: CLAUSE-OK"}],
               "max_tokens": 10, "temperature": 0}
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())
        ms = round((time.perf_counter() - t0) * 1000)
        reply = ((body.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        return {"ok": True, "ms": ms, "model": body.get("model", cfg.get("model")),
                "reply": reply.strip()[:120]}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:  # timeouts, refused, DNS
        return {"ok": False, "error": str(e)[:200]}


# --------------------------------------------------------- text extraction
def extract_pages(path):
    """Return list of page texts. pypdf -> fitz -> pdftotext -> plain read."""
    if not path.lower().endswith(".pdf"):
        try:
            return [open(path, encoding="utf-8", errors="ignore").read()]
        except OSError:
            return []
    try:
        import pypdf
        return [(p.extract_text() or "") for p in pypdf.PdfReader(path).pages]
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(path)
        return [pg.get_text() for pg in doc]
    except Exception:
        pass
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.split("\f")
    except Exception:
        pass
    return []


# --------------------------------------------------------- classification
REGISTER_SCHEMAS = {
    "po_register.csv": {"po_number", "spec_section", "vendor", "value_inr", "order_date"},
    "schedule.csv": {"activity_id", "duration_days", "predecessors", "float_days"},
    "cx_test_register.csv": {"test_id", "spec_clause", "acceptance_criteria"},
    "rfi_log.csv": {"rfi_id", "query", "response"},
    "rfi_register.csv": {"rfi_id", "section", "question", "status"},
    "lifecycle_ledger.csv": {"equipment_tag", "po_number", "stage", "timestamp"},
    "effort_baseline.csv": {"task", "minutes_per_item", "items_per_project"},
}
CLAUSE_LINE_RE = re.compile(r"^\d{2} \d{2} \d{2} Part \d", re.M)
SEC_RE = re.compile(r"\b(\d{2}) (\d{2}) (\d{2})\b")
KIND_DIR = {"specification": "specs", "submittal": "submittals",
            "addendum": "addenda", "project document": "project_docs",
            "reference": "external"}


def classify_csv(text):
    try:
        hdr = next(csv.reader(io.StringIO(text)))
    except (StopIteration, csv.Error):
        return None
    cols = {h.strip().lower() for h in hdr}
    for canon, req in REGISTER_SCHEMAS.items():
        if req <= cols:
            return canon
    return None


def classify_text(head):
    first = "\n".join(head.strip().split("\n")[:12])
    # transmittal metadata may be rendered as table cells (no colon after the label)
    if re.search(r"Package\s*ID\b", head) and re.search(r"Reference\s*Section\b", head):
        return "submittal"
    if re.search(r"\bADDENDUM\b", first, re.I) or re.search(r"\bADD-\d{3}\b", first):
        return "addendum"
    if re.search(r"\bSUB-\d{6}-\d{2}(?:-R\d+)?\b", first):
        return "submittal"
    if len(CLAUSE_LINE_RE.findall(head)) >= 2 or re.search(r"\bSECTION\s+\d{2} \d{2} \d{2}\b", head, re.I):
        return "specification"
    return "project document"


def doc_text_head(name, ext, data):
    """(first-pages text, page count, has_any_text)"""
    if ext == ".pdf":
        tmpp = os.path.join("/tmp", "clause_up_" + re.sub(r"[^A-Za-z0-9._-]", "_", name))
        open(tmpp, "wb").write(data)
        try:
            pages = extract_pages(tmpp)
        finally:
            try:
                os.remove(tmpp)
            except OSError:
                pass
        return "\n\n".join(pages[:3]), len(pages), any(p.strip() for p in pages)
    text = data.decode("utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        text = re.sub(r"<(style|script)\b[^>]*>.*?</\1\s*>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    return text[:20000], 1, bool(text.strip())


def llm_map_csv(text, name):
    """Fallback for register CSVs whose headers do not match the canonical
    schemas. Real projects export these from Primavera P6, Procore, SAP or
    Excel with their own column names - so instead of refusing, ask the model
    to map the columns onto one canonical register and rewrite the header row.
    Cached like every other LLM call. Returns (canon, text, note)."""
    try:
        if PIPELINE not in sys.path:
            sys.path.insert(0, PIPELINE)
        from common import llm as _llm
        env = read_env()  # .env may have changed since import - refresh
        _llm.API_KEY = env.get("DEEPSEEK_API_KEY", _llm.API_KEY)
        _llm.MODEL = env.get("DEEPSEEK_MODEL", _llm.MODEL)
        _llm.BASE_URL = env.get("DEEPSEEK_BASE_URL", _llm.BASE_URL)
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 2:
            return None, text, "CSV has a header but no data rows"
        schemas = {k: sorted(v) for k, v in REGISTER_SCHEMAS.items()}
        system = ("You map construction-project CSV exports (Primavera P6, Procore, SAP, Excel) "
                  "onto canonical register schemas. Reply with JSON only, no prose: "
                  '{"register": "<schema file name or none>", '
                  '"column_map": {"<original header>": "<canonical column>"}}. '
                  "Map only when the meaning of a column is unambiguous.")
        user = ("Canonical schemas (register file name -> required columns):\n"
                + json.dumps(schemas) + "\n\nCSV file '" + name + "', header + first rows:\n"
                + "\n".join(",".join(r) for r in rows[:4]))
        raw = _llm.call(system, user).strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
        out = json.loads(raw)
        canon = str(out.get("register") or "").strip().lower()
        if canon and canon != "none" and not canon.endswith(".csv"):
            canon += ".csv"  # models sometimes drop the file extension
        cmap = {str(k).strip().lower(): str(v).strip().lower()
                for k, v in (out.get("column_map") or {}).items()}
        if canon not in REGISTER_SCHEMAS:
            return None, text, "columns do not correspond to any register schema (model checked)"
        hdr = [cmap.get(h.strip().lower(), h.strip().lower()) for h in rows[0]]
        if not set(REGISTER_SCHEMAS[canon]) <= set(hdr):
            return None, text, f"model mapped this to {canon} but required columns are still missing"
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(hdr)
        w.writerows(rows[1:])
        note = f"columns mapped onto {canon} by {_llm.MODEL} (cached)"
        return canon, buf.getvalue(), note
    except Exception as e:  # noqa: BLE001 - includes the no-API-key case
        return None, text, ("unrecognized CSV columns - see CORPUS_FORMAT.md for the four register "
                            "schemas, or add an API key in Settings and CLAUSE maps unfamiliar "
                            "export headers automatically (" + str(e)[:90] + ")")


def feed_kind(obj):
    """Classify a connector JSON payload by shape (deterministic, zero LLM)."""
    if not isinstance(obj, dict):
        return None
    rows = obj.get("results")
    if isinstance(rows, list) and rows and isinstance(rows[0], dict) and rows[0].get("displayId"):
        return "quality", "ACC issues export -> quality/ (issues join the object graph)"
    if any(isinstance(obj.get(k), list) for k in ("worklogEntries", "materialsEntries", "equipmentEntries")):
        return "field", "ACC daily-log export -> field/ (crew and equipment insights)"
    if isinstance(obj.get("bomLines"), list) or isinstance(obj.get("pmsClasses"), list):
        return "materials", "Hexagon Smart Materials BOM -> materials/ (PMS-class compliance checks)"
    if isinstance(obj.get("documents"), list) or isinstance(obj.get("transmittals"), list) or isinstance(obj.get("workflows"), list):
        return "documents", "Aconex-style document register -> documents/ (review-cycle insights)"
    if isinstance(obj.get("wbsElements"), list) or isinstance(obj.get("costLines"), list):
        return "finance", "SAP PS WBS/cost export -> finance/ (budget-pressure insights)"
    return None


TABLE_SYSTEMS = {
    "p6": {"project", "projwbs", "task", "taskpred", "rsrc", "taskrsrc", "calendar"},
    "sap": {"proj", "prps", "prhi", "aufk", "afvc", "resb", "coep", "ekko", "ekpo",
            "eket", "ekbe", "lfa1", "acdoca"},
    "aconex": {"document_register", "mail_module", "transmittal_registry", "workflow_history"},
    "acc": {"form_templates", "issues", "worklogentries", "materialsentries", "equipmententries"},
    "hexagon": {"bom_schema", "material_master", "pcf_repository", "pms_class"},
}


def table_wrap(name, obj):
    """Bare-list source-system table exports (P6/SAP/Aconex/ACC/Hexagon) ->
    canonical feed payloads the ontology stage understands. Deterministic."""
    stem = os.path.splitext(name)[0]
    low = stem.lower()
    rows = obj if isinstance(obj, list) else None
    if rows is None and isinstance(obj, dict):
        for k in ("rows", "records", "value", "items"):
            if isinstance(obj.get(k), list):
                rows = obj[k]
                break
    if not rows or not all(isinstance(r, dict) for r in rows[:5]):
        return None
    if low in ("worklogentries", "materialsentries", "equipmententries"):
        key = {"worklogentries": "worklogEntries", "materialsentries": "materialsEntries",
               "equipmententries": "equipmentEntries"}[low]
        return "field", {key: rows}, f"ACC {key} table -> field/ (crew and equipment insights)"
    if "issue" in low:
        rows = [dict(r, displayId=r.get("displayId") or r.get("issue_id") or r.get("id")) for r in rows]
        return "quality", {"results": rows}, "ACC issues table -> quality/ (issues join the object graph)"
    if "document_register" in low or low == "documents":
        return "documents", {"documents": rows}, "Aconex document register -> documents/ (review-cycle insights)"
    if "transmittal" in low:
        return "documents", {"transmittals": rows}, "Aconex transmittal registry -> documents/"
    if "workflow" in low:
        return "documents", {"workflows": rows}, "Aconex workflow history -> documents/"
    if "bom" in low:
        return "materials", {"bomLines": rows}, "Hexagon BOM table -> materials/ (PMS-class compliance checks)"
    if "pms" in low:
        return "materials", {"pmsClasses": rows}, "Hexagon PMS class table -> materials/"
    system = next((s for s, names in TABLE_SYSTEMS.items() if low in names), None)
    if system is None:
        cols = {c.lower() for r in rows[:5] for c in r.keys()}
        strong = {"task_code", "task_id", "posid", "objnr", "ebeln", "bom_id", "doc_id",
                  "equipment_tag", "po_number", "part_number", "supplier", "component"}
        if not cols & strong:
            return None
        system = "source"
    return "tables", {"table": stem, "system": system, "rows": rows}, \
        f"{system.upper()} table export ({len(rows)} rows) -> tables/ (joined into the object graph by S12)"


def _manual_hours():
    """Total manual coordination baseline (hours) from effort_baseline.csv."""
    p = os.path.join(STAGE, "registers", "effort_baseline.csv")
    if not os.path.exists(p):
        return None
    try:
        tot = 0.0
        for r in csv.DictReader(io.StringIO(open(p).read())):
            tot += float(r.get("minutes_per_item") or 0) * float(r.get("items_per_project") or 0)
        return round(tot / 60)
    except Exception:  # noqa: BLE001
        return None


def merge_po_csv(existing_text, incoming_text, prefer_incoming=False):
    """Merge two PO registers by digit-normalized po_number. Fills empty cells;
    prefer_incoming=True lets the new file win on conflicts."""
    import io
    ex_rd = csv.DictReader(io.StringIO(existing_text))
    cols = list(ex_rd.fieldnames or [])
    ex = list(ex_rd)
    inc_rd = csv.DictReader(io.StringIO(incoming_text))
    for c in (inc_rd.fieldnames or []):
        if c not in cols:
            cols.append(c)
    inc = list(inc_rd)

    def dig(r):
        return re.sub(r"\D", "", str(r.get("po_number") or ""))[-10:]

    by = {dig(r): dict(r) for r in ex}
    added = filled = 0
    for r in inc:
        k = dig(r)
        if k in by:
            tgt = by[k]
            for c, v in r.items():
                if v and (prefer_incoming or not (tgt.get(c) or "").strip()):
                    if (tgt.get(c) or "").strip() != str(v).strip():
                        filled += 1
                    tgt[c] = v
        else:
            by[k] = dict(r)
            added += 1
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in by.values():
        w.writerow(r)
    return buf.getvalue(), f"merged by PO number: {filled} cell(s) updated, {added} new PO(s)"


def stage_file(rel, name, data):
    """Classify one uploaded file by content and stage it. Returns a result row."""
    ext = os.path.splitext(name)[1].lower()
    low = (rel + " " + name).lower()
    segs = [p for p in rel.replace(os.sep, "/").lower().split("/")[:-1]]
    if any(b in low for b in BANNED) or any(g in segs for g in ("bible", "_answer_key", "answer_key", "ground_truth")):
        return {"name": name, "kind": "refused",
                "note": "evaluation ground truth - the pipeline never reads this (contamination rule)"}
    if ext == ".csv":
        text = data.decode("utf-8", errors="ignore")
        canon, note = classify_csv(text), None
        if not canon:
            canon, text, note = llm_map_csv(text, name)
        if not canon:
            return {"name": name, "kind": "error", "note": note}
        d = os.path.join(STAGE, "registers")
        os.makedirs(d, exist_ok=True)
        _cpath = os.path.join(d, canon)
        if canon == "po_register.csv" and os.path.exists(_cpath):
            text, _mn = merge_po_csv(open(_cpath).read(), text, prefer_incoming=True)
            note = (note or f"columns match {canon}") + "; " + _mn
        open(_cpath, "wb").write(text.encode("utf-8"))
        return {"name": name, "kind": "register", "note": note or f"columns match {canon}", "stored_as": f"registers/{canon}"}
    if ext == ".xml":
        # Primavera P6 connector: deterministic XML -> canonical schedule.csv, zero LLM
        if PIPELINE not in sys.path:
            sys.path.insert(0, PIPELINE)
        from connectors import p6xml
        if not p6xml.sniff(data):
            return {"name": name, "kind": "error",
                    "note": "XML, but not a recognizable Primavera P6 export (expected APIBusinessObjects / Project / Activity elements) - see CORPUS_FORMAT.md"}
        try:
            text, cnote = p6xml.convert(data)
        except Exception as e:  # noqa: BLE001
            return {"name": name, "kind": "error", "note": "P6 XML parse failed: " + str(e)[:120]}
        d = os.path.join(STAGE, "registers")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "schedule.csv"), "wb").write(text.encode("utf-8"))
        return {"name": name, "kind": "register",
                "note": "Primavera P6 XML -> schedule.csv - " + cnote,
                "stored_as": "registers/schedule.csv"}
    if ext == ".xer":
        # Primavera P6 native XER: deterministic parse -> canonical schedule.csv
        if PIPELINE not in sys.path:
            sys.path.insert(0, PIPELINE)
        from connectors import p6xer
        if not p6xer.sniff(data):
            return {"name": name, "kind": "error", "note": "XER, but no TASK table found - not a Primavera P6 export"}
        try:
            text, cnote = p6xer.convert(data)
        except Exception as e:  # noqa: BLE001
            return {"name": name, "kind": "error", "note": "P6 XER parse failed: " + str(e)[:120]}
        d = os.path.join(STAGE, "registers")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "schedule.csv"), "wb").write(text.encode("utf-8"))
        return {"name": name, "kind": "register",
                "note": "Primavera P6 XER -> schedule.csv - " + cnote,
                "stored_as": "registers/schedule.csv"}
    if ext == ".json":
        # SAP OData / logistics-visibility connectors: deterministic JSON -> registers
        if PIPELINE not in sys.path:
            sys.path.insert(0, PIPELINE)
        from connectors import logistics, sap_odata
        try:
            obj = json.loads(data.decode("utf-8", errors="ignore"))
        except ValueError:
            return {"name": name, "kind": "error", "note": "file is not valid JSON"}
        if sap_odata.sniff(obj):
            try:
                text, cnote = sap_odata.convert(obj)
            except Exception as e:  # noqa: BLE001
                return {"name": name, "kind": "error", "note": "SAP OData parse failed: " + str(e)[:120]}
            d = os.path.join(STAGE, "registers")
            os.makedirs(d, exist_ok=True)
            po_path = os.path.join(d, "po_register.csv")
            if os.path.exists(po_path):
                text, mnote = merge_po_csv(open(po_path).read(), text)
                cnote += "; " + mnote
            open(po_path, "wb").write(text.encode("utf-8"))
            return {"name": name, "kind": "register",
                    "note": "SAP OData purchase orders -> po_register.csv - " + cnote,
                    "stored_as": "registers/po_register.csv"}
        if logistics.sniff(obj):
            d = os.path.join(STAGE, "supply_chain")
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, name), "wb").write(data)
            note = "shipment-visibility feed -> supply_chain/ (drives the globe and the object graph)"
            po_path = os.path.join(STAGE, "registers", "po_register.csv")
            if os.path.exists(po_path):
                try:
                    merged, cnote = logistics.merge(open(po_path).read(), obj)
                    open(po_path, "w").write(merged)
                    note += "; merged into po_register.csv - " + cnote
                except Exception as e:  # noqa: BLE001
                    note += "; po_register merge skipped (" + str(e)[:80] + ")"
            else:
                note += "; po_register merge skipped (no PO register staged yet - upload it and re-upload this feed to patch delivery columns)"
            return {"name": name, "kind": "feed", "note": note, "stored_as": f"supply_chain/{name}"}
        fk = feed_kind(obj)
        if fk:
            folder, label = fk
            d = os.path.join(STAGE, folder)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, name), "wb").write(data)
            return {"name": name, "kind": "feed", "note": label, "stored_as": f"{folder}/{name}"}
        tw = table_wrap(name, obj)
        if tw:
            folder, payload, label = tw
            d = os.path.join(STAGE, folder)
            os.makedirs(d, exist_ok=True)
            fname = os.path.splitext(name)[0] + ".json"
            open(os.path.join(d, fname), "w").write(json.dumps(payload, indent=1))
            return {"name": name, "kind": "feed", "note": label, "stored_as": f"{folder}/{fname}"}
        return {"name": name, "kind": "error",
                "note": "JSON, but not a recognizable connector payload (SAP OData POs, shipment visibility, ACC issues or daily logs, Aconex document register, Hexagon BOM, SAP PS finance) - see CORPUS_FORMAT.md"}
    if ext not in (".pdf", ".html", ".htm", ".txt", ".md"):
        return {"name": name, "kind": "skipped", "note": "not a project document type (pdf/html/csv/xml/json/txt/md)"}
    # anything the user files under external/ is third-party reference
    if "external/" in rel.replace(os.sep, "/").lower():
        d = os.path.join(STAGE, "external")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, name), "wb").write(data)
        return {"name": name, "kind": "reference", "note": "third-party reference - kept on file, not analysed", "stored_as": f"external/{name}"}
    head, npages, has_text = doc_text_head(name, ext, data)
    if not has_text:
        return {"name": name, "kind": "error",
                "note": "no extractable text (image-only PDF) - needs OCR; see roadmap"}
    kind = classify_text(head) if ext in (".pdf", ".html", ".htm") else "project document"
    save_name = name
    if kind == "specification" and ext in (".html", ".htm"):
        # canonical name so the M10 lint can find raw spec text
        secs = SEC_RE.findall(head)
        if secs:
            a, b, c = max(set(secs), key=secs.count)
            save_name = f"spec_{a}_{b}_{c}.html"
    d = os.path.join(STAGE, KIND_DIR[kind])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, save_name), "wb").write(data)
    note = f"{npages} page(s)" if ext == ".pdf" else "raw text"
    return {"name": name, "kind": kind, "note": note,
            "stored_as": f"{KIND_DIR[kind]}/{save_name}"}


# -------------------------------------------------------------- run state
def run_running():
    return RUN["proc"] is not None and RUN["proc"].poll() is None


def clear_out():
    for p in glob.glob(os.path.join(OUT, "*.json")):
        os.remove(p)
    for sub in ("post", "paperwork", "external", "uploads"):
        shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
    for extra in ("ncr_register.csv", "run.log", "run_status.json"):
        try:
            os.remove(os.path.join(OUT, extra))
        except OSError:
            pass


CATALOG_SYSTEMS = {
    "documents": ("Contract documents", "Specifications, vendor submittals and client addenda - the compliance core the rulebook is built from."),
    "registers": ("Project registers (CSV)", "The canonical flat files CLAUSE computes on. Every connector below ultimately lands here or in the object graph."),
    "tables": ("Source-system tables", "Raw ERP/field-system exports staged with this project - each becomes a dataset object in the graph."),
    "p6": ("Oracle Primavera P6", "The planner's scheduling system. The activity network decides when every purchase must arrive - and how much float protects it."),
    "sap": ("SAP ERP (PO + PS modules)", "The money system: purchase orders, WBS cost structure, reservations and actual postings."),
    "acc": ("Autodesk Construction Cloud", "The field system: daily work logs, manpower, and quality issues pinned to model elements."),
    "aconex": ("Oracle Aconex", "Document control: the register of record, transmittals, review workflows and correspondence."),
    "hexagon": ("Hexagon Smart Materials", "Engineering materials: BOMs, piping classes, component files and the material catalogue."),
    "logistics": ("Shipment visibility (FourKites-style)", "Live GPS/AIS tracking of purchased equipment moving from vendor works to site - drives the globe."),
}
CATALOG_TABLES = {
    "task": ("p6", "Every schedule activity with dates, durations and percent complete.", "Activity names carry PO numbers; the supply stage joins each purchase order to the activity that needs it - need-by dates come from here."),
    "taskpred": ("p6", "The logic links between activities (finish-to-start and friends).", "Feeds the CPM float calculation - float is what decides whether a late delivery is an emergency or a shrug."),
    "taskrsrc": ("p6", "Resource assignments: which crew works which activity.", "Connects resources to activities in the object graph."),
    "rsrc": ("p6", "The resource pool: crews, cranes, engineers.", "Gives assignments their names."),
    "project": ("p6", "Project header: id and data date of this schedule update.", "Confirms which update of the schedule you are looking at."),
    "projwbs": ("p6", "The work-breakdown tree the schedule hangs from.", "Places every activity in the WBS."),
    "po_odata": ("sap", "Purchase orders exactly as SAP serves them (EBELN, BEDAT, EINDT, LIFNR...).", "Normalized into po_register.csv and merged field-by-field - one PO truth, richer columns never wiped."),
    "proj": ("sap", "SAP PS project definition.", "Anchors the cost side of the ontology."),
    "prps": ("sap", "WBS elements with budget structure.", "Money rolls up the WBS in the graph."),
    "prhi": ("sap", "WBS hierarchy pointers.", "Glues the WBS rows into a tree."),
    "aufk": ("sap", "Orders (networks) for execution work.", "Ties factory and site work to cost objects."),
    "afvc": ("sap", "Network activities / operations.", "SAP's view of the work, cross-checkable against P6."),
    "resb": ("sap", "Material reservations per order.", "Which materials each work order will consume."),
    "coep": ("sap", "Cost line items - actual postings.", "Actual money spent, attached to cost objects."),
    "issues": ("acc", "Quality issues pinned to model elements, with root-cause categories.", "Open issues attach to equipment and sections, and block certification readiness until closed."),
    "worklogentries": ("acc", "Daily work logs: trade, headcount, hours.", "Field reality - trades become graph objects with real hours."),
    "materialsentries": ("acc", "Materials received and consumed on site.", "Site-side material movements."),
    "equipmententries": ("acc", "Plant and equipment hours on site.", "What machinery worked and for how long."),
    "form_templates": ("acc", "The site form definitions (daily log, inspections...).", "Context for how field data was captured."),
    "document_register": ("aconex", "The controlled document register - the record of what officially exists.", "Documents join the graph, linked to their spec sections and packages."),
    "transmittal_registry": ("aconex", "Who sent what to whom, and when.", "Proves submission dates on the compliance timeline."),
    "workflow_history": ("aconex", "Review workflows: ball-in-court, due dates, status.", "Overdue reviews raise insights on the affected documents."),
    "mail_module": ("aconex", "Project correspondence threads.", "Searchable context for the copilot."),
    "bom_schema": ("hexagon", "Bill of materials: part numbers, line numbers, cut lengths.", "Materials trace from BOM line to PO to site."),
    "pms_class": ("hexagon", "Piping material specification classes.", "The engineering rules behind every pipe spec."),
    "pcf_repository": ("hexagon", "Piping component files (isometric interchange).", "Geometry-level piping data."),
    "material_master": ("hexagon", "The material catalogue.", "Canonical identities behind BOM rows."),
    "po_register": ("registers", "The canonical purchase-order register.", "The spine of supply-chain risk: value, lead time, status, live location per PO."),
    "schedule": ("registers", "The canonical activity register (from CSV, P6 XML or native XER).", "Need-by dates and float for the PO join - the supply stage runs on this."),
    "rfi_register": ("registers", "Requests for information.", "RFIs join the graph against their spec sections."),
    "rfi_log": ("registers", "Requests for information.", "RFIs join the graph against their spec sections."),
    "cx_test_register": ("registers", "Commissioning tests L1-L5 with acceptance criteria.", "Readiness packs build from this; coverage gaps surface in certification evidence."),
    "effort_baseline": ("registers", "Minutes-per-task baselines for manual document review.", "Powers the manual-review-hours number on the scoreboard - impact in hours, not percentages."),
    "lifecycle_ledger": ("registers", "Equipment lifecycle stamps: ordered, FAT, shipped, delivered, installed.", "Each equipment object carries its lifecycle trail through the supply chain."),
    "tier2_dependencies": ("registers", "Sub-supplier dependencies beneath the main vendors.", "Tier-2 risk: a component delay propagates up to the parent PO."),
}


def build_catalog():
    """Everything staged with this project: which system it came from, what is
    inside, and what CLAUSE does with it. Powers the Data tab."""
    if not os.path.isdir(STAGE):
        return {"systems": []}
    systems = {}

    def add(sysid, item):
        nm, blurb = CATALOG_SYSTEMS.get(sysid, (sysid, "Source-system exports staged with this project."))
        g = systems.setdefault(sysid, {"id": sysid, "name": nm, "blurb": blurb, "items": []})
        g["items"].append(item)

    for path in sorted(glob.glob(os.path.join(STAGE, "**", "*.*"), recursive=True)):
        rel = os.path.relpath(path, STAGE).replace(os.sep, "/")
        top = rel.split("/")[0]
        if top in ("specs", "submittals", "addenda", "project_docs", "external"):
            continue
        name = os.path.basename(path)
        stem, ext = os.path.splitext(name)[0].lower(), os.path.splitext(name)[1].lower()
        count, fields = "", ""
        try:
            if ext == ".json":
                dd = json.load(open(path))
                rows = dd.get("rows") if isinstance(dd, dict) else (dd if isinstance(dd, list) else None)
                if rows is None and isinstance(dd, dict):
                    for v in dd.values():
                        if isinstance(v, list):
                            rows = v
                            break
                        if isinstance(v, dict) and isinstance(v.get("results"), list):
                            rows = v["results"]
                            break
                if isinstance(rows, list):
                    count = "%d rows" % len(rows)
                    if rows and isinstance(rows[0], dict):
                        fields = "fields: " + ", ".join(sorted(rows[0].keys())[:12])
            elif ext == ".csv":
                rdr = list(csv.reader(open(path)))
                count = "%d rows" % max(len(rdr) - 1, 0)
                if rdr:
                    fields = "columns: " + ", ".join(rdr[0][:12])
        except Exception:  # noqa: BLE001
            pass
        info = CATALOG_TABLES.get(stem)
        if not info and "shipment" in stem:
            info = ("logistics", "Live shipment tracking: position updates, ETAs, exception codes.",
                    "Patches delivery status, location and ETA onto matching POs; position trails draw on the globe.")
        if info:
            add(info[0], {"file": rel, "count": count, "what": info[1], "use": info[2], "fields": fields})
        else:
            add(top, {"file": rel, "count": count, "what": "Source-system table export.",
                      "use": "Folded into the ontology as a dataset object; rows link to the POs, packages and activities they reference.",
                      "fields": fields})
    for folder, what, use in (
            ("specs", "Contract specifications (CSI-numbered); the PDF is the record.", "Parsed clause by clause into the checkable rulebook (S1-S2)."),
            ("submittals", "Vendor submittal packages: datasheets, ITPs, drawings.", "Vendor claims are extracted and each one verified against the rulebook (S3-S5)."),
            ("addenda", "Client addenda amending the specs after award.", "Applied in date order; every affected check is re-verdicted (S6)."),
            ("project_docs", "Minutes, reports, correspondence.", "Parsed and indexed as context for the copilot.")):
        fdir = os.path.join(STAGE, folder)
        if os.path.isdir(fdir):
            n = len([f for f in os.listdir(fdir) if os.path.isfile(os.path.join(fdir, f))])
            if n:
                add("documents", {"file": folder + "/", "count": "%d file(s)" % n, "what": what, "use": use, "fields": ""})
    order = ["documents", "registers", "p6", "sap", "acc", "aconex", "hexagon", "logistics"]
    return {"systems": sorted(systems.values(), key=lambda g: order.index(g["id"]) if g["id"] in order else 99)}


def score_answer_key(key):
    """EVAL ONLY - compare the finished ledger against an answer key the user
    explicitly uploads AFTER a run. Never read by any pipeline stage."""
    items = key if isinstance(key, list) else None
    if items is None and isinstance(key, dict):
        for k in ("planted", "planted_errors", "items", "checks", "labels", "deviations", "violations"):
            if isinstance(key.get(k), list):
                items = key[k]
                break
        if items is None:
            items = [e for v in key.values() if isinstance(v, list)
                     for e in v if isinstance(e, dict)]
    rows = []
    for p in glob.glob(os.path.join(OUT, "verdicts_*.json")):
        v = json.load(open(p))
        for r in v.get("results", []):
            rows.append({"package": v.get("package", ""), "section": v.get("section", ""), **r})
    if not rows:
        raise ValueError("no verdicts in the current run - run the pipeline first")

    def toks(s):
        return set(re.findall(r"[a-z0-9.]+", str(s or "").lower()))

    def row_text(r):
        req = r.get("requirement") or {}
        return " ".join(str(x) for x in (r.get("rule_id"), r.get("parameter"),
                                          req.get("quote"), r.get("reason"), r.get("section")))

    CAUGHT, FLAGGED = {"DEVIATION"}, {"NEEDS_REVIEW", "MISSING_EVIDENCE"}
    tally = {"planted": 0, "caught": 0, "flagged": 0, "missed": 0}
    detail = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        expected = str(it.get("expected_verdict") or it.get("verdict_pre_addendum")
                       or it.get("verdict") or it.get("expected") or "").upper()
        if expected in ("", "COMPLY", "COMPLIANT"):
            continue
        tally["planted"] += 1
        want = toks(it.get("spec_clause")) | toks(it.get("parameter")) | \
               toks(it.get("clause")) | toks(it.get("description")) | toks(it.get("explanation"))
        best, bs = None, 0
        for r in rows:
            sc = len(want & toks(row_text(r)))
            if sc > bs:
                best, bs = r, sc
        got = (best or {}).get("verdict", "")
        cls = ("caught" if got in CAUGHT else "flagged" if got in FLAGGED else "missed") \
              if best is not None and bs >= 2 else "missed"
        tally[cls] += 1
        detail.append({"id": it.get("check_id") or it.get("id") or it.get("parameter") or "?",
                       "expected": expected, "result": cls,
                       "matched_rule": (best or {}).get("rule_id") if bs >= 2 else None,
                       "pipeline_verdict": got if bs >= 2 else None,
                       "package": (best or {}).get("package") if bs >= 2 else None})
    tally["found"] = tally["caught"] + tally["flagged"]
    return {"tally": tally, "detail": detail,
            "note": "approximate text matcher - scored after the run, never an input to it"}


def start_run():
    if run_running():
        return False, "a run is already in progress"
    if not os.path.isdir(STAGE) or not any(os.scandir(STAGE)):
        return False, "nothing staged - upload documents first"
    clear_out()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "wb")
    RUN["proc"] = subprocess.Popen(
        [sys.executable, "-u", "runner.py", "--corpus", STAGE, "--out", "out"],
        cwd=PIPELINE, stdout=logf, stderr=subprocess.STDOUT)
    return True, ""


def staged_state():
    staged, files = {}, []
    if os.path.isdir(STAGE):
        for root, _, fns in os.walk(STAGE):
            for fn in fns:
                rel = os.path.relpath(os.path.join(root, fn), STAGE).replace(os.sep, "/")
                staged[rel.split("/")[0]] = staged.get(rel.split("/")[0], 0) + 1
                files.append(rel)
    return staged, sorted(files)


def project_state():
    pj = os.path.join(OUT, "project.json")
    loaded = json.load(open(pj)) if os.path.exists(pj) else None
    staged, files = staged_state()
    env = read_env()
    return {"loaded": bool(loaded),
            "loaded_at": (loaded or {}).get("loaded_at"),
            "failed_stages": (loaded or {}).get("failed_stages", []),
            "running": run_running(),
            "staged": staged, "staged_files": files, "staged_total": len(files),
            "model": env.get("DEEPSEEK_MODEL", ""),
            "has_key": bool(env.get("DEEPSEEK_API_KEY"))}


# ------------------------------------------------------------------ data
def load(path):
    p = os.path.join(OUT, path)
    return json.load(open(p)) if os.path.exists(p) else None


def summary():
    def verdict_counts(sub):
        counts, fc = {}, 0
        for p in glob.glob(os.path.join(OUT, sub, "verdicts_*.json")):
            v = json.load(open(p))
            for r in v["results"]:
                counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
                fc += "false_comply" in r["flags"]
        return counts, fc
    pre, fc_pre = verdict_counts("")
    post, fc_post = verdict_counts("post")
    rules = sum(len(json.load(open(p))["rules"])
                for p in glob.glob(os.path.join(OUT, "rulebook_*.json")))
    claims = sum(len(json.load(open(p))["claims"])
                 for p in glob.glob(os.path.join(OUT, "claims_*.json")))
    lint = load("lint.json") or {"findings": []}
    onto = load("ontology.json") or {}
    types = {t.get("type"): t.get("count") for t in (onto.get("types") or [])}
    totals = (onto.get("project") or {}).get("totals") or {}
    staged, _ = staged_state()
    env = read_env()
    return {
        "rules": rules, "claims": claims,
        "sections": len(glob.glob(os.path.join(OUT, "rulebook_*.json"))),
        "packages": len(glob.glob(os.path.join(OUT, "claims_*.json"))),
        "manual_hours_baseline": _manual_hours(),
        "verdicts_pre": pre, "verdicts_post": post,
        "false_comply_pre": fc_pre, "false_comply_post": fc_post,
        "lint_findings": len(lint["findings"]),
        "graph_nodes": totals.get("objects", 0), "graph_edges": totals.get("links", 0),
        "node_types": types,
        "money": {"procurement_value_inr": totals.get("procurement_value_inr", 0),
                  "value_at_risk_inr": totals.get("value_at_risk_inr", 0)},
        "cert": onto.get("cert"),
        "corpus_files": sum(staged.values()),
        "staged": staged,
        "model": env.get("DEEPSEEK_MODEL", ""),
        "ncrs": len((load("dispositions.json") or {}).get("queue", [])),
    }


# --------------------------------------------------------------- dossier
def node_dossier(nid):
    """Everything the ledger knows about one graph node."""
    g = load("graph.json") or {"nodes": [], "edges": []}
    node = next((n for n in g["nodes"] if n["id"] == nid), None)
    if not node:
        return {"error": "unknown node", "id": nid}
    d = {"id": nid, "type": node["type"], "label": node["label"],
         "status": node.get("status"), "meta": node.get("meta", {})}
    neigh = []
    for e in g["edges"]:
        other = e["t"] if e["s"] == nid else (e["s"] if e["t"] == nid else None)
        if other:
            on = next((n for n in g["nodes"] if n["id"] == other), None)
            if on:
                neigh.append({"id": other, "type": on["type"], "label": on["label"],
                              "status": on.get("status"), "edge": e["type"]})
    d["neighbors"] = neigh[:40]
    d["degree"] = len(neigh)

    if nid.startswith("cl:"):
        body = nid[3:]
        sec = body.split(" Part ")[0]
        clause = body.split(" Part ", 1)[1] if " Part " in body else ""
        d["section"], d["clause"] = sec, clause
        checks = []
        for p in glob.glob(os.path.join(OUT, "post", "verdicts_*.json")):
            pkg = os.path.basename(p)[9:-5]
            for r in json.load(open(p))["results"]:
                sc = (r.get("requirement") or {}).get("source_clause", "") or ""
                if clause and clause in sc:
                    checks.append({"package": pkg, "verdict": r["verdict"],
                                   "parameter": r.get("parameter"),
                                   "flags": r.get("flags", []),
                                   "reason": r.get("reason"),
                                   "requirement": r.get("requirement"),
                                   "claim": r.get("governing_claim")})
        order = {"DEVIATION": 0, "NEEDS_REVIEW": 1, "COMPLY": 2,
                 "MISSING_EVIDENCE": 3, "NOT_ADDRESSED": 4}
        checks.sort(key=lambda c: order.get(c["verdict"], 5))
        d["checks"] = checks[:8]
        cxp = load("cx_packs.json") or {"tests": []}
        d["cx_tests"] = [t for t in cxp["tests"]
                         if body in (t.get("clause") or t.get("verifies_rule") or "")][:5]
        d["pos"] = [n for n in g["nodes"] if n["type"] == "po"
                    and n["meta"].get("section") == sec][:10]

    elif nid.startswith("pkg:"):
        pkg = nid[4:]
        disp = load("dispositions.json") or {"queue": []}
        item = next((i for i in disp["queue"] if i.get("package") == pkg), None)
        if item:
            d["severity"] = item.get("severity_score")
            d["vendor"] = item.get("vendor")
            d["ncrs"] = (item.get("items") or [])[:6]
        letter = f"letter_{pkg}.md"
        if os.path.exists(os.path.join(OUT, "paperwork", letter)):
            d["letter"] = letter

    elif nid.startswith("po:"):
        wave = load("blast_wave.json") or {}
        for p in wave.get("pos_invalidated", []):
            if p.get("po_number") == node["label"]:
                d["invalidation"] = p

    elif nid.startswith("cx:"):
        cxp = load("cx_packs.json") or {"tests": []}
        t = next((t for t in cxp["tests"] if t.get("test_id") == node["label"]), None)
        if t:
            d["test"] = t

    elif nid.startswith("sec:"):
        sec = nid[4:]
        rb = load(f"rulebook_{sec.replace(' ', '_')}.json") or {"rules": []}
        d["rule_count"] = len(rb["rules"])
        lint = load("lint.json") or {"findings": []}
        d["lint"] = [f for f in lint["findings"] if sec in json.dumps(f)][:5]

    elif nid.startswith("add:"):
        wave = load("blast_wave.json") or {}
        d["wave"] = wave.get("summary")
        for w in wave.get("waves", []):
            if w.get("addendum") == node["label"]:
                d["wave"] = w.get("summary")

    return d


# ---------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if not ctype.startswith("application/json"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)
        p = self.path.split("?")[0]
        if p.startswith("/api/") and p not in ("/api/activity", "/api/run/log", "/api/project"):
            with ACT_LOCK:
                ACTIVITY.append({
                    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                    "method": self.command, "path": self.path[:80], "status": code,
                    "ms": round((time.perf_counter() - self._t0) * 1000, 1),
                    "bytes": len(data),
                })

    def log_message(self, *a):
        pass

    def _query(self):
        q = parse_qs(urlparse(self.path).query)
        return {k: unquote(v[0]) for k, v in q.items()}

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n == 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode())
        except ValueError:
            return {}

    def do_GET(self):
        self._t0 = time.perf_counter()
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            return self.api(path)
        if path == "/":
            path = "/index.html"
        full = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if full.startswith(STATIC) and os.path.isfile(full):
            ext = os.path.splitext(full)[1]
            return self._send(200, open(full, "rb").read(), MIME.get(ext, "text/plain"))
        self._send(404, {"error": "not found"})

    def api(self, path):
        parts = path.strip("/").split("/")[1:]
        q = self._query()
        if parts and parts[0] in GATED and not os.path.exists(os.path.join(OUT, "project.json")):
            return self._send(409, {"error": "no_project",
                                    "hint": "upload your project documents from the hub and run the pipeline"})
        simple = {
            ("summary",): summary,
            ("graph",): lambda: load("graph.json") or {"nodes": [], "edges": []},
            ("queue",): lambda: load("dispositions.json") or {"queue": []},
            ("paperwork",): lambda: load("paperwork_index.json") or {"documents": []},
            ("cx",): lambda: load("cx_packs.json") or {"tests": []},
            ("supply",): lambda: load("supply_risk.json") or {},
            ("ontology",): lambda: load("ontology.json") or {"objects": [], "links": []},
            ("project",): project_state,
            ("catalog",): build_catalog,
        }
        key = tuple(parts)
        if key in simple:
            return self._send(200, simple[key]())
        if parts == ["activity"]:
            with ACT_LOCK:
                return self._send(200, {"events": list(ACTIVITY)[-60:]})
        if parts == ["run", "log"]:
            off = int(q.get("offset", "0") or 0)
            p = os.path.join(OUT, "run.log")
            text, size = "", 0
            if os.path.exists(p):
                size = os.path.getsize(p)
                if off < size:
                    with open(p, "rb") as fh:
                        fh.seek(off)
                        text = fh.read().decode("utf-8", errors="ignore")
            return self._send(200, {"text": text, "offset": max(size, off),
                                    "status": load("run_status.json"),
                                    "running": run_running()})
        if parts == ["meta"]:
            arts = {}
            for p in glob.glob(os.path.join(OUT, "*.json")):
                arts[os.path.basename(p)] = datetime.datetime.fromtimestamp(
                    os.path.getmtime(p)).isoformat(timespec="seconds")
            staged, _ = staged_state()
            return self._send(200, {
                "python": sys.version.split()[0],
                "server_started": STARTED_AT,
                "now": datetime.datetime.now().isoformat(timespec="seconds"),
                "today": datetime.date.today().isoformat(),
                "artifacts": arts,
                "corpus_files": sum(staged.values()),
            })
        if parts == ["node"]:
            return self._send(200, node_dossier(q.get("id", "")))
        if parts == ["guide"]:
            fn = os.path.basename(q.get("f", ""))
            full = os.path.join(PIPELINE, fn)
            if fn in GUIDES and os.path.isfile(full):
                return self._send(200, {"file": fn, "markdown": open(full).read()})
            return self._send(404, {"error": "no such guide"})
        if parts == ["llm", "config"]:
            return self._send(200, llm_config())
        if parts == ["paperwork", "doc"]:
            fn = os.path.basename(q.get("f", ""))
            full = os.path.join(OUT, "paperwork", fn)
            if fn.endswith(".md") and os.path.isfile(full):
                return self._send(200, {"file": fn, "markdown": open(full).read()})
            return self._send(404, {"error": "no such document"})
        if parts == ["packages"]:
            pkgs = sorted(os.path.basename(p)[9:-5]
                          for p in glob.glob(os.path.join(OUT, "verdicts_*.json")))
            return self._send(200, {"packages": pkgs})
        if parts[0] == "verdicts" and len(parts) == 2:
            sub = "post" if q.get("mode") == "post" else ""
            return self._send(200, load(os.path.join(sub, f"verdicts_{parts[1]}.json")) or {})
        if parts == ["ncr"]:
            p = os.path.join(OUT, "ncr_register.csv")
            rows = list(csv.DictReader(open(p))) if os.path.exists(p) else []
            return self._send(200, {"ncrs": rows})
        self._send(404, {"error": "unknown endpoint"})

    def do_POST(self):
        self._t0 = time.perf_counter()
        path = self.path.split("?")[0]
        if path == "/api/upload":
            body = self._body()
            results = []
            for f in (body.get("files") or [])[:400]:
                rel = f.get("relpath") or f.get("name") or "upload"
                name = re.sub(r"[^A-Za-z0-9._ -]", "_", os.path.basename(rel))[:120]
                try:
                    data = base64.b64decode(f.get("b64", ""))
                except Exception:
                    results.append({"name": name, "kind": "error", "note": "could not decode file data"})
                    continue
                try:
                    results.append(stage_file(rel, name, data))
                except Exception as e:  # noqa: BLE001 - report, never crash the batch
                    results.append({"name": name, "kind": "error", "note": str(e)[:160]})
            staged, _ = staged_state()
            return self._send(200, {"results": results, "staged": staged,
                                    "staged_total": sum(staged.values())})
        if path == "/api/score":
            body = self._body()
            try:
                return self._send(200, score_answer_key(body))
            except Exception as e:  # noqa: BLE001
                return self._send(400, {"error": str(e)[:300]})
        if path in ("/api/run", "/api/recompute"):
            ok, err = start_run()
            return self._send(200 if ok else 409, {"ok": ok, "error": err or None})
        if path == "/api/project/reset":
            if run_running():
                RUN["proc"].terminate()
                RUN["proc"] = None
            clear_out()
            shutil.rmtree(WORKSPACE, ignore_errors=True)
            return self._send(200, {"ok": True})
        if path == "/api/llm/config":
            body = self._body()
            cur = llm_config(masked=False)
            base = (body.get("base_url") or cur["base_url"]).strip()
            model = (body.get("model") or cur["model"]).strip()
            if body.get("api_keys") is not None:
                keys = split_keys(body.get("api_keys"))
            elif body.get("api_key"):
                keys = split_keys(body.get("api_key"))
            else:
                keys = cur.get("api_keys") or []
            workers = body.get("workers", cur.get("workers", 0))
            try:
                workers = max(0, min(64, int(workers or 0)))
            except (TypeError, ValueError):
                workers = 0
            write_env(base, model, keys, workers)
            return self._send(200, llm_config())
        if path == "/api/llm/test":
            body = self._body()
            cfg = llm_config(masked=False)
            for k in ("base_url", "model", "api_key"):
                if body.get(k):
                    cfg[k] = body[k]
            return self._send(200, llm_test(cfg))
        if path in ("/api/agent", "/api/agent/stream"):
            if not os.path.exists(os.path.join(OUT, "project.json")):
                return self._send(409, {"error": "no_project",
                                        "hint": "upload documents and run the pipeline first - the copilot only speaks about a loaded project"})
            body = self._body()
            env = read_env()
            keys = env_keys(env)
            cfg = {"base_url": env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                   "model": env.get("DEEPSEEK_MODEL", "deepseek-chat"),
                   "api_key": keys[0] if keys else ""}
            import agent as _agent
            if path == "/api/agent/stream":
                # NDJSON stream: one JSON object per line, flushed per event, so
                # the UI can relay every tool call live (server stays HTTP/1.0 -
                # the closed connection marks the end of the stream).
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                def _emit(ev):
                    self.wfile.write((json.dumps(ev) + "\n").encode())
                    self.wfile.flush()

                try:
                    res = _agent.run_agent(str(body.get("message", ""))[:2000],
                                           body.get("history"), cfg, emit=_emit,
                                           page=str(body.get("page") or "")[:40])
                    _emit({"event": "reply", **res})
                except _agent.AgentError as e:
                    try:
                        _emit({"event": "error", "error": str(e)})
                    except Exception:  # noqa: BLE001 - client went away
                        pass
                except Exception as e:  # noqa: BLE001
                    try:
                        _emit({"event": "error", "error": "copilot error: " + str(e)[:240]})
                    except Exception:  # noqa: BLE001
                        pass
                return
            try:
                res = _agent.run_agent(str(body.get("message", ""))[:2000], body.get("history"), cfg,
                                       page=str(body.get("page") or "")[:40])
                return self._send(200, res)
            except _agent.AgentError as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:  # noqa: BLE001
                return self._send(500, {"error": "copilot error: " + str(e)[:240]})
        self._send(404, {"error": "unknown endpoint"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8020
    staged, _ = staged_state()
    loaded = os.path.exists(os.path.join(OUT, "project.json"))
    print(f"CLAUSE AI serving on http://localhost:{port} "
          f"(project loaded: {loaded}, staged files: {sum(staged.values())}, Ctrl-C to stop)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
