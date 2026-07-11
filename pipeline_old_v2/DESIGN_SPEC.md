# CLAUSE AI — Design & Technical Specification

For use with OpenDesign or any design agent. This is the canonical spec for the
CLAUSE AI web console. The reference implementation lives in `app/static/`
(`index.html`, `style.css`, `app.js`) and runs against the API in
`app/server.py`. A design agent may restyle freely **within the constraints
marked MUST**; everything else is a strong default.

---

## 1. Product intent (read this first)

CLAUSE is a **requirement ledger** for data-centre EPC delivery. It reads
specifications, compiles them into machine-checkable rules, verifies vendor
submittals against them with exact quotes, and prices the consequences
(schedule, margin, paperwork, commissioning).

Design consequences of that intent:

- **Evidence is the hero.** Every verdict must sit next to the two quotes it
  rests on (spec quote + submittal quote, each with page number). MUST never
  hide the quotes behind an extra click at the row level.
- **It must feel live, not preloaded.** Every view MUST show fetch latency and
  artifact compute time ("fetched 12 ms · computed 2026-07-11 16:41"). The
  topbar MUST have a working recompute action that re-runs the pipeline
  server-side and reports per-module timings.
- **Calm, forensic, anti-flashy.** This is an instrument, not a dashboard for
  a lobby TV. No gradients-for-decoration, no glassmorphism, no animation
  longer than 150 ms except the skeleton shimmer. It should look like a tool
  an engineer trusts at 2 AM.
- **Honesty markers are part of the design.** DRAFT badges on generated
  paperwork, "labelled assumption" notes, and the manufactured-corpus vs
  real-documents distinction on the External screen are content, not chrome.
  MUST keep them.

## 2. Design tokens (MUST use as CSS custom properties)

```css
--bg0:#08090c;  /* page      */  --bg1:#0e1117; /* panel     */
--bg2:#141922;  /* inset     */  --bg3:#1b2230; /* raised    */
--line:rgba(255,255,255,.07);    --line-strong:rgba(255,255,255,.13);
--tx:#e6eaf2;   /* primary   */  --tx2:#8b94a7; /* secondary */
--tx3:#5c6577;  /* tertiary  */
--acc:#6ea8ff;  /* accent / links / primary action */
--ok:#3fb97f;   --warn:#e8b453;  --bad:#ff5c69;  --purple:#a78bfa;
/* each accent has a -dim variant at ~13% alpha for badge backgrounds */
--mono:"SF Mono","JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;
--sans:-apple-system,"Inter","Segoe UI",system-ui,Roboto,sans-serif;
--r:10px; --r-sm:6px;
```

Rules:
- Base font 13.5 px sans; ALL numbers, IDs, quotes, timestamps in `--mono`
  with `font-variant-numeric: tabular-nums`.
- Verdict colour map is semantic and MUST NOT be remapped:
  ok/green = COMPLY, SATISFIABLE, READY, CLOSED · red = DEVIATION,
  FALSE_COMPLY, CHECK_FAILS, EXPIRED, OPEN · amber = MISSING_EVIDENCE, THIN,
  STALE · purple = NEEDS_REVIEW, REVIEW · grey = NOT_ADDRESSED.
- Contrast: body text vs panel ≥ 7:1, secondary ≥ 4.5:1.

## 3. Layout (MUST)

CSS grid, full viewport, no page scroll (only `main` scrolls):

```
┌────────────────────────────────────────────── 48px topbar
│ CLAUSE · tagline | net-dot+latency | LLM spend | clock | [Recompute]
├─────────┬────────────────────────────────────
│ 218px   │  main view, 22/26px padding
│ sidebar │
├─────────┴──────────────────────────────────── 30px ticker
│ LIVE API · GET /api/graph 200 9ms · …
```

Sidebar nav groups (order fixed):
- **OVERSIGHT**: Overview · Decision Clock · Queue
- **EVIDENCE**: Review · Graph · Spec Defects · External (real docs)
- **CONSEQUENCE**: Blast Wave · Margins · Vendors
- **OUTPUT**: Paperwork · Commissioning · NCR Register

Nav items may carry count pills (e.g. Review shows open deviations in red).
Active item: `--acc-dim` background + accent text. Hash routing
(`#review/SUB-…/post`), so every screen is deep-linkable.

## 4. Component inventory

- **Metric card**: label (10.5px uppercase, letter-spaced, `--tx3`) over a
  26px mono number, optional one-line sub-caption. 4-up grid on desktop.
- **Badge**: 10px mono uppercase chip, dim background + full-strength text of
  its semantic colour.
- **Evidence quote block**: mono 11px on `--bg2`, 2px left border — blue
  (`--acc`) for spec/requirement, amber (`--warn`) for submittal/claim.
  Always preceded by a source line: `SPEC 2.3.1.E p14 · amended by ADD-003`.
- **Evidence pair**: requirement quote and claim quote side-by-side
  (1fr/1fr, stacks under 1100px).
- **Table**: sticky uppercase header row, hairline row borders, right-aligned
  mono numerics, row hover +2% white.
- **Skeleton**: shimmer bars while any fetch is in flight (MUST — never a
  blank panel).
- **Toast**: bottom-right, used for recompute timings (module name + ms per
  row), auto-dismiss 9 s.
- **Doc modal**: centred 780px reader for generated Markdown paperwork with
  DRAFT provenance retained.
- **Error overlay**: any runtime JS error renders a red mono banner into the
  view. MUST — a blank screen is a forbidden failure mode.

## 5. Screens (content contracts)

Each screen states its API source; shapes are exactly what `app/server.py`
returns.

