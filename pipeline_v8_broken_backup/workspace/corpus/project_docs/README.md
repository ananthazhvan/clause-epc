# CLAUSE AI — Project Meridian Test Corpus (v2, restyled)

This is the complete synthetic document set for **Project Meridian**, a fictional 20MW data centre
build in Navi Mumbai. It is the "exam paper" that the CLAUSE AI pipeline will be graded against:
every document here was generated from a single source of truth (`project_bible.yaml`), with **48
known deviations** deliberately planted across the vendor submittals.

## Integrity note (important)

This v2 corpus is a **visual restyle + rename only** of the frozen, audited M0 corpus (frozen 9 Jul
after a 29-point independent audit).

- Extracted text of all 19 PDFs verified **character-for-character identical** to the frozen version
  (whitespace-normalized diff: 19/19 identical).
- The generator's own verifier re-run after restyling: all 93 labels verified, no forbidden words in
  base specs.
- Only the stylesheet (colors, tables, typography) and the delivery file names changed. No content,
  no values, no pagination changed.

## Folder map

| Folder | What it is |
|---|---|
| `specs/` | The 6 **specifications** — the buyer's rulebook. Each one covers one trade (UPS, generators, switchgear, cooling, fire suppression) and says what the equipment MUST do, clause by clause. Named by CSI section number, e.g. `spec_26_33_53` = the UPS & battery spec. |
| `submittals/` | The 7 **vendor submittals** — each vendor's homework answer. "Here is the equipment we propose, here are its numbers, and here is our claim that it complies." Each has a cover page, a technical datasheet, sometimes performance curves, a compliance matrix, and a certificate page. This is where the 48 planted errors live. |
| `project_docs/` | The connective tissue of a real project: `addendum_3.pdf` (an official mid-project rule change — it OVERRIDES the specs), `design_basis_report.pdf` (the project's founding assumptions), review minutes, a change order, a method statement. |
| `registers/` | Spreadsheets a project manager lives in: purchase orders, the schedule, commissioning tests, RFIs. Used later for the business-impact layer (what a caught error is worth in ₹ and days). |
| `_answer_key/` | **`labels.json` = the answer key** (all 93 labels: every planted deviation, where it is, and the correct verdict). For scoring the pipeline only. **The pipeline must never read this folder** — see `WARNING.md`. |
| `manifest.json` | Maps these pretty file names back to the original package IDs (e.g. `submittal_VoltEdge_UPS_R0.pdf` = `SUB-263353-01-R0.pdf`). The package IDs still appear *inside* the documents, which is realistic — real transmittal numbers look like that. |

Every PDF also has its `.html` source next to it, so you can open it in a browser or tweak the look.

## Spec index

| File | Trade | Clauses |
|---|---|---|
| `spec_26_05_00` | Common electrical requirements | 25 |
| `spec_26_33_53` | UPS + batteries (VoltEdge) | 69 |
| `spec_26_32_13` | Diesel generators (Deccan) | 44 |
| `spec_26_13_26` | MV switchgear (Trident) | 33 |
| `spec_23_81_23` | CRAH cooling units (CryoCore) | 43 |
| `spec_21_22_00` | Clean-agent fire suppression (AegisFire) | 31 |

## How checking works (the one idea that matters)

Every requirement in a spec has a **clause ID** like `26 33 53 Part 2.3.2.C`. The submittal's
compliance matrix quotes that same ID. The ID is the *join key*: requirement (spec) ↔ claim
(submittal). The matrix's "Requirement Summary" column is just a truncated preview — real vendors
paraphrase too — so nothing is ever checked against the summary text, only against the full clause
in the spec.

## Start here

Open `REVIEWER_GUIDE.md` and do the three walkthroughs (Tier 1, 2, 3). Total time: ~15 minutes.
That is exactly the manual job CLAUSE AI automates.
