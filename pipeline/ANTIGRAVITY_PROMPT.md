# PROJECT MERIDIAN - FULL SOURCE-SYSTEM CORPUS (PHASED BUILD PROMPT)

Paste ONE PHASE AT A TIME into the agent. Do not paste the whole file. Each
phase ends with a verification gate - the agent must stop and report, and you
review before pasting the next phase. This is how we prevent hallucination.

## CONTEXT (include with every phase)

You are building the existing enterprise databases of PROJECT MERIDIAN
(MERIDIAN-1 Data Centre, Hall A, project code MER-1-2026), a fictional Indian
hyperscale data-centre EPC project. The data will be exported from five
"source systems" - Oracle Primavera P6 (6 tables), SAP S/4HANA PS (7 tables),
Oracle Aconex (4 tables), Autodesk Construction Cloud (5 sources), Hexagon
Smart Materials (4 tables) - 26 tables total, plus the engineering documents
(5 CSI spec sections, 8 submittal packages, 1 addendum). Everything must be
mutually consistent: one bible, one timeline, one set of IDs.

PRIME DIRECTIVES (violations = task failure):
1. corpus/bible/project_bible.yaml is the single source of truth. After
   Phase 0 it is READ-ONLY. Every rendered file is a pure function of it.
2. Never invent columns. Appendix A lists the exact columns per table - use
   those names and types verbatim.
3. No ground-truth leakage: no check IDs, tier labels, or the words "planted",
   "deviation type", "answer key" in any corpus file. The answer key lives
   ONLY in corpus/answer_key/ (violations_key.json + evaluation.md).
4. Fictional vendors only: VoltEdge Power Systems (SAP vendor 0000104412),
   CryoCore Climate (0000101877), AegisFire Systems (0000108230), Meridian
   Switchgear (0000110051), Trident Fabrication (0000112584). Never any real
   manufacturer or model number.
5. Indian conventions: 415V/11kV, 50Hz, IS/IEC standards, INR values,
   Asia/Kolkata timestamps. POs are 4500012301..4500012307.
6. Existing anchors you must keep (already used by the checker app):
   - CSI sections: 21 22 00 (clean-agent fire), 23 21 13 (CHW piping),
     23 64 26 (chillers), 26 24 13 (LV switchboards), 26 33 53 (UPS).
   - Submittals: SUB-212200-01-R0, SUB-232113-01-R0, SUB-236426-01-R0/-R1,
     SUB-262413-01-R0, SUB-262413-02-R0, SUB-263353-01-R0, SUB-263353-02-R0.
   - Addendum ADD-001 dated 2026-03-02 (Section 23 64 26 Clause 2.1 COP
     6.0 -> 6.3; Section 26 33 53 Clause 2.7 IEC 62040-3:2021 unity-pf note).
   - Schedule activities A1000..A4010 incl. "(PO-45000123xx)" tags in names.
7. Deterministic generation: Jinja2 templates + one generator script; same
   bible in -> identical corpus out. Verify with a marker-free verifier, then
   report. Never weaken the verifier to pass.

FILE-FORMAT CONTRACT (the checker ingests these by CONTENT, not filename):
- Specs/submittals/addendum: HTML (+ PDF via headless Chromium print).
  Submittal page 1 must carry "Package ID:", "Reference Section:",
  "Reviewed Spec Revision:" transmittal lines. Addendum uses the structured
  grammar: `Reference: Section NN NN NN, Part X.Y` / `Action: DELETE '<old>'
  and INSERT '<new>'` / `Clause: <description>` (prose "Delete...substitute"
  is also parsed, but structured is preferred).
- Registers (CSV): po_register.csv (po_number,equipment_tag,spec_section,
  vendor,item_description,value_inr,order_date,lead_time_weeks,
  delivery_status), schedule.csv (activity_id,name,duration_days,
  predecessors,float_days,critical_path), cx_test_register.csv (test_id,
  level,system,spec_clause,acceptance_criteria,status), rfi_register.csv
  (rfi_id,section,question,status).
- P6 export: XER or P6-XML (APIBusinessObjects/Project/Activity) - the app
  converts it to schedule.csv deterministically.
- SAP PO export: OData JSON (d.results with Ebeln/Lifnr/Matnr-style fields
  per EKKO/EKPO) - converted to po_register.csv.
