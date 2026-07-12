"""CLAUSE AI demo server v3 - Python stdlib only, zero dependencies.

Run from the pipeline/ directory:  python3 app/server.py [port]
Then open http://localhost:8020

v3 adds on top of v2:
  POST /api/ingest        - upload documents (JSON base64). Files are
                            fingerprinted (sha256) against the project
                            corpus; recognized files map to their role,
                            unknown files get a live deterministic
                            numeric-claim harvest (no LLM, no cache).
  POST /api/ingest/run    - re-run the deterministic pipeline, timed.
  GET/POST /api/llm/config- bring-your-own-model: OpenAI-compatible
                            base URL + key + model, stored locally in
                            out/llm_config.json (never leaves machine).
  POST /api/llm/test      - live round-trip test against that endpoint.
  GET  /api/node?id=...   - dossier join for a graph node: what the
                            clause demands, who promised what, verdicts,
                            money, tests, addendum history.
  GET  /api/guide?f=...   - serve markdown guides (LOCAL_LLM.md etc).

Every request is logged to an in-memory activity feed (/api/activity).
No LLM calls happen in the server unless you explicitly test your own
endpoint via /api/llm/test.
"""
import base64
import csv
import datetime
import glob
import hashlib
import json
import os
import re
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
CORPUS = os.path.normpath(os.path.join(PIPELINE, "..", "clause_corpus"))
UPLOADS = os.path.join(OUT, "uploads")
LLM_CFG = os.path.join(OUT, "llm_config.json")
MIME = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
        ".json": "application/json", ".svg": "image/svg+xml"}

STARTED_AT = datetime.datetime.now().isoformat(timespec="seconds")
ACTIVITY = deque(maxlen=200)
ACT_LOCK = threading.Lock()
RERUN_MODULES = ["m5_addendum.py", "m5_graph.py", "m6_disposition.py",
                 "m7_options.py", "m8_margin.py", "m9_vendor.py",
                 "m10_paperwork.py", "m11_cx.py"]
GUIDES = {"LOCAL_LLM.md", "README.md", "DESIGN_SPEC.md", "M7_M12_NOTES.md"}

# ---------------------------------------------------------------- corpus
MANIFEST = {}
KINDS = {"specs": "specification", "submittals": "vendor submittal",
         "project_docs": "project document", "registers": "register",
         "external": "external document", "bible": "corpus bible",
         "_answer_key": "answer key"}


def build_manifest():
    if not os.path.isdir(CORPUS):
        return
    for root, _, files in os.walk(CORPUS):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, CORPUS)
            try:
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            except OSError:
                continue
            MANIFEST[h] = {"file": fn, "path": rel.replace(os.sep, "/"),
                           "kind": KINDS.get(rel.split(os.sep)[0], "document")}


# ------------------------------------------------------------- harvester
# Same deterministic L0 discipline as m12: number + unit with an
# obligation word nearby. No LLM, nothing planted, quotes + pages.
OBLIGATION = re.compile(
    r"\b(shall|must|minimum|maximum|not less than|at least|not exceed(?:ing)?|"
    r"required|rated|capacity|provide[ds]?)\b", re.I)
NUM_UNIT = re.compile(
    r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(\u00b0?\s?C\b|TR\b|kW\b|kVA\b|kA\b|dB\s?\(?A\)?"
    r"|%|V\b|Hz\b|PSI\b|kg\b|[Ll]/h\b|min(?:ute)?s?\b|bar\b|mm\b|A\b)")


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


def harvest(path):
    """Live numeric-claim harvest of an unseen document."""
    pages = extract_pages(path)
    if not pages:
        return {"pages": 0, "total_hits": 0, "hits": [],
                "error": "could not extract text (image-only PDF needs OCR - see roadmap)"}
    hits, seen = [], set()
    for i, pg in enumerate(pages, 1):
        text = re.sub(r"\s+", " ", pg)
        for m in NUM_UNIT.finditer(text):
            ctx = text[max(0, m.start() - 130):m.end() + 130].strip()
            if not OBLIGATION.search(ctx):
                continue
            key = (m.group(1), m.group(2).strip(), ctx[:60])
            if key in seen:
                continue
            seen.add(key)
            hits.append({"page": i, "value": m.group(1),
                         "unit": m.group(2).strip(), "quote": ctx[:240]})
    return {"pages": len(pages), "total_hits": len(hits), "hits": hits[:40]}


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
    spend = 0.0
    cost_path = os.path.join(PIPELINE, "cost_log.jsonl")
    if os.path.exists(cost_path):
        for line in open(cost_path):
            try:
                spend += json.loads(line).get("usd", 0) or 0
            except (ValueError, TypeError):
                pass
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
    return {
        "rules": rules, "claims": claims,
        "verdicts_pre": pre, "verdicts_post": post,
        "false_comply_pre": fc_pre, "false_comply_post": fc_post,
        "eval_pre": load("eval_report.json"),
        "eval_post": load("post/eval_report.json"),
        "blast": (load("blast_wave.json") or {}).get("summary"),
        "lint_findings": len(lint["findings"]),
        "external_checks": len(ext.get("checks", [])),
        "decide_by": min([p.get("decide_concessions_by") for p in opts.get("packages", [])
                          if p.get("decide_concessions_by")], default=None),
        "days_to_decide": min([p.get("days_to_decide") for p in opts.get("packages", [])
                               if isinstance(p.get("days_to_decide"), (int, float))], default=None),
        "llm_spend_usd": round(spend, 4),
        "graph_nodes": len(g["nodes"]), "graph_edges": len(g["edges"]),
        "node_types": types,
        "corpus_files": len(MANIFEST),
        "ncrs": len((load("dispositions.json") or {}).get("queue", [])),
    }


def rerun(modules):
    timings, ok, log = [], True, []
    for mod in modules:
        if not os.path.exists(os.path.join(PIPELINE, mod)):
            continue
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, mod], cwd=PIPELINE,
                           capture_output=True, text=True)
        ms = round((time.perf_counter() - t0) * 1000)
        timings.append({"module": mod, "ms": ms, "ok": r.returncode == 0})
        log.append(r.stdout.strip() or r.stderr.strip()[-500:])
        if r.returncode != 0:
            ok = False
            break
    return {"ok": ok, "timings": timings, "log": "\n".join(log)[-4000:],
            "finished_at": datetime.datetime.now().isoformat(timespec="seconds")}


