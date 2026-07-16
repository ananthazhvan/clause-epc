#!/usr/bin/env python3
"""Synthetic replication benchmark for the deterministic verification core.

HONEST LABEL: this replicates the project's REAL rulebooks and claims N times
(with rewritten IDs) and times M4 verification on the inflated ledger. It is
a synthetic scale test of the deterministic core - it does NOT call any LLM.
The point it proves: everything outside the two LLM map stages costs
milliseconds per document, so scaling CLAUSE = scaling an embarrassingly
parallel map (see SCALABILITY.md and common/pool.py).

Usage: python3 bench_scale.py [--factor 100] [--out out]
Needs a completed run in out/ (rulebook_*.json + claims_*.json).
"""
import argparse
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", type=int, default=100, help="replication factor (default 100)")
    ap.add_argument("--out", default="out", help="source artifact dir of a completed run")
    a = ap.parse_args()
    rulebooks = sorted(glob.glob(os.path.join(a.out, "rulebook_*.json")))
    claimfiles = sorted(glob.glob(os.path.join(a.out, "claims_*.json")))
    docfiles = sorted(glob.glob(os.path.join(a.out, "doc_*.json")))
    if not rulebooks or not claimfiles:
        sys.exit("no rulebook_*/claims_* in %s - run the pipeline first" % a.out)

    n_rules = sum(len(json.load(open(f))["rules"]) for f in rulebooks)
    n_claims = sum(len(json.load(open(f))["claims"]) for f in claimfiles)
    print(f"source ledger: {len(rulebooks)} rulebooks / {n_rules} rules, "
          f"{len(claimfiles)} packages / {n_claims} claims")
    print(f"replicating x{a.factor} (SYNTHETIC - real artifacts, rewritten IDs) ...")

    bench = tempfile.mkdtemp(prefix="clause_bench_")
    try:
        for f in docfiles:  # M4 may consult doc text for context - copy as-is
            shutil.copy(f, bench)
        for f in rulebooks:
            d = json.load(open(f))
            big = {"section": d["section"], "rules": []}
            for i in range(a.factor):
                for r in d["rules"]:
                    r2 = copy.deepcopy(r)
                    r2["rule_id"] = f"{r['rule_id']}-X{i}"
                    big["rules"].append(r2)
            json.dump(big, open(os.path.join(bench, os.path.basename(f)), "w"))
        for f in claimfiles:
            d = json.load(open(f))
            big = dict(d, claims=[])
            for i in range(a.factor):
                big["claims"].extend(copy.deepcopy(d["claims"]))
            json.dump(big, open(os.path.join(bench, os.path.basename(f)), "w"))
        for extra in ("project.json",):
            p = os.path.join(a.out, extra)
            if os.path.exists(p):
                shutil.copy(p, bench)
        for f in glob.glob(os.path.join(a.out, "spec_*.json")) + glob.glob(os.path.join(a.out, "ontology_*.json")):
            shutil.copy(f, bench)

        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, os.path.join(HERE, "m4_verify.py"), "--all", "--out", bench],
                           capture_output=True, text=True)
        dt = time.perf_counter() - t0
        if r.returncode != 0:
            sys.exit("m4_verify failed on the replicated ledger:\n" + (r.stderr or r.stdout)[-2000:])
        checks = 0
        for f in glob.glob(os.path.join(bench, "verdicts_*.json")):
            d = json.load(open(f))
            checks += len(d.get("results") or d.get("verdicts") or [])
        print(f"\nM4 verification: {checks} rule-checks in {dt:.2f}s "
              f"= {checks / dt:,.0f} checks/sec (single process, stdlib only)")
        per_pkg = dt / (len(claimfiles) * a.factor)
        print(f"\u2248 {per_pkg * 1000:.1f} ms of deterministic verification per submittal package")
        print(f"\u2192 extrapolation (same laptop, single process): "
              f"{3600 / per_pkg:,.0f} packages/hour of deterministic verification")
        print("\nThe LLM map stages (M2/M3) are the only real cost at scale; they")
        print("parallelise linearly across API keys - see SCALABILITY.md \u00a72.")
    finally:
        shutil.rmtree(bench, ignore_errors=True)


if __name__ == "__main__":
    main()
