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
└── external/         third-party reference PDFs — kept on file, not analysed
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

## Where these formats come from (industry reality)

- **Schedules** live in Primavera P6 / MS Project; teams exchange XER / XML /
  XLSX exports. `schedule.csv` is a flattened export of exactly the fields the
  pipeline uses (activity, duration, predecessors, float). **P6 XML import is
  implemented** — see “Connector formats” below. Native XER is roadmap — same
  slot, different reader.
- **Procurement**: expediting reports (Procore, SAP, 4castplus) track each PO
  through vendor documentation → fabrication → shipment → site delivery.
  `po_register.csv` is the core of that report. **SAP OData purchase-order
  JSON import is implemented** — see “Connector formats” below. Extra columns
  (e.g. `dispatch_date`, `eta`, `current_location`) are accepted and preserved.
- **Change orders / addenda** are issued as documents (letters, forms, PDFs) —
  never as CSV — which is why CLAUSE ingests addenda as PDFs and computes the
  blast wave from their text.
- **Commissioning** follows the 5-level convention (L1 factory tests → L5
  integrated systems test); `cx_test_register.csv` mirrors a standard Cx log.
- **Header names need not match exactly.** If a CSV's headers don't match a
  canonical schema and an API key is configured, the model maps the columns
  onto the canonical names (cached, shown in the staging note) and the file is
  staged with canonical headers. Without a key you get an honest error and
  this document.

## Connector formats (implemented — deterministic, zero LLM)

The upload screen auto-detects three system-of-record export formats and
converts them to canonical registers on the spot. The staging note always
says exactly what was read and what was computed.

### Primavera P6 XML → `registers/schedule.csv`

An `APIBusinessObjects` export (any P6 namespace version). Read per activity:
`Id`, `Name`, `PlannedDuration` (hours ÷ 8 → days; falls back to
planned start/finish dates), `TotalFloat` (hours ÷ 8). `Relationship`
elements become the `predecessors` column (`;`-joined); `Lag` is honoured.
If the export carries no `TotalFloat`, float is computed with a CPM
forward/backward pass over finish-to-start logic — and the note says so.
Non-FS link types are treated as FS for float and counted in the note.
`ResourceAssignment`/`Resource` elements become an extra `resources` column
(preserved, not required by the pipeline).

### SAP OData purchase orders → `registers/po_register.csv`

Accepts OData v2 (`{"d":{"results":[…]}}`), v4 (`{"value":[…]}`) or a bare
list of PO objects, with items under `to_PurchaseOrderItem(.results)` /
`Items`. Dates may be `/Date(ms)/` or ISO. Mapping: `PurchaseOrder` →
`po_number`, `Material` → `equipment_tag`, `SupplierName` → `vendor`,
`PurchaseOrderItemText` → `item_description`, `NetPrice × OrderQuantity` →
`value_inr`, `CreationDate` → `order_date`, `ScheduleLineDeliveryDate −
order_date` → `lead_time_weeks`. `spec_section` is read from a custom field
(SAP convention `YY1_*`, e.g. `YY1_SpecSection_PDH`, or any `*spec*section*`
key) — rows without one are staged with the field EMPTY and counted in the
note; CLAUSE never guesses a spec section. Non-INR currencies are flagged,
not converted.

### Shipment-visibility JSON → merged into `po_register.csv`

FourKites/project44-style feeds (`{"shipments":[…]}` etc., keyed by
`purchaseOrderNumber`). Matching rows get `delivery_status`,
`current_location`, `eta` updated; unmatched shipment POs are listed in the
note. Requires a staged `po_register.csv` first (CSV or SAP JSON).

Sample exports of all three — generated from this corpus's own registers, so
they roundtrip exactly — live in `clause_corpus/connectors/`. CLI version:
`python3 connectors/convert.py <file> [--po po_register.csv]`.
