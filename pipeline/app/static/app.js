/* CLAUSE AI frontend - vanilla JS, zero dependencies. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const api = (p, opt) => fetch("/api/" + p, opt).then(r => r.json());
const fmtINR = n => "\u20b9" + (n >= 1e7 ? (n / 1e7).toFixed(1) + " Cr" : (n / 1e5).toFixed(1) + " L");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const badge = v => `<span class="badge ${esc(v)}">${esc(String(v).replace(/_/g, " "))}</span>`;

/* ---------- navigation ---------- */
$$(".nav-btn").forEach(b => b.onclick = () => show(b.dataset.view));
function show(view) {
  $$(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + view));
  if (view === "graph" && !Graph.started) Graph.start();
}

/* ---------- dashboard ---------- */
async function dashboard() {
  const s = await api("summary");
  const vp = s.verdicts_post || {}, ev = s.eval_pre || {}, evp = s.eval_post || {};
  const pct = x => x == null ? "\u2013" : Math.round(x * 100) + "%";
  $("#view-dashboard").innerHTML = `
  <h2>Project health — post-Addendum 3 reality</h2>
  <div class="cards">
    <div class="card"><div class="k">Machine-checkable rules</div><div class="v">${s.rules}</div><div class="d">compiled from 6 spec sections</div></div>
    <div class="card"><div class="k">Extracted claims</div><div class="v">${s.claims}</div><div class="d">from 7 submittal packages</div></div>
    <div class="card red"><div class="k">Open deviations</div><div class="v">${vp.DEVIATION || 0}</div><div class="d">${s.false_comply_post || 0} vendor-stamped "Comply" disproven</div></div>
    <div class="card amber"><div class="k">Routed to human review</div><div class="v">${(vp.NEEDS_REVIEW || 0) + (vp.MISSING_EVIDENCE || 0)}</div><div class="d">ambiguity is never guessed away</div></div>
    <div class="card blue"><div class="k">LLM spend (entire project)</div><div class="v">$${(s.llm_spend_usd ?? 0).toFixed(2)}</div><div class="d">vs ~30 engineer-hours/package manual</div></div>
  </div>
  <h3>Measured against the labeled answer key (${(ev.deviations_total || 0)} + ${(evp.deviations_total || 0)} planted checks, pre / post addendum)</h3>
  <div class="cards">
    <div class="card green"><div class="k">False alarms</div><div class="v">${(ev.false_alarms ?? 0) + (evp.false_alarms ?? 0)}</div><div class="d">a tool that cries wolf is dead on arrival</div></div>
    <div class="card"><div class="k">Caught outright</div><div class="v">${pct(ev.hard_recall)} / ${pct(evp.hard_recall)}</div><div class="d">deviation named, both documents cited</div></div>
    <div class="card"><div class="k">Caught or flagged</div><div class="v">${pct(ev.flag_inclusive_recall)} / ${pct(evp.flag_inclusive_recall)}</div><div class="d">nothing slips through silently</div></div>
    <div class="card red"><div class="k">Blast wave of ADD-003</div><div class="v">${s.blast ? s.blast.verdict_flips + s.blast.pos_invalidated + s.blast.cx_tests_stale : "\u2013"}</div><div class="d">${s.blast ? `${s.blast.verdict_flips} verdicts · ${s.blast.pos_invalidated} POs · ${s.blast.cx_tests_stale} Cx tests` : ""}</div></div>
  </div>
  <h3>Verdict distribution (post-addendum)</h3>
  <div class="cards">${Object.entries(vp).sort((a,b)=>b[1]-a[1]).map(([k, v]) =>
    `<div class="card"><div class="k">${esc(k.replace(/_/g, " "))}</div><div class="v">${v}</div></div>`).join("")}
  </div>`;
}

/* ---------- queue ---------- */
async function queue() {
  const q = (await api("queue")).queue || [];
  $("#view-queue").innerHTML = `
  <h2>Submittal queue — ranked by blast-radius severity</h2>
  <table><thead><tr><th>#</th><th>Package</th><th>Section</th><th>Severity</th><th>Open NCRs</th><th>Needs review</th><th>PO exposure</th><th>Lead time</th><th>Min float</th></tr></thead>
  <tbody>${q.map((p, i) => `<tr data-pkg="${esc(p.package)}"><td>${i + 1}</td><td class="mono">${esc(p.package)}</td><td>${esc(p.section)}</td><td><b>${p.severity_score}</b></td><td>${p.open_ncrs ? badge("MAJOR") : ""} ${p.open_ncrs}</td><td>${p.needs_review}</td><td>${fmtINR(p.value_inr)}</td><td>${p.lead_time_weeks} wk</td><td>${p.min_float_days ?? "\u2013"} d</td></tr>`).join("")}</tbody></table>
  <p class="small" style="margin-top:10px">Click a package to open it in Review.</p>`;
  $$("#view-queue tbody tr").forEach(tr => tr.onclick = () => { Review.pkg = tr.dataset.pkg; review(); show("review"); });
}

