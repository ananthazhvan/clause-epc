# CLAUSE — data-centre EPC requirement ledger

An AI intelligence layer for data-centre EPC delivery. CLAUSE reads the project's
own documents — CSI-format specifications, vendor submittals, addenda, the P6
schedule, the SAP purchase-order register, logistics feeds, quality records — and
compiles them into one living requirement ledger: every checkable rule in the spec,
every claim a vendor made, every verdict, every non-conformance, every purchase
order joined to the schedule activity that needs it.

Built for the ET AI Hackathon 2026 (PS-4: AI Intelligence Platform for Data Centre
EPC Project Delivery).

## The idea

EPC information lives in disconnected systems: the spec in one folder, submittals
in a document register, the schedule in Primavera P6, procurement in SAP, shipment
tracking in a logistics portal, quality issues in a QMS. Each is fine on its own.
The failures happen **between** them — a submittal that quietly deviates from the
spec, a PO whose lead time breaks an activity nobody linked it to.

CLAUSE turns every real-world thing into an object (spec section, clause, package,
vendor, PO, activity, shipment, commissioning test, NCR) with typed relationships
(*complies_with, deviates_from, supplies, delivers, feeds, verifies, amends,
blocks*). Questions become graph walks instead of folder searches.

## How the LLM is used — and how hallucination is kept out

We never dump whole documents into a model and ask for an opinion.

1. **Rules** — each spec clause is sent to the model alone; it returns a structured
   rule (parameter, operator, limit, unit). 12 sections -> 335 checkable rules on
   our test corpus.
2. **Claims** — each submittal page is sent alone; it returns claims (parameter,
   value, unit, verbatim quote, page number).
3. **Verification is deterministic Python** — rules x claims, unit-normalised
   comparison. No model in the loop. Same inputs, same ledger, every run.
4. **Adjudication** — only unresolved checks go back to the model, now with full
   package context.
5. **Conflict sweep** — before any check settles as COMPLY, every piece of evidence
   for that parameter is re-read. If the compliance matrix says one value and the
   factory test report says another, the check is routed to a human with both
   quotes. Conflicting evidence is never silent compliance.
6. **Addenda** — applied in issue-date order; each one re-opens exactly the checks
   it touches. Contract documents are living documents.

Every verdict carries the rule quote, the claim quote and the page number, so a
human can confirm or dismiss it in seconds.

## Measured results (MERIDIAN test corpus)

We generated a full synthetic project — MERIDIAN-1, a Navi Mumbai data centre —
to evaluate against: 12 CSI spec sections, 22 submittal packages, 2 addenda, 120
schedule activities, 15 POs across 9 vendors, 8 tracked shipments, 82 commissioning
tests. 48 defects were planted with a difficulty tier system (Tier-1: plain
datasheet contradictions; Tier-2: buried in compliance matrices, certificates and
factory test pages; Tier-3: only visible across systems), plus 40 explicitly
conforming controls to measure false alarms. The answer key is never an input to
the pipeline — scoring runs after the ledger is frozen.

| Measure | Result |
|---|---|
| Planted defects found | 48 / 48 (20 caught as deviations, 28 routed to human review, 0 missed) |
| False deviations on the 40 conforming controls | 0 |
| Checks run | 618, from 668 extracted vendor claims |
| Manual review baseline avoided | 91 engineer-hours per cycle |

## Run it

```bash
cd pipeline
python3 app/server.py 8000
```

Open http://localhost:8000, upload a project folder (see `CORPUS_FORMAT.md`),
press **Run**, and every screen builds from the output. Python 3 standard library
only — no packages to install.

### Reproduce our results offline — no API key

The repo ships the LLM response cache (`pipeline/.cache/`). Rerunning the MERIDIAN
corpus replays every model response byte-for-byte: same rules, same claims, same
verdicts, no API calls, no key, no network. Change the corpus or the model and the
pipeline makes real calls instead.

### Bring your own model — keep your data in-house

Settings accepts any OpenAI-compatible endpoint. Point it at a local model (e.g.
Ollama) and nothing leaves your machine — the model only ever sees one clause or
one page at a time, which is exactly why a small local model is enough. Paste
multiple API keys and the LLM stages fan out across parallel workers.

## The app

**Hub** scoreboard, run log, answer-key scoring · **Compliance** per-section
detection ledger · **Risk** the SAP x P6 join plus a seeded Monte Carlo with stress
sliders · **Ledger / Queue** every verdict with quotes; the human-review queue ·
**NCR** auto-raised register · **Cx** commissioning packs, gated on open NCRs ·
**Globe** shipment trails and routes · **Objects / Graph** the ontology · **Data**
every connected source and table · **Copilot** a tool-calling agent over the
ontology that fans out research subagents and only states what a tool returned.

## Repository layout

```
pipeline/          the whole product: pipeline stages (m1..m17), app/ server + UI
pipeline/.cache/   LLM response cache — offline reproduction
corpus/            the MERIDIAN test corpus, generator and answer key
CORPUS_FORMAT.md   what to upload and the document grammar CLAUSE reads
```
