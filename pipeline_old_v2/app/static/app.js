/* CLAUSE AI frontend v2 - vanilla JS, no dependencies.
   Every view fetches from the live API and stamps fetch latency +
   artifact compute time, so nothing on screen is preloaded. */
"use strict";

/* ---------------- helpers ---------------- */
const $ = (s, el) => (el || document).querySelector(s);
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const fmtINR = (n) => "\u20b9" + Number(n).toLocaleString("en-IN");
const NET = { last: null, ok: true };

async function api(path) {
  const t0 = performance.now();
  try {
    const r = await fetch("/api/" + path);
    const ms = Math.round(performance.now() - t0);
    NET.last = ms; NET.ok = r.ok;
    updateNetDot();
    if (!r.ok) throw new Error(path + " -> " + r.status);
    const j = await r.json();
    j.__ms = ms;
    return j;
  } catch (e) {
    NET.ok = false; updateNetDot();
    throw e;
  }
}

function updateNetDot() {
  const d = $("#net-dot"), l = $("#net-lat");
  if (!d) return;
  d.className = "dot " + (NET.ok ? "ok" : "bad");
  l.textContent = NET.last == null ? "\u2014" : NET.last + " ms";
}

function badge(text, cls) { return `<span class="badge ${cls}">${esc(text)}</span>`; }
function verdictBadge(v) {
  const map = { COMPLY: "b-ok", DEVIATION: "b-bad", FALSE_COMPLY: "b-bad",
    MISSING_EVIDENCE: "b-warn", NOT_ADDRESSED: "b-mut", NEEDS_REVIEW: "b-purple",
    SATISFIABLE: "b-ok", CHECK_FAILS: "b-bad", REVIEW: "b-purple",
    OPEN: "b-bad", CLOSED: "b-ok", STALE: "b-warn", READY: "b-ok", EXPIRED: "b-bad" };
  return badge(v, map[v] || "b-mut");
}
function provenance(ms, artifact) {
  const when = META.artifacts && artifact && META.artifacts[artifact];
  return `<span class="provenance">fetched <b>${ms} ms</b>${when ? ` &middot; computed <b>${esc(when.replace("T", " "))}</b>` : ""}</span>`;
}
function skeleton(rows) {
  let h = "";
  for (let i = 0; i < (rows || 5); i++) h += `<div class="skel" style="height:${i ? 15 : 26}px;margin:10px 0;width:${88 - i * 9}%"></div>`;
  return `<div class="card">${h}</div>`;
}
function daysBetween(a, b) { return Math.round((new Date(b) - new Date(a)) / 86400000); }

/* ---------------- shell: clock, ticker, meta ---------------- */
let META = {};
setInterval(() => {
  const d = new Date();
  $("#clock").textContent = d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) +
    " " + d.toLocaleTimeString("en-IN", { hour12: false });
}, 1000);

async function pollActivity() {
  try {
    const a = await fetch("/api/activity").then((r) => r.json());
    const t = $("#ticker");
    t.innerHTML = a.events.slice(-14).reverse().map((e) =>
      `<span><b>${esc(e.method)}</b> ${esc(e.path)} <span class="${e.status < 400 ? "ok" : "bad"}">${e.status}</span> ${e.ms}ms</span>`
    ).join("");
  } catch (e) { /* server down; dot already red */ }
}
setInterval(pollActivity, 4000);

/* ---------------- router ---------------- */
const VIEWS = [
  { group: "Oversight", id: "overview", label: "Overview" },
  { group: "Oversight", id: "clock", label: "Decision Clock" },
  { group: "Oversight", id: "queue", label: "Queue" },
  { group: "Evidence", id: "review", label: "Review" },
  { group: "Evidence", id: "graph", label: "Graph" },
  { group: "Evidence", id: "lint", label: "Spec Defects" },
  { group: "Evidence", id: "external", label: "External (real docs)" },
  { group: "Consequence", id: "blast", label: "Blast Wave" },
  { group: "Consequence", id: "margins", label: "Margins" },
  { group: "Consequence", id: "vendors", label: "Vendors" },
  { group: "Output", id: "paperwork", label: "Paperwork" },
  { group: "Output", id: "cx", label: "Commissioning" },
  { group: "Output", id: "ncr", label: "NCR Register" },
];
const NAV_COUNTS = {};

function renderNav() {
  const groups = {};
  VIEWS.forEach((v) => { (groups[v.group] = groups[v.group] || []).push(v); });
  $("#nav").innerHTML = Object.entries(groups).map(([g, items]) =>
    `<div class="nav-group"><h4>${g}</h4>` + items.map((v) => {
      const c = NAV_COUNTS[v.id];
      return `<a class="nav-item${location.hash === "#" + v.id ? " active" : ""}" href="#${v.id}">` +
        `<span>${v.label}</span>${c ? `<span class="pill ${c.cls || ""}">${c.n}</span>` : ""}</a>`;
    }).join("") + "</div>").join("");
}

window.addEventListener("hashchange", route);
async function route() {
  stopGraph();
  const id = (location.hash || "#overview").slice(1).split("/")[0];
  renderNav();
  const main = $("#main");
  main.innerHTML = skeleton(6);
  try {
    await (RENDER[id] || RENDER.overview)(main);
  } catch (e) {
    main.innerHTML = `<div class="empty">Failed to load: <code>${esc(e.message)}</code><br><br>` +
      `Is the server running? <code>python3 app/server.py</code></div>`;
  }
}

/* ---------------- views ---------------- */
const RENDER = {};

