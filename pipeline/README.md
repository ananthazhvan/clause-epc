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
| M6–M12 | NCRs, decision clock, margins, vendor trust, paperwork, spec lint, Cx packs, external cross-checks | no |

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
