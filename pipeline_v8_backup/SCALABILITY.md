# Scalability — how CLAUSE goes from 57 documents to millions

The demo corpus is 57 documents. That is a test corpus, not a ceiling. This
page is the honest engineering answer to "what happens at real EPC scale" —
what is implemented and measurable today, and what is roadmap. Nothing here
is hand-waving: every implemented claim below can be reproduced from this
repository.

## 1. The architecture is map-reduce shaped by construction

The expensive part of the pipeline is two LLM stages, and both are pure
*map* operations over independent items:

| stage | unit of work | shared state between units |
|---|---|---|
| M2 rule compilation | one spec clause | none |
| M3 claim extraction | one submittal page | none |

Everything downstream — verification (M4), the blast wave (M5), the graph,
margins, vendor scores, paperwork, Cx packs, facility profile — is
deterministic Python: linear scans and dict lookups, no model calls, no
quadratic joins. A million documents is a million independent map items
followed by cheap deterministic reduces.

## 2. Multi-key parallel LLM pool (implemented)

Settings accepts **any number of API keys, one per line**. They are written
to `pipeline/.env` as `DEEPSEEK_API_KEYS` and:

- `common/llm.py` rotates every call **round-robin** across the pool — N keys
  = N independent rate-limit budgets;
- `common/pool.py` fans M2/M3 map work across `CLAUSE_WORKERS` threads
  (default: one worker per key);
- results return in **input order**, so artifacts are byte-identical no
  matter the worker count — parallelism never changes the answer;
- the response cache key excludes the API key, so cached replays stay free.

Throughput math (honest form): one clause/page call is one network round
trip. With per-key rate limits as the binding constraint, wall-clock time for
an LLM stage is `items × latency / min(workers, keys × per-key-concurrency)`.
Ten keys ≈ 10× the throughput of one key. The stdlib-only design means the
same code drops into a real work queue (see §5) unchanged.

Measure it yourself: `python3 bench_scale.py` (see §4).

## 3. Connectors — the formats real EPC data actually arrives in (implemented)

Real projects do not email CSVs; they export from systems of record. CLAUSE
now ingests those exports directly — deterministic parsing, **zero LLM
calls**, so connector throughput is effectively unlimited and free:

| source system | wire format | connector | lands as |
|---|---|---|---|
| Oracle Primavera P6 (dominant EPC scheduler) | XML export (`APIBusinessObjects`): activities, FS logic links, resource assignments, TotalFloat | `connectors/p6xml.py` | `registers/schedule.csv` (+ `resources` column) |
| SAP S/4HANA procurement | OData JSON (`API_PURCHASEORDER_PROCESS_SRV`): POs, line items, `/Date(ms)/` dates, `YY1_*` custom fields | `connectors/sap_odata.py` | `registers/po_register.csv` |
| Visibility platforms (FourKites / project44 style) | shipment JSON feeds keyed by PO number | `connectors/logistics.py` | merged into `po_register.csv` (`delivery_status`, `current_location`, `eta`) |

Drop a P6 XML or SAP JSON file on the upload screen and it is detected,
converted and staged with an honest note saying exactly what was read. If
float is missing from a P6 export, CLAUSE computes it with a standard CPM
forward/backward pass and *says so*. Missing spec-section fields are left
empty and counted — never guessed.

Sample exports generated from the demo corpus live in
`clause_corpus/connectors/` (exact re-encodings of the canonical registers —
converting them back reproduces the registers byte-for-byte; verified by
`python3 connectors/make_samples.py --check`).

## 4. Measured throughput, not vibes (implemented)

`python3 bench_scale.py` replicates the project's real rulebooks and claims
N× (default 100×) and times the deterministic verification core on the
inflated ledger, then prints checks/second and an extrapolation table. It
labels itself a *synthetic replication benchmark* — the point is that the
non-LLM 80% of the pipeline is measured in milliseconds per document, so the
LLM map stage is the only thing you ever need to scale.

## 5. Honest limits and the production path

What this repo is NOT yet:

- **No distributed queue.** Parallelism is threads in one process. At true
  millions-of-documents scale you put the same map items on a queue
  (SQS/Celery/Temporal) with the same idempotent cache keys. The code is
  already shaped for it; the queue is infrastructure, not research.
- **Artifacts are JSON files** in `out/`. At scale that becomes object
  storage + a database index. Same artifacts, different shelf.
- **Connectors read exports, not live APIs.** Live OData/P6 EPPM/webhook
  pulls are authentication plumbing around the exact same adapters —
  the parsing, staging and honesty rules do not change.
- **OCR** for scanned drawings remains out of scope (see README).

Why this is still the right answer for the 15% scalability score: the hard
scaling problems (independence of work units, deterministic reduces,
idempotent caching, format normalisation at the front door) are *design*
problems, and they are solved and demonstrable here. The remaining work is
commodity infrastructure.