RENDER.overview = async (main) => {
  const [s, opts] = await Promise.all([api("summary"), api("options")]);
  const post = s.verdicts_post || {}, pre = s.verdicts_pre || {};
  const total = Object.values(post).reduce((a, b) => a + b, 0);
  NAV_COUNTS.review = { n: post.DEVIATION || 0, cls: "bad" };
  NAV_COUNTS.lint = { n: s.lint_findings, cls: "warn" };
  renderNav();
  const gate = opts.commissioning || {};
  const days = gate.decide_concessions_by ? daysBetween(META.today || new Date(), gate.decide_concessions_by) : null;
  $("#top-spend").innerHTML = `LLM spend <b>$${s.llm_spend_usd}</b>`;
  main.innerHTML = `
  <div class="view-head"><h1>Overview</h1>${provenance(s.__ms)}</div>
  <div class="view-sub">Machine-verified requirement ledger for a 6-package data-centre EPC submittal cycle.
  Every number below is recomputed from artifacts on disk &mdash; press <b>Recompute ledger</b> to watch it happen.</div>
  <div class="grid c4">
    <div class="card"><h3>Requirements compiled</h3><div class="metric acc">${s.rules}</div><div class="metric-sub">from 6 spec sections + addendum</div></div>
    <div class="card"><h3>Vendor claims extracted</h3><div class="metric">${s.claims}</div><div class="metric-sub">from 7 submittal packages</div></div>
    <div class="card"><h3>Checks executed</h3><div class="metric">${total}</div><div class="metric-sub">deterministic comparator, post-addendum</div></div>
    <div class="card"><h3>Deviations found</h3><div class="metric bad">${post.DEVIATION || 0}</div><div class="metric-sub">${s.false_comply_post} stamped &ldquo;Comply&rdquo; by the vendor</div></div>
  </div>
  <div class="grid c4 mt">
    <div class="card"><h3>Spec defects (linter)</h3><div class="metric warn">${s.lint_findings}</div><div class="metric-sub">defects in the spec itself, pre-vendor</div></div>
    <div class="card"><h3>Real-document checks</h3><div class="metric purple">${s.external_checks}</div><div class="metric-sub">live on IIT-B tender + 2 vendor brochures</div></div>
    <div class="card"><h3>Concession deadline</h3><div class="metric ${days != null && days < 30 ? "bad" : "warn"}">${days != null ? days + "<small>days</small>" : "\u2014"}</div><div class="metric-sub">decide by ${esc(gate.decide_concessions_by || "?")} (gate ${esc(gate.gate_activity || "")})</div></div>
    <div class="card"><h3>Verification accuracy</h3><div class="metric ok">${s.eval_post ? Math.round(s.eval_post.precision * 100) + "<small>%</small>" : "\u2014"}</div><div class="metric-sub">precision vs frozen answer key &middot; 0 false alarms</div></div>
  </div>
  <div class="card mt">
    <h3>Verdict distribution &mdash; pre vs post Addendum 3</h3>
    <table><thead><tr><th>Verdict</th><th class="num">Pre</th><th class="num">Post</th><th class="num">&Delta;</th></tr></thead><tbody>
    ${["COMPLY", "DEVIATION", "NEEDS_REVIEW", "MISSING_EVIDENCE", "NOT_ADDRESSED"].map((k) =>
      `<tr><td>${verdictBadge(k)}</td><td class="num">${pre[k] || 0}</td><td class="num">${post[k] || 0}</td>` +
      `<td class="num">${(post[k] || 0) - (pre[k] || 0) > 0 ? "+" : ""}${(post[k] || 0) - (pre[k] || 0)}</td></tr>`).join("")}
    </tbody></table>
  </div>`;
};

RENDER.clock = async (main) => {
  const o = await api("options");
  const gate = o.commissioning || {};
  const days = gate.decide_concessions_by ? daysBetween(META.today || new Date(), gate.decide_concessions_by) : "?";
  main.innerHTML = `
  <div class="view-head"><h1>Decision Clock</h1>${provenance(o.__ms, "options.json")}</div>
  <div class="view-sub">CPM pass over the live schedule register. Anchor: ${esc(o.derivation ? o.derivation.anchor : "")}
  Approval lead time is a labelled assumption of ${o.assumptions ? o.assumptions.approval_lead_days : 30} days.</div>
  <div class="card clock-hero">
    <div class="clock-big">${days}<small>days to decide concessions</small></div>
    <div style="flex:1;min-width:260px">
      <div class="metric-sub">Commissioning gate <b>${esc(gate.gate_activity || "")}</b> opens <b>${esc(gate.gate_date || "")}</b>.
      Open deviations must be accepted as concessions or rejected before <b>${esc(gate.decide_concessions_by || "")}</b>.
      Rejection windows for delivered equipment have already expired &mdash; the honest options below price that reality.</div>
    </div>
  </div>
  <div class="card mt"><h3>Per-package rejection economics</h3>
  <table><thead><tr><th>Package</th><th>Need on site</th><th>Last safe rejection</th><th>Status</th><th class="num">Slip if rejected today</th><th class="num">Float left</th></tr></thead><tbody>
  ${(o.packages || []).map((p) => `<tr>
    <td><b>${esc(p.package)}</b><div class="src">${esc(p.section)} &middot; ${esc(p.vendor)}</div></td>
    <td class="num">${esc(p.need_on_site)}</td>
    <td class="num">${esc(p.last_safe_rejection)}</td>
    <td>${verdictBadge(p.reject_status)}</td>
    <td class="num" style="color:var(--bad)">${p.slip_if_rejected_today_days} d</td>
    <td class="num">${p.float_days} d</td></tr>`).join("")}
  </tbody></table></div>`;
};

