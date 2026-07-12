# CLAUSE — what to upload, and what format it must follow

CLAUSE is document-driven. You upload a folder of project documents; the pipeline
classifies every file **by its content, not its filename**, builds the requirement
ledger from scratch, and every screen in the app is rendered from that output.
Nothing on screen comes from anywhere else.

Bring a completely different project — different section numbers, different vendors,
different rule counts — and it works the same way, as long as the documents follow
the grammars below.

## Folder layout (recommended, not required)

```
your_project/
├── specs/            specification sections (PDF and/or HTML)
├── submittals/       vendor submittal packages (PDF)
├── addenda/          client addendum letters (PDF)
├── registers/        CSV registers (see schemas below)
├── project_docs/     minutes, change orders, reports (PDF/HTML/MD)
└── external/         real-world vendor datasheets (PDF) — treated as reference
```

Subfolder names do not matter except `external/`: anything under a folder named
`external` is treated as third-party reference material rather than a project
document. Everything else is classified by reading the file.

## How files are classified (by content)

| Detected as | Trigger inside the file |
|---|---|
| specification | 2+ clause lines matching the grammar `NN NN NN Part x.y.z Title` or a `SECTION NN NN NN` header |
| submittal | a transmittal block containing `Package ID:` and `Reference Section:` |
| addendum | the word `ADDENDUM` in the first lines of page 1 |
| register | a CSV whose header matches one of the four schemas below |
| project document | any other PDF/HTML/TXT/MD with extractable text |
| reference | any file under an `external/` folder |

Accepted types: `.pdf`, `.html`, `.csv`, `.txt`, `.md`. Image-only (scanned) PDFs are
rejected with an honest error — OCR is on the roadmap, not faked. Plain `.txt`/`.md`
notes are never promoted to specs/submittals/addenda.

**Refused on upload:** anything that looks like evaluation ground truth
(`project_bible.yaml`, `labels.json`, answer keys, or any file inside a `bible/` or
`_answer_key/` folder). The pipeline must never see the answer key — that is the
contamination rule, and it is enforced at the upload boundary.

## Specification grammar

Each checkable clause is one line:

```
26 33 53 Part 2.3.4 Inverter efficiency shall be not less than 96.0 percent at full load.
```

- `NN NN NN` — CSI-style section number (any numbers work)
- `Part x.y.z[.A]` — clause reference
- The sentence itself is what the LLM compiles into checkable rules (parameter,
  comparator, value, unit). Shall/should/may wording, ranges, and referenced
  standards are all handled by the compiler.

## Submittal grammar

Page 1 must carry a transmittal block; the remaining pages are free-form vendor
content (tables, datasheets, prose) that the LLM reads for claims:

```
Reference Section: 26 33 53
Package ID: SUB-263353-01-R0
Revision: R0
Reviewed Spec Revision: Rev 2024
Date: 01-01-2025
```

`Reviewed Spec Revision` is how CLAUSE catches vendors reviewing a stale spec.

## Addendum grammar

A client letter, PDF, with `ADDENDUM` in the header of page 1:

```
ADDENDUM NO. 3          Date: 2026-06-15
Reference: Section 26 33 53, Part 2.3.4
DELETE: "not less than 96.0 percent"
INSERT: "not less than 96.5 percent"
```

Multiple addenda are applied cumulatively in date order. There is no "apply
addendum" button anywhere — an addendum is just another uploaded document, and the
blast wave page shows one section per addendum found.

## CSV register schemas

Headers are matched case-insensitively; extra columns are kept and ignored. A CSV
that matches none of these is rejected with an error naming this file.

**po_register.csv** — required: `po_number, spec_section, vendor, value_inr, order_date`

```
po_number,equipment_tag,spec_section,vendor,item_description,value_inr,order_date,lead_time_weeks,delivery_status
```

**schedule.csv** — required: `activity_id, duration_days, predecessors, float_days`

```
activity_id,name,duration_days,predecessors,float_days,critical_path
```

**cx_test_register.csv** — required: `test_id, spec_clause, acceptance_criteria`

```
test_id,level,system,spec_clause,acceptance_criteria,status
```

**rfi_log.csv** — required: `rfi_id, query, response`

```
rfi_id,subject,query,response,status
```

These registers are the money-and-time half of the graph: POs connect packages to
rupees, the schedule connects packages to the calendar, the Cx register connects
clauses to test procedures. Change a PO value or a float and re-run — the decision
clock, margins, and blast wave all recompute from the new numbers.

## LLM cache — what it is and is not

`pipeline/.cache/` stores one file per `(model, prompt)` pair, keyed by
`sha256(model + prompt)`. It exists for exactly one reason: not paying twice for the
same LLM call. It contains raw LLM responses only — no parsed documents, no
verdicts, no page data. Every run re-parses your documents and re-verifies every
claim from zero; only the LLM responses replay. Change the model in Settings
(written to `pipeline/.env`) and the keys stop matching: the next run makes real
calls to your endpoint and takes real time.