- Logistics: FourKites-style JSON with loadNumber + positionUpdates
  [{latitude, longitude, locationDescription, timestamp}] - drives the globe.
- Other feeds: JSON arrays (ACC issues/worklog/materials/equipment, Aconex
  document/transmittal/mail/workflow, Hexagon BOM/material/PMS/PCF) - the
  ontology stage ingests them as typed objects.

---

## PHASE 0 - THE BIBLE (human gate before anything else)

Write corpus/bible/project_bible.yaml containing:
- project: identity, 4 halls x 5MW, PUE target, key dates (NTP 2025-11,
  Hall A RFS 2026-12), org chart (client, EPC, consultants).
- timeline: one dated event list from NTP to L5 test - every document,
  transmittal, mail, PO, delivery, test MUST reference dates from here.
- equipment: per tag (UPS-A1..A4, BAT cabinets, CH-A1/A2, CRAH rows,
  LVSG-A, suppression skid): true_val, spec_val, claimed_val,
  claimed_condition, where_expressed for every checkable parameter.
- registers: full row data for the 4 CSVs + the 26 source tables (counts:
  ~60 P6 activities, 7 POs w/ line items, ~40 Cx tests, 10 RFIs, ~25 Aconex
  mails, ~30 ACC issues, ~50 Hexagon BOM lines).
- planted_errors: exactly 48, each with id (V1..V48), tier (T1 blatant /
  T2 buried / T3 cross-document), document, parameter, spec_clause,
  submitted_value, expected_verdict (DEVIATION / MISSING_EVIDENCE /
  NEEDS_REVIEW), and a one-line rationale. Distribution: 20 T1 / 18 T2 /
  10 T3. T3 errors must require joining two sources (e.g. datasheet value
  contradicts Hexagon mill cert; Aconex mail admits a slip the schedule
  hides; SAP delivery date breaks a P6 constraint).
- compliant_checks: >= 30 explicitly compliant parameters (false-alarm bait).
Run a self-check script that asserts: every planted error's document exists,
every clause cited resolves, every date is inside the timeline, PO/vendor/
tag IDs are consistent across all 26 tables. Print the assertion table.
STOP. Report the bible summary + assertion table for human approval.

## PHASE 1 - PRIMAVERA P6 (6 tables)

From the bible only, emit corpus/p6/ as an XER file (PROJECT, PROJWBS, TASK,
TASKPRED, RSRC, TASKRSRC - columns per Appendix A) AND meridian_p6.xml
(P6-XML APIBusinessObjects) carrying the same activities as schedule.csv,
including "(PO-45000123xx)" in procurement activity names, float_days,
critical_path flags. Consistency checks: activity count matches bible;
every TASKPRED pair exists; every TASKRSRC rate x hours reconciles with the
PO value it supports (+-5%). STOP and report.

## PHASE 2 - SAP S/4HANA (7 tables)

Emit corpus/sap/ as OData-style JSON exports: PROJ, PRPS, PRHI, AUFK, AFVC,
RESB, COEP (columns per Appendix A) plus sap_po_odata.json (EKKO/EKPO-shaped
d.results for the 7 POs - this one the app ingests directly). Consistency:
PRPS WBS codes match P6 PROJWBS; COEP postings sum to PO values; RESB
component needs match Hexagon BOM quantities (Phase 5 will assert the same
numbers - take them from the bible now). STOP and report.

## PHASE 3 - ORACLE ACONEX (4 tables)

Emit corpus/aconex/: document_register.json, transmittal_registry.json,
workflow_history.json, mail_module.json (columns per Appendix A). Every
submittal package appears as a document + transmittal with the SAME package
IDs and dates as the bible; the 10 RFIs appear as mail threads; at least two
T3 planted errors live here (a mail that contradicts a datasheet claim; a
workflow approval that skipped a required reviewer). STOP and report.

## PHASE 4 - AUTODESK CONSTRUCTION CLOUD (5 sources)

Emit corpus/acc/: worklogEntries.json, materialsEntries.json,
equipmentEntries.json, issues.json, form_templates.json (columns per
Appendix A; issues.json doubles as acc_qms_issues.json for the app). QMS
issues must include the NCR-adjacent observations implied by the planted
errors (without naming them). Daily logs must be date-consistent with P6
actuals. STOP and report.