RENDER.queue = async (main) => {
  const q = await api("queue");
  const items = q.queue || [];
  main.innerHTML = `
  <div class="view-head"><h1>Disposition Queue</h1>${provenance(q.__ms, "dispositions.json")}</div>
  <div class="view-sub">Deviations ranked by consequence, not by page order. Severity blends blast radius, schedule exposure and margin impact.</div>
  ${items.length ? `<div class="card"><table><thead><tr><th class="num">Sev</th><th>Submittal</th><th class="num">Open NCRs</th><th>Top items</th></tr></thead><tbody>
  ${items.map((it) => `<tr><td class="num"><b style="color:${it.severity_score > 40 ? "var(--bad)" : "var(--warn)"}">${it.severity_score}</b></td>
    <td><b>${esc(it.package)}</b><div class="src">${esc(it.vendor || "")}</div></td>
    <td class="num">${it.open_ncrs}</td>
    <td>${(it.items || []).slice(0, 3).map((x) => `<div>${badge(x.recommended, x.recommended === "REJECT" ? "b-bad" : x.recommended === "ACCEPT_AS_NOTED" ? "b-warn" : "b-mut")} <span class="src">${esc(x.ncr_id)}</span> ${esc((x.parameter || "").split(".").pop())}</div>`).join("")}</td>
  </tr>`).join("")}</tbody></table></div>` : `<div class="empty">Queue is empty.</div>`}`;
};

RENDER.review = async (main) => {
  const pk = await api("packages");
  const sel = (location.hash.split("/")[1]) || pk.packages[0];
  const mode = location.hash.includes("pre") ? "pre" : "post";
  const v = await api(`verdicts/${sel}?mode=${mode}`);
  const rows = (v.results || []).filter((r) => r.verdict !== "NOT_ADDRESSED");
  main.innerHTML = `
  <div class="view-head"><h1>Submittal Review</h1>${provenance(v.__ms)}</div>
  <div class="view-sub">Machine verdicts with the exact quotes they rest on. Select a package; every row cites spec + submittal page.</div>
  <div class="card" style="display:flex;gap:10px;flex-wrap:wrap">
    ${pk.packages.map((p) => `<button class="btn" style="${p === sel ? "" : "background:var(--bg2);color:var(--tx2);border-color:var(--line)"}" onclick="location.hash='review/${p}/${mode}'">${p}</button>`).join("")}
    <span style="flex:1"></span>
    <button class="btn" style="${mode === "post" ? "" : "background:var(--bg2);color:var(--tx2);border-color:var(--line)"}" onclick="location.hash='review/${sel}/post'">post-addendum</button>
    <button class="btn" style="${mode === "pre" ? "" : "background:var(--bg2);color:var(--tx2);border-color:var(--line)"}" onclick="location.hash='review/${sel}/pre'">pre</button>
  </div>
  <div class="card mt"><h3>${esc(sel)} &middot; ${rows.length} addressed checks (${mode})</h3>
  ${rows.slice(0, 120).map((r) => {
    const req = r.requirement || {}, g = r.governing_claim || {};
    return `<div style="padding:10px 0;border-bottom:1px solid var(--line)">
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">${verdictBadge(r.verdict)}
        ${(r.flags || []).includes("false_comply") ? badge("vendor stamped COMPLY", "b-bad") : ""}
        <b>${esc(r.parameter)}</b><span class="src">${esc(r.rule_id || "")}</span></div>
      <div class="ev-pair">
        <div><div class="src">SPEC ${esc(req.source_clause || "")} p${esc(req.page)}${req.amended_by ? " &middot; amended by " + esc(req.amended_by) : ""}</div>
          <div class="quote req">${esc(req.quote)}</div></div>
        <div><div class="src">SUBMITTAL ${esc(g.location || "\u2014")} p${esc(g.page != null ? g.page : "\u2014")}</div>
          <div class="quote claim">${esc(g.quote || "no governing evidence found")}</div></div>
      </div>
      <div class="src">${esc(r.reason || "")}</div>
    </div>`;
  }).join("")}
  </div>`;
};

RENDER.lint = async (main) => {
  const l = await api("lint");
  main.innerHTML = `
  <div class="view-head"><h1>Spec Defects</h1>${provenance(l.__ms, "lint.json")}</div>
  <div class="view-sub">The spec is also a document that can be wrong. A deterministic linter reads the compiled requirement ledger and the raw sections, and flags contradictions, unverifiable language, withdrawn standards and statutory collisions &mdash; before any vendor is blamed.</div>
  ${(l.findings || []).map((f, i) => `<div class="card" style="margin-bottom:10px">
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">${badge(f.lint.replace(/_/g, " "), "b-warn")}<b>${esc(f.summary)}</b></div>
    ${f.a ? `<div class="src" style="margin-top:8px">${esc(f.a.clause || "")}${f.a.page ? " p" + f.a.page : ""}</div><div class="quote req">${esc(f.a.quote)}</div>` : ""}
    ${f.b ? `<div class="src">${esc(f.b.clause || "")}${f.b.page ? " p" + f.b.page : ""}</div><div class="quote claim">${esc(f.b.quote)}</div>` : ""}
    <div class="src" style="margin-top:6px">auto-drafted RFI available in Paperwork &rarr; RFI-DRAFT-${String(i + 1).padStart(3, "0")}</div>
  </div>`).join("")}`;
};

