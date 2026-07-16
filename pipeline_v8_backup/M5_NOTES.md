# M5 + M6 + UI — Addendum Blast Wave, Disposition Engine, Demo UI

Drop-in delivery. Unzip into `pipeline/` (overwrites `eval_recall.py`, adds the rest).
Everything in this delivery is **deterministic — zero LLM calls, zero cost, ~2 s total**.

## What's in the zip

| File | What it does |
|---|---|
| `m5_addendum.py` | Parses `out/doc_addendum_3.json`, amends the affected rules (preserving originals + audit trail), re-runs the M4 verifier against the amended rulebooks into `out/post/`, diffs verdicts, and walks the registers: POs ordered against superseded values -> INVALID, Cx tests testing old values -> STALE. Writes `out/blast_wave.json`. |
| `m5_graph.py` | Builds `out/graph.json` — the requirements-ledger graph (353 nodes / ~710 edges: sections, clauses, packages, POs, activities, Cx tests, addendum). Every node/edge derived from artifacts, nothing invented. |
| `m6_disposition.py` | For every open deviation: PO exposure, lead time, schedule float -> reorder math (`lead_weeks*7 − min_float = days onto critical path`), three disposition options with the math shown, recommendation. Writes `out/dispositions.json` + `out/ncr_register.csv` (32 NCRs). Engineers close NCRs; CLAUSE drafts them. |
| `eval_recall.py` | Updated: `--post` flag scores against post-addendum ground truth; also writes `out/eval_report.json` for the UI. |
| `app/server.py` | Demo server, Python stdlib only, no pip installs. Serves the UI + JSON APIs. `POST /api/blastwave/apply` re-runs M5+M6 live — that's the demo moment. |
| `app/static/` | The UI. Vanilla JS, zero dependencies, works offline. Dashboard / Submittal Queue / Review (spec-vs-evidence side by side) / Ledger Graph (force-directed, Obsidian-style) / Blast Wave / NCR Register. |

## Run order (all free)

```bash
cd pipeline
python3 m5_addendum.py        # blast wave -> out/post/, out/blast_wave.json
python3 m5_graph.py           # -> out/graph.json
python3 m6_disposition.py     # -> out/dispositions.json, out/ncr_register.csv
python3 eval_recall.py        # pre-addendum score  (writes out/eval_report.json)
python3 eval_recall.py --post # post-addendum score (writes out/post/eval_report.json)
python3 app/server.py         # open http://localhost:8020
```

## Honest numbers (frozen for the PDF)

- Pre-addendum, 42 planted deviations: **16 caught (38%), 39 caught-or-flagged (93%), 0 false alarms** (±1 label run-to-run at temp 0).
- Post-addendum, 46 in scope: **20 caught (43%), 43 caught-or-flagged (93%), 0 false alarms.** The addendum layer catches what pre-addendum verification structurally cannot.
- Blast wave of ADD-003: 2 contract changes -> 5 rules amended -> 6 verdicts flipped -> 8 POs invalidated (₹20 Cr ordered against superseded requirements) -> 2 commissioning tests stale.
- Known misses (named, all NO_COVERAGE from M2): DEV-UPS-R0-REV, DEV-GEN-DAYTANK, DEV-FIRE-STD-OBS.

## Design decisions (defend these in Q&A)

- **M5 is deterministic, not an LLM.** Addendum changes are precise legal edits; parsing them with regex + numeric matching means the blast wave is *provable*, reproducible, and free. The LLM already did its job upstream (M1 structuring).
- **Amended rules keep `original_value`, `amended_by`, `amended_on`.** The ledger never destroys history — that's the audit-trail requirement in the PS.
- **PO invalidation rule:** PO's spec section was amended AND `order_date` < addendum date. **Cx staleness rule:** the deleted value appears *with its unit* in the acceptance criteria (unit-aware, so "step 10" doesn't false-match 10°C).
- **M6 outputs options with math, never a decision.** Disposition authority stays with engineers; the tool shows `slip = lead_time − float` and cost exposure per option.
- **UI is stdlib + vanilla JS** so the demo has zero infrastructure risk: no npm, no CDN, works with wifi off.
