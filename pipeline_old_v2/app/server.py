"""CLAUSE AI demo server v2 - Python stdlib only, zero dependencies.

Run from the pipeline/ directory:  python3 app/server.py [port]
Then open http://localhost:8020

Serves the M1-M12 artifacts in out/ to the frontend and exposes two
actions that re-run the deterministic layer LIVE:

  POST /api/blastwave/apply  - addendum -> amended rules -> re-verify ->
                               registers -> options/margins/vendors/
                               paperwork/cx (M5..M11), timed per module
  POST /api/recompute        - same rerun without needing an addendum

Every request is logged to an in-memory activity feed (/api/activity)
that the UI renders as a live ticker - the point being that what you see
on screen is fetched, computed, and timed, not preloaded. No LLM calls
happen in the server.
"""
import csv
import datetime
import glob
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PIPELINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(PIPELINE, "app", "static")
OUT = os.path.join(PIPELINE, "out")
MIME = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
        ".json": "application/json", ".svg": "image/svg+xml"}

STARTED_AT = datetime.datetime.now().isoformat(timespec="seconds")
ACTIVITY = deque(maxlen=200)
ACT_LOCK = threading.Lock()
RERUN_MODULES = ["m5_addendum.py", "m5_graph.py", "m6_disposition.py",
                 "m7_options.py", "m8_margin.py", "m9_vendor.py",
                 "m10_paperwork.py", "m11_cx.py"]


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
    return {
        "rules": rules, "claims": claims,
        "verdicts_pre": pre, "verdicts_post": post,
        "false_comply_pre": fc_pre, "false_comply_post": fc_post,
        "eval_pre": load("eval_report.json"),
        "eval_post": load("post/eval_report.json"),
        "blast": (load("blast_wave.json") or {}).get("summary"),
        "lint_findings": len(lint["findings"]),
        "external_checks": len(ext.get("checks", [])),
        "decide_by": (opts.get("commissioning") or {}).get("decide_concessions_by"),
        "llm_spend_usd": round(spend, 4),
    }


def rerun(modules):
    """Re-run the deterministic layer, timing each module."""
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
        # activity feed (skip static + the feed itself to avoid noise)
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

    def parse_response(self):  # noqa: N802 - hook for timing
        return super().parse_request()

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
        parts = path.strip("/").split("/")[1:]  # after 'api'
        q = {}
        if "?" in self.path:
            for kv in self.path.split("?", 1)[1].split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    q[k] = v.replace("%20", " ")
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
            })
        if parts == ["paperwork", "doc"]:
            fn = os.path.basename(q.get("f", ""))  # path-safe
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
        if self.path == "/api/blastwave/apply":
            res = rerun(RERUN_MODULES)
            res["wave"] = load("blast_wave.json")
            return self._send(200 if res["ok"] else 500, res)
        if self.path == "/api/recompute":
            res = rerun(RERUN_MODULES)
            return self._send(200 if res["ok"] else 500, res)
        self._send(404, {"error": "unknown endpoint"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8020
    print(f"CLAUSE AI serving on http://localhost:{port} (Ctrl-C to stop)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