RENDER.external = async (main) => {
  const e = await api("external");
  const docs = [e.spec, e.submittal].concat(e.documents_extra || []).filter(Boolean);
  main.innerHTML = `
  <div class="view-head"><h1>External &mdash; Real Documents</h1>${provenance(e.__ms, "external.json")}</div>
  <div class="view-sub">Everything else in this demo runs on a manufactured corpus with a frozen answer key.
  This screen runs on <b>real, unseen documents</b>: a public NTPC/IIT-Bombay data-centre tender and two real vendor brochures.
  Method: ${esc(e.method || "")}</div>
  <div class="grid c3">${docs.map((d) => `<div class="card"><h3>${esc(d.title)}</h3>
    <div class="src">${esc(d.file)} &middot; ${d.pages} pages${d.requirements_harvested != null ? " &middot; " + d.requirements_harvested + " requirements harvested" : ""}${d.claims_harvested != null ? " &middot; " + d.claims_harvested + " claims harvested" : ""}</div></div>`).join("")}</div>
  <div class="card mt"><h3>Cross-document checks &mdash; every quote verifiable against the PDFs</h3>
  ${(e.checks || []).map((c) => `<div style="padding:10px 0;border-bottom:1px solid var(--line)">
    <div style="display:flex;gap:8px;align-items:center">${verdictBadge(c.verdict)}<b>${esc(c.family.replace(/_/g, " "))}</b></div>
    <div class="ev-pair">
      <div><div class="src">TENDER p${c.requirement.page} &middot; ${esc(c.requirement.operator)} ${esc(c.requirement.value)} ${esc(c.requirement.unit || "")}</div><div class="quote req">${esc(c.requirement.quote)}</div></div>
      <div><div class="src">BROCHURE p${c.claim.page} &middot; ${esc(c.claim.value)} ${esc(c.claim.unit || "")}</div><div class="quote claim">${esc(c.claim.quote)}</div></div>
    </div>
    ${c.note ? `<div class="src">${esc(c.note)}</div>` : ""}
  </div>`).join("")}</div>`;
};

RENDER.blast = async (main) => {
  const w = await api("blastwave");
  const inv = w.pos_invalidated || [];
  main.innerHTML = `
  <div class="view-head"><h1>Blast Wave &mdash; Addendum ${esc(w.addendum || "3")}</h1>${provenance(w.__ms, "blast_wave.json")}
    <button class="btn danger" id="btn-blast">Re-apply addendum live</button></div>
  <div class="view-sub">One addendum changed ${(w.changes || []).length} requirement values on ${esc(w.date || "")}. The ledger re-verifies everything downstream: rules, verdicts, purchase orders, commissioning tests.</div>
  <div class="grid c4">
    <div class="card"><h3>Rules amended</h3><div class="metric warn">${(w.rule_amendments || []).length}</div></div>
    <div class="card"><h3>Verdicts flipped</h3><div class="metric bad">${(w.verdict_flips || []).length}</div></div>
    <div class="card"><h3>POs invalidated</h3><div class="metric bad">${inv.length}</div><div class="metric-sub">${fmtINR(inv.reduce((a, p) => a + (+p.value_inr || 0), 0))} exposure</div></div>
    <div class="card"><h3>Cx tests stale</h3><div class="metric warn">${(w.cx_tests_stale || []).length}</div><div class="metric-sub">updated procedures in Commissioning</div></div>
  </div>
  <div class="card mt"><h3>Verdict flips</h3><table><thead><tr><th>Package</th><th>Rule</th><th>Before</th><th>After</th></tr></thead><tbody>
  ${(w.verdict_flips || []).map((f) => `<tr><td>${esc(f.package)}</td><td class="src">${esc(f.rule_id)}</td><td>${verdictBadge(f.verdict_before)}</td><td>${verdictBadge(f.verdict_after)}</td></tr>`).join("")}
  </tbody></table></div>
  <div class="card mt"><h3>Invalidated purchase orders</h3><table><thead><tr><th>PO</th><th>Vendor</th><th class="num">Value</th><th>Reason</th></tr></thead><tbody>
  ${inv.map((p) => `<tr><td class="src">${esc(p.po_number)}</td><td>${esc(p.vendor)}</td><td class="num">${fmtINR(p.value_inr)}</td><td class="src">${esc(p.reason || "references superseded value")}</td></tr>`).join("")}
  </tbody></table></div>`;
  $("#btn-blast").onclick = () => recompute("blastwave/apply");
};

