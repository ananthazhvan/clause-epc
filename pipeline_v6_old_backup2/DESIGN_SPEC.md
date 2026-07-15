# CLAUSE console — design spec v2 · “ink & paper”

One idea: **an engineer’s field ledger, printed and stamped.** Paper background, ink
keylines, vermillion used only where judgement was exercised. Nothing decorative that
isn’t also information.

## Tokens
- Paper: `--paper #f3ecdf`, panels `#faf7ef`, inset `#ece4d2`, raised `#e3d9c4`
- Ink: `#211c14` / `#5a5140` / `#94886e`
- Vermillion (hanko, judgement only): `#c9442a` · ok `#3f7d4e` · warn `#a07416` · bad `#b3382e` · purple (draft) `#6d5f92`
- Keyline: `1.5px solid ink`; card shadow `3px 3px 0` solid — print offset, not blur
- Type: Iowan Old Style/Palatino/Georgia for voice; ui-monospace for every number

## Layout
- Grid rows `50px / 1fr / 58px / 24px`: header · view · **bottom tabs** · live ticker
- Bottom tabs (his call): grouped by job — Hub | Overview·Clock·Queue | Review·Graph·Defects·External | Blast·Margins·Vendors | Paperwork·Cx·NCR; active tab = inverted ink + vermillion shadow
- Header right: net dot + last-fetch ms, cumulative LLM spend, clock, Recompute, Settings gear

## Language of the UI
- **Stamps, not badges.** Verdicts render rotated ~-1°, uppercase, keyline border. A
  vendor’s unearned “Comply” renders as a struck-through stamp — the visual argument.
- **Two quotes side by side** everywhere a verdict appears (spec vs submittal, page-cited).
- **Liveness contract:** every screen shows fetch latency + timestamp; ticker replays the
  server access log; Recompute and Blast-apply re-run real modules and show real ms.
- Icons: hand-drawn 24-grid SVG set (`icons.js`), one per tab, stroke 1.6, ≤3 paths.

## Hub (landing)
- Left: canvas constellation — CLAUSE seal (vermillion hanko block) center, five sources
  orbiting with live counts (files/rules/activities/POs/tests·NCRs), packets flowing inward,
  assemble-in intro, click a source → its ledger view.
- Right: **dropzone**. sha-256 fingerprint against corpus manifest → “IN LEDGER” stamp, or
  “NEW” + live numeric-claim harvest (pages, hits, page-cited quotes). Then “Run the
  pipeline” replays real per-module timings as a stagelist.

## Graph
- Same bounded physics (seeded mulberry32, clamped forces, settle cap — NaN impossible).
- Hover = neighbor highlight (rest fade to 12%). Click = **dossier** (`/api/node?id=`):
  what this clause does to you — verdicts w/ stamps, the two quotes, money riding on the
  section, tests that prove it, neighbors (clickable), deep-links into Review/Blast.
- `#graph/<node-id>` deep-link focuses + opens dossier; “connections” fab on Clock/Review/Queue/Vendors.

## Settings
- BYO model: OpenAI-compatible base URL + key + model, saved to `out/llm_config.json`,
  masked readback, one-click round-trip test. Local guide (`LOCAL_LLM.md`): Ollama/LM
  Studio/llama.cpp, 4B models on 8 GB laptops — nothing leaves the machine.
