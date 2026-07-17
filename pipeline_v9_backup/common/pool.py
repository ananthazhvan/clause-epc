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
from concurrent.futures import ThreadPoolExecutor

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
    """Ordered parallel map. Falls back to a plain loop when workers == 1,
    so single-key setups behave exactly as before."""
    items = list(items)
    w = min(workers or worker_count(), max(1, len(items)))
    if w <= 1:
        return [fn(x) for x in items]
    with ThreadPoolExecutor(max_workers=w) as ex:
        return list(ex.map(fn, items))