RENDER.margins = async (main) => {
  const m = await api("margins");
  const en = (m.energy_penalty || {}).rows || [];
  main.innerHTML = `
  <div class="view-head"><h1>Margin Erosion</h1>${provenance(m.__ms, "margins.json")}</div>
  <div class="view-sub">Every accepted concession is a signed-away margin. Numeric deviations are priced against the requirement; the tariff slider recomputes the energy penalty live in your browser &mdash; the maths is client-side, the inputs are server-computed.</div>
  <div class="grid c3">
    <div class="card"><h3>Numeric margins tracked</h3><div class="metric">${(m.ledger || []).length}</div></div>
    <div class="card"><h3>Thin (&lt;2%)</h3><div class="metric warn">${(m.ledger || []).filter((x) => x.classification === "THIN").length}</div></div>
    <div class="card"><h3>Negative</h3><div class="metric bad">${(m.ledger || []).filter((x) => x.classification === "NEGATIVE").length}</div></div>
  </div>
  <div class="card mt"><h3>Energy penalty of accepting UPS efficiency concessions</h3>
    <div class="slider-row"><span class="src">Tariff</span>
      <input type="range" id="tariff" min="4" max="14" step="0.5" value="8">
      <span class="slider-val" id="tariff-val"></span></div>
    <table class="mt"><thead><tr><th>Rule</th><th class="num">Required</th><th class="num">Offered</th><th class="num">Extra loss</th><th class="num">kWh / year</th><th class="num">Cost / year</th></tr></thead>
    <tbody id="energy-rows"></tbody></table>
    <div class="src mt" id="energy-total"></div></div>
  <div class="card mt"><h3>Signed-margin ledger (worst first)</h3>
  <table><thead><tr><th>Package / parameter</th><th class="num">Required</th><th class="num">Offered</th><th class="num">Margin</th><th>Class</th></tr></thead><tbody>
  ${(m.ledger || []).slice(0, 40).map((x) => `<tr><td><b>${esc(x.package)}</b><div class="src">${esc(x.parameter)}</div></td>
    <td class="num">${esc(x.required)}</td><td class="num">${esc(x.offered)}</td>
    <td class="num" style="color:${x.margin_pct < 0 ? "var(--bad)" : x.margin_pct < 2 ? "var(--warn)" : "var(--ok)"}">${x.margin_pct}%</td>
    <td>${badge(x.classification, x.classification === "NEGATIVE" ? "b-bad" : x.classification === "THIN" ? "b-warn" : "b-ok")}</td></tr>`).join("")}
  </tbody></table></div>`;
  const slider = $("#tariff");
  const draw = () => {
    const t = parseFloat(slider.value);
    $("#tariff-val").textContent = "\u20b9" + t.toFixed(1) + "/kWh";
    let total = 0;
    $("#energy-rows").innerHTML = en.map((r) => {
      const cost = r.extra_kwh_per_year * t; total += cost;
      return `<tr><td class="src">${esc(r.rule_id)}<div>${esc(r.package)}</div></td>
        <td class="num">${r.required_eff_pct}%</td><td class="num">${r.offered_eff_pct}%</td>
        <td class="num">${r.extra_loss_kw} kW</td><td class="num">${r.extra_kwh_per_year.toLocaleString("en-IN")}</td>
        <td class="num" style="color:var(--bad)">${fmtINR(Math.round(cost))}</td></tr>`;
    }).join("");
    $("#energy-total").innerHTML = `Fleet basis ${en[0] ? en[0].fleet_kw + " kW" : "\u2014"} &middot; total exposure <b style="color:var(--bad)">${fmtINR(Math.round(total))}/year</b> at \u20b9${t.toFixed(1)}/kWh &mdash; recomputed in your browser just now`;
  };
  slider.oninput = draw; draw();
};

RENDER.vendors = async (main) => {
  const v = await api("vendors");
  main.innerHTML = `
  <div class="view-head"><h1>Vendor Trust</h1>${provenance(v.__ms, "vendors.json")}</div>
  <div class="view-sub">Evidence-based review intensity: false-comply stamps weigh 3&times; a plain deviation. Formula: ${esc(v.method || "")}</div>
  <div class="card"><table><thead><tr><th>Vendor</th><th>Trust</th><th class="num">Checks</th><th class="num">Deviations</th><th class="num">False comply</th><th class="num">Exposure</th><th>Review intensity</th></tr></thead><tbody>
  ${(v.vendors || []).map((x) => `<tr>
    <td><b>${esc(x.vendor)}</b><div class="src">${esc(x.section)}</div></td>
    <td><div style="display:flex;align-items:center;gap:8px"><div class="bar-wrap" style="flex:1"><div class="bar" style="width:${x.trust_score}%;background:${x.trust_score >= 90 ? "var(--ok)" : x.trust_score >= 70 ? "var(--warn)" : "var(--bad)"}"></div></div><b class="num" style="font-family:var(--mono)">${x.trust_score}</b></div></td>
    <td class="num">${x.checks}</td><td class="num">${x.deviations}</td>
    <td class="num" style="color:${x.false_comply ? "var(--bad)" : "inherit"}">${x.false_comply}</td>
    <td class="num">${x.exposure_inr ? fmtINR(x.exposure_inr) : "\u2014"}</td>
    <td>${badge(x.review_intensity, x.review_intensity === "STANDARD" ? "b-ok" : x.review_intensity === "TARGETED_SAMPLING" ? "b-warn" : "b-bad")}</td></tr>`).join("")}
  </tbody></table></div>
  ${(v.revision_trends || []).length ? `<div class="card mt"><h3>R0 &rarr; R1 revision trends</h3>
  ${(v.revision_trends || []).map((t) => `<div class="src" style="padding:4px 0">${esc(t.package_r0)} &rarr; ${esc(t.package_r1)}: ${esc(t.summary)}</div>`).join("")}</div>` : ""}`;
};

RENDER.paperwork = async (main) => {
  const p = await api("paperwork");
  const groups = { rfi: "RFI drafts (from spec defects)", letter: "Returned-submittal letters", notice: "Client impact notices" };
  main.innerHTML = `
  <div class="view-head"><h1>Paperwork</h1>${provenance(p.__ms, "paperwork_index.json")}</div>
  <div class="view-sub">The verdicts are machine-verified; the paperwork writes itself around them. Every document is marked DRAFT and carries its evidence &mdash; a human signs, the machine cites.</div>
  ${Object.entries(groups).map(([k, title]) => {
    const docs = (p.documents || []).filter((d) => d.type === k);
    return docs.length ? `<div class="card" style="margin-bottom:12px"><h3>${title}</h3>
      ${docs.map((d) => `<div class="nav-item" style="margin:2px 0" onclick="openDoc('${esc(d.file)}')"><span>${esc(d.title)}</span><span class="pill">open</span></div>`).join("")}</div>` : "";
  }).join("")}`;
};

