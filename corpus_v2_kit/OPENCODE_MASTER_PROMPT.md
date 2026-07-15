# Paste everything below this line into opencode (run from the repo root)

You are the corpus architect for CLAUSE AI. Build a complete new test corpus
at `corpus_v2/` in this repository. Do not touch `pipeline/` or
`clause_corpus/`.

READ FIRST (in this order, they are the law):
1. `pipeline/CORPUS_FORMAT.md` — the exact grammar every file must follow
   (spec grammar, submittal grammar, addendum grammar, CSV schemas,
   connector formats).
2. `corpus_v2_kit/BLUEPRINT.md` — the design: 14 CSI spec sections with the
   real standards each must cite, 59 submittal packages across ~55 vendors,
   the planted-violations budget, register requirements, build order.

PROCESS — use subagents, one per spec section (14 lanes):
- Each lane produces: 1 spec file + its 2–6 submittal packages + its rows for
  po_register.csv + its cx_test_register.csv rows + its share of the
  violations key.
- A final integrator pass merges registers, builds schedule.csv (~120
  activities, `;`-joined predecessors, coherent forward-pass dates, one true
  critical path), writes the addendum, and assembles
  `_answer_key/violations_key.json`.

HARD RULES:
- Specs: CSI MasterFormat sectioning exactly like `clause_corpus/specs/*`
  (PART / numbered clauses / one checkable quantitative requirement per
  clause, SI units). Cite the real standard named in the blueprint inside the
  clause text, but the checkable number must live in the clause itself.
- Submittals: transmittal cover with SUB-<section>-<seq>-R0, vendor product
  data with SPECIFIC numeric values for every requirement of its section,
  compliance matrix table. 3–6 pages. Text-based (markdown is fine; convert
  to PDF only if trivial).
- Violations: plant per the blueprint budget (~15% FAIL, ~8% NEI). Subtle and
  realistic, never cartoonish. Record EVERY planted item in the violations
  key with page numbers. Never hint at them inside the submittals.
- Vendors: ~55 unique names, with 3–4 platform vendors spanning multiple
  sections (per blueprint §2). Same vendor name spelled identically
  everywhere (po_register, submittals, transmittals).
- Internal consistency: a submittal's values are consistent within itself;
  PO values, lead times and schedule activities are mutually plausible.
- NEVER copy spec text verbatim as a submitted value; vendors paraphrase.

VERIFICATION LOOP (do not skip):
1. `cd pipeline && python3 -c "import m1_parse"` sanity, then run the
   pipeline's upload/classification on `corpus_v2/` (or `python3 runner.py`
   with the corpus staged) and confirm: every spec classifies as spec, every
   submittal as submittal, registers as registers, ZERO unknown/external.
2. If anything misclassifies: fix the generated document to match
   CORPUS_FORMAT.md. Never modify pipeline code or classifiers.
3. `python3 connectors/make_samples.py --corpus ../corpus_v2 --check` must
   print roundtrip OK for P6 and SAP.
4. Full run M1→M13, then `python3 eval_recall.py` against
   `corpus_v2/_answer_key/violations_key.json` and report precision/recall.
5. Iterate until the loop is green, then output a manifest: file count per
   folder, total planted FAIL/NEI, vendor count, and the eval numbers.
