# Corpus v2 — "Meridian-2" authentic hyperscale DC corpus

## Why this design (read first)

The IITB HPC-BYOH document was dropped for a genre reason, not a size reason:
it is an Indian public-tender BOQ (Schedule of Requirements + prose specs),
not a hyperscale EPC specification. Real hyperscale/colo projects issue specs
in **CSI MasterFormat** sections — which is exactly the grammar CLAUSE's M1/M2
already parse. So corpus v2 keeps the CSI format (that IS the authentic
format) and imports authenticity three other ways:

1. **Real standards cited inside every clause** — ASHRAE TC 9.9, TIA-942-B,
   Uptime Tier III, NFPA 2001/72, IEEE 519, IEC 62040-3, ISO 14644, EN 50600.
   Requirements reference the real clause families the way real specs do.
2. **Real supply-chain shape** — 59 submittal packages consolidating to ~55
   unique vendors (the approved-makes many-to-many insight: one vendor like a
   Schneider-analogue supplies 7 different line items, so one vendor failure
   fans out across sections — M9 vendor scoring and the M5 blast wave will
   light this up for free).
3. **System-of-record ingestion** — schedule arrives as Primavera P6 XML,
   procurement as SAP OData JSON, shipment status as a visibility feed
   (connectors already shipped in v7; regenerate samples per §6).

Everything stays synthetic ON PURPOSE: synthetic means we can plant known
violations and hold a sealed answer key — that is the accountability story.

## 1. Spec sections (14 files, CSI MasterFormat)

| file | CSI section | title | real standards to cite |
|---|---|---|---|
| spec_21_22_00 | 21 22 00 | Clean-Agent Fire Suppression (FK-5-1-12) | NFPA 2001, ISO 14520 |
| spec_21_10_00 | 21 10 00 | Fire Detection & VESDA | NFPA 72, EN 54-20 |
| spec_23_64_26 | 23 64 26 | Water-Cooled Screw Chillers | AHRI 550/590, ASHRAE 90.1 |
| spec_23_81_23 | 23 81 23 | In-Row Cooling / CRAH | ASHRAE TC 9.9 (A1 class), AHRI 1360 |
| spec_23_09_00 | 23 09 00 | BMS / EPMS | BACnet ASHRAE 135, EN 50600-2-3 |
| spec_26_32_13 | 26 32 13 | Diesel Generator Sets | ISO 8528-5 G3, NFPA 110 Type 10 |
| spec_26_33_53 | 26 33 53 | Static UPS (already exists — port + tighten) | IEC 62040-3 Class 1, IEEE 519 |
| spec_26_24_13 | 26 24 13 | LV Switchboards | IEC 61439-2, arc-flash IEEE 1584 |
| spec_26_05_19 | 26 05 19 | LV Cables (FRLS/LSZH) | IEC 60502-1, IEC 60332-3 |
| spec_26_05_26 | 26 05 26 | Earthing & Bonding | IEEE 80, <1 Ω grid resistance |
| spec_27_15_00 | 27 15 00 | Structured Cabling Cat 6A | TIA-568.2-D Class EA, ISO/IEC 11801 |
| spec_28_10_00 | 28 10 00 | Access Control & Biometrics | IEC 60839, UL 294 |
| spec_28_23_00 | 28 23 00 | Video Surveillance | IEC 62676, ONVIF Profile S |
| spec_11_53_00 | 11 53 00 | Racks & Containment | EIA-310-E, 1500 kg static load |

Grammar: EXACTLY the existing corpus grammar (see pipeline/CORPUS_FORMAT.md
§Specification grammar) — `PART n`, numbered clauses `3.4.2.H`, one checkable
requirement per clause, quantitative values with units. A real standard is
cited in the clause text; the checkable number still lives in the clause
itself (CLAUSE verifies the clause, not the external standard).

## 2. Submittals — 59 packages, ~55 unique vendors

- Distribution: chillers 4, in-row 5, UPS 6, gensets 4, switchboards 4,
  cables 5, earthing 2, fire suppression 4, detection 3, cabling 5, access 4,
  CCTV 4, racks 5, BMS 4 = 59.
- Vendor consolidation: create ~55 named vendors; 3–4 "platform" vendors
  supply multiple sections (e.g. `VoltEdge` does UPS + switchboards + cables)
  so the vendor-risk fan-out is real in the data.
- Each submittal: 3–6 pages, transmittal cover (matching CORPUS_FORMAT.md
  §Submittal grammar: SUB-<section>-<seq>-R0 numbering), product data with
  specific numeric values, compliance matrix table.
- Naming: `submittal_<Vendor>_<Package>_R0.pdf` (text-based PDF or .md→PDF).

## 3. Planted-violations budget (the sealed answer key)

- ~15% of all checkable claims FAIL (subtle-realistic: capacity quoted at
  35 °C where spec demands 45 °C; THD 8% vs IEEE 519 5%; Class EA margin
  tested at 100 m not 90 m …)
- ~8% NEI: requirement simply never addressed in the submittal.
- Remainder genuinely compliant.
- EVERY planted item recorded in `_answer_key/violations_key.json`:
  `{submittal, page, parameter, spec_clause, spec_value, submitted_value,
  expected_verdict: FAIL|NEI, reason}`. Nothing else in the corpus mentions
  them. `_answer_key/` is never uploaded (contamination rules already ban it).

## 4. Registers (canonical CSVs first, wire formats second)

- `registers/schedule.csv` — ~120 activities, realistic EPC WBS (civils →
  substation → LV → mechanical → IT fit-out → Cx L1-L5), `;`-joined
  predecessors, float, critical path through chiller delivery + Cx.
- `registers/po_register.csv` — 59 POs, one per submittal package, vendor
  names matching §2, INR values, realistic lead times (chillers 30+ weeks).
- `registers/cx_test_register.csv` — L2–L5 tests keyed to spec clauses.
- `registers/rfi_log.csv` — 15–25 RFIs, some referencing planted conflicts.

## 5. Addendum (blast-wave demo)

One addendum PDF changing 2–3 quantitative requirements (e.g. UPS runtime
5 → 10 min at N load; chiller CHW setpoint change) — picked to hit the
critical path and at least 4 POs, so M5's blast wave is dramatic and TRUE.

## 6. Connector wire formats (after registers are final)

```
cd pipeline
python3 connectors/make_samples.py --corpus ../corpus_v2 --check
```

regenerates `corpus_v2/connectors/{*_p6.xml, *_sap_odata.json,
*_visibility.json}` from the new registers with exact roundtrip verification.
Demo flow: upload the P6 XML + SAP JSON instead of the CSVs.

## 7. Build order + verification loop (non-negotiable)

1. Specs → 2. registers → 3. submittals + violations key → 4. addendum →
5. connector samples → 6. **verification loop**: upload corpus_v2 cold, run
M1, and require: every spec classifies as spec, every submittal as submittal,
zero `external`/`unknown` misclassifications. If a file misclassifies, FIX
THE DOCUMENT to match the corpus grammar — never loosen the classifier.
Then full M1→M13 run; then `eval_recall.py` against the violations key.
