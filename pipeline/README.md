# CLAUSE pipeline - M1-M3

Built and pre-tested in the Notion AI sandbox against the frozen corpus (9 Jul 2026).

## Layout

Drop this `pipeline/` folder next to your corpus:

```
/home/ananth/Projects/clause_ai_et/
  clause_corpus/     <- the restyled corpus zip, unzipped (input, READ-ONLY)
  pipeline/          <- this folder
```

## One-time setup

1. `pip install pypdf` (the only external dependency; everything else is stdlib)
2. `cp .env.example .env`, open `.env`, put in your DeepSeek API key and the exact
   model id from the DeepSeek platform. Never commit `.env`, never paste the key anywhere.

## Run the gate FIRST (one spec + one submittal, then STOP)

```
bash run_gate.sh ../clause_corpus
```

What it does, in order:
- Step 0: plumbing tests with a mocked LLM (free, no key needed)
- Step 1: M1 deterministic parse of ALL documents + hard acceptance asserts (free)
- Step 2: M2 rule compiler on section 26 33 53 only (LLM)
- Step 3: M3 claim extractor on SUB-263353-01-R0 only (LLM)
- Step 4: honesty checker - every quote must exist verbatim in its source
- Step 5: prints the footnote-trap evidence (rule from 2.2.2.B + the 50%-load claims)

Then STOP and send back for audit: `out/rulebook_26_33_53.json`,
`out/claims_SUB-263353-01-R0.json`, `cost_log.jsonl`, and the full console output.

## Full run (ONLY after the gate is audited)

```
python3 m2_rules.py --all
python3 m3_claims.py --all
python3 check_extractions.py
```

## What "pre-tested" means (honest boundary)

- M1 ran end-to-end in the sandbox on the real corpus: 245/245 clauses, exact ID match,
  all 7 submittal transmittals parsed.
- M2/M3 plumbing (cache, schema validation, repair loop, checker) is covered by
  `test_plumbing.py` with a mocked LLM.
- The ONLY untested part is live DeepSeek output quality - which is exactly what the
  gate + checker verify on your machine. Reruns are ~free: every call is cached in
  `pipeline/.cache/` keyed by prompt content.

## Standing rules

- The pipeline reads ONLY `corpus/rendered/`. It must NEVER open `project_bible.yaml`,
  `labels.json`, or `curves_data.json` - those are M9 evaluation ground truth.
- If `check_extractions.py` fails: fix extraction, never the checker.
- Real-world note (for the PDF & Q&A): structure recovery is deterministic for
  digital-native CSI-format specs; documents failing the structure check route through
  LLM structuring (`m1_parse.py --allow-llm`) with the same output schema.
"""