/* ---------- review (money screen) ---------- */
const Review = { pkg: null, filter: "PROBLEMS" };
async function review() {
  const pkgs = (await api("packages")).packages;
  Review.pkg = Review.pkg || pkgs[0];
  const v = await api(`verdicts/${Review.pkg}?mode=post`);
  const FILTERS = ["PROBLEMS", "DEVIATION", "NEEDS_REVIEW", "MISSING_EVIDENCE", "COMPLY", "ALL"];
  let rows = (v.results || []).filter(r => r.verdict !== "NOT_ADDRESSED");
  if (Review.filter === "PROBLEMS") rows = rows.filter(r => ["DEVIATION", "NEEDS_REVIEW"].includes(r.verdict) || r.flags.length);
  else if (Review.filter !== "ALL") rows = rows.filter(r => r.verdict === Review.filter);
  const sev = { DEVIATION: 4, NEEDS_REVIEW: 3, MISSING_EVIDENCE: 2, COMPLY: 1 };
  rows.sort((a, b) => (sev[b.verdict] || 0) - (sev[a.verdict] || 0) || b.flags.length - a.flags.length);
  $("#view-review").innerHTML = `
  <h2>Review — spec vs evidence, side by side</h2>
  <div class="controls">
    <select id="pkg-sel">${pkgs.map(p => `<option ${p === Review.pkg ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>
    ${FILTERS.map(f => `<button class="chip ${Review.filter === f ? "on" : ""}" data-f="${f}">${f.replace(/_/g, " ")}</button>`).join("")}
    <span class="small">${rows.length} of ${(v.results || []).length} checks</span>
  </div>
  ${rows.map(r => {
    const g = r.governing_claim || {};
    return `<div class="vcard">
    <div class="head">${badge(r.verdict)}${r.flags.map(f => `<span class="badge flag">${esc(f.replace(/_/g, " "))}</span>`).join("")}
      <span class="rule">${esc(r.rule_id)}${r.requirement.amended_by ? " · amended by " + esc(r.requirement.amended_by) : ""}</span></div>
    <div class="duel">
      <div class="quote"><div class="src">Specification · ${esc(r.requirement.source_clause)} · p${r.requirement.page}</div>“${esc(r.requirement.quote)}”</div>
      <div class="quote claim"><div class="src">Submittal · ${esc(g.location || "no evidence")} · ${g.page ? "p" + g.page : "\u2013"}</div>${g.quote ? "“" + esc(g.quote) + "”" : "<i>no governing evidence found in package</i>"}</div>
    </div>
    <div class="reason"><b>${esc(r.requirement.parameter)}</b> ${esc(r.requirement.operator)} ${esc(JSON.stringify(r.requirement.value))}${r.requirement.unit ? " " + esc(r.requirement.unit) : ""}${r.requirement.condition ? ` <i>(${esc(r.requirement.condition)})</i>` : ""} — ${esc(r.reason)}</div>
  </div>`; }).join("") || "<p class='small'>Nothing matches this filter.</p>"}`;
  $("#pkg-sel").onchange = e => { Review.pkg = e.target.value; review(); };
  $$("#view-review .chip").forEach(c => c.onclick = () => { Review.filter = c.dataset.f; review(); });
}

/* ---------- ledger graph ---------- */
const COLORS = { section: "#7aa2ff", clause: "#5b8dd6", package: "#e0b458", po: "#68c7a5", activity: "#9a86d8", cx: "#d87ba8", addendum: "#ff5d5d" };
const BAD = new Set(["DEVIATION", "INVALID", "STALE", "AMENDS"]);
const Graph = {
  started: false, nodes: [], edges: [], scale: 1, ox: 0, oy: 0, sel: null,
  async start() {
    this.started = true;
    const g = await api("graph");
    const idx = {}; g.nodes.forEach((n, i) => idx[n.id] = i);
    this.nodes = g.nodes.map(n => ({ ...n, x: Math.random() * 1200 - 600, y: Math.random() * 800 - 400, vx: 0, vy: 0,
      r: n.type === "section" ? 14 : n.type === "package" ? 11 : n.type === "addendum" ? 12 : n.type === "clause" ? 4.5 : 6 }));
    this.edges = g.edges.filter(e => idx[e.s] != null && idx[e.t] != null).map(e => ({ ...e, si: idx[e.s], ti: idx[e.t] }));
    const deg = {}; this.edges.forEach(e => { deg[e.si] = (deg[e.si] || 0) + 1; deg[e.ti] = (deg[e.ti] || 0) + 1; });
    this.nodes.forEach((n, i) => n.r += Math.min(4, (deg[i] || 0) * .08));
    this.canvas = $("#graph-canvas"); this.ctx = this.canvas.getContext("2d");
    this.resize(); addEventListener("resize", () => this.resize());
    this.bind(); this.warm = 300; this.loop();
    $("#graph-legend").innerHTML = Object.entries(COLORS).map(([t, c]) => `<span class="leg"><span class="dot" style="background:${c}"></span>${t}</span>`).join("") + `<span class="leg"><span class="dot" style="background:none;border:2px solid var(--dev)"></span>problem</span>`;
  },
  resize() { const r = this.canvas.parentElement.getBoundingClientRect(); this.canvas.width = r.width; this.canvas.height = r.height; },
  tick() {
    const N = this.nodes, E = this.edges;
    // Barnes-Hut is overkill at 350 nodes; simple grid-bucketed repulsion.
    const cell = 120, grid = {};
    N.forEach((n, i) => { const k = ((n.x / cell) | 0) + ":" + ((n.y / cell) | 0); (grid[k] = grid[k] || []).push(i); });
    N.forEach((n, i) => {
      const gx = (n.x / cell) | 0, gy = (n.y / cell) | 0;
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        (grid[(gx + dx) + ":" + (gy + dy)] || []).forEach(j => {
          if (j <= i) return; const m = N[j];
          let ddx = n.x - m.x, ddy = n.y - m.y, d2 = ddx * ddx + ddy * ddy + .01;
          if (d2 > 14400) return; const f = 900 / d2;
          ddx *= f; ddy *= f; n.vx += ddx; n.vy += ddy; m.vx -= ddx; m.vy -= ddy;
        });
      }
      n.vx -= n.x * .004; n.vy -= n.y * .004; // gravity to centre
    });
    E.forEach(e => {
      const a = N[e.si], b = N[e.ti];
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) + .01;
      const f = (d - 60) * .004;
      a.vx += dx / d * f * d * .02; a.vy += dy / d * f * d * .02;
      b.vx -= dx / d * f * d * .02; b.vy -= dy / d * f * d * .02;
    });
    N.forEach(n => { n.x += n.vx *= .82; n.y += n.vy *= .82; });
  },
  loop() {
    if (this.warm > 0) { this.tick(); this.warm--; }
    this.draw();
    requestAnimationFrame(() => this.loop());
  },
  draw() {
    const c = this.ctx, W = this.canvas.width, H = this.canvas.height;
    c.clearRect(0, 0, W, H); c.save();
    c.translate(W / 2 + this.ox, H / 2 + this.oy); c.scale(this.scale, this.scale);
    const t = Date.now() / 1000;
    c.lineWidth = .6;
    this.edges.forEach(e => {
      const a = this.nodes[e.si], b = this.nodes[e.ti];
      c.strokeStyle = e.type === "amends" ? "rgba(255,93,93,.8)" : e.status && BAD.has(e.status) ? "rgba(255,93,93,.35)" : "rgba(120,145,175,.16)";
      c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(b.x, b.y); c.stroke();
    });
    this.nodes.forEach(n => {
      const bad = BAD.has(n.status);
      if (bad) { // pulsing halo on problem nodes
        c.beginPath(); c.arc(n.x, n.y, n.r + 4 + Math.sin(t * 3 + n.x) * 1.5, 0, 7);
        c.strokeStyle = "rgba(255,93,93,.7)"; c.lineWidth = 1.6; c.stroke(); c.lineWidth = .6;
      }
      c.beginPath(); c.arc(n.x, n.y, n.r, 0, 7);
      c.fillStyle = COLORS[n.type] || "#888"; c.globalAlpha = bad ? 1 : .88; c.fill(); c.globalAlpha = 1;
      if (n === this.sel) { c.strokeStyle = "#fff"; c.lineWidth = 2; c.stroke(); c.lineWidth = .6; }
      if (n.r >= 9 || this.scale > 1.6) {
        c.fillStyle = "rgba(219,228,238,.85)"; c.font = `${11 / this.scale}px sans-serif`;
        c.fillText(n.type === "clause" ? n.label : n.label.slice(0, 26), n.x + n.r + 3, n.y + 3);
      }
    });
    c.restore();
  },
  pick(mx, my) {
    const W = this.canvas.width, H = this.canvas.height;
    const x = (mx - W / 2 - this.ox) / this.scale, y = (my - H / 2 - this.oy) / this.scale;
    return this.nodes.find(n => (n.x - x) ** 2 + (n.y - y) ** 2 < (n.r + 4) ** 2);
  },
  bind() {
    const cv = this.canvas; let drag = null, moved = false;
    cv.onmousedown = e => { drag = { x: e.offsetX, y: e.offsetY }; moved = false; };
    cv.onmousemove = e => { if (!drag) return; this.ox += e.offsetX - drag.x; this.oy += e.offsetY - drag.y; drag = { x: e.offsetX, y: e.offsetY }; moved = true; };
    cv.onmouseup = e => {
      if (!moved) { this.sel = this.pick(e.offsetX, e.offsetY); this.panel(); }
      drag = null;
    };
    cv.onwheel = e => { e.preventDefault(); const f = e.deltaY < 0 ? 1.12 : .89; this.scale = Math.min(6, Math.max(.25, this.scale * f)); };
  },
  panel() {
    const p = $("#graph-panel"), n = this.sel;
    if (!n) { p.classList.add("hidden"); return; }
    p.classList.remove("hidden");
    const rows = Object.entries(n.meta || {}).filter(([, v]) => typeof v !== "object").slice(0, 9)
      .map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><span>${esc(String(v).slice(0, 34))}</span></div>`).join("");
    p.innerHTML = `<h4>${esc(n.label)}</h4><div class="kv"><span>type</span><span>${esc(n.type)}</span></div>
      <div class="kv"><span>status</span><span>${n.status ? badge(n.status) : "\u2013"}</span></div>${rows}
      <div class="small" style="margin-top:8px">${this.edges.filter(e => this.nodes[e.si] === n || this.nodes[e.ti] === n).length} connections</div>`;
  },
};

