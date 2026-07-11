"""CLAUSE AI demo server - Python stdlib only, zero dependencies.

Run from the pipeline/ directory:  python3 app/server.py [port]
Then open http://localhost:8020

Serves the M1-M6 artifacts in out/ to the frontend, and exposes one
action: POST /api/blastwave/apply re-runs the deterministic M5+M6 layer
live (addendum -> amended rules -> re-verify -> registers), which is the
live-demo moment. No LLM calls happen in the server.
"""
import csv
import glob
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PIPELINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(PIPELINE, "app", "static")
OUT = os.path.join(PIPELINE, "out")
MIME = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
        ".json": "application/json", ".svg": "image/svg+xml"}


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
    return {
        "rules": rules, "claims": claims,
        "verdicts_pre": pre, "verdicts_post": post,
        "false_comply_pre": fc_pre, "false_comply_post": fc_post,
        "eval_pre": load("eval_report.json"),
        "eval_post": load("post/eval_report.json"),
        "blast": (load("blast_wave.json") or {}).get("summary"),
        "llm_spend_usd": round(spend, 4),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

    def do_GET(self):
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
                    q[k] = v
        if parts == ["summary"]:
            return self._send(200, summary())
        if parts == ["graph"]:
            return self._send(200, load("graph.json") or {})
        if parts == ["blastwave"]:
            return self._send(200, load("blast_wave.json") or {})
        if parts == ["queue"]:
            return self._send(200, load("dispositions.json") or {"queue": []})
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
        if self.path == "/api/blastwave/apply":
            r = subprocess.run(
                [sys.executable, "m5_addendum.py"], cwd=PIPELINE,
                capture_output=True, text=True)
            if r.returncode == 0:
                subprocess.run([sys.executable, "m5_graph.py"], cwd=PIPELINE,
                               capture_output=True, text=True)
                subprocess.run([sys.executable, "m6_disposition.py"], cwd=PIPELINE,
                               capture_output=True, text=True)
            return self._send(200, {"ok": r.returncode == 0,
                                     "log": (r.stdout + r.stderr)[-4000:],
                                     "wave": load("blast_wave.json")})
        self._send(404, {"error": "unknown endpoint"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8020
    print(f"CLAUSE AI serving on http://localhost:{port} (Ctrl-C to stop)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
