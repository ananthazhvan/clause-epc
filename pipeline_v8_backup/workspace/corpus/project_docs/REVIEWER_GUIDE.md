# Reviewer Guide — find one planted error per tier, by hand

Do these three exercises in order. You are playing the role of the consulting engineer whose job
CLAUSE AI automates. Each tier needs strictly more intelligence than the one before it — that
escalation IS the product story.

---

## Tier 1 — direct number mismatch (a lookup can catch this)

**Open:** `specs/spec_26_33_53.pdf`, **page 4** → find clause **26 33 53 Part 2.3.2.C**:

> "Battery system nominal DC bus voltage shall be **480 VDC** to match the UPS inverter..."

**Then open:** `submittals/submittal_VoltEdge_Battery_R0.pdf`, **page 2** (Technical Datasheet) →
find row **Nominal DC Bus Voltage: 400 VDC**.

**The error:** 400 ≠ 480. One requirement, one claim, same units, direct contradiction.

**The kicker:** same submittal, **page 3** (Compliance Matrix) → the row for **2.3.2.C** says
**"Comply"**. The vendor *claims* compliance while their own datasheet two pages earlier proves
otherwise. Catching this needs two pages of one document plus one clause of the spec.

---

## Tier 2 — the rule changed mid-project (needs cross-document reasoning)

**Open:** `project_docs/addendum_3.pdf` (1 page) → first change:

> Reference: Section 26 33 53, **Part 2.3.4** — DELETE '96%' INSERT '**96.5%**'

An addendum is an official amendment: it silently rewrites the spec for everyone, dated 15-06-2026.

**Then open:** `specs/spec_26_33_53.pdf`, **page 4** → **Part 2.3.4** still reads "minimum of
96.0%..." — the spec document itself is now *stale*. That is realistic: nobody reprints specs
mid-project.

**Then open:** `submittals/submittal_VoltEdge_UPS_R1.pdf`, **page 2** → efficiency rows:
**96.2% / 96% / 96.2%** at 100/75/50% load.

**The error:** R1 passed the *original* spec (≥96.0) — and every one of those numbers **fails the
post-addendum requirement (≥96.5)**. No single document contains a contradiction. The error only
exists when you read three documents in the right chronological order. This is the "addendum blast
wave": one line in an addendum silently flips verdicts across every affected submittal.

---

## Tier 3 — the footnote trap (needs actual understanding of conditions)

**Open:** `specs/spec_26_33_53.pdf`, **page 3** → clause **26 33 53 Part 2.2.2.B**:

> efficiency at 75% and 50% load shall each be minimum **96.0%**... "All efficiency values shall be
> measured in **VFI mode with harmonic filters active**."

(VFI = double-conversion, the UPS's protected-but-lossy mode. The measurement *condition* is part
of the requirement.)

**Then open:** `submittals/submittal_VoltEdge_UPS_R0.pdf`, **page 2** → the table says
**"Efficiency at 50% Load: 96.1%"** with a superscript. Now read the footnote at the bottom of the
page:

> "Efficiency reduces to **95.1%** under VFI mode when harmonic filters are active at 50% load."

**The error:** the table's 96.1% is measured in the *wrong condition*. The number that matches the
spec's required condition is **95.1% → FAIL**. And the compliance matrix (**page 4**) marks 2.2.2.B
"Comply" anyway. A number-matcher sees 96.1 ≥ 96.0 and passes it; only something that understands
*conditions* catches it. This is where LLM extraction earns its place: every stated value must be
captured **with its condition**, table value and footnote value as two separate claims, and the
deterministic checker then picks the claim whose condition matches the spec's.

---

## What this proves about the system

| Tier | What it takes | Who can do it |
|---|---|---|
| 1 | Compare two numbers with the same meaning | Regex/script — IF extraction is perfect |
| 2 | Order documents in time; apply overrides | Graph of documents + effective-date logic |
| 3 | Read conditions, footnotes, fine print | LLM extraction with condition-aware claims |

The corpus contains 48 planted deviations across these tiers (18 T1 / 20 T2 / 10 T3), all indexed
in `_answer_key/labels.json`. A reviewer who finds all 48 by hand needs days. The pipeline should
do it in minutes — and every finding it reports must carry a verbatim quote + page number so a
human can verify it in seconds, exactly like you just did.