window.openDoc = async (f) => {
  const d = await api("paperwork/doc?f=" + encodeURIComponent(f));
  const html = esc(d.markdown)
    .replace(/^# (.*)$/gm, "<h1>$1</h1>").replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^&gt; (.*)$/gm, "<blockquote>$1</blockquote>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/^- (.*)$/gm, "<li>$1</li>").replace(/\n\n/g, "<p></p>");
  $("#doc-box").innerHTML = `<span class="doc-close" onclick="document.getElementById('doc-modal').style.display='none'">&times;</span>` + html;
  $("#doc-modal").style.display = "flex";
};
$("#doc-modal").onclick = (e) => { if (e.target.id === "doc-modal") e.target.style.display = "none"; };

RENDER.cx = async (main) => {
  const c = await api("cx");
  const tests = c.tests || [];
  main.innerHTML = `
  <div class="view-head"><h1>Commissioning</h1>${provenance(c.__ms, "cx_packs.json")}</div>
  <div class="view-sub">Cx tests trace to the requirement values they verify. When an addendum changes a value, the affected procedures go STALE and updated drafts are generated with provenance.</div>
  <div class="grid c3">
    <div class="card"><h3>Tests tracked</h3><div class="metric">${tests.length}</div></div>
    <div class="card"><h3>Stale after ADD-003</h3><div class="metric warn">${tests.filter((t) => t.status === "STALE").length}</div></div>
    <div class="card"><h3>Blocked by open NCRs</h3><div class="metric bad">${tests.filter((t) => (t.open_ncrs || 0) > 0).length}</div></div>
  </div>
  <div class="card mt"><table><thead><tr><th>Test</th><th>Level</th><th>Verifies</th><th>Status</th><th class="num">Open NCRs</th><th></th></tr></thead><tbody>
  ${tests.map((t) => `<tr><td><b>${esc(t.test_id)}</b><div class="src">${esc(t.description || "")}</div></td>
    <td>${esc(t.level || "")}</td><td class="src">${esc(t.verifies_rule || "")}</td>
    <td>${verdictBadge(t.status)}</td><td class="num">${t.open_ncrs || 0}</td>
    <td>${t.updated_procedure ? `<button class="btn" onclick="openDoc('${esc(t.updated_procedure)}')">updated draft</button>` : ""}</td></tr>`).join("")}
  </tbody></table></div>`;
};

RENDER.ncr = async (main) => {
  const n = await api("ncr");
  main.innerHTML = `
  <div class="view-head"><h1>NCR Register</h1>${provenance(n.__ms)}</div>
  <div class="view-sub">Non-conformance reports auto-raised from DEVIATION verdicts, each carrying its clause and evidence.</div>
  <div class="card"><table><thead><tr><th>NCR</th><th>Package</th><th>Parameter</th><th>Severity</th><th>Status</th></tr></thead><tbody>
  ${(n.ncrs || []).map((r) => `<tr><td class="src">${esc(r.ncr_id)}</td><td>${esc(r.package)}</td>
    <td class="src">${esc(r.parameter)}</td><td>${badge(r.severity || "\u2014", (r.severity || "").match(/major|high/i) ? "b-bad" : "b-warn")}</td>
    <td>${verdictBadge(r.status || "OPEN")}</td></tr>`).join("")}
  </tbody></table></div>`;
};

/* ---------------- graph (rebuilt: deterministic + bounded) ------------ */
let GRAPH = { raf: null, running: false };

function stopGraph() {
  if (GRAPH.raf) cancelAnimationFrame(GRAPH.raf);
  GRAPH.raf = null; GRAPH.running = false;
}

function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const NODE_COLORS = { section: "#7aa2ff", clause: "#5b8dd6", package: "#e0b458",
  po: "#68c7a5", activity: "#9a86d8", cx: "#d87ba8", addendum: "#ff5d5d", rule: "#5b8dd6", claim: "#e0b458" };
const BAD = new Set(["DEVIATION", "INVALID", "STALE", "AMENDS"]);

RENDER.graph = async (main) => {
  const g = await api("graph");
  main.innerHTML = `
  <div class="view-head"><h1>Knowledge Graph</h1>${provenance(g.__ms, "graph.json")}</div>
  <div class="view-sub">${(g.nodes || []).length} nodes / ${(g.edges || []).length} edges: sections, clauses, packages, POs, schedule activities, Cx tests and the addendum that cut across all of them. Red edges are consequences. Drag to pan, scroll to zoom, hover for detail.</div>
  <div id="graph-wrap">
    <canvas id="graph-canvas"></canvas>
    <div class="graph-hud" id="graph-hud"></div>
    <div class="graph-legend">${Object.entries(NODE_COLORS).filter(([k]) => !["rule", "claim"].includes(k)).map(([k, c]) => `<span><i style="background:${c}"></i>${k}</span>`).join("")}</div>
    <div id="graph-tip"></div>
  </div>`;
  try { initGraph(g); } catch (e) {
    $("#graph-wrap").insertAdjacentHTML("beforeend", `<div class="err-overlay">graph error:\n${esc(e.message)}</div>`);
  }
};

function initGraph(g) {
  const canvas = $("#graph-canvas"), wrap = $("#graph-wrap"), tip = $("#graph-tip"), hud = $("#graph-hud");
  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  let W = wrap.clientWidth, H = wrap.clientHeight;
  canvas.width = W * DPR; canvas.height = H * DPR;
  const ctx = canvas.getContext("2d");

  const nodes = (g.nodes || []).map((n) => Object.assign({}, n));
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const edges = (g.edges || []).filter((e) => idx.has(e.s || e.source) && idx.has(e.t || e.target))
    .map((e) => ({ s: idx.get(e.s || e.source), t: idx.get(e.t || e.target), type: (e.type || "").toUpperCase() }));

  /* deterministic initial layout: rings by type (seeded, never random) */
  const rand = mulberry32(1337);
  const typeOrder = ["section", "clause", "package", "po", "activity", "cx", "addendum"];
  const ringOf = (t) => { const i = typeOrder.indexOf(t); return i < 0 ? 3.4 : 0.55 + i * 0.55; };
  const byType = {};
  nodes.forEach((n) => { (byType[n.type] = byType[n.type] || []).push(n); });
  Object.values(byType).forEach((arr) => {
    arr.forEach((n, i) => {
      const R = ringOf(n.type) * Math.min(W, H) * 0.16;
      const a = (i / arr.length) * Math.PI * 2 + rand() * 0.25;
      n.x = Math.cos(a) * R + (rand() - 0.5) * 18;
      n.y = Math.sin(a) * R + (rand() - 0.5) * 18;
      n.vx = 0; n.vy = 0;
      const deg = 0; n.deg = deg;
    });
  });
  edges.forEach((e) => { nodes[e.s].deg++; nodes[e.t].deg++; });

  /* bounded physics: clamped spring + capped velocity + alpha cooling */
  const SPRING_LEN = 46, MAX_FORCE = 0.9, MAX_VEL = 3.5;
  let alpha = 1, ticks = 0, settled = false;
  const clamp = (v, m) => (v > m ? m : v < -m ? -m : v);

  function tick() {
    /* repulsion on a coarse grid (O(n) buckets, not O(n^2) full) */
    const CELL = 70, grid = new Map();
    nodes.forEach((n, i) => {
      const k = ((n.x / CELL) | 0) + ":" + ((n.y / CELL) | 0);
      (grid.get(k) || grid.set(k, []).get(k)).push(i);
    });
    nodes.forEach((n, i) => {
      const gx = (n.x / CELL) | 0, gy = (n.y / CELL) | 0;
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        const cell = grid.get((gx + dx) + ":" + (gy + dy));
        if (!cell) continue;
        for (const j of cell) {
          if (j <= i) continue;
          const m = nodes[j];
          let ddx = n.x - m.x, ddy = n.y - m.y;
          let d2 = ddx * ddx + ddy * ddy;
          if (d2 < 1) { ddx = (rand() - 0.5); ddy = (rand() - 0.5); d2 = 1; }
          if (d2 > 8100) continue;
          const f = clamp(340 / d2, MAX_FORCE) * alpha;
          const d = Math.sqrt(d2);
          n.vx += (ddx / d) * f; n.vy += (ddy / d) * f;
          m.vx -= (ddx / d) * f; m.vy -= (ddy / d) * f;
        }
      }
    });
    /* springs: force bounded regardless of distance (the old build grew
       force with d^2 -> NaN -> blank screen; this one cannot) */
    for (const e of edges) {
      const a = nodes[e.s], b = nodes[e.t];
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.max(Math.sqrt(dx * dx + dy * dy), 0.01);
      const f = clamp((d - SPRING_LEN) * 0.012, MAX_FORCE) * alpha;
      a.vx += (dx / d) * f; a.vy += (dy / d) * f;
      b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
    }
    /* integrate with velocity cap + NaN guard + gentle centering */
    for (const n of nodes) {
      if (n === drag.node) { n.vx = 0; n.vy = 0; continue; }
      n.vx = clamp((n.vx - n.x * 0.0012 * alpha) * 0.82, MAX_VEL);
      n.vy = clamp((n.vy - n.y * 0.0012 * alpha) * 0.82, MAX_VEL);
      n.x += n.vx; n.y += n.vy;
      if (!isFinite(n.x) || !isFinite(n.y)) { n.x = (rand() - 0.5) * 200; n.y = (rand() - 0.5) * 200; n.vx = n.vy = 0; }
    }
    alpha = Math.max(alpha * 0.996, 0.02);
    ticks++;
    if (ticks > 900 && !settled) { settled = true; alpha = 0.02; }
  }

  /* view transform */
  const view = { x: W / 2, y: H / 2, k: 0.9 };
  const drag = { node: null, panning: false, px: 0, py: 0 };

  function draw() {
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.translate(view.x, view.y); ctx.scale(view.k, view.k);
    ctx.lineWidth = 0.6 / view.k;
    for (const e of edges) {
      const a = nodes[e.s], b = nodes[e.t];
      ctx.strokeStyle = BAD.has(e.type) ? "rgba(255,92,105,0.5)" : "rgba(255,255,255,0.08)";
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    for (const n of nodes) {
      const r = Math.min(3 + Math.sqrt(n.deg || 1) * 1.3, 14);
      ctx.fillStyle = NODE_COLORS[n.type] || "#8b94a7";
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 7); ctx.fill();
      if (BAD.has(String(n.status || "").toUpperCase())) {
        ctx.strokeStyle = "#ff5c69"; ctx.lineWidth = 1.4 / view.k;
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 2.5 / view.k, 0, 7); ctx.stroke();
        ctx.lineWidth = 0.6 / view.k;
      }
      if (view.k > 1.3 && (n.deg || 0) > 5) {
        ctx.fillStyle = "rgba(230,234,242,0.8)";
        ctx.font = `${10 / view.k}px ui-monospace,monospace`;
        ctx.fillText(n.label || n.id, n.x + r + 3 / view.k, n.y + 3 / view.k);
      }
    }
  }

  function frame() {
    if (!GRAPH.running) return;
    if (!document.hidden) {
      if (!settled || drag.node) tick();
      draw();
      hud.textContent = `${nodes.length} nodes \u00b7 ${edges.length} edges \u00b7 ${settled ? "settled" : "cooling " + alpha.toFixed(2)} \u00b7 zoom ${view.k.toFixed(1)}x`;
    }
    GRAPH.raf = requestAnimationFrame(frame);
  }

  /* interactions */
  const toWorld = (mx, my) => [(mx - view.x) / view.k, (my - view.y) / view.k];
  const pick = (mx, my) => {
    const [wx, wy] = toWorld(mx, my);
    let best = null, bd = 144;
    for (const n of nodes) {
      const dx = n.x - wx, dy = n.y - wy, d2 = dx * dx + dy * dy;
      if (d2 < bd) { bd = d2; best = n; }
    }
    return best;
  };
  canvas.onmousedown = (ev) => {
    const r = canvas.getBoundingClientRect();
    const n = pick(ev.clientX - r.left, ev.clientY - r.top);
    if (n) { drag.node = n; settled = false; alpha = Math.max(alpha, 0.25); }
    else { drag.panning = true; }
    drag.px = ev.clientX; drag.py = ev.clientY;
  };
  window.addEventListener("mousemove", (ev) => {
    const r = canvas.getBoundingClientRect();
    if (drag.node) {
      const [wx, wy] = toWorld(ev.clientX - r.left, ev.clientY - r.top);
      drag.node.x = wx; drag.node.y = wy;
    } else if (drag.panning) {
      view.x += ev.clientX - drag.px; view.y += ev.clientY - drag.py;
      drag.px = ev.clientX; drag.py = ev.clientY;
    } else if (canvas.matches(":hover")) {
      const n = pick(ev.clientX - r.left, ev.clientY - r.top);
      if (n) {
        tip.style.display = "block";
        tip.style.left = (ev.clientX - r.left + 14) + "px";
        tip.style.top = (ev.clientY - r.top + 10) + "px";
        tip.innerHTML = `<div class="t-type">${esc(n.type)}</div><b>${esc(n.label || n.id)}</b>` +
          (n.status ? `<div class="src">status: ${esc(n.status)}</div>` : "") +
          (n.meta && Object.keys(n.meta).length ? `<div class="src">${esc(Object.entries(n.meta).map(([k, v]) => k + ": " + v).join(" · "))}</div>` : "");
      } else tip.style.display = "none";
    }
  });
  window.addEventListener("mouseup", () => { drag.node = null; drag.panning = false; });
  canvas.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const r = canvas.getBoundingClientRect();
    const mx = ev.clientX - r.left, my = ev.clientY - r.top;
    const k2 = Math.min(Math.max(view.k * (ev.deltaY < 0 ? 1.12 : 0.89), 0.25), 5);
    view.x = mx - ((mx - view.x) / view.k) * k2;
    view.y = my - ((my - view.y) / view.k) * k2;
    view.k = k2;
  }, { passive: false });

  GRAPH.running = true;
  frame();
}

