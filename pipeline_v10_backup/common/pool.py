"""Parallel map for LLM stage work - the scale-out lever.

Every LLM stage in CLAUSE (M2 rule compilation, M3 claim extraction) is
embarrassingly parallel map work: one independent call per clause / per page,
no shared state between items. So throughput scales linearly by fanning the
map across threads, with common/llm.py rotating requests round-robin over the
DEEPSEEK_API_KEYS pool (N keys = N separate rate-limit budgets).

- CLAUSE_WORKERS in pipeline/.env sets the fan-out
  (0 or unset = auto: one worker per configured API key)
- results are returned in INPUT ORDER, so rule numbering and every output
  artifact stay byte-identical regardless of worker count - determinism is
  part of the honesty contract, not an accident
- pure stdlib (concurrent.futures), like everything else in the pipeline
"""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import llm

MAX_WORKERS = 64


def worker_count():
    try:
        w = int(os.environ.get("CLAUSE_WORKERS", "0") or 0)
    except ValueError:
        w = 0
    if w <= 0:
        w = max(1, len(llm.keys()))
    return max(1, min(w, MAX_WORKERS))


def pmap(fn, items, workers=None):
    """Ordered parallel map with live progress, so long LLM calls never look
    like a hang: every completion prints, and a heartbeat reports what is
    still in flight while nothing is completing."""
    items = list(items)
    w = min(workers or worker_count(), max(1, len(items)))
    if w <= 1 or len(items) <= 1:
        return [fn(x) for x in items]
    state = {"done": 0, "stop": False}
    lock = threading.Lock()

    def heartbeat():
        while True:
            time.sleep(12)
            with lock:
                if state["stop"]:
                    return
                print(f"    ... waiting on the model: {state['done']}/{len(items)} "
                      f"call(s) answered, {len(items) - state['done']} in flight", flush=True)

    threading.Thread(target=heartbeat, daemon=True).start()
    res = [None] * len(items)
    try:
        with ThreadPoolExecutor(max_workers=w) as ex:
            futs = {ex.submit(fn, x): i for i, x in enumerate(items)}
            for f in as_completed(futs):
                res[futs[f]] = f.result()
                with lock:
                    state["done"] += 1
    finally:
        with lock:
            state["stop"] = True
    return res
