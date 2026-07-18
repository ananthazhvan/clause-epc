# M4 delivery notes (2026-07-11)

## New files
- `m4_verify.py` - deterministic verdict engine (M4). Joins rulebooks x claims.
  ZERO LLM calls. Verdicts: COMPLY / DEVIATION / MISSING_EVIDENCE /
  NEEDS_REVIEW / NOT_ADDRESSED. Flags: false_comply, unsubstantiated_comply,
  conflict, condition_unverified. Every verdict carries verbatim quotes and
  page numbers from both spec and submittal.
- `eval_recall.py` - eval harness ONLY. Reads `_answer_key/labels.json`
  (the pipeline itself never touches it). Scores M4 against pre-addendum
  ground truth; the addendum precedence layer is M5 and will be scored
  against post-addendum truth when built.
- `common/quotecheck.py` - single source of truth for verbatim-quote matching
  (whitespace/case normalization only, never fuzzy).

## Changed files
- `m1_parse.py` - dehyphenation now also rejoins digit fragments
  (`FK-5-1- 12`, `IEC 60502- 2`) and strips the page header/footer line that
  was bleeding into 37/245 clause texts.
- `common/llm.py` - new `get_checked_items()`: verifies every quote against
  the source text immediately after extraction; one repair re-prompt on
  failure; still-bad items get QUARANTINED to `out/quarantine.jsonl` loudly.
- `m2_rules.py` / `m3_claims.py` - use the self-checking extraction path.
- `check_extractions.py` - unchanged behavior, now delegates to quotecheck.

## Commands (in order, from pipeline/)
1. `python3 m1_parse.py --corpus ../clause_corpus --out out`   (free)
2. `python3 m2_rules.py --all && python3 m3_claims.py --all && python3 check_extractions.py`
   (~40 clauses re-billed because their text got cleaner; everything else
   replays from cache; expect a few cents)
3. `python3 m4_verify.py --all && python3 eval_recall.py`      (free, no API)

## Current eval (against HIS run-4 artifacts, pre-addendum ground truth)
=== M4 vs answer key (pre-addendum ground truth) ===
  OK: {'ok': 38}
  T1: {'missed': 1, 'flagged': 10, 'caught': 6, 'ok': 1}
  T2: {'caught': 8, 'flagged': 9, 'ok': 1, 'missed': 2}
  T3: {'caught': 3, 'flagged': 3, 'ok': 4}

  hard recall (caught): 17/42 = 40%
  flag-inclusive recall: 39/42 = 93%
  false alarms: 0   out of scope for M4: 7 (DEF-001, DEF-002, DEF-003, DEF-004, DEF-005, DEF-006, DEF-007)

=== MISSES (actionable) ===
   ('DEV-UPS-R0-REV', 'SUB-263353-01-R0', '26 33 53 Part 1.3.1', 'NO_COVERAGE', "Submittal transmittal cover sheet states the submittal is reviewed against spec revision 'Rev 2020', but the active project specification is")
   ('DEV-GEN-DAYTANK', 'SUB-263213-01-R0', '26 32 13 Part 2.3.8.C', 'NO_COVERAGE', 'Vendor submittal day tank has a maximum capacity of 990 Liters, providing only 1.9 hours of autonomy at full load. This violates spec 2.3.8.')
   ('DEV-FIRE-STD-OBS', 'SUB-212200-01-R0', '21 22 00 Part 1.2.1', 'NO_COVERAGE', 'Submittal states compliance with NFPA 2001 (2008 Edition). The project specification requires NFPA 2001 (2018 Edition), which contains criti')
