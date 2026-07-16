#!/usr/bin/env python3
"""Plumbing tests with a mocked LLM transport - no network, no API key needed.
Tests: schema validator, disk cache, repair loop, quote checker.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import llm, schemas  # noqa: E402
import check_extractions as chk  # noqa: E402

GOOD = {
    "parameter": "ups.efficiency_50_load",
    "operator": ">=",
    "value": 96.0,
    "unit": "%",
    "condition": "measured in VFI mode with harmonic filters active",
    "quote": "efficiency at 50% rated load shall be a minimum of 96.0%",
}
BAD = dict(GOOD, operator="MAYBE")
calls = []


def fake_post(url, payload, headers, timeout=180):
    user = payload["messages"][1]["content"]
    calls.append(user)
    if "failed validation" in user:
        rules = [GOOD]  # repaired output
    elif "INVALID_FIRST" in user:
        rules = [BAD]  # first output is schema-invalid
    else:
        rules = [GOOD]
    return {
        "choices": [{"message": {"content": json.dumps({"rules": rules})}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }


llm._http_post = fake_post
llm.API_KEY = "mock"
# use a throwaway cache + cost log so tests NEVER touch the real ones
import tempfile
llm.CACHE_DIR = tempfile.mkdtemp(prefix="plumbing_cache_")
llm.COST_LOG = os.path.join(llm.CACHE_DIR, "cost_log.jsonl")

# 1. schema validator catches a bad enum value
errs = schemas.validate_items([BAD], schemas.RULE_FIELDS, "t")
assert errs, "validator missed invalid operator"

# 2. happy path + disk cache (second identical call must not hit the API)
r1 = llm.get_items("sys", "clause text A", "rules", schemas.RULE_FIELDS, "t")
n_after_first = len(calls)
r2 = llm.get_items("sys", "clause text A", "rules", schemas.RULE_FIELDS, "t")
assert r1 == r2 == [GOOD], "happy path failed"
assert len(calls) == n_after_first, "cache miss on identical prompt"

# 3. repair loop: invalid first output triggers ONE re-prompt containing the error
r3 = llm.get_items("sys", "INVALID_FIRST clause", "rules", schemas.RULE_FIELDS, "t")
assert r3 == [GOOD], "repair loop did not recover"
assert any("failed validation" in c for c in calls), "repair prompt never sent"

# 4. quote checker normalization
assert chk.contains("Efficiency   reduces to 95.1%\nMore text", "efficiency reduces to 95.1%")
assert not chk.contains("completely different text", "efficiency reduces to 95.1%")

shutil.rmtree(llm.CACHE_DIR, ignore_errors=True)
print("ALL PLUMBING TESTS PASS (validator, cache, repair loop, quote checker)")
