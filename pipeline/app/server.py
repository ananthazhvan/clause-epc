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
          "M7_M12_NOTES.md"}

# Data endpoints that require a loaded project (top path segment).
GATED = {"summary", "graph", "blastwave", "queue", "options", "margins",
         "vendors", "lint", "paperwork", "cx", "external", "node",
         "packages", "verdicts", "ncr"}

# Ground truth is never read by the pipeline (contamination rule).
BANNED = ("project_bible", "labels.json", "curves_data", "answer_key")


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


def write_env(base_url, model, api_key):
    lines = [
        "# CLAUSE LLM configuration - written by the Settings screen,",
        "# read directly by the pipeline modules (common/llm.py) and runner.py.",
        "# NEVER commit this file.",
        f"DEEPSEEK_BASE_URL={base_url}",
        f"DEEPSEEK_MODEL={model}",
    ]
    if api_key:
        lines.append(f"DEEPSEEK_API_KEY={api_key}")
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


def llm_config(masked=True):
    env = read_env()
    out = {"base_url": env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
           "model": env.get("DEEPSEEK_MODEL", ""),
           "configured": bool(env.get("DEEPSEEK_MODEL")),
           "source": ".env"}
    key = env.get("DEEPSEEK_API_KEY", "")
    if masked:
        out["api_key_masked"] = (key[:4] + "\u2026" + key[-4:]) if len(key) > 8 else ("set" if key else "")
    else:
        out["api_key"] = key
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
    first = "\n".join(head.strip().split("\n")[:8])
    if re.search(r"\bADDENDUM\b", first, re.I):
        return "addendum"
    if re.search(r"Package ID:", head) and re.search(r"Reference Section:", head):
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
        text = re.sub(r"<[^>]+>", " ", text)
    return text[:20000], 1, bool(text.strip())


def stage_file(rel, name, data):
    """Classify one uploaded file by content and stage it. Returns a result row."""
    ext = os.path.splitext(name)[1].lower()
    low = (rel + " " + name).lower()
    segs = [p for p in rel.replace(os.sep, "/").lower().split("/")[:-1]]
    if any(b in low for b in BANNED) or any(g in segs for g in ("bible", "_answer_key", "answer_key", "ground_truth")):
        return {"name": name, "kind": "refused",
                "note": "evaluation ground truth - the pipeline never reads this (contamination rule)"}
    if ext == ".csv":
        canon = classify_csv(data.decode("utf-8", errors="ignore"))
        if not canon:
            return {"name": name, "kind": "error",
                    "note": "unrecognized CSV columns - see CORPUS_FORMAT.md for the four register schemas"}
        d = os.path.join(STAGE, "registers")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, canon), "wb").write(data)
        return {"name": name, "kind": "register", "note": f"columns match {canon}", "stored_as": f"registers/{canon}"}
    if ext not in (".pdf", ".html", ".htm", ".txt", ".md"):
        return {"name": name, "kind": "skipped", "note": "not a project document type (pdf/html/csv/txt/md)"}
    # anything the user files under external/ is third-party reference
    if "external/" in rel.replace(os.sep, "/").lower():
        d = os.path.join(STAGE, "external")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, name), "wb").write(data)
        return {"name": name, "kind": "reference", "note": "third-party reference (M12 checks)", "stored_as": f"external/{name}"}
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
    ext = load("external.json") or {}
    opts = load("options.json") or {}
    g = load("graph.json") or {"nodes": [], "edges": []}
    types = {}
    for n in g["nodes"]:
        types[n["type"]] = types.get(n["type"], 0) + 1
    staged, _ = staged_state()
    env = read_env()
    return {
        "rules": rules, "claims": claims,
        "verdicts_pre": pre, "verdicts_post": post,
        "false_comply_pre": fc_pre, "false_comply_post": fc_post,
        "blast": (load("blast_wave.json") or {}).get("summary"),
        "addenda": len((load("blast_wave.json") or {}).get("waves", []) or []),
        "lint_findings": len(lint["findings"]),
        "external_checks": len(ext.get("checks", [])),
        "decide_by": min([p.get("decide_concessions_by") for p in opts.get("packages", [])
                          if p.get("decide_concessions_by")], default=None),
        "days_to_decide": min([p.get("days_to_decide") for p in opts.get("packages", [])
                               if isinstance(p.get("days_to_decide"), (int, float))], default=None),
        "graph_nodes": len(g["nodes"]), "graph_edges": len(g["edges"]),
        "node_types": types,
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
            ("blastwave",): lambda: load("blast_wave.json") or {},
            ("queue",): lambda: load("dispositions.json") or {"queue": []},
            ("options",): lambda: load("options.json") or {},
            ("margins",): lambda: load("margins.json") or {},
            ("vendors",): lambda: load("vendors.json") or {},
            ("lint",): lambda: load("lint.json") or {"findings": []},
            ("paperwork",): lambda: load("paperwork_index.json") or {"documents": []},
            ("cx",): lambda: load("cx_packs.json") or {"tests": []},
            ("external",): lambda: load("external.json") or {},
            ("project",): project_state,
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
            key = (body.get("api_key") or cur.get("api_key", "")).strip()
            write_env(base, model, key)
            return self._send(200, llm_config())
        if path == "/api/llm/test":
            body = self._body()
            cfg = llm_config(masked=False)
            for k in ("base_url", "model", "api_key"):
                if body.get(k):
                    cfg[k] = body[k]
            return self._send(200, llm_test(cfg))
        self._send(404, {"error": "unknown endpoint"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8020
    staged, _ = staged_state()
    loaded = os.path.exists(os.path.join(OUT, "project.json"))
    print(f"CLAUSE AI serving on http://localhost:{port} "
          f"(project loaded: {loaded}, staged files: {sum(staged.values())}, Ctrl-C to stop)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