/* ---------------- recompute ---------------- */
async function recompute(endpoint) {
  const btn = $("#btn-recompute");
  btn.disabled = true; btn.textContent = "Recomputing\u2026";
  try {
    const r = await fetch("/api/" + (endpoint || "recompute"), { method: "POST" });
    const j = await r.json();
    const toast = $("#toast");
    toast.innerHTML = `<h5>${j.ok ? "Ledger recomputed live" : "Recompute failed"}</h5>` +
      (j.timings || []).map((t) => `<div class="mod-row"><span>${esc(t.module)}</span><span class="ms">${t.ms} ms ${t.ok ? "" : "\u2717"}</span></div>`).join("") +
      `<div class="src" style="margin-top:6px">finished ${esc(j.finished_at || "")}</div>`;
    toast.style.display = "block";
    setTimeout(() => { toast.style.display = "none"; }, 9000);
    META = await api("meta");
    route();
  } finally {
    btn.disabled = false; btn.textContent = "Recompute ledger";
  }
}
$("#btn-recompute").onclick = () => recompute();

/* ---------------- Esc key for modal ---------------- */
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    const m = $("#doc-modal");
    if (m && m.style.display === "flex") m.style.display = "none";
  }
});

/* ---------------- error overlay instead of silent blank ------------- */
window.onerror = (msg) => {
  const main = $("#main");
  if (main && !main.innerHTML.includes("err-overlay")) {
    main.insertAdjacentHTML("afterbegin",
      `<div class="card" style="border-color:var(--bad);color:var(--bad);font-family:var(--mono);font-size:11px">runtime error: ${esc(msg)}</div>`);
  }
};

/* ---------------- boot ---------------- */
(async () => {
  try { META = await api("meta"); } catch (e) { META = {}; }
  renderNav();
  route();
  pollActivity();
})();