1. **Overview** — `GET /api/summary` + `/api/options`. 8 metric cards
   (rules 424, claims 185, checks, deviations 32 with "19 stamped Comply",
   lint findings, real-doc checks, days-to-decide countdown, precision) +
   pre/post addendum verdict table with deltas.
2. **Decision Clock** — `GET /api/options`. Hero countdown (46px mono, amber)
   to `decide_concessions_by`; table of per-package rejection economics
   (need-on-site, last safe rejection, EXPIRED status, slip-if-rejected-today,
   float). The expired dates are true and MUST be shown, not softened.
3. **Queue** — `GET /api/queue`. Severity-ranked dispositions; severity > 40
   renders red.
4. **Review** — `GET /api/packages`, `GET /api/verdicts/<pkg>?mode=pre|post`.
   Package switcher + pre/post toggle; one evidence-pair row per check with
   verdict badge, `vendor stamped COMPLY` badge on false-complies, reason line.
5. **Graph** — `GET /api/graph` (353 nodes / 711 edges; node `{id,type,label,
   status,meta}`, edge `{s,t,type}`). Canvas force layout, spec in §6.
6. **Spec Defects** — `GET /api/lint`. One card per finding: lint-kind badge,
   summary, quote A/quote B with pages, pointer to its auto-drafted RFI.
7. **External (real docs)** — `GET /api/external`. MUST open with the honesty
   statement (manufactured demo corpus vs real IIT-B tender + Liebert + Kidde
   brochures), doc cards with page counts, then evidence-pair checks incl.
   REVIEW verdicts with their reasoning notes.
8. **Blast Wave** — `GET /api/blastwave`, `POST /api/blastwave/apply`.
   Impact metric cards (rules amended, verdict flips, POs invalidated with ₹
   exposure, Cx stale) + flip table + invalidated-PO table + a danger-styled
   "Re-apply addendum live" button that actually recomputes.
9. **Margins** — `GET /api/margins`. Ledger classed NEGATIVE/THIN/OK; energy
   penalty table with a tariff slider (₹4–14/kWh) recomputing cost/year
   client-side from server-computed `extra_kwh_per_year`. Caption MUST say the
   maths just ran in the browser.
10. **Vendors** — `GET /api/vendors`. Trust bar (green ≥90, amber ≥70, red
    below) + checks/deviations/false-comply/exposure + review-intensity badge.
11. **Paperwork** — `GET /api/paperwork`, `GET /api/paperwork/doc?f=…`.
    Grouped lists (RFI drafts / returned-submittal letters / impact notices)
    opening in the doc modal.
12. **Commissioning** — `GET /api/cx`. Counts + test table with STALE badges
    and "updated draft" buttons into the doc modal.
13. **NCR Register** — `GET /api/ncr`.

## 6. Graph engine (MUST follow — this fixed a real crash)

The previous build blank-screened: spring force grew with distance²,
positions diverged to NaN, canvas went blank. The constraints below are the
fix; keep all of them in any re-implementation.

- **Deterministic init**: seeded PRNG (mulberry32, seed 1337); nodes placed
  on concentric rings by type (section → clause → package → po → activity →
  cx → addendum). Same layout every load. No `Math.random()`.
- **Bounded physics**: spring force `clamp((d − 46) × 0.012, ±0.9)`;
  repulsion `clamp(340/d², ±0.9)` on a 70px spatial grid (near-O(n), skip
  pairs beyond 90px); velocity clamped ±3.5 px/tick; damping 0.82; weak
  centering force.
- **Cooling**: alpha 1 → ×0.996/tick → floor 0.02; force-settle at 900 ticks.
  Physics stops when settled; only redraws (drag re-heats to α 0.25).
- **Guards**: per-tick `isFinite(x,y)` reset; `try/catch` around init and a
  visible error overlay; pause simulation when `document.hidden`; canvas
  sized at `devicePixelRatio` (cap 2).
- **Interaction**: drag nodes, drag background to pan, wheel-zoom to cursor
  (0.25–5×), hover tooltip (type, label, status, meta), labels appear on
  hubs at zoom > 1.3×.
- **Encoding**: node colours — section #7aa2ff, clause #5b8dd6, package
  #e0b458, po #68c7a5, activity #9a86d8, cx #d87ba8, addendum #ff5d5d; radius
  ∝ √degree (3–14px); red ring on nodes and red edges for consequence states
  {DEVIATION, INVALID, STALE, AMENDS}; normal edges 8% white.

## 7. Liveness contract (MUST)

- Topbar: green/red network dot + last fetch ms; live IST clock (1 s tick);
  LLM spend from `/api/summary`.
- Ticker: poll `GET /api/activity` every 4 s, render last ~14 requests
  (method, path, status, ms), newest first.
- Recompute: `POST /api/recompute` → toast with per-module ms (8 modules,
  ~450 ms total) → refresh meta + re-render current view.
- Provenance line on every view: fetch ms + artifact mtime from `/api/meta`.

## 8. Voice & microcopy

Sentence case; verbs over nouns ("Recompute ledger"); no exclamation marks;
no marketing adjectives. Say what the machine did and what it rests on:
"19 stamped 'Comply' by the vendor", "labelled assumption: 30-day approval
lead", "recomputed in your browser just now". Empty states name the fix
(`Is the server running? python3 app/server.py`).

## 9. Performance & quality bars

- No frameworks, no build step, no external fonts/CDNs (must run air-gapped);
  vanilla ES2020, one JS file, one CSS file.
- First contentful render < 300 ms on localhost; graph steady-state ≤ 60 fps
  with 353 nodes on integrated graphics; JSON payloads ≤ 150 KB per view.
- Keyboard: all nav reachable by Tab; modal closes on backdrop click and Esc.
- `node --check` clean; zero console errors on all 13 routes headless.
