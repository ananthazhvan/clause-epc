#!/usr/bin/env python3
"""CLAUSE runner - executes the real pipeline against an uploaded corpus,
streaming every module's stdout; the web console tails this output.

Honesty contract:
  - every artifact the UI shows is rebuilt here from the uploaded documents
  - the ONLY cache is the LLM response cache (.cache/), keyed by
    sha256(model + prompt); identical prompts to the same model replay free,
    anything new goes to the live endpoint configured in pipeline/.env
  - modules whose inputs were not uploaded are SKIPPED with the reason
    printed - nothing is faked
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

PIPE = os.path.dirname(os.path.abspath(__file__))


def load_env(corpus):
    env = dict(os.environ)
    envfile = os.path.join(PIPE, ".env")
    if os.path.exists(envfile):
        for line in open(envfile):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    env["PYTHONUNBUFFERED"] = "1"
    env["CLAUSE_CORPUS"] = corpus
    return env


class Status:
    def __init__(self, path, stages):
        self.path = path
        self.doc = {"running": True, "ok": None, "error": None,
                    "started": time.time(), "finished": None,
                    "stages": [{"id": s["id"], "label": s["label"],
                                 "llm": s["llm"], "status": "pending",
                                 "secs": None, "note": ""} for s in stages]}
        self.write()

    def set(self, sid, **kw):
        for s in self.doc["stages"]:
            if s["id"] == sid:
                s.update(kw)
        self.write()

    def finish(self, ok, error=None):
        self.doc.update(running=False, ok=ok, error=error, finished=time.time())
        self.write()

    def write(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.doc, f, indent=1)
        os.replace(tmp, self.path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="uploaded corpus root")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    corpus = os.path.abspath(a.corpus)
    out = a.out
    os.makedirs(out, exist_ok=True)
    env = load_env(corpus)
    py = sys.executable
    reg = os.path.join(corpus, "registers")

    def have(n):
        return os.path.exists(os.path.join(reg, n))

    def spec_parsed():
        return bool(glob.glob(os.path.join(out, "spec_*.json")))

    def subs_parsed():
        for f in glob.glob(os.path.join(out, "doc_*.json")):
            try:
                if "transmittal" in json.load(open(f)):
                    return True
            except Exception:
                pass
        return False

    def claims_exist():
        return bool(glob.glob(os.path.join(out, "claims_*.json")))

    def registers_all():
        return have("schedule.csv") and have("po_register.csv") and have("cx_test_register.csv")

    stages = [
        dict(id="M1", label="parse every uploaded document", llm=False, core=True,
             cmd=[py, "-u", "m1_parse.py", "--corpus", corpus, "--out", out, "--allow-llm"],
             need=lambda: True, why=""),
        dict(id="M2", label="compile specification clauses into checkable rules", llm=True, core=True,
             cmd=[py, "-u", "m2_rules.py", "--all", "--out", out],
             need=spec_parsed, why="no specification recognized in the upload"),
        dict(id="M3", label="extract vendor claims from submittal packages", llm=True, core=True,
             cmd=[py, "-u", "m3_claims.py", "--all", "--out", out],
             need=subs_parsed, why="no submittal transmittal recognized in the upload"),
        dict(id="M4", label="verify every claim against every rule", llm=False, core=True,
             cmd=[py, "-u", "m4_verify.py", "--all", "--out", out],
             need=claims_exist, why="no vendor claims extracted"),
        dict(id="M4B", label="adjudicate unresolved verdicts against full package text", llm=True, core=True,
             cmd=[py, "-u", "m4b_adjudicate.py", "--out", out],
             need=claims_exist, why="no vendor claims extracted"),
        dict(id="M5", label="apply addenda in date order + blast wave", llm=False, core=True,
             cmd=[py, "-u", "m5_addendum.py"], need=lambda: True, why=""),
        dict(id="M6", label="dispositions + NCR register", llm=False, core=False,
             cmd=[py, "-u", "m6_disposition.py"], need=registers_all,
             why="register CSVs not uploaded"),
        dict(id="M9", label="vendor trust ledger", llm=False, core=False,
             cmd=[py, "-u", "m9_vendor.py"], need=lambda: have("po_register.csv"),
             why="po_register.csv not uploaded"),
        dict(id="M15", label="supply-chain risk: join every PO to the schedule", llm=True, core=False,
             cmd=[py, "-u", "m15_supply.py", "--corpus", corpus, "--out", out],
             need=lambda: have("schedule.csv") and have("po_register.csv"),
             why="schedule/PO register CSVs not uploaded"),
        dict(id="M10", label="paperwork drafts + specification self-lint", llm=False, core=False,
             cmd=[py, "-u", "m10_paperwork.py"], need=lambda: True, why=""),
        dict(id="M11", label="commissioning readiness packs", llm=False, core=False,
             cmd=[py, "-u", "m11_cx.py"], need=lambda: have("cx_test_register.csv"),
             why="cx_test_register.csv not uploaded"),
        dict(id="M16", label="compile the ontology - objects, links, money, rollups, certification evidence", llm=False, core=False,
             cmd=[py, "-u", "m16_ontology.py", "--corpus", corpus, "--out", out],
             need=lambda: True, why=""),
    ]

    status = Status(os.path.join(out, "run_status.json"), stages)
    model = env.get("DEEPSEEK_MODEL", "deepseek-chat")
    print(f"CLAUSE pipeline run\ncorpus: {corpus}")
    print(f"model: {model}  endpoint: {env.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}")
    print("LLM cache: .cache/ keyed by sha256(model+prompt) - cached prompts "
          "replay free, new prompts go to the live endpoint\n")

    failed = []
    for st in stages:
        if not st["need"]():
            print(f"== {st['id']} SKIPPED - {st['why']} ==\n")
            status.set(st["id"], status="skipped", note=st["why"])
            continue
        tag = "LLM" if st["llm"] else "deterministic"
        print(f"== {st['id']} - {st['label']} [{tag}] ==")
        status.set(st["id"], status="running")
        t0 = time.time()
        proc = subprocess.Popen(st["cmd"], cwd=PIPE, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in proc.stdout:
            print(f"  {line.rstrip()}")
        proc.wait()
        secs = round(time.time() - t0, 2)
        if proc.returncode != 0:
            if st["core"]:
                print(f"== {st['id']} FAILED after {secs}s - run stopped ==")
                status.set(st["id"], status="failed", secs=secs)
                status.finish(False, f"{st['id']} failed - see the log above")
                sys.exit(1)
            print(f"== {st['id']} FAILED after {secs}s - continuing (non-core) ==\n")
            status.set(st["id"], status="failed", secs=secs)
            failed.append(st["id"])
        else:
            print(f"== {st['id']} done in {secs}s ==\n")
            status.set(st["id"], status="done", secs=secs)

    with open(os.path.join(out, "project.json"), "w") as f:
        json.dump({"loaded_at": time.time(), "corpus": corpus, "model": model,
                   "failed_stages": failed}, f, indent=1)
    status.finish(True)
    print("RUN COMPLETE - the ledger is live." +
          (f" (non-core failures: {', '.join(failed)})" if failed else ""))


if __name__ == "__main__":
    main()
