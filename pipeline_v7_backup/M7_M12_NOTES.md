# CLAUSE AI — M7–M12 + UI v2 run notes (2026-07-11)

All modules stdlib-only Python 3. Run from `pipeline/`: `python3 m7_options.py` etc.
Server: `python3 app/server.py [port]` (default 8020) from `pipeline/`, then open http://localhost:PORT.

## Modules

| Module | Output | Result on frozen corpus |
|---|---|---|
| m7_options.py | out/options.json | 5 packages; all rejection windows EXPIRED (true calendar); decide concessions by 2026-10-06 (gate 2026-11-05 − 30d labelled assumption) |
| m8_margin.py | out/margins.json | 14 numeric margins: 10 THIN, 4 NEGATIVE; concession stack SUB-263353-01-R0 = 3.19% compound; energy rows on 4800 kW fleet (96.5→95.1% = 36.6 kW, 320,727 kWh/yr) |
| m9_vendor.py | out/vendors.json | AegisFire 86 / VoltEdge 86 → TARGETED_SAMPLING; Deccan 89; CryoCore 91, Trident 94 → STANDARD |
| m10_paperwork.py | out/lint.json, out/paperwork/ | 10 lint findings, 7/7 planted spec defects caught (DEF-001…007), 17 draft documents (RFIs, returned-submittal letters, impact notice), all marked DRAFT |
| m11_cx.py | out/cx_packs.json | 40 Cx tests; 2 STALE after ADD-003; 10 ready; 2 updated procedures drafted with provenance |
| m12_external.py | out/external.json | REAL documents: IIT-B tender + Liebert HPC brochure + Kidde Fluoro-K brochure. 5 requirements, 26 claims, **7 cross-document checks** — 3 REVIEW (2 ambient derating questions, 1 agent-identity gap: tender says Novec 1230, brochure never states FK-5-1-12 in text), 4 SATISFIABLE (50/55°C ratings, UL/FM listings, 0–54°C operating range vs 41.4°C site max). Page-cited quotes throughout. |

## Server v2 (app/server.py)

GET /api/{summary, graph, blastwave, queue, packages, verdicts/<pkg>?mode=pre|post,
ncr, options, margins, vendors, lint, paperwork, paperwork/doc?f=<md>, cx,
external, activity, meta} · POST /api/{recompute, blastwave/apply} — both POSTs
re-run m5→m11 and return per-module timings (~450 ms total).

## UI v2 (app/static/)

Full rebuild: index.html + style.css + app.js (vanilla, no deps, air-gapped).
13 hash-routed views, live clock/latency/ticker/provenance everywhere,
tariff slider (client-side ₹/kWh × server-computed kWh), doc modal, toast
with recompute timings, error overlay instead of blank screens.

### Graph crash fix (root cause)
Old build: spring force ∝ distance² → divergence → NaN → blank canvas.
New engine: seeded deterministic ring layout (mulberry32), clamped forces
(±0.9), velocity cap (±3.5 px/tick), alpha cooling with settle-freeze at 900
ticks, per-tick isFinite guards, spatial-grid repulsion, DPR-aware canvas,
pause on hidden tab, error overlay. Verified headless: 353 nodes / 711 edges,
0 runtime errors on #overview and #graph.

## Test log (this machine)
- node --check app.js: clean
- All 15 GET endpoints: 200
- POST recompute: ok, 8 modules timed
- POST blastwave/apply: ok
- Headless Chromium renders #overview (real metrics: 424/185/591/32) and
  #graph (353·711, settled) with zero error overlays

---

**2026-07-13 (v6):** the M12 external-checks page was removed — demo-only value,
not part of the product story. M13 (data-centre facility profile) replaces it in
the run. This file stays as historical run notes.
