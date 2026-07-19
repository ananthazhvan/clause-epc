# Manual document QA — corrected issue

Date: 2026-07-19 (Asia/Kolkata)

## Review performed

- Opened the specification HTML and compared its cover, clause pages, tables, spacing, colours and page breaks with the corresponding Chromium-rendered PDF.
- Opened the vendor submittal HTML and compared its cover and clause-by-clause statement with the corresponding PDF.
- Reviewed a rendered critical Part 2 page for all 12 specification sections in one inspection sheet.
- Reviewed the rendered compliance-statement page for all 22 submittal packages in one inspection sheet.
- Confirmed all PDFs are generated directly from the same HTML and print CSS; no secondary text-only PDF renderer is used.
- Confirmed browser-added dates, titles, local file paths and page-number headers are disabled.
- Confirmed specification clauses appear in the relevant CSI part instead of being repeated on every page.
- Confirmed every specification uses PART 1 — GENERAL, PART 2 — PRODUCTS and PART 3 — EXECUTION.
- Confirmed every submittal has distinct transmittal, technical schedule, compliance, evidence, traceability, inspection-plan and declaration pages.
- Confirmed tables remain within page boundaries and no inspected page showed overlap, clipping or horizontal overflow.

## Result

Manual document review passed after correction. Machine consistency checks remain supplementary and do not replace this review.

## CSI hierarchy correction — 2026-07-19

- Removed duplicated list markers such as visually repeated A/A and A/B sequences.
- Removed fabricated article numbers 2.1.9 and 2.1.10.
- Removed blue requirement callout blocks from the specification body.
- Rebuilt each section using article → uppercase paragraph → numbered subparagraph hierarchy.
- Verified every scheduled requirement is located at its exact clause position. For example, Section 26 33 53 places rated output at 2.2.A and efficiency at 2.4.C.
- Programmatically inspected all 12 specifications for correct article and paragraph positions, then visually inspected the corrected UPS 2.1/2.2 and 2.3/2.4 pages.