/* ---------- blast wave ---------- */
async function blast() {
  $("#view-blast").innerHTML = `
  <h2>Addendum blast wave — one document lands, the ledger repaints</h2>
  <div class="controls"><button class="act danger" id="drop-btn">⚡ Process Addendum 3</button>
  <span class="small">re-runs the deterministic precedence layer + verifier live (no LLM, ~2 s)</span></div>
  <div id="stages"></div>`;
  $("#drop-btn").onclick = async () => {
    $("#drop-btn").disabled = true; $("#drop-btn").textContent = "processing\u2026";
    const r = await api("blastwave/apply", { method: "POST" });
    const w = r.wave;
    const stages = [
      [`📨 ADD-003 parsed — ${w.changes.length} contract change(s), dated ${w.date}`, w.changes.map(ch => `${ch.clause}: DELETE '${ch.delete}' → INSERT '${ch.insert}'`)],
      [`📐 ${w.rule_amendments.length} rules amended in the ledger (original values preserved)`, w.rule_amendments.map(a => `${a.rule_id}: ${a.from} → ${a.to}`)],
      [`⚖️ ${w.verdict_flips.length} verdicts flipped on re-verification`, w.verdict_flips.map(f => `${f.package} · ${f.rule_id}: ${f.verdict_before} → ${f.verdict_after}`)],
      [`💰 ${w.pos_invalidated.length} purchase orders invalidated — ${fmtINR(w.pos_invalidated.reduce((s, p) => s + +p.value_inr, 0))} ordered against superseded requirements`, w.pos_invalidated.map(p => `${p.po_number}: ${p.item_description}`)],
      [`🧪 ${w.cx_tests_stale.length} commissioning tests now STALE — they still test the old values`, w.cx_tests_stale.map(t => `${t.test_id}: ${t.ledger_reason}`)],
    ];
    const box = $("#stages");
    box.innerHTML = stages.map(([t, items]) => `<div class="stage"><div class="t">${esc(t)}</div><ul>${items.map(i => `<li>${esc(i)}</li>`).join("")}</ul></div>`).join("");
    $$(".stage").forEach((el, i) => setTimeout(() => el.classList.add("lit"), 500 + i * 900));
    $("#drop-btn").textContent = "⚡ Process Addendum 3"; $("#drop-btn").disabled = false;
    Graph.started = false; // force graph rebuild with fresh statuses
    dashboard(); queue();
  };
}

/* ---------- NCR register ---------- */
async function ncr() {
  const rows = (await api("ncr")).ncrs;
  $("#view-ncr").innerHTML = `
  <h2>NCR register — the QMS audit trail, auto-drafted</h2>
  <table><thead><tr><th>NCR</th><th>Package</th><th>Clause</th><th>Severity</th><th>Finding</th><th>Recommended disposition</th><th>Slip if rejected</th><th>Exposure</th></tr></thead>
  <tbody>${rows.map(r => `<tr><td class="mono">${esc(r.ncr_id)}</td><td class="mono">${esc(r.package)}</td><td>${esc(r.spec_clause)}</td><td>${badge(r.severity)}</td><td style="max-width:420px">${esc(r.description)}</td><td>${esc(r.recommended_disposition.replace(/_/g, " "))}</td><td>${r.schedule_slip_if_rejected_days} d</td><td>${fmtINR(+r.cost_exposure_inr)}</td></tr>`).join("")}</tbody></table>`;
}

dashboard(); queue(); review(); blast(); ncr();