## PHASE 5 - HEXAGON SMART MATERIALS (4 tables)

Emit corpus/hexagon/: bom.json, material_master.json, pms_class.json,
pcf_repository.json (columns per Appendix A). Include mill-cert/MTC
references for CHW piping (23 21 13) - one planted T3 error: a heat number
on a cert that does not exist in material_master. Quantities reconcile with
SAP RESB. STOP and report.

## PHASE 6 - ENGINEERING DOCUMENTS

Render the 5 spec sections (HTML+PDF, clause-numbered PART 1/2/3 structure),
the 8 submittal packages (transmittal page + datasheet + compliance matrix +
certificates; every planted error placed exactly per where_expressed), and
ADD-001 in the structured grammar. Base specs contain zero references to the
addendum. STOP and report.

## PHASE 7 - ANSWER KEY + VERIFIER

Emit corpus/answer_key/violations_key.json (all 48 planted items + the
compliant list + cross-source insights) and evaluation.md (scoring rubric:
caught / flagged-to-human / missed / false alarm). Write verify_corpus.py:
marker-free, re-derives every planted error's location from the rendered
files, asserts cross-table consistency (IDs, dates, sums) across all 26
tables, asserts zero leakage strings. 100% green required. Print the final
table: files, counts, checks passed. Report uncertain decisions explicitly.
## APPENDIX A - EXACT SOURCE-SYSTEM SCHEMAS (from research2.txt - do not invent columns)

### 1. Oracle Primavera P6 Schema (Scheduling Layer)

### 2. SAP S/4HANA (Project System & Materials Management)

### 3. Oracle Aconex (CDE & Document Control Layer)

### 4. Autodesk Construction Cloud (BIM & Field Execution Layer)

### 5. Hexagon Smart Materials (Specialty Procurement Layer)

**`PROJECT` (Project Metadata)**
Columns: `proj_id` (INTEGER), `proj_short_name` (VARCHAR(40)), `proj_name` (VARCHAR(120)), `clndr_id` (INTEGER), `data_date` (DATETIME), `acct_id` (INTEGER)

**`PROJWBS` (Work Breakdown Structure)**
Columns: `wbs_id` (INTEGER), `proj_id` (INTEGER), `parent_wbs_id` (INTEGER), `wbs_name` (VARCHAR(100)), `wbs_short_name` (VARCHAR(40)), `wbs_level` (INTEGER)

**`TASK` (Activities)**
Columns: `task_id` (INTEGER), `proj_id` (INTEGER), `wbs_id` (INTEGER), `task_code` (VARCHAR(40)), `task_name` (VARCHAR(120)), `task_type` (VARCHAR(20)), `phys_complete_pct` (NUMERIC(5,2)), `early_start_date` (DATETIME), `early_end_date` (DATETIME), `late_start_date` (DATETIME), `late_end_date` (DATETIME), `act_start_date` (DATETIME), `act_end_date` (DATETIME), `total_float_hr_cnt` (NUMERIC(8,1))

**`TASKPRED` (Activity Relationships)**
Columns: `task_pred_id` (INTEGER), `task_id` (INTEGER), `pred_task_id` (INTEGER), `proj_id` (INTEGER), `pred_type` (VARCHAR(2)), `lag_hr_cnt` (NUMERIC(8,1))

**`RSRC` (Resources)**
Columns: `rsrc_id` (INTEGER), `parent_rsrc_id` (INTEGER), `rsrc_short_name` (VARCHAR(20)), `rsrc_name` (VARCHAR(100)), `rsrc_type` (VARCHAR(12))

**`TASKRSRC` (Activity Resource Assignments)**
Columns: `taskrsrc_id` (INTEGER), `task_id` (INTEGER), `rsrc_id` (INTEGER), `proj_id` (INTEGER), `target_qty` (NUMERIC(15,2)), `act_qty` (NUMERIC(15,2)), `remain_qty` (NUMERIC(15,2)), `target_cost` (NUMERIC(15,2)), `act_cost` (NUMERIC(15,2)), `remain_cost` (NUMERIC(15,2))

**`PROJ` (Project Definition)**
Columns: `PSPNR` (NUMC(8)), `PSPID` (CHAR(24)), `POST1` (CHAR(40)), `WERKS` (CHAR(4))