# --------------------------------------------------------------- dossier
def node_dossier(nid):
    """Everything the ledger knows about one graph node."""
    g = load("graph.json") or {"nodes": [], "edges": []}
    node = next((n for n in g["nodes"] if n["id"] == nid), None)
    if not node:
        return {"error": "unknown node", "id": nid}
    d = {"id": nid, "type": node["type"], "label": node["label"],
         "status": node.get("status"), "meta": node.get("meta", {})}
    # neighbors (both directions) with edge type
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
        # most informative first: deviations, then anything with evidence
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
        d["wave"] = (load("blast_wave.json") or {}).get("summary")

    return d


# ------------------------------------------------------------------- llm
def llm_config(masked=True):
    cfg = {}
    if os.path.exists(LLM_CFG):
        try:
            cfg = json.load(open(LLM_CFG))
        except ValueError:
            cfg = {}
    out = {"base_url": cfg.get("base_url", ""), "model": cfg.get("model", ""),
           "configured": bool(cfg.get("base_url") and cfg.get("model"))}
    key = cfg.get("api_key", "")
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
        if p.startswith("/api/") and p != "/api/activity":
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
        simple = {
            ("summary",): summary,
            ("graph",): lambda: load("graph.json") or {},
            ("blastwave",): lambda: load("blast_wave.json") or {},
            ("queue",): lambda: load("dispositions.json") or {"queue": []},
            ("options",): lambda: load("options.json") or {},
            ("margins",): lambda: load("margins.json") or {},
            ("vendors",): lambda: load("vendors.json") or {},
            ("lint",): lambda: load("lint.json") or {"findings": []},
            ("paperwork",): lambda: load("paperwork_index.json") or {"documents": []},
            ("cx",): lambda: load("cx_packs.json") or {"tests": []},
            ("external",): lambda: load("external.json") or {},
        }
        key = tuple(parts)
        if key in simple:
            return self._send(200, simple[key]())
        if parts == ["activity"]:
            with ACT_LOCK:
                return self._send(200, {"events": list(ACTIVITY)[-60:]})
        if parts == ["meta"]:
            arts = {}
            for p in glob.glob(os.path.join(OUT, "*.json")):
                arts[os.path.basename(p)] = datetime.datetime.fromtimestamp(
                    os.path.getmtime(p)).isoformat(timespec="seconds")
            return self._send(200, {
                "python": sys.version.split()[0],
                "server_started": STARTED_AT,
                "now": datetime.datetime.now().isoformat(timespec="seconds"),
                "today": datetime.date.today().isoformat(),
                "artifacts": arts,
                "corpus_files": len(MANIFEST),
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
        if path == "/api/blastwave/apply":
            res = rerun(RERUN_MODULES)
            res["wave"] = load("blast_wave.json")
            return self._send(200 if res["ok"] else 500, res)
        if path == "/api/recompute":
            res = rerun(RERUN_MODULES)
            return self._send(200 if res["ok"] else 500, res)
        if path == "/api/ingest":
            body = self._body()
            os.makedirs(UPLOADS, exist_ok=True)
            recognized, unknown = [], []
            for f in (body.get("files") or [])[:20]:
                name = re.sub(r"[^A-Za-z0-9._ -]", "_", f.get("name", "upload"))[:120]
                try:
                    data = base64.b64decode(f.get("b64", ""))
                except Exception:
                    unknown.append({"name": name, "error": "could not decode"})
                    continue
                h = hashlib.sha256(data).hexdigest()
                if h in MANIFEST:
                    recognized.append({"name": name, **MANIFEST[h]})
                else:
                    dest = os.path.join(UPLOADS, name)
                    open(dest, "wb").write(data)
                    res = harvest(dest)
                    unknown.append({"name": name, **res})
            return self._send(200, {"recognized": recognized, "unknown": unknown,
                                    "corpus_files": len(MANIFEST)})
        if path == "/api/ingest/run":
            res = rerun(RERUN_MODULES)
            res["summary"] = summary()
            return self._send(200 if res["ok"] else 500, res)
        if path == "/api/llm/config":
            body = self._body()
            cfg = llm_config(masked=False)
            new = {"base_url": (body.get("base_url") or cfg.get("base_url", "")).strip(),
                   "model": (body.get("model") or cfg.get("model", "")).strip(),
                   "api_key": (body.get("api_key") if body.get("api_key") else cfg.get("api_key", "")).strip()}
            os.makedirs(OUT, exist_ok=True)
            json.dump(new, open(LLM_CFG, "w"))
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
    build_manifest()
    print(f"CLAUSE AI serving on http://localhost:{port} "
          f"({len(MANIFEST)} corpus files fingerprinted, Ctrl-C to stop)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
