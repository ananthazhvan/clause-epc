# test_docs - MERIDIAN-1 Data Centre, Hall A

A small, hand-built, fully interlinked EPC document drop. Every ID in any file
resolves to a real object in another file. Six planted compliance items
(answer_key/violations_key.json), five cross-source insights that CANNOT be
derived from any single document.

## Contents
- specs/            3 CSI sections (HTML; print to PDF via headless Chrome if needed)
- addenda/          ADD-001 raising chiller COP 6.0 -> 6.3 (before/after test)
- submittals/       5 packages incl. one R0->R1 revision pair
- schedule/         MERIDIAN1.xer - genuine P6 XER table format (ERMHDR/%T/%F/%R)
- registers/        schedule.csv, po_register.csv, cx_register.csv (pipeline-ingestible)
- procurement/      sap_po_odata.json - SAP S/4HANA API_PURCHASEORDER_PROCESS_SRV shape
- supply_chain/     fourkites_shipments.json - loads, GPS breadcrumbs, ETAs, exceptions
- quality/          acc_qms_issues.json - Autodesk Construction Cloud Issues shape
- answer_key/       ground truth: 6 planted items + 5 cross-source insights
- MASTER_CONTENT.txt  plain text of every narrative document (for manual PDF creation)

## The one-decision walkthrough
"Will Hall A hit Ready-for-Service?" requires: P6 (A2010 zero float) + SAP
(PO 4500012304) + FourKites (SHP-88121 delayed, ETA 08-10) + spec/addendum
(COP 6.3) + submittal R1 (closes the deviation) + QMS (QI-001 weld NCR open).
Six sources, one answer. That is the ontology pitch in one example.

Make PDFs (optional):
  for f in specs/*.html submittals/*.html addenda/*.html; do
    chromium --headless --disable-gpu --print-to-pdf="${f%.html}.pdf" "$f"; done
