# CLAUSE — the requirement ledger

A document-driven compliance engine for data centre EPC project delivery.
Upload the project's documents; CLAUSE compiles the specification into checkable
rules, extracts vendor claims, verifies every claim against every rule, and shows
the consequences — verdicts, money, calendar — with a verbatim quote behind every
single claim it makes.

Nothing on screen is pre-loaded. The app starts empty. Everything you see is built
from the documents you upload, on your machine.

## Layout

```
/home/ananth/Projects/clause_ai_et/
  clause_corpus/     <- test corpus (generated from a bible YAML; see below)
  pipeline/          <- this folder
```

## One-time setup

```
pip install pypdf        # the only external dependency; everything else is stdlib
```

Optionally put an LLM key in `pipeline/.env` (or do it later from the Settings
screen in the app — same file):

```
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=sk-...        # never commit this file
```

Any OpenAI-compatible endpoint works (DeepSeek, OpenAI, or Ollama on
`http://localhost:11434/v1` — see `LOCAL_LLM.md`).

## Run

```
cd pipeline
python3 app/server.py          # serves on http://localhost:8020
```

Open the browser. The hub asks for your project documents — drop the whole folder
(specs, submittals, addenda, CSV registers, minutes, vendor datasheets). Files are
classified **by content, not filename**; evaluation ground truth (bible YAML, answer
keys) is refused at the upload boundary. Press **Run** and watch the pipeline stream
live: every parsed page, every compiled rule, every extracted claim, every verdict.

Document format rules (spec clause grammar, transmittal block, addendum grammar,
the four CSV register schemas) are in **`CORPUS_FORMAT.md`** — follow those and any
project works, with any section numbers, vendors, and values.

## The LLM cache — read this

`.cache/` stores raw LLM responses keyed by `sha256(model + prompt)`. It exists for
one reason: not paying twice for the same call. It contains no parsed documents, no
verdicts, no page data. Every run re-parses and re-verifies everything from zero;
only LLM responses replay. Change the model or bring new documents and the pipeline
makes real calls that take real time and need a real key.

## Pipeline stages

| Stage | What it does | LLM |
|---|---|---|
| M1 | parse every document (PDF/HTML/CSV) | no |
| M2 | compile spec clauses into checkable rules | yes |
| M3 | extract vendor claims from submittals | yes |
| M4 | verify every claim against every rule | no |
| M5 | apply addenda in date order + blast wave | no |
| GRAPH | assemble the project graph | no |
| M6–M11 | NCRs, decision clock, margins, vendor trust, paperwork, spec lint, Cx packs | no |
| M13 | data-centre facility profile — Tier / TIA-942 declarations, redundancy topology (N+1 / 2N / 2N+1) by system, standards invoked, gaps | no |

The deterministic layer is deliberately large: the LLM reads documents; it never
decides verdicts. Verdicts come from comparing numbers, and numbers do not
hallucinate.

## Evaluation (offline only, on purpose)

The test corpus is generated from `bible/project_bible.yaml`, which doubles as the
answer key. The eval scripts score CLAUSE against it offline — they are for the
submission PDF and demo video. The app never sees the answer key: uploads of
ground-truth files are refused. That is the contamination rule.

## Honest limitations

- Image-only (scanned) PDFs are rejected with an error — OCR is roadmap, not faked.
- Documents must follow the grammars in `CORPUS_FORMAT.md`; free-form specs need
  the RAG layer (roadmap).
- One project per server instance.

## The copilot — the AI layer over the connected data

A first-class feature: the Copilot tab (or the “Ask CLAUSE” launcher) opens a
full-height drawer once a project is loaded. `POST /api/agent/stream` runs a
small tool-calling harness (temperature 0, max 8 steps) and relays every tool
call live as NDJSON events — the UI shows each step (“Searching documents for
…”, “Reading spec_26_33_53 · page 4”) with a spinner that turns into a tick,
then renders the answer as real markdown (tables, lists, headings, code).
`POST /api/agent` still returns the same result in one shot. The tools are:
keyword search across every parsed page (grep-style, because project data is
precise — rule IDs, PO numbers, clause numbers), verbatim page reads, exact ID
lookups (rules, claims, POs, activities, Cx tests, graph nodes), and the same
JSON artifacts every site page renders. The model may only state what the tools
return and cites document + page inline; the tool trace is shown in the chat.
Completions are disk-cached in `.cache/` like every other LLM call — a scripted
demo replays free, new questions need a key in `pipeline/.env` (Settings).

## Images and scanned drawings — honest limits

Real submittal packages contain drawings, stamped scans and nameplate photos.
CLAUSE today extracts text only; an image-only PDF is refused at upload with an
explicit error rather than guessed at. Roadmap: a vision-model pass that turns
drawing pages into structured claims under the same evidence rule (every
finding must carry its page reference). Spatial judgements (“will it fit in
the room”) stay with engineers — the tool's job is to surface the drawing and
the governing clause side by side, not to pretend it can read floor plans.

## Roadmap — live data instead of exports

Registers are CSV exports today because that is what every project team can
produce (P6/MS Project schedules, Procore/SAP procurement reports, Cx logs).
The staging interface is deliberately an adapter seam — and three connectors
now fill it (deterministic parsing, zero LLM calls):

- **Primavera P6 XML** schedule exports → `registers/schedule.csv`
  (activities, FS logic, lags, TotalFloat or a CPM pass, resource assignments)
- **SAP OData purchase-order JSON** (`API_PURCHASEORDER_PROCESS_SRV` shape)
  → `registers/po_register.csv`, including `YY1_*` spec-section custom fields
- **Shipment-visibility JSON** (FourKites/project44 style) → merged into
  `po_register.csv` as `delivery_status` / `current_location` / `eta`

Drop those files on the upload screen or run `python3 connectors/convert.py`.
Details and honest limits: `CORPUS_FORMAT.md` (Connector formats). Sample
exports generated from the demo corpus: `clause_corpus/connectors/`. Live API
pulls (P6 EPPM, SAP OData endpoints, webhooks) remain roadmap — they are
authentication plumbing around these same adapters. XER import: roadmap.

## Scalability — the multi-key parallel LLM pool

Settings accepts any number of API keys (one per line → `DEEPSEEK_API_KEYS`).
`common/llm.py` rotates calls round-robin over the pool and `common/pool.py`
fans the M2/M3 map stages across `CLAUSE_WORKERS` parallel workers (default:
one per key). Results return in input order, so artifacts are byte-identical
at any worker count. N keys ≈ N× throughput on the only expensive stages.
Benchmark the deterministic core with `python3 bench_scale.py`. The full
argument (and its honest limits): `SCALABILITY.md`.