**`PRPS` (WBS Element Master Data)**
Columns: `PSPNR` (NUMC(8)), `POSID` (CHAR(24)), `POST1` (CHAR(40)), `PSPHI` (NUMC(8)), `OBJNR` (CHAR(22))

**`PRHI` (WBS Hierarchy Pointer)**
Columns: `POSNR` (NUMC(8)), `UP` (NUMC(8)), `DOWN` (NUMC(8)), `LEFT` (NUMC(8)), `RIGHT` (NUMC(8))

**`AUFK` (Order Master Data)**
Columns: `AUFNR` (CHAR(12)), `AUTYP` (NUMC(2)), `PSPEL` (NUMC(8))

**`AFVC` (Network Operations / Activities)**
Columns: `AUFPL` (NUMC(10)), `APLZL` (NUMC(8)), `VORNR` (CHAR(4)), `LTXA1` (CHAR(40)), `PROJN` (NUMC(8))

**`RESB` (Network Reservations / Components)**
Columns: `RSNUM` (NUMC(10)), `RSPOS` (NUMC(4)), `MATNR` (CHAR(18)), `WERKS` (CHAR(4)), `BDMNG` (QUAN(13,3)), `ENMNG` (QUAN(13,3)), `AUFNR` (CHAR(12))

**`COEP` (CO Object Line Items)**
Columns: `KOKRS` (CHAR(4)), `BELNR` (CHAR(10)), `BUZEI` (NUMC(3)), `OBJNR` (CHAR(22)), `WRTTP` (CHAR(2)), `WTGXXX` (CURR(15,2))

**`Document Register`**
Columns: `doc_id` (LONG), `document_number` (VARCHAR(40)), `title` (VARCHAR(255)), `discipline` (VARCHAR(50)), `revision_status` (VARCHAR(10)), `document_type_id` (LONG)

**`Transmittal Registry`**
Columns: `transmittal_id` (LONG), `doc_id` (LONG), `sender_user_id` (LONG), `recipient_user_id` (LONG), `transmittal_date` (DATETIME)

**`Workflow History`**
Columns: `workflow_instance_id` (LONG), `workflow_step_id` (LONG), `user_id` (LONG), `assigned_organization` (VARCHAR(100)), `status_label` (VARCHAR(20)), `days_late` (INTEGER)

**`Mail Module`**
Columns: `mail_id` (LONG), `mail_type_id` (LONG), `subject` (VARCHAR(255)), `sender_id` (LONG), `sent_date` (DATETIME)

**`worklogEntries` (Labor Log Table)**
Columns: `id` (UUID), `form_id` (UUID), `trade` (VARCHAR(100)), `headcount` (INTEGER), `timespan` (BIGINT)

**`materialsEntries` (Materials Log Table)**
Columns: `id` (UUID), `form_id` (UUID), `item` (VARCHAR(150)), `quantity` (NUMERIC(12,2)), `unit` (VARCHAR(20))

**`equipmentEntries` (Equipment Log Table)**
Columns: `id` (UUID), `form_id` (UUID), `item` (VARCHAR(150)), `timespan` (BIGINT), `quantity` (INTEGER)

**`Issues`**
Columns: `issue_id` (UUID), `title` (VARCHAR(255)), `root_cause_category` (VARCHAR(100)), `status` (VARCHAR(20)), `model_node_id` (VARCHAR(50))

**`Form Templates`**
Columns: `template_id` (UUID), `name` (VARCHAR(255)), `section_uid` (UUID)

**`BOM Schema`**
Columns: `bom_id` (VARCHAR(50)), `line_number` (VARCHAR(100)), `part_number` (VARCHAR(50)), `cut_length` (NUMERIC(10,2))

**`Material Master`**
Columns: `part_number` (VARCHAR(50)), `nominal_size` (NUMERIC(6,2)), `wall_thickness_schedule` (VARCHAR(10)), `asme_material_standard` (VARCHAR(50))

**`PMS Class` (Piping Material Specification)**
Columns: `pms_id` (VARCHAR(50)), `pressure_rating` (VARCHAR(20)), `gasket_type` (VARCHAR(50))

**`PCF Repository` (Piping Component Files)**
Columns: `pcf_file_id` (VARCHAR(50)), `isometric_drawing_ref` (VARCHAR(100)), `weld_joint_id` (VARCHAR(50))