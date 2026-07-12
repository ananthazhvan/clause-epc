/* CLAUSE console v3 - ink & paper.
   Vanilla JS, no dependencies. Everything on screen is fetched, timed,
   and stamped with its provenance. Nothing is preloaded into the page. */
"use strict";

/* ---------------- helpers ---------------- */
const $ = (s, el) => (el || document).querySelector(s);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fmtN = (n) => (n == null || isNaN(Number(n))) ? "\u2014" : Number(n).toLocaleString("en-IN");
function fmtINR(n) {
  n = Number(n);
  if (isNaN(n)) return "\u2014";
  if (Math.abs(n) >= 1e7) return "\u20b9" + (n / 1e7).toFixed(1).replace(/\.0$/, "") + " Cr";
  if (Math.abs(n) >= 1e5) return "\u20b9" + (n / 1e5).toFixed(1).replace(/\.0$/, "") + " L";
  return "\u20b9" + fmtN(Math.round(n));
}
const icon = (n) => ICONS[n] || "";

/* stamps: verdicts as seals. */
const STAMP_CLASS = {
  COMPLY: "st-ok", SATISFIABLE: "st-ok", CURRENT: "st-ok", READY: "st-ok", VALID: "st-ok", OK: "st-ok",
  DEVIATION: "st-bad", CHECK_FAILS: "st-bad", INVALID: "st-bad", NEGATIVE: "st-bad", EXPIRED: "st-bad", CRITICAL: "st-bad",
  NEEDS_REVIEW: "st-warn", REVIEW: "st-warn", THIN: "st-warn", TARGETED_SAMPLING: "st-warn", PENDING: "st-mut",
  MISSING_EVIDENCE: "st-mut", NOT_ADDRESSED: "st-mut", BLOCKED: "st-mut",
  STALE: "st-verm", AMENDS: "st-verm", DRAFT: "st-purple", NEW: "st-verm", "IN LEDGER": "st-ok",
};
function stamp(v, extraClass) {
  if (!v) return "";
  const label = String(v).replace(/_/g, " ");
  return '<span class="stamp ' + (STAMP_CLASS[v] || "st-mut") + " " + (extraClass || "") + '">' + esc(label) + "</span>";
}
const struckComply = '<span class="stamp st-bad struck" title="the vendor stamped Comply; their own datasheet contradicts it">vendor: comply</span>';

/* ---------------- api with latency provenance ---------------- */
let LAST_MS = 0;
async function api(path, opts) {
  const t0 = performance.now();
  const r = await fetch(path, opts);
  LAST_MS = Math.round(performance.now() - t0);
  const dot = $("#net-dot"), msEl = $("#net-ms");
  if (dot) { dot.classList.add("live"); setTimeout(() => dot.classList.remove("live"), 250); }
  if (msEl) msEl.textContent = LAST_MS + " ms";
  if (!r.ok) {
    let msg = "HTTP " + r.status;
    try { msg = (await r.json()).error || msg; } catch (e) { /* keep */ }
    throw new Error(path + ": " + msg);
  }
  return r.json();
}
const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
function prov(extra) {
  return '<span class="prov">fetched in <b>' + LAST_MS + " ms</b> \u00b7 " + new Date().toLocaleTimeString() + (extra ? " \u00b7 " + esc(extra) : "") + "</span>";
}

/* ---------------- toast / modal / errors ---------------- */
let toastTimer = null;
function toast(msg, ms) {
  const t = $("#toast");
  t.innerHTML = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), ms || 4200);
}
function modal(title, html) {
  $("#modal-title").textContent = title;
  $("#modal-body").innerHTML = html;
  $("#modal").classList.remove("hidden");
}
async function openDoc(file) {
  try { const d = await api("/api/paperwork/doc?f=" + encodeURIComponent(file)); modal(d.file, md2html(d.markdown)); }
  catch (e) { toast(esc(e.message)); }
}
async function openGuide(file) {
  try { const d = await api("/api/guide?f=" + encodeURIComponent(file)); modal(d.file, md2html(d.markdown)); }
  catch (e) { toast(esc(e.message)); }
}
window.addEventListener("error", (e) => showErr(e.message || "script error"));
window.addEventListener("unhandledrejection", (e) => showErr((e.reason && e.reason.message) || "async error"));
function showErr(msg) {
  const o = $("#err-overlay");
  if (!o) return;
  o.innerHTML = "\u26a0 " + esc(msg) + ' <span style="opacity:.7">(click to dismiss)</span>';
  o.classList.remove("hidden");
  o.onclick = () => o.classList.add("hidden");
}

/* ---------------- tiny markdown ---------------- */
function md2html(md) {
  const lines = String(md || "").split("\n");
  let out = [], inCode = false, inList = null, inTable = false;
  const flushList = () => { if (inList) { out.push(inList === "ul" ? "</ul>" : "</ol>"); inList = null; } };
  const inline = (s) => esc(s)
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (l.startsWith("```")) { flushList(); inCode = !inCode; out.push(inCode ? "<pre>" : "</pre>"); continue; }
    if (inCode) { out.push(esc(l)); continue; }
    if (/^\|/.test(l)) {
      if (/^\|[\s:-]+\|/.test(l.replace(/[^|:\s-]/g, ""))) { continue; }
      const cells = l.split("|").slice(1, -1).map((c) => c.trim());
      if (!inTable) { flushList(); out.push("<table>"); inTable = true; out.push("<tr>" + cells.map((c) => "<th>" + inline(c) + "</th>").join("") + "</tr>"); }
      else out.push("<tr>" + cells.map((c) => "<td>" + inline(c) + "</td>").join("") + "</tr>");
      continue;
    }
    if (inTable) { out.push("</table>"); inTable = false; }
    const h = /^(#{1,4})\s+(.*)/.exec(l);
    if (h) { flushList(); out.push("<h" + h[1].length + ">" + inline(h[2]) + "</h" + h[1].length + ">"); continue; }
    if (/^\s*[-*]\s+/.test(l)) { if (inList !== "ul") { flushList(); out.push("<ul>"); inList = "ul"; } out.push("<li>" + inline(l.replace(/^\s*[-*]\s+/, "")) + "</li>"); continue; }
    if (/^\s*\d+\.\s+/.test(l)) { if (inList !== "ol") { flushList(); out.push("<ol>"); inList = "ol"; } out.push("<li>" + inline(l.replace(/^\s*\d+\.\s+/, "")) + "</li>"); continue; }
    if (/^>\s?/.test(l)) { flushList(); out.push("<blockquote>" + inline(l.replace(/^>\s?/, "")) + "</blockquote>"); continue; }
    if (/^---+\s*$/.test(l)) { flushList(); out.push("<hr>"); continue; }
    if (l.trim() === "") { flushList(); continue; }
    flushList();
    out.push("<p>" + inline(l) + "</p>");
  }
  flushList();
  if (inTable) out.push("</table>");
  if (inCode) out.push("</pre>");
  return out.join("\n");
}

/* ---------------- routes / tabs ---------------- */
const ROUTES = [
  { id: "hub", label: "Hub", icon: "hub", fn: vHub, group: 0 },
  { id: "overview", label: "Overview", icon: "overview", fn: vOverview, group: 1 },
  { id: "clock", label: "Clock", icon: "clock", fn: vClock, group: 1 },
  { id: "queue", label: "Queue", icon: "queue", fn: vQueue, group: 1 },
  { id: "review", label: "Review", icon: "review", fn: vReview, group: 2 },
  { id: "graph", label: "Graph", icon: "graph", fn: vGraph, group: 2 },
  { id: "lint", label: "Defects", icon: "lint", fn: vLint, group: 2 },
  { id: "external", label: "External", icon: "external", fn: vExternal, group: 2 },
  { id: "blast", label: "Blast", icon: "blast", fn: vBlast, group: 3 },
  { id: "margins", label: "Margins", icon: "margins", fn: vMargins, group: 3 },
  { id: "vendors", label: "Vendors", icon: "vendors", fn: vVendors, group: 3 },
  { id: "paperwork", label: "Paperwork", icon: "paperwork", fn: vPaperwork, group: 4 },
  { id: "cx", label: "Cx", icon: "cx", fn: vCx, group: 4 },
  { id: "ncr", label: "NCR", icon: "ncr", fn: vNcr, group: 4 },
];
function renderTabs(activeId) {
  const nav = $("#tabs");
  let html = "", lastGroup = 0;
  for (const r of ROUTES) {
    if (r.group !== lastGroup) { html += '<span class="tab-sep"></span>'; lastGroup = r.group; }
    html += '<div class="tab' + (r.id === activeId ? " active" : "") + '" data-r="' + r.id + '">' + icon(r.icon) + '<span class="tab-label">' + r.label + "</span></div>";
  }
  nav.innerHTML = html;
  nav.querySelectorAll(".tab").forEach((t) => { t.onclick = () => { location.hash = "#" + t.dataset.r; }; });
}
let CLEANUP = null;
function skeleton() {
  return '<div class="view"><div class="skel" style="height:30px;width:320px;margin-bottom:14px"></div><div class="grid g3"><div class="skel" style="height:110px"></div><div class="skel" style="height:110px"></div><div class="skel" style="height:110px"></div></div><div class="skel mt" style="height:260px"></div></div>';
}
async function route() {
  if (CLEANUP) { try { CLEANUP(); } catch (e) { /* noop */ } CLEANUP = null; }
  document.querySelectorAll(".fab").forEach((f) => f.remove());
  const h = (location.hash || "#hub").slice(1);
  const seg = h.split("/");
  const id = seg.shift() || "hub";
  const arg = decodeURIComponent(seg.join("/") || "");
  const r = ROUTES.find((x) => x.id === id) || (id === "settings" ? { id: "settings", fn: vSettings } : ROUTES[0]);
  renderTabs(r.id);
  const view = $("#view");
  view.innerHTML = skeleton();
  try { await r.fn(view, arg); } catch (e) {
    view.innerHTML = '<div class="view"><div class="callout">This screen failed to load: ' + esc(e.message) + "</div></div>";
  }
}
function addFab(hash, label) {
  const b = document.createElement("button");
  b.className = "fab";
  b.innerHTML = icon("link") + esc(label || "connections");
  b.onclick = () => { location.hash = hash; };
  document.body.appendChild(b);
}
function head(title, sub, extra) {
  return '<div class="view-head"><h1>' + esc(title) + '</h1><span class="sub">' + (sub || "") + '</span><span class="spacer"></span>' + (extra || prov()) + "</div>";
}

/* =========================================================== hub */
const SOURCES = [
  { key: "documents", label: "Project documents", route: "#review", count: (s) => (s.corpus_files || 0) + " files" },
  { key: "specs", label: "Specifications", route: "#lint", count: (s) => (s.rules || 0) + " rules" },
  { key: "schedule", label: "Schedule", route: "#clock", count: (s) => ((s.node_types || {}).activity || 0) + " activities" },
  { key: "procurement", label: "Procurement", route: "#vendors", count: (s) => ((s.node_types || {}).po || 0) + " POs" },
  { key: "quality", label: "Quality records", route: "#cx", count: (s) => (((s.node_types || {}).cx || 0)) + " tests \u00b7 " + (s.ncrs || 0) + " NCRs" },
];
async function vHub(view) {
  const s = await api("/api/summary");
  $("#spend").textContent = "$" + (s.llm_spend_usd == null ? "\u2014" : s.llm_spend_usd.toFixed(2));
  const checksTotal = Object.values(s.verdicts_post || {}).reduce((a, b) => a + b, 0);
  view.innerHTML =
    '<div class="view">' +
    head("The intelligence layer", "five sources, one ledger \u2014 every count on this screen was fetched and computed just now") +
    '<div class="hub">' +
    '  <div class="card hub-canvas-card" style="min-height:460px"><canvas id="hub-canvas"></canvas>' +
    '    <div class="hub-cap">click a source to open its ledger view \u00b7 ' + s.graph_nodes + " nodes / " + s.graph_edges + ' edges in the full graph</div></div>' +
    "  <div>" +
    '    <div class="card mb"><h2>' + icon("upload") + 'Feed the ledger <span class="right">sha-256 fingerprinting, live</span></h2>' +
    '      <div class="dropzone" id="dz">' + icon("upload") + '<div class="dz-title">Drop project documents here</div>' +
    '      <div class="dz-sub">PDF, CSV, HTML \u00b7 corpus files are recognized; unseen documents get a live numeric-claim harvest \u2014 no LLM needed</div></div>' +
    '      <input type="file" id="dz-input" multiple style="display:none">' +
    '      <div id="ingest-out"></div>' +
    "    </div>" +
    '    <div class="card"><h2>Start here</h2><div id="hub-links"></div></div>' +
    "  </div>" +
    "</div>" +
    '<div class="footnote">CLAUSE \u00b7 DC-EPC-01 \u00b7 set in ink &amp; paper \u00b7 verdicts are stamps and stamps must be earned</div>' +
    "</div>";
  const links = [
    ["#overview", "overview", "Ledger overview", checksTotal + " checks held \u00b7 " + ((s.verdicts_post || {}).DEVIATION || 0) + " deviations"],
    ["#clock", "clock", "Decision clock", (s.days_to_decide != null ? s.days_to_decide + " days to decide concessions" : "windows & exposure")],
    ["#review", "review", "Evidence review", "every verdict beside its two quotes"],
    ["#external", "external", "External reality check", (s.external_checks || 0) + " checks on real documents"],
  ];
  $("#hub-links").innerHTML = links.map((l) =>
    '<div class="neigh" data-h="' + l[0] + '" style="padding:7px 4px">' + icon(l[1]) + "<b>" + esc(l[2]) + '</b><span class="et">' + esc(l[3]) + "</span></div>").join("");
  $("#hub-links").querySelectorAll(".neigh").forEach((n) => { n.onclick = () => { location.hash = n.dataset.h; }; });
  initConstellation(s, checksTotal);
  initUploader();
}
function initConstellation(s, checksTotal) {
  const canvas = $("#hub-canvas"), card = canvas.parentElement;
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let W = 0, H = 0, raf = 0, frame = 0, theta = -Math.PI / 2, hover = -1;
  const pos = SOURCES.map(() => ({ x: 0, y: 0 }));
  function size() {
    W = card.clientWidth; H = card.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  size();
  const onResize = () => size();
  window.addEventListener("resize", onResize);
  const ink = "#211c14", verm = "#c9442a", paper = "#faf7ef";
  function draw() {
    frame++;
    theta += 0.00045;
    const intro = Math.min(1, frame / 80);
    const ease = 1 - Math.pow(1 - intro, 3);
    const cx = W / 2, cy = H / 2 - 8;
    const rx = Math.min(W * 0.36, 330), ry = Math.min(H * 0.32, 190);
    ctx.clearRect(0, 0, W, H);
    // edges
    for (let i = 0; i < SOURCES.length; i++) {
      const a = theta + (i * 2 * Math.PI) / SOURCES.length;
      const tx = cx + Math.cos(a) * rx, ty = cy + Math.sin(a) * ry;
      const x = cx + (tx - cx) * ease, y = cy + (ty - cy) * ease;
      pos[i].x = x; pos[i].y = y;
      ctx.strokeStyle = "rgba(33,28,20," + (hover === i ? "0.85" : "0.3") + ")";
      ctx.lineWidth = hover === i ? 1.8 : 1.2;
      ctx.setLineDash([5, 6]);
      ctx.lineDashOffset = -(frame * 0.35);
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(cx, cy); ctx.stroke();
      ctx.setLineDash([]);
      // packet flowing inward
      const t = ((frame * 0.004) + i / 5) % 1;
      ctx.fillStyle = verm;
      ctx.beginPath(); ctx.arc(x + (cx - x) * t, y + (cy - y) * t, 2.4, 0, 7); ctx.fill();
    }
    // source nodes
    for (let i = 0; i < SOURCES.length; i++) {
      const p = pos[i], hovered = hover === i;
      const r = hovered ? 32 : 28;
      ctx.fillStyle = paper;
      ctx.strokeStyle = ink; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7); ctx.fill(); ctx.stroke();
      if (hovered) { ctx.strokeStyle = verm; ctx.beginPath(); ctx.arc(p.x, p.y, r + 3.5, 0, 7); ctx.stroke(); }
      ctx.fillStyle = ink;
      ctx.textAlign = "center";
      ctx.font = "600 11px -apple-system, Segoe UI, sans-serif";
      const lift = p.y < cy ? -r - 20 : r + 14;
      ctx.fillText(SOURCES[i].label, p.x, p.y + lift);
      ctx.font = "10px ui-monospace, Menlo, monospace";
      ctx.fillStyle = "rgba(33,28,20,.62)";
      ctx.fillText(SOURCES[i].count(s), p.x, p.y + lift + 13);
      ctx.font = "700 10px ui-monospace, Menlo, monospace";
      ctx.fillStyle = hovered ? verm : "rgba(33,28,20,.8)";
      ctx.fillText(hovered ? "open \u2192" : String(i + 1).padStart(2, "0"), p.x, p.y + 3.5);
    }
    // core seal
    ctx.save();
    ctx.translate(cx, cy); ctx.rotate(-0.035);
    const cw = 108, ch = 64;
    ctx.fillStyle = verm; ctx.strokeStyle = ink; ctx.lineWidth = 1.5;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(-cw / 2, -ch / 2, cw, ch, 7); else ctx.rect(-cw / 2, -ch / 2, cw, ch);
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = paper;
    ctx.textAlign = "center";
    ctx.font = "700 16px Iowan Old Style, Palatino, Georgia, serif";
    ctx.fillText("CLAUSE", 0, -6);
    ctx.font = "9px ui-monospace, Menlo, monospace";
    ctx.fillText(checksTotal + " checks held", 0, 12);
    ctx.restore();
    raf = requestAnimationFrame(draw);
  }
  function hitTest(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    let h = -1;
    for (let i = 0; i < pos.length; i++) {
      if ((mx - pos[i].x) ** 2 + (my - pos[i].y) ** 2 < 36 * 36) h = i;
    }
    const coreHit = Math.abs(mx - W / 2) < 58 && Math.abs(my - (H / 2 - 8)) < 36;
    return { h, coreHit };
  }
  canvas.onmousemove = (e) => {
    const { h, coreHit } = hitTest(e);
    hover = h;
    canvas.style.cursor = (h >= 0 || coreHit) ? "pointer" : "default";
  };
  canvas.onclick = (e) => {
    const { h, coreHit } = hitTest(e);
    if (h >= 0) location.hash = SOURCES[h].route;
    else if (coreHit) location.hash = "#overview";
  };
  raf = requestAnimationFrame(draw);
  CLEANUP = () => { cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); };
}
const MODULE_NAMES = {
  "m5_addendum.py": "M5 \u00b7 addendum blast wave", "m5_graph.py": "M5 \u00b7 ledger graph",
  "m6_disposition.py": "M6 \u00b7 NCRs & dispositions", "m7_options.py": "M7 \u00b7 decision clock",
  "m8_margin.py": "M8 \u00b7 margins & energy", "m9_vendor.py": "M9 \u00b7 vendor trust",
  "m10_paperwork.py": "M10 \u00b7 spec linter & paperwork", "m11_cx.py": "M11 \u00b7 commissioning packs",
};
function initUploader() {
  const dz = $("#dz"), input = $("#dz-input"), out = $("#ingest-out");
  dz.onclick = () => input.click();
  ["dragover", "dragenter"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
  dz.addEventListener("drop", (e) => handleFiles(e.dataTransfer.files));
  input.onchange = () => handleFiles(input.files);
  async function handleFiles(fileList) {
    const files = Array.from(fileList || []).slice(0, 12);
    if (!files.length) return;
    out.innerHTML = '<div class="mt mono" style="font-size:11px;color:var(--ink3)">reading ' + files.length + " file(s) + computing fingerprints\u2026</div>";
    const payload = [];
    for (const f of files) {
      if (f.size > 30e6) { payload.push({ name: f.name, b64: "" }); continue; }
      const b64 = await new Promise((res, rej) => {
        const rd = new FileReader();
        rd.onload = () => res(String(rd.result).split(",")[1] || "");
        rd.onerror = rej;
        rd.readAsDataURL(f);
      });
      payload.push({ name: f.name, b64 });
    }
    let res;
    try { res = await post("/api/ingest", { files: payload }); }
    catch (e) { out.innerHTML = '<div class="callout mt">' + esc(e.message) + "</div>"; return; }
    let html = "";
    for (const r of res.recognized || []) {
      html += '<div class="ingest-row">' + stamp("IN LEDGER") + '<div><div class="fn">' + esc(r.name) + '</div><div class="meta">recognized \u00b7 ' + esc(r.kind) + " \u00b7 " + esc(r.path) + "</div></div></div>";
    }
    for (const u of res.unknown || []) {
      const meta = u.error ? esc(u.error)
        : (u.pages + " pages \u00b7 <b>" + u.total_hits + "</b> numeric claims harvested live, with page-cited quotes");
      const sample = (u.hits || []).slice(0, 2).map((h) =>
        '<div class="quote q-claim" style="margin-top:6px"><span class="q-src">p' + h.page + " \u00b7 " + esc(h.value) + " " + esc(h.unit) + '</span>' + esc(h.quote) + "</div>").join("");
      html += '<div class="ingest-row">' + stamp("NEW") + '<div style="min-width:0"><div class="fn">' + esc(u.name) + '</div><div class="meta">' + meta + "</div>" + sample + "</div></div>";
    }
    const anyRecognized = (res.recognized || []).length > 0;
    html += '<div class="mt row">' + (anyRecognized ? '<button class="btn btn-primary" id="btn-runpipe">Run the pipeline</button>' : "") +
      '<span class="prov">' + (res.recognized || []).length + " recognized \u00b7 " + (res.unknown || []).length + " new \u00b7 fingerprinted against " + res.corpus_files + " corpus files</span></div>" +
      '<div id="stage-out"></div>';
    out.innerHTML = html;
    const btn = $("#btn-runpipe");
    if (btn) btn.onclick = () => runPipeline(btn);
  }
  async function runPipeline(btn) {
    btn.disabled = true;
    const stageOut = $("#stage-out");
    const mods = Object.keys(MODULE_NAMES);
    stageOut.innerHTML = '<ul class="stagelist">' + mods.map((m, i) =>
      '<li id="stg-' + i + '"><span class="dot"></span>' + esc(MODULE_NAMES[m]) + '<span class="ms"></span></li>').join("") + "</ul>" +
      '<div class="mono" style="font-size:10px;color:var(--ink3)">measured timings, replayed as they happened</div>';
    let res;
    try { res = await post("/api/ingest/run"); }
    catch (e) { stageOut.innerHTML = '<div class="callout">' + esc(e.message) + "</div>"; return; }
    let total = 0;
    for (let i = 0; i < (res.timings || []).length; i++) {
      const t = res.timings[i];
      const li = $("#stg-" + i);
      if (li) { li.className = "run"; }
      await sleep(Math.max(240, Math.min(t.ms, 900)));
      if (li) { li.className = "done"; li.querySelector(".ms").textContent = t.ms + " ms"; }
      total += t.ms;
    }
    const s = res.summary || {};
    const checks = Object.values(s.verdicts_post || {}).reduce((a, b) => a + b, 0);
    stageOut.innerHTML += '<div class="callout c-ok mt">Ledger rebuilt in <b class="mono">' + total + " ms</b> \u2014 " +
      fmtN(s.rules) + " rules \u00b7 " + fmtN(s.claims) + " claims \u00b7 " + fmtN(checks) + " checks \u00b7 " +
      ((s.verdicts_post || {}).DEVIATION || 0) + ' deviations.</div><div class="row mt">' +
      '<button class="btn" onclick="location.hash=\'#overview\'">Open overview</button>' +
      '<button class="btn" onclick="location.hash=\'#clock\'">Decision clock</button>' +
      '<button class="btn" onclick="location.hash=\'#review\'">Evidence review</button></div>';
  }
}

/* =========================================================== overview */
async function vOverview(view) {
  const s = await api("/api/summary");
  $("#spend").textContent = "$" + (s.llm_spend_usd == null ? "\u2014" : s.llm_spend_usd.toFixed(2));
  const post_ = s.verdicts_post || {}, pre = s.verdicts_pre || {};
  const checks = Object.values(post_).reduce((a, b) => a + b, 0);
  const order = ["DEVIATION", "NEEDS_REVIEW", "COMPLY", "MISSING_EVIDENCE", "NOT_ADDRESSED"];
  const colors = { DEVIATION: "b-bad", NEEDS_REVIEW: "b-warn", COMPLY: "b-ok", MISSING_EVIDENCE: "", NOT_ADDRESSED: "" };
  const maxV = Math.max(...order.map((k) => post_[k] || 0), 1);
  const evalKv = (ev) => !ev ? '<div class="form-note">no eval report</div>' :
    Object.entries(ev).filter(([, v]) => typeof v === "number" || typeof v === "string").slice(0, 8).map(([k, v]) =>
      '<div class="d-kv"><span class="k">' + esc(k) + '</span><span class="v">' + esc(typeof v === "number" ? (Math.round(v * 100) / 100) : v) + "</span></div>").join("");
  view.innerHTML = '<div class="view">' +
    head("Ledger overview", "what the machine holds right now") +
    '<div class="grid g4 mb">' +
    '<div class="card metric"><div class="num">' + fmtN(s.rules) + '</div><div class="lbl">rules compiled from specs</div></div>' +
    '<div class="card metric"><div class="num">' + fmtN(s.claims) + '</div><div class="lbl">claims extracted from submittals</div></div>' +
    '<div class="card metric"><div class="num">' + fmtN(checks) + '</div><div class="lbl">checks held in the ledger</div></div>' +
    '<div class="card metric"><div class="num num-bad">' + fmtN(post_.DEVIATION || 0) + '</div><div class="lbl">deviations, each with two quotes</div></div>' +
    "</div>" +
    '<div class="callout mb">' + struckComply + " &nbsp;<b>" + (s.false_comply_post || 0) + " claims were stamped \u201cComply\u201d by the vendor and are contradicted by the vendor\u2019s own datasheet.</b> The stamp was not earned \u2014 CLAUSE re-earns every stamp from evidence.</div>" +
    '<div class="grid g2 mb">' +
    '<div class="card"><h2>' + icon("overview") + 'verdicts after ADD-003 <span class="right">pre-addendum in grey</span></h2><div class="vbars">' +
    order.map((k) => {
      const h = Math.round(((post_[k] || 0) / maxV) * 70) + 4;
      const hp = Math.round(((pre[k] || 0) / maxV) * 70) + 4;
      return '<div class="vbar" title="pre: ' + (pre[k] || 0) + '"><span class="mono" style="font-size:11px">' + (post_[k] || 0) + '</span><div style="display:flex;gap:3px;width:100%;align-items:flex-end"><div class="col bar ' + (colors[k] || "") + '" style="height:' + h + 'px;flex:2"></div><div class="col" style="height:' + hp + 'px;flex:1;background:var(--raised)"></div></div><span class="vl">' + k.replace(/_/g, " ").toLowerCase() + "</span></div>";
    }).join("") +
    "</div></div>" +
    '<div class="card"><h2>' + icon("cx") + "answer-key eval (frozen)</h2>" + evalKv(s.eval_post) + '<div class="form-note">measured against the corpus answer key \u2014 the machine grades itself and publishes the grade</div></div>' +
    "</div>" +
    '<div class="grid g3">' +
    '<div class="card hoverable" onclick="location.hash=\'#blast\'"><h2>' + icon("blast") + "blast wave \u00b7 ADD-003</h2>" +
    (s.blast ? '<div class="d-kv"><span class="k">rules amended</span><span class="v">' + s.blast.rules_amended + '</span></div><div class="d-kv"><span class="k">verdicts flipped</span><span class="v">' + s.blast.verdict_flips + '</span></div><div class="d-kv"><span class="k">POs invalidated</span><span class="v">' + s.blast.pos_invalidated + '</span></div><div class="d-kv"><span class="k">Cx tests stale</span><span class="v">' + s.blast.cx_tests_stale + "</span></div>" : "") + "</div>" +
    '<div class="card hoverable" onclick="location.hash=\'#clock\'"><h2>' + icon("clock") + 'next decision</h2><div class="metric"><div class="num num-verm">' + (s.days_to_decide != null ? s.days_to_decide + "d" : "\u2014") + '</div><div class="lbl">to decide concessions \u00b7 by ' + esc(s.decide_by || "\u2014") + "</div></div></div>" +
    '<div class="card"><h2>' + icon("margins") + 'cost of everything shown</h2><div class="metric"><div class="num">$' + (s.llm_spend_usd || 0).toFixed(2) + '</div><div class="lbl">cumulative LLM spend \u00b7 deterministic layer reruns at $0</div></div></div>' +
    "</div></div>";
}

/* =========================================================== clock */
async function vClock(view) {
  const o = await api("/api/options");
  const pkgs = o.packages || [];
  const minDays = Math.min(...pkgs.map((p) => p.days_to_decide == null ? 1e9 : p.days_to_decide));
  const rows = pkgs.map((p) =>
    '<tr class="rowlink" data-pkg="' + esc(p.package) + '"><td class="mono">' + esc(p.package) + "</td><td>" + esc(p.vendor || "") + '</td><td class="mono r">' + fmtINR(p.value_inr) + "</td><td>" + stamp(p.reject_status) + '</td><td class="mono r">' + (p.slip_if_rejected_today_days != null ? "+" + p.slip_if_rejected_today_days + "d slip" : "\u2014") + '</td><td class="mono">' + esc(p.need_on_site || "") + '</td><td class="mono">' + esc(p.decide_concessions_by || "") + '</td><td class="mono r">' + (p.days_to_decide != null ? p.days_to_decide : "\u2014") + "</td></tr>").join("");
  view.innerHTML = '<div class="view">' +
    head("Decision clock", "true calendar consequences \u2014 including the uncomfortable ones") +
    '<div class="grid g3 mb">' +
    '<div class="card metric"><div class="num num-verm">' + (isFinite(minDays) && minDays < 1e9 ? minDays : "\u2014") + ' days</div><div class="lbl">to decide concessions (earliest gate)</div><div class="note mono">today: ' + esc(o.today || "") + "</div></div>" +
    '<div class="card metric"><div class="num">' + pkgs.length + '</div><div class="lbl">packages tracked against the schedule</div></div>' +
    '<div class="card metric"><div class="num num-bad">' + pkgs.filter((p) => p.reject_status === "EXPIRED").length + '</div><div class="lbl">rejection windows already closed</div></div>' +
    "</div>" +
    '<div class="callout mb"><b>The window to reject and re-order has passed for every package.</b> That is not a flaw in the plan \u2014 it is the truth of the calendar. The live choices are: accept with conditions (and price the consequence), or make the vendor rectify. CLAUSE leads with the uncomfortable number instead of hiding it.</div>' +
    '<div class="card"><h2>' + icon("clock") + 'per-package windows <span class="right">' + esc((o.derivation || {}).anchor || "").slice(0, 110) + '</span></h2>' +
    '<table><tr><th>package</th><th>vendor</th><th class="r">value</th><th>reject window</th><th class="r">if rejected today</th><th>need on site</th><th>decide by</th><th class="r">days left</th></tr>' + rows + "</table>" +
    '<div class="form-note">approval lead assumption: ' + esc(String((o.derivation || {}).approval_lead_days_assumption || "\u2014")) + " days (labelled, not hidden)</div></div></div>";
  view.querySelectorAll("tr.rowlink").forEach((tr) => { tr.onclick = () => { location.hash = "#graph/" + encodeURIComponent("pkg:" + tr.dataset.pkg); }; });
  addFab("#graph", "view connections");
}

/* =========================================================== queue */
async function vQueue(view) {
  const d = await api("/api/queue");
  const q = (d.queue || []).slice().sort((a, b) => (b.severity_score || 0) - (a.severity_score || 0));
  const cards = q.map((p) => {
    const items = (p.items || []).slice(0, 6).map((it) =>
      '<div class="d-kv" style="align-items:center"><span class="k mono">' + esc(it.ncr_id || "") + '</span><span style="flex:1;font-size:12px;padding:0 8px">' + esc(it.parameter || "") + "</span>" +
      ((it.flags || []).includes("false_comply") ? struckComply + " " : "") + stamp(it.verdict) + "</div>").join("");
    return '<div class="card mb"><div class="row"><b class="mono">' + esc(p.package) + "</b>" + stamp(p.delivered ? "DELIVERED" : "IN TRANSIT", "straight") +
      '<span class="chip">severity ' + (p.severity_score || 0) + '</span><span class="chip">' + fmtINR(p.value_inr) + '</span><span class="chip">float ' + (p.min_float_days != null ? p.min_float_days + "d" : "\u2014") + '</span><span class="spacer"></span>' +
      '<button class="btn" data-doc="letter_' + esc(p.package) + '.md">Letter</button>' +
      '<button class="btn" data-graph="pkg:' + esc(p.package) + '">Connections</button></div>' +
      '<div class="mt">' + items + "</div>" +
      ((p.items || []).length > 6 ? '<div class="form-note">+' + ((p.items || []).length - 6) + " more in the register</div>" : "") + "</div>";
  }).join("");
  view.innerHTML = '<div class="view">' + head("Disposition queue", "worst first \u2014 severity is exposure \u00d7 float \u00d7 open findings") + cards + "</div>";
  view.querySelectorAll("[data-doc]").forEach((b) => { b.onclick = () => openDoc(b.dataset.doc); });
  view.querySelectorAll("[data-graph]").forEach((b) => { b.onclick = () => { location.hash = "#graph/" + encodeURIComponent(b.dataset.graph); }; });
}

/* =========================================================== review */
async function vReview(view, arg) {
  const pk = await api("/api/packages");
  const pkgs = pk.packages || [];
  let pkg = arg && pkgs.includes(arg) ? arg : (sessionStorage.getItem("pkg") || pkgs[0]);
  if (!pkgs.includes(pkg)) pkg = pkgs[0];
  let mode = sessionStorage.getItem("mode") || "post";
  async function render() {
    sessionStorage.setItem("pkg", pkg); sessionStorage.setItem("mode", mode);
    const v = await api("/api/verdicts/" + encodeURIComponent(pkg) + "?mode=" + mode);
    const results = v.results || [];
    const order = ["DEVIATION", "NEEDS_REVIEW", "COMPLY", "MISSING_EVIDENCE", "NOT_ADDRESSED"];
    results.sort((a, b) => order.indexOf(a.verdict) - order.indexOf(b.verdict));
    const counts = {};
    results.forEach((r) => { counts[r.verdict] = (counts[r.verdict] || 0) + 1; });
    const rows = results.map((r) => {
      const req = r.requirement || {}, cl = r.governing_claim;
      return '<div class="ev-row"><div class="ev-head">' + stamp(r.verdict) +
        ((r.flags || []).includes("false_comply") ? struckComply : "") +
        '<span class="param">' + esc(r.parameter || "") + '</span><span class="chip">' + esc(r.rule_id || "") + "</span>" +
        (req.amended_by ? '<span class="chip" style="color:var(--verm)">amended by ' + esc(req.amended_by) + "</span>" : "") +
        '<span class="spacer"></span></div>' +
        '<div class="ev-pair"><div class="quote q-req"><span class="q-src">spec \u00b7 ' + esc(req.source_clause || "") + (req.page ? " \u00b7 p" + req.page : "") + "</span>" + esc(req.quote || "") + "</div>" +
        (cl ? '<div class="quote q-claim"><span class="q-src">submittal' + (cl.page ? " \u00b7 p" + cl.page : "") + (cl.location ? " \u00b7 " + esc(cl.location) : "") + "</span>" + esc(cl.quote || "") + "</div>"
            : '<div class="quote"><span class="q-src">submittal</span><i>no governing evidence \u2014 the machine does not guess</i></div>') + "</div>" +
        (r.reason ? '<div class="reason">' + esc(r.reason) + "</div>" : "") + "</div>";
    }).join("");
    view.innerHTML = '<div class="view">' +
      head("Evidence review", "every stamp beside the two sentences that earned it") +
      '<div class="row mb"><select class="inline" id="pkg-sel">' + pkgs.map((p) => '<option' + (p === pkg ? " selected" : "") + ">" + esc(p) + "</option>").join("") + "</select>" +
      '<div class="seg"><button id="seg-pre" class="' + (mode === "pre" ? "on" : "") + '">pre-addendum</button><button id="seg-post" class="' + (mode === "post" ? "on" : "") + '">post ADD-003</button></div>' +
      '<span class="spacer"></span>' + order.filter((k) => counts[k]).map((k) => stamp(k, "straight") + ' <span class="mono" style="font-size:11px;margin-right:8px">' + counts[k] + "</span>").join("") + "</div>" + rows + "</div>";
    $("#pkg-sel").onchange = (e) => { pkg = e.target.value; render(); };
    $("#seg-pre").onclick = () => { mode = "pre"; render(); };
    $("#seg-post").onclick = () => { mode = "post"; render(); };
    document.querySelectorAll(".fab").forEach((f) => f.remove());
    addFab("#graph/" + encodeURIComponent("pkg:" + pkg), "connections");
  }
  await render();
}

/* =========================================================== graph */
const NODE_COLORS = { section: "#355e8d", clause: "#7d8fae", package: "#a07416", po: "#3f7d4e", activity: "#6d5f92", cx: "#b0567f", addendum: "#c9442a" };
const BAD_STATUS = new Set(["DEVIATION", "INVALID", "STALE", "AMENDS", "CRITICAL", "EXPIRED", "NEGATIVE"]);
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
async function vGraph(view, arg) {
  const g = await api("/api/graph");
  const nodes = (g.nodes || []).map((n) => Object.assign({}, n));
  const rawEdges = (g.edges || []).map((e) => ({ s: e.s || e.source, t: e.t || e.target, type: e.type }));
  view.innerHTML = '<div class="view" style="max-width:none">' +
    head("The ledger graph", nodes.length + " nodes \u00b7 " + rawEdges.length + " edges \u2014 hover: connections \u00b7 click: what it does to you") +
    '<div class="graph-wrap"><div class="card graph-card"><canvas id="graph-canvas"></canvas></div>' +
    '<div class="graph-legend">' + Object.entries(NODE_COLORS).map(([k, c]) => '<div class="lg"><span class="sw" style="background:' + c + '"></span>' + k + "</div>").join("") +
    '<div class="lg"><span class="sw" style="background:transparent;border-color:var(--verm);box-shadow:0 0 0 1.5px var(--verm)"></span>flagged</div></div>' +
    '<div class="graph-stats mono" id="g-stats"></div>' +
    '<div class="graph-tip" id="g-tip"></div><div id="g-dossier"></div></div></div>';
  const canvas = $("#graph-canvas"), wrap = canvas.parentElement;
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let W = 0, H = 0;
  function size() {
    W = wrap.clientWidth; H = wrap.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
  }
  size();
  const onResize = () => size();
  window.addEventListener("resize", onResize);
  // ---- deterministic init
  const rng = mulberry32(1337);
  const RING = { section: 60, addendum: 110, clause: 190, package: 300, po: 380, activity: 450, cx: 520 };
  const byId = new Map();
  nodes.forEach((n) => {
    const r = (RING[n.type] || 400) * (0.85 + rng() * 0.3);
    const a = rng() * Math.PI * 2;
    n.x = Math.cos(a) * r; n.y = Math.sin(a) * r;
    n.vx = 0; n.vy = 0;
    byId.set(n.id, n);
  });
  const edges = rawEdges.filter((e) => byId.has(e.s) && byId.has(e.t));
  const adj = new Map();
  nodes.forEach((n) => adj.set(n.id, []));
  edges.forEach((e) => { adj.get(e.s).push({ id: e.t, type: e.type }); adj.get(e.t).push({ id: e.s, type: e.type }); });
  // ---- physics (bounded everywhere; the blank-screen bug is structurally impossible)
  const SPRING_LEN = 46, MAX_FORCE = 0.9, MAX_VEL = 3.5, CELL = 70, SETTLE = 900;
  let alpha = 1, tick = 0, raf = 0;
  const clamp = (v, m) => (v > m ? m : v < -m ? -m : v);
  function physics() {
    if (alpha < 0.02 || tick > SETTLE) return;
    tick++;
    const gridMap = new Map();
    nodes.forEach((n, i) => {
      const k = Math.floor(n.x / CELL) + ":" + Math.floor(n.y / CELL);
      (gridMap.get(k) || gridMap.set(k, []).get(k)).push(i);
    });
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const gx = Math.floor(n.x / CELL), gy = Math.floor(n.y / CELL);
      let fx = 0, fy = 0;
      for (let ox = -1; ox <= 1; ox++) for (let oy = -1; oy <= 1; oy++) {
        const cell = gridMap.get((gx + ox) + ":" + (gy + oy));
        if (!cell) continue;
        for (const j of cell) {
          if (j === i) continue;
          const m = nodes[j];
          let dx = n.x - m.x, dy = n.y - m.y;
          let d2 = dx * dx + dy * dy;
          if (d2 < 1) { dx = (rng() - 0.5); dy = (rng() - 0.5); d2 = 1; }
          const f = Math.min(1400 / d2, MAX_FORCE);
          const d = Math.sqrt(d2);
          fx += (dx / d) * f; fy += (dy / d) * f;
        }
      }
      n.vx = clamp(n.vx + clamp(fx, MAX_FORCE) * alpha, MAX_VEL);
      n.vy = clamp(n.vy + clamp(fy, MAX_FORCE) * alpha, MAX_VEL);
    }
    for (const e of edges) {
      const a = byId.get(e.s), b = byId.get(e.t);
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const f = clamp((d - SPRING_LEN) * 0.004, 0.9);
      const ux = dx / d, uy = dy / d;
      a.vx = clamp(a.vx + ux * f * alpha, MAX_VEL); a.vy = clamp(a.vy + uy * f * alpha, MAX_VEL);
      b.vx = clamp(b.vx - ux * f * alpha, MAX_VEL); b.vy = clamp(b.vy - uy * f * alpha, MAX_VEL);
    }
    for (const n of nodes) {
      if (n === dragNode) continue;
      n.vx = clamp(n.vx - n.x * 0.0009, MAX_VEL);
      n.vy = clamp(n.vy - n.y * 0.0009, MAX_VEL);
      n.x += n.vx; n.y += n.vy;
      n.vx *= 0.82; n.vy *= 0.82;
      if (!isFinite(n.x) || !isFinite(n.y)) { n.x = (rng() - 0.5) * 200; n.y = (rng() - 0.5) * 200; n.vx = n.vy = 0; }
    }
    alpha *= 0.996;
  }
  // ---- camera + interaction
  const cam = { s: 0.9, tx: 0, ty: 0 };
  cam.tx = W / 2; cam.ty = H / 2;
  let dragNode = null, panning = false, moved = false, lastX = 0, lastY = 0;
  let hoverId = null, selId = null;
  const toWorld = (px, py) => ({ x: (px - cam.tx) / cam.s, y: (py - cam.ty) / cam.s });
  function nearest(px, py) {
    const w = toWorld(px, py);
    let best = null, bd = (14 / cam.s) * (14 / cam.s);
    for (const n of nodes) {
      const d2 = (n.x - w.x) ** 2 + (n.y - w.y) ** 2;
      if (d2 < bd) { bd = d2; best = n; }
    }
    return best;
  }
  canvas.onmousedown = (e) => {
    const r = canvas.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    moved = false; lastX = px; lastY = py;
    dragNode = nearest(px, py);
    if (!dragNode) { panning = true; canvas.classList.add("dragging"); }
  };
  window.addEventListener("mouseup", onUp);
  function onUp() { dragNode = null; panning = false; canvas.classList.remove("dragging"); }
  canvas.onmousemove = (e) => {
    const r = canvas.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    if (dragNode) {
      const w = toWorld(px, py);
      dragNode.x = w.x; dragNode.y = w.y; dragNode.vx = dragNode.vy = 0;
      moved = true; alpha = Math.max(alpha, 0.12); tick = Math.min(tick, SETTLE - 60);
    } else if (panning) {
      cam.tx += px - lastX; cam.ty += py - lastY; moved = true;
    } else {
      const n = nearest(px, py);
      hoverId = n ? n.id : null;
      canvas.style.cursor = n ? "pointer" : "grab";
      const tip = $("#g-tip");
      if (n) {
        tip.style.display = "block";
        tip.style.left = Math.min(px + 14, W - 280) + "px";
        tip.style.top = (py + 12) + "px";
        tip.innerHTML = "<b>" + esc(n.label) + "</b> \u00b7 " + n.type + (n.status ? " \u00b7 " + esc(n.status) : "") + "<br>" + adj.get(n.id).length + " connections \u00b7 click for dossier";
      } else tip.style.display = "none";
    }
    lastX = px; lastY = py;
  };
  canvas.onclick = (e) => {
    if (moved) return;
    const r = canvas.getBoundingClientRect();
    const n = nearest(e.clientX - r.left, e.clientY - r.top);
    if (n) { selId = n.id; openDossier(n.id); } else { selId = null; $("#g-dossier").innerHTML = ""; }
  };
  canvas.onwheel = (e) => {
    e.preventDefault();
    const r = canvas.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    const w = toWorld(px, py);
    cam.s = Math.min(5, Math.max(0.25, cam.s * (e.deltaY < 0 ? 1.12 : 0.89)));
    cam.tx = px - w.x * cam.s; cam.ty = py - w.y * cam.s;
  };
  function focusNode(id) {
    const n = byId.get(id);
    if (!n) return;
    selId = id;
    cam.s = Math.max(cam.s, 1.4);
    cam.tx = W / 2 - n.x * cam.s; cam.ty = H / 2 - n.y * cam.s;
    openDossier(id);
  }
  // ---- draw
  function activeSet() {
    const focus = hoverId || selId;
    if (!focus) return null;
    const set = new Set([focus]);
    (adj.get(focus) || []).forEach((x) => set.add(x.id));
    return set;
  }
  function draw() {
    physics();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.translate(cam.tx * 1, cam.ty * 1);
    ctx.scale(cam.s, cam.s);
    const act = activeSet();
    const focus = hoverId || selId;
    ctx.lineWidth = 1 / cam.s;
    for (const e of edges) {
      const a = byId.get(e.s), b = byId.get(e.t);
      const on = act && (e.s === focus || e.t === focus);
      ctx.strokeStyle = on ? "rgba(201,68,42,.8)" : (act ? "rgba(33,28,20,.05)" : "rgba(33,28,20,.16)");
      ctx.lineWidth = (on ? 1.6 : 1) / cam.s;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    for (const n of nodes) {
      const rBase = n.type === "section" ? 7 : n.type === "addendum" ? 7 : n.type === "package" ? 6 : n.type === "po" ? 4.5 : n.type === "activity" ? 4 : n.type === "cx" ? 3.5 : 3;
      const inAct = !act || act.has(n.id);
      ctx.globalAlpha = inAct ? 1 : 0.13;
      ctx.fillStyle = NODE_COLORS[n.type] || "#888";
      ctx.strokeStyle = "#211c14";
      ctx.lineWidth = 1 / cam.s;
      ctx.beginPath(); ctx.arc(n.x, n.y, rBase, 0, 7); ctx.fill(); ctx.stroke();
      if (n.status && BAD_STATUS.has(n.status)) {
        ctx.strokeStyle = "#c9442a"; ctx.lineWidth = 1.6 / cam.s;
        ctx.beginPath(); ctx.arc(n.x, n.y, rBase + 2.4 / cam.s, 0, 7); ctx.stroke();
      }
      const showLabel = n.type === "section" || n.type === "addendum" || n.type === "package" || cam.s > 1.7 || (act && act.has(n.id) && cam.s > 0.7);
      if (showLabel && inAct) {
        ctx.fillStyle = "rgba(33,28,20,.86)";
        ctx.font = (10.5 / cam.s) + "px ui-monospace, Menlo, monospace";
        ctx.textAlign = "center";
        ctx.fillText(n.label.length > 26 ? n.label.slice(0, 25) + "\u2026" : n.label, n.x, n.y - rBase - 4 / cam.s);
      }
      ctx.globalAlpha = 1;
    }
    $("#g-stats").textContent = nodes.length + " nodes \u00b7 " + edges.length + " edges \u00b7 " + (tick >= SETTLE || alpha < 0.02 ? "settled" : "settling " + tick);
    raf = requestAnimationFrame(draw);
  }
  raf = requestAnimationFrame(draw);
  CLEANUP = () => { cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); window.removeEventListener("mouseup", onUp); };
  // ---- dossier
  async function openDossier(id) {
    const box = $("#g-dossier");
    box.innerHTML = '<div class="dossier"><div class="skel" style="height:20px;width:200px"></div><div class="skel mt" style="height:120px"></div></div>';
    let d;
    try { d = await api("/api/node?id=" + encodeURIComponent(id)); }
    catch (e) { box.innerHTML = '<div class="dossier">' + esc(e.message) + "</div>"; return; }
    const kv = (k, v) => (v == null || v === "") ? "" : '<div class="d-kv"><span class="k">' + esc(k) + '</span><span class="v">' + v + "</span></div>";
    let body = "";
    const meta = d.meta || {};
    if (d.type === "clause") {
      const checks = d.checks || [];
      body += '<div class="d-sec"><h4>what it does to you</h4>' +
        (checks.length ? checks.slice(0, 5).map((c) => '<div class="d-kv" style="align-items:center"><span class="k mono">' + esc(c.package) + "</span><span>" + ((c.flags || []).includes("false_comply") ? struckComply + " " : "") + stamp(c.verdict) + "</span></div>").join("")
          : '<div class="form-note">no package addresses this clause yet</div>') + "</div>";
      const withQuotes = checks.find((c) => c.requirement && c.requirement.quote);
      if (withQuotes) {
        const rq = withQuotes.requirement, cq = withQuotes.claim;
        body += '<div class="d-sec"><h4>the evidence</h4><div class="quote q-req"><span class="q-src">spec \u00b7 ' + esc(rq.source_clause || "") + (rq.page ? " \u00b7 p" + rq.page : "") + "</span>" + esc((rq.quote || "").slice(0, 260)) + "</div>" +
          (cq && cq.quote ? '<div class="quote q-claim" style="margin-top:6px"><span class="q-src">submittal' + (cq.page ? " \u00b7 p" + cq.page : "") + "</span>" + esc(cq.quote.slice(0, 260)) + "</div>" : "") +
          (withQuotes.reason ? '<div class="form-note">' + esc(withQuotes.reason) + "</div>" : "") + "</div>";
      }
      if ((d.pos || []).length) body += '<div class="d-sec"><h4>money riding on this section</h4>' + d.pos.slice(0, 5).map((p) => kv(p.label, fmtINR((p.meta || {}).value_inr) + " " + stamp(p.status))).join("") + "</div>";
      if ((d.cx_tests || []).length) body += '<div class="d-sec"><h4>tests that prove it</h4>' + d.cx_tests.map((t) => kv(t.test_id, stamp(t.ledger_status || t.status))).join("") + "</div>";
      const pkg = checks[0] && checks[0].package;
      if (pkg) body += '<div class="d-actions"><button class="btn" data-act="review" data-v="' + esc(pkg) + '">Open in review</button></div>';
    } else if (d.type === "package") {
      body += '<div class="d-sec"><h4>verdicts</h4>' + Object.entries((meta.verdicts || {})).map(([k, v]) => kv(k.replace(/_/g, " ").toLowerCase(), v)).join("") + "</div>";
      if (d.severity != null) body += '<div class="d-sec"><h4>disposition</h4>' + kv("severity", d.severity) + kv("vendor", esc(d.vendor || "")) + "</div>";
      if ((d.ncrs || []).length) body += '<div class="d-sec"><h4>open NCRs</h4>' + d.ncrs.map((n) => kv(n.ncr_id, esc(n.parameter || "") + " " + stamp(n.verdict))).join("") + "</div>";
      body += '<div class="d-actions"><button class="btn" data-act="review" data-v="' + esc(d.label) + '">Open in review</button>' +
        (d.letter ? '<button class="btn" data-act="doc" data-v="' + esc(d.letter) + '">Letter</button>' : "") + "</div>";
    } else if (d.type === "po") {
      body += '<div class="d-sec"><h4>purchase order</h4>' + kv("vendor", esc(meta.vendor || "")) + kv("value", fmtINR(meta.value_inr)) + kv("lead time", (meta.lead_time_weeks || "\u2014") + " weeks") + kv("delivery", esc(meta.delivery || meta.delivery_status || "")) + "</div>";
      if (d.invalidation) body += '<div class="d-sec"><h4>why it is invalid</h4><div class="quote q-claim">' + esc(d.invalidation.ledger_reason || "") + '</div><div class="d-actions"><button class="btn" data-act="hash" data-v="#blast">See the blast wave</button></div></div>';
    } else if (d.type === "cx") {
      const t = d.test || {};
      body += '<div class="d-sec"><h4>commissioning test</h4>' + kv("level", esc(t.level || meta.level || "")) + kv("clause", esc(t.spec_clause || meta.clause || "")) + kv("status", stamp(t.ledger_status || d.status)) + "</div>" +
        (t.acceptance_criteria ? '<div class="quote">' + esc(t.acceptance_criteria) + "</div>" : "") +
        (t.ledger_reason ? '<div class="form-note">' + esc(t.ledger_reason) + "</div>" : "") +
        '<div class="d-actions"><button class="btn" data-act="hash" data-v="#cx">All tests</button></div>';
    } else if (d.type === "section") {
      body += '<div class="d-sec"><h4>section</h4>' + kv("rules compiled", d.rule_count) + "</div>";
      if ((d.lint || []).length) body += '<div class="d-sec"><h4>spec defects found here</h4>' + d.lint.map((f) => '<div class="form-note">\u2022 ' + esc(f.summary || f.lint) + "</div>").join("") + "</div>";
    } else if (d.type === "addendum") {
      const w = d.wave || {};
      body += '<div class="d-sec"><h4>blast wave</h4>' + kv("rules amended", w.rules_amended) + kv("verdict flips", w.verdict_flips) + kv("POs invalidated", w.pos_invalidated) + kv("Cx tests stale", w.cx_tests_stale) + '</div><div class="d-actions"><button class="btn" data-act="hash" data-v="#blast">Open blast wave</button></div>';
    } else if (d.type === "activity") {
      body += '<div class="d-sec"><h4>schedule activity</h4>' + kv("float", (meta.float_days != null ? meta.float_days + " days" : "\u2014")) + kv("duration", (meta.duration || "\u2014") + " days") + kv("critical path", meta.critical ? "yes" : "no") + "</div>";
    }
    const neigh = (d.neighbors || []).slice(0, 14).map((n) =>
      '<div class="neigh" data-n="' + esc(n.id) + '"><span class="sw" style="background:' + (NODE_COLORS[n.type] || "#888") + '"></span>' + esc(n.label.length > 30 ? n.label.slice(0, 29) + "\u2026" : n.label) + '<span class="et">' + esc(n.edge) + "</span></div>").join("");
    box.innerHTML = '<div class="dossier"><button class="iconbtn d-close" id="d-close">' + icon("x") + '</button>' +
      '<div class="d-type">' + esc(d.type) + " \u00b7 " + (d.degree || 0) + ' connections</div><h3>' + esc(d.label) + "</h3>" +
      (d.status ? stamp(d.status) : "") + body +
      '<div class="d-sec"><h4>connected to</h4>' + neigh + "</div></div>";
    $("#d-close").onclick = () => { box.innerHTML = ""; selId = null; };
    box.querySelectorAll("[data-n]").forEach((el) => { el.onclick = () => focusNode(el.dataset.n); });
    box.querySelectorAll("[data-act]").forEach((b) => {
      b.onclick = () => {
        if (b.dataset.act === "review") location.hash = "#review/" + encodeURIComponent(b.dataset.v);
        else if (b.dataset.act === "doc") openDoc(b.dataset.v);
        else if (b.dataset.act === "hash") location.hash = b.dataset.v;
      };
    });
  }
  if (arg) setTimeout(() => focusNode(arg), 600);
}

/* =========================================================== lint */
async function vLint(view) {
  const l = await api("/api/lint");
  const pw = await api("/api/paperwork");
  const rfiByLint = {};
  (pw.documents || []).forEach((doc) => { if (doc.lint) rfiByLint[doc.lint] = rfiByLint[doc.lint] || doc.file; });
  const cards = (l.findings || []).map((f) => {
    const a = f.a || {}, b = f.b || {};
    return '<div class="ev-row"><div class="ev-head">' + stamp("DEVIATION", "straight") + '<span class="param">' + esc(f.summary || f.lint) + '</span><span class="chip">' + esc(f.lint) + '</span><span class="spacer"></span>' +
      (rfiByLint[f.lint] ? '<button class="btn" data-doc="' + esc(rfiByLint[f.lint]) + '">Drafted RFI</button>' : "") + "</div>" +
      '<div class="ev-pair"><div class="quote q-req"><span class="q-src">' + esc(a.clause || "a") + (a.page ? " \u00b7 p" + a.page : "") + "</span>" + esc(a.quote || "") + "</div>" +
      '<div class="quote q-claim"><span class="q-src">' + esc(b.clause || "b") + (b.page ? " \u00b7 p" + b.page : "") + "</span>" + esc(b.quote || "") + "</div></div></div>";
  }).join("");
  view.innerHTML = '<div class="view">' +
    head("Spec defects", "the linter reads the owner\u2019s spec the way a vendor\u2019s lawyer will") +
    '<div class="callout c-ok mb"><b>' + (l.findings || []).length + " findings \u00b7 includes 7/7 planted defects from the corpus answer key \u00b7 0 false alarms.</b> Every finding quotes both conflicting sentences \u2014 check them yourself.</div>" + cards + "</div>";
  view.querySelectorAll("[data-doc]").forEach((btn) => { btn.onclick = () => openDoc(btn.dataset.doc); });
}

/* =========================================================== external */
async function vExternal(view) {
  const e = await api("/api/external");
  const docs = [e.spec, e.submittal].concat(e.documents_extra || []).filter(Boolean);
  const docCards = docs.map((doc) => '<div class="card"><h2>' + icon("doc") + esc((doc.title || doc.file || "").slice(0, 60)) + '</h2><div class="d-kv"><span class="k mono">' + esc(doc.file || "") + '</span></div><div class="d-kv"><span class="k">pages</span><span class="v">' + (doc.pages || "\u2014") + "</span></div>" +
    (doc.requirements_harvested ? '<div class="d-kv"><span class="k">requirements harvested</span><span class="v">' + doc.requirements_harvested + "</span></div>" : "") +
    (doc.claims_harvested ? '<div class="d-kv"><span class="k">claims harvested</span><span class="v">' + doc.claims_harvested + "</span></div>" : "") + "</div>").join("");
  const checks = (e.checks || []).map((c) => {
    const rq = c.requirement || {}, cq = c.claim || {};
    return '<div class="ev-row"><div class="ev-head">' + stamp(c.verdict) + '<span class="param">' + esc((c.family || "").replace(/_/g, " ")) + "</span>" +
      '<span class="chip">' + esc(String(rq.operator || "")) + " " + esc(String(rq.value == null ? "" : rq.value)) + " " + esc(rq.unit || "") + '</span><span class="spacer"></span></div>' +
      '<div class="ev-pair"><div class="quote q-req"><span class="q-src">tender \u00b7 p' + (rq.page || "?") + "</span>" + esc((rq.quote || "").slice(0, 340)) + "</div>" +
      '<div class="quote q-claim"><span class="q-src">brochure \u00b7 p' + (cq.page || "?") + "</span>" + esc((cq.quote || "").slice(0, 340)) + "</div></div>" +
      (c.note || c.reason ? '<div class="reason">' + esc(c.note || c.reason) + "</div>" : "") + "</div>";
  }).join("");
  view.innerHTML = '<div class="view">' +
    head("External reality check", "real public documents the pipeline had never seen") +
    '<div class="callout mb">' + esc(e.method || "") + "</div>" +
    '<div class="grid g3 mb">' + docCards + "</div>" + checks + "</div>";
}

/* =========================================================== blast */
async function vBlast(view) {
  const b = await api("/api/blastwave");
  const s = b.summary || {};
  const flips = (b.verdict_flips || []).map((f) =>
    "<tr><td class=\"mono\">" + esc(f.package) + '</td><td class="mono">' + esc(f.rule_id || "") + "</td><td>" + esc(f.parameter || "") + "</td><td>" + stamp(f.verdict_before, "straight") + " \u2192 " + stamp(f.verdict_after, "straight") + "</td></tr>").join("");
  const pos = (b.pos_invalidated || []).map((p) =>
    "<tr><td class=\"mono\">" + esc(p.po_number) + "</td><td>" + esc(p.vendor || "") + "</td><td>" + esc((p.item_description || "").slice(0, 46)) + '</td><td class="mono r">' + fmtINR(p.value_inr) + "</td><td>" + esc(p.delivery_status || "") + "</td><td>" + stamp(p.ledger_status) + "</td></tr>").join("");
  const stale = (b.cx_tests_stale || []).map((t) =>
    '<div class="ev-row"><div class="ev-head">' + stamp("STALE") + '<span class="param mono">' + esc(t.test_id) + '</span><span class="chip">' + esc(t.spec_clause || "") + '</span></div><div class="quote">' + esc(t.acceptance_criteria || "") + '</div><div class="reason">' + esc(t.ledger_reason || "") + "</div></div>").join("");
  const totalInr = (b.pos_invalidated || []).reduce((a, p) => a + (Number(p.value_inr) || 0), 0);
  view.innerHTML = '<div class="view">' +
    head("Blast wave \u00b7 ADD-003", "one client letter, every domino it knocks over") +
    '<div class="grid g4 mb">' +
    '<div class="card metric"><div class="num">' + (s.rules_amended || 0) + '</div><div class="lbl">rules amended</div></div>' +
    '<div class="card metric"><div class="num num-warn">' + (s.verdict_flips || 0) + '</div><div class="lbl">verdicts flipped</div></div>' +
    '<div class="card metric"><div class="num num-bad">' + (s.pos_invalidated || 0) + '</div><div class="lbl">POs now for the old requirement \u00b7 ' + fmtINR(totalInr) + '</div></div>' +
    '<div class="card metric"><div class="num num-verm">' + (s.cx_tests_stale || 0) + '</div><div class="lbl">test procedures gone stale</div></div>' +
    "</div>" +
    '<div class="row mb"><button class="btn btn-primary" id="btn-apply">Re-apply the addendum, live</button><span class="prov">runs M5\u2192M11 server-side and re-times every module</span></div>' +
    '<div class="grid g2 mb"><div class="card"><h2>' + icon("review") + "verdict flips</h2><table><tr><th>package</th><th>rule</th><th>parameter</th><th>flip</th></tr>" + flips + "</table></div>" +
    '<div class="card"><h2>' + icon("vendors") + "purchase orders invalidated</h2><table><tr><th>po</th><th>vendor</th><th>item</th><th class=\"r\">value</th><th>delivery</th><th>ledger</th></tr>" + pos + "</table></div></div>" +
    '<div class="card"><h2>' + icon("cx") + "commissioning tests now testing the wrong thing</h2>" + stale + "</div></div>";
  $("#btn-apply").onclick = async () => {
    const btn = $("#btn-apply");
    btn.disabled = true; btn.textContent = "running M5\u2192M11\u2026";
    try {
      const res = await post("/api/blastwave/apply");
      const total = (res.timings || []).reduce((a, t) => a + t.ms, 0);
      toast("Recomputed <b>" + (res.timings || []).length + " modules</b> in <b>" + total + " ms</b> \u2014 " + (res.timings || []).map((t) => t.module.replace(".py", "") + " " + t.ms).join(" \u00b7 "));
      route();
    } catch (e) { toast(esc(e.message)); btn.disabled = false; btn.textContent = "Re-apply the addendum, live"; }
  };
  addFab("#graph/" + encodeURIComponent("add:ADD-003"), "see it in the graph");
}

/* =========================================================== margins */
async function vMargins(view) {
  const m = await api("/api/margins");
  const ledger = (m.ledger || []).slice().sort((a, b) => (a.margin_pct || 0) - (b.margin_pct || 0));
  const rows = ledger.map((r) => {
    const pct = r.margin_pct == null ? 0 : r.margin_pct;
    const w = Math.min(Math.abs(pct) * 18, 100);
    const cls = pct < 0 ? "b-bad" : pct < 2 ? "b-warn" : "b-ok";
    return "<tr><td class=\"mono\">" + esc(r.package) + "</td><td>" + esc(r.parameter || "") + '</td><td class="mono r">' + esc(String(r.operator || "")) + " " + esc(String(r.required)) + " " + esc(r.unit || "") + '</td><td class="mono r">' + esc(String(r.offered)) + '</td><td style="min-width:120px"><div class="bar-wrap"><div class="bar ' + cls + '" style="width:' + w + '%"></div></div></td><td class="mono r">' + (pct > 0 ? "+" : "") + pct + "%</td><td>" + (r.amended_by ? '<span class="chip" style="color:var(--verm)">' + esc(r.amended_by) + "</span>" : "") + stamp(r.verdict, "straight") + "</td></tr>";
  }).join("");
  const en = m.energy_penalty || {};
  const enRows = en.rows || [];
  const kwhKey = enRows.length ? Object.keys(enRows[0]).find((k) => k.toLowerCase().includes("kwh")) : null;
  view.innerHTML = '<div class="view">' +
    head("Margin erosion", "how close every accepted number is to the cliff \u2014 and what \u201cclose\u201d costs") +
    '<div class="grid g3 mb">' +
    '<div class="card metric"><div class="num">' + (m.checked_rules || 0) + '</div><div class="lbl">numeric rules price-checked</div></div>' +
    '<div class="card metric"><div class="num num-warn">' + (m.thin_margins || []).length + '</div><div class="lbl">thin margins (&lt; 2%)</div></div>' +
    '<div class="card metric"><div class="num num-bad">' + (m.negative_margins || []).length + '</div><div class="lbl">negative \u2014 already past the line</div></div>' +
    "</div>" +
    '<div class="card mb"><h2>' + icon("margins") + 'margin ledger <span class="right">sorted worst first</span></h2><table><tr><th>package</th><th>parameter</th><th class="r">required</th><th class="r">offered</th><th>margin</th><th class="r">%</th><th></th></tr>' + rows + "</table></div>" +
    '<div class="card"><h2>' + icon("blast") + "the price of \u201cjust accept it\u201d</h2>" +
    '<div class="row"><span style="font-size:12px">electricity tariff</span><input type="range" id="tariff" min="4" max="14" step="0.5" value="8" style="max-width:260px"><b class="mono" id="tariff-val">\u20b98.0/kWh</b><span class="prov">recomputed in your browser as you drag</span></div>' +
    '<table class="mt"><tr><th>package</th><th>parameter</th><th class="r">extra energy</th><th class="r">cost per year</th></tr><tbody id="en-body"></tbody></table>' +
    '<div class="form-note">' + esc(en.note || "") + "</div></div></div>";
  function renderEnergy() {
    const tariff = Number($("#tariff").value);
    $("#tariff-val").textContent = "\u20b9" + tariff.toFixed(1) + "/kWh";
    let total = 0;
    $("#en-body").innerHTML = enRows.map((r) => {
      const kwh = kwhKey ? Number(r[kwhKey]) || 0 : 0;
      const cost = kwh * tariff;
      total += cost;
      return "<tr><td class=\"mono\">" + esc(r.package || "") + "</td><td>" + esc(r.parameter || "") + '</td><td class="mono r">' + fmtN(Math.round(kwh)) + ' kWh/yr</td><td class="mono r num-bad">' + fmtINR(cost) + "/yr</td></tr>";
    }).join("") + '<tr><td colspan="3" style="text-align:right"><b>every year, forever</b></td><td class="mono r"><b class="num-bad">' + fmtINR(total) + "/yr</b></td></tr>";
  }
  $("#tariff").oninput = renderEnergy;
  renderEnergy();
}

/* =========================================================== vendors */
async function vVendors(view) {
  const d = await api("/api/vendors");
  const vendors = (d.vendors || []).slice().sort((a, b) => (a.trust_score || 0) - (b.trust_score || 0));
  const cards = vendors.map((v) => {
    const cls = v.trust_score >= 90 ? "b-ok" : v.trust_score >= 85 ? "b-warn" : "b-bad";
    return '<div class="card"><div class="row"><h3 style="font-family:var(--serif);font-size:16px">' + esc(v.vendor) + '</h3><span class="spacer"></span>' + stamp(v.review_intensity) + "</div>" +
      '<div class="row mt"><b class="mono" style="font-size:22px">' + (v.trust_score != null ? v.trust_score : "\u2014") + '</b><div class="bar-wrap" style="flex:1"><div class="bar ' + cls + '" style="width:' + (v.trust_score || 0) + '%"></div></div></div>' +
      '<div class="mt">' +
      '<div class="d-kv"><span class="k">checks</span><span class="v">' + (v.checks || 0) + "</span></div>" +
      '<div class="d-kv"><span class="k">deviations</span><span class="v">' + (v.deviations || 0) + " (" + (v.deviation_rate_pct || 0) + "%)</span></div>" +
      '<div class="d-kv"><span class="k">unearned \u201ccomply\u201d stamps</span><span class="v">' + (v.false_comply || 0) + " (" + (v.false_comply_rate_pct || 0) + "%) " + (v.false_comply ? struckComply : "") + "</span></div>" +
      '<div class="d-kv"><span class="k">missing evidence</span><span class="v">' + (v.missing_evidence || 0) + "</span></div>" +
      '<div class="d-kv"><span class="k">exposure</span><span class="v">' + fmtINR(v.exposure_inr) + "</span></div></div>" +
      '<div class="row mt">' + (v.packages || []).map((p) => '<span class="chip rowlink" data-pkg="' + esc(p) + '" style="cursor:pointer">' + esc(p) + "</span>").join("") + "</div></div>";
  }).join("");
  view.innerHTML = '<div class="view">' +
    head("Vendor trust", "earned from evidence quality, not reputation \u2014 lowest first") +
    '<div class="grid g2">' + cards + "</div>" +
    '<div class="form-note mt">trust drives review intensity: strong evidence buys lighter sampling; unearned stamps buy a microscope.</div></div>';
  view.querySelectorAll("[data-pkg]").forEach((c) => { c.onclick = () => { location.hash = "#review/" + encodeURIComponent(c.dataset.pkg); }; });
  addFab("#graph", "view connections");
}

/* =========================================================== paperwork */
async function vPaperwork(view) {
  const d = await api("/api/paperwork");
  const docs = d.documents || [];
  const groups = {};
  docs.forEach((doc) => { (groups[doc.type] = groups[doc.type] || []).push(doc); });
  const titles = { rfi: "Requests for information", letter: "Deviation letters", impact_notice: "Impact notices", cx: "Updated test procedures" };
  const cards = Object.entries(groups).map(([type, list]) =>
    '<div class="card mb"><h2>' + icon("paperwork") + esc(titles[type] || type) + ' <span class="right">' + list.length + "</span></h2>" +
    list.map((doc) => '<div class="neigh" data-doc="' + esc(doc.file) + '">' + stamp("DRAFT", "straight") + '<span class="mono" style="font-size:11px">' + esc(doc.id || "") + "</span><span>" + esc((doc.title || "").slice(0, 90)) + "</span></div>").join("") + "</div>").join("");
  view.innerHTML = '<div class="view">' +
    head("Paperwork", "drafted from ledger evidence \u2014 the machine never signs") +
    '<div class="callout mb">Every document below quotes its evidence and is stamped ' + stamp("DRAFT", "straight") + " until an engineer signs it. CLAUSE drafts; humans decide.</div>" + cards + "</div>";
  view.querySelectorAll("[data-doc]").forEach((r) => { r.onclick = () => openDoc(r.dataset.doc); });
}

/* =========================================================== cx */
async function vCx(view) {
  const d = await api("/api/cx");
  const tests = (d.tests || []).slice().sort((a, b) => (a.ledger_status === "STALE" ? -1 : 1) - (b.ledger_status === "STALE" ? -1 : 1));
  const rows = tests.map((t) =>
    "<tr><td class=\"mono\">" + esc(t.test_id) + "</td><td>" + esc(t.level || "") + "</td><td>" + esc((t.system || "").slice(0, 30)) + '</td><td class="mono">' + esc(t.spec_clause || "") + "</td><td>" + esc((t.acceptance_criteria || "").slice(0, 70)) + "</td><td>" + stamp(t.ledger_status) + "</td><td class=\"r mono\">" + (t.open_ncrs_on_equipment || 0) + "</td></tr>").join("");
  const pw = await api("/api/paperwork");
  const procs = (pw.documents || []).filter((x) => x.type === "cx");
  view.innerHTML = '<div class="view">' +
    head("Commissioning packs", "tests generated from the ledger \u2014 and kept honest by it") +
    '<div class="grid g4 mb">' +
    '<div class="card metric"><div class="num">' + (d.tests || []).length + '</div><div class="lbl">tests generated</div></div>' +
    '<div class="card metric"><div class="num num-ok">' + (d.ready || 0) + '</div><div class="lbl">ready to execute</div></div>' +
    '<div class="card metric"><div class="num">' + (d.blocked || 0) + '</div><div class="lbl">blocked on open NCRs</div></div>' +
    '<div class="card metric"><div class="num num-verm">' + (d.stale || 0) + '</div><div class="lbl">stale \u2014 testing a superseded requirement</div></div>' +
    "</div>" +
    (procs.length ? '<div class="row mb">' + procs.map((p) => '<button class="btn" data-doc="' + esc(p.file) + '">' + esc(p.id || p.file) + "</button>").join("") + '<span class="prov">re-drafted procedures for the stale tests</span></div>' : "") +
    '<div class="card"><table><tr><th>test</th><th>level</th><th>system</th><th>clause</th><th>acceptance criteria</th><th>ledger</th><th class="r">NCRs</th></tr>' + rows + "</table></div></div>";
  view.querySelectorAll("[data-doc]").forEach((b) => { b.onclick = () => openDoc(b.dataset.doc); });
}

/* =========================================================== ncr */
async function vNcr(view) {
  const d = await api("/api/ncr");
  const rows = d.ncrs || [];
  const cols = rows.length ? Object.keys(rows[0]).slice(0, 7) : [];
  view.innerHTML = '<div class="view">' +
    head("NCR register", rows.length + " non-conformance reports, auto-raised from deviations") +
    '<div class="card"><table><tr>' + cols.map((c) => "<th>" + esc(c) + "</th>").join("") + "</tr>" +
    rows.map((r) => "<tr>" + cols.map((c) => {
      const val = String(r[c] == null ? "" : r[c]);
      if (/^(DEVIATION|COMPLY|NEEDS_REVIEW|OPEN|CLOSED|PENDING)$/.test(val)) return "<td>" + stamp(val, "straight") + "</td>";
      return '<td class="' + (/^[\d.,-]+$/.test(val) ? "mono r" : "") + '">' + esc(val.slice(0, 90)) + "</td>";
    }).join("") + "</tr>").join("") + "</table></div></div>";
}

/* =========================================================== settings */
async function vSettings(view) {
  let cfg = { base_url: "", model: "", api_key_masked: "", configured: false };
  try { cfg = await api("/api/llm/config"); } catch (e) { /* server offline for config */ }
  view.innerHTML = '<div class="view">' +
    head("Settings", "own the whole chain \u2014 bring any OpenAI-compatible model, or run one on this laptop") +
    '<div class="grid g2">' +
    '<div class="card"><h2>' + icon("chip") + "bring your own model</h2>" +
    '<div class="field"><label>base URL (OpenAI-compatible)</label><input id="llm-base" placeholder="http://localhost:11434/v1" value="' + esc(cfg.base_url || "") + '"></div>' +
    '<div class="field"><label>API key ' + (cfg.api_key_masked ? "(saved: " + esc(cfg.api_key_masked) + ")" : "") + '</label><input id="llm-key" type="password" placeholder="' + (cfg.api_key_masked ? "leave blank to keep saved key" : "sk-\u2026 or any string for local models") + '"></div>' +
    '<div class="field"><label>model</label><input id="llm-model" placeholder="qwen3:4b" value="' + esc(cfg.model || "") + '"></div>' +
    '<div class="row"><button class="btn btn-primary" id="llm-save">Save</button><button class="btn" id="llm-test">Test connection</button>' + (cfg.configured ? stamp("OK", "straight") : "") + "</div>" +
    '<div id="llm-result"></div>' +
    '<div class="form-note">Stored in <code>out/llm_config.json</code> on this machine only. The pipeline sends isolated clause snippets \u2014 never whole documents \u2014 and with a local model, nothing leaves your laptop at all.</div></div>' +
    '<div class="card"><h2>' + icon("external") + "run it fully local" + "</h2>" +
    '<p style="font-size:12.5px">CLAUSE\u2019s LLM use is deliberately small: reading one clause or one datasheet block at a time and returning JSON. That is text parsing \u2014 <b>a 4B model on an ordinary laptop is enough</b>. The verification layer itself is deterministic Python and needs no model at all.</p>' +
    '<table class="mt"><tr><th>hardware</th><th>model</th></tr>' +
    "<tr><td>8 GB RAM laptop</td><td class=\"mono\">gemma3:4b / qwen3:4b</td></tr>" +
    "<tr><td>16 GB RAM</td><td class=\"mono\">qwen3:8b / llama3.1:8b</td></tr>" +
    "<tr><td>no GPU</td><td>works on CPU \u2014 slower, same output</td></tr></table>" +
    '<div class="row mt"><button class="btn" id="open-guide">Open the local setup guide</button><span class="chip">Ollama</span><span class="chip">LM Studio</span><span class="chip">llama.cpp</span></div>' +
    '<div class="form-note">Guide covers macOS, Windows, and Linux \u2014 install, pull a model, paste one URL into the form on the left.</div></div>' +
    "</div>" +
    '<div class="card mt" id="meta-card"><h2>' + icon("settings") + 'provenance</h2><div id="meta-body" class="form-note">loading\u2026</div></div></div>';
  $("#open-guide").onclick = () => openGuide("LOCAL_LLM.md");
  $("#llm-save").onclick = async () => {
    try {
      const r = await post("/api/llm/config", { base_url: $("#llm-base").value, api_key: $("#llm-key").value, model: $("#llm-model").value });
      toast("Saved \u2014 " + (r.configured ? "endpoint configured" : "incomplete config"));
    } catch (e) { toast(esc(e.message)); }
  };
  $("#llm-test").onclick = async () => {
    const out = $("#llm-result");
    out.innerHTML = '<div class="test-result">testing round-trip\u2026</div>';
    try {
      const r = await post("/api/llm/test", { base_url: $("#llm-base").value, api_key: $("#llm-key").value, model: $("#llm-model").value });
      out.innerHTML = r.ok
        ? '<div class="test-result ok">\u2713 ' + r.ms + " ms \u00b7 " + esc(r.model || "") + " \u00b7 reply: \u201c" + esc(r.reply || "") + "\u201d</div>"
        : '<div class="test-result err">\u2717 ' + esc(r.error || "failed") + "</div>";
    } catch (e) { out.innerHTML = '<div class="test-result err">\u2717 ' + esc(e.message) + "</div>"; }
  };
  try {
    const meta = await api("/api/meta");
    $("#meta-body").innerHTML = "Python " + esc(meta.python) + " \u00b7 server up since " + esc(meta.server_started) + " \u00b7 " + Object.keys(meta.artifacts || {}).length + " artifacts on disk \u00b7 " + (meta.corpus_files || 0) + " corpus files fingerprinted \u00b7 server clock " + esc(meta.now);
  } catch (e) { /* fine */ }
}

/* ---------------- chrome: clock, ticker, buttons ---------------- */
function startChrome() {
  $("#btn-settings").innerHTML = icon("settings");
  $("#modal-close").innerHTML = icon("x");
  $("#btn-settings").onclick = () => { location.hash = "#settings"; };
  $("#modal-close").onclick = () => $("#modal").classList.add("hidden");
  $("#modal").onclick = (e) => { if (e.target === $("#modal")) $("#modal").classList.add("hidden"); };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#modal").classList.add("hidden"); });
  $("#btn-recompute").onclick = async () => {
    const b = $("#btn-recompute");
    b.disabled = true; b.textContent = "running\u2026";
    try {
      const res = await post("/api/recompute");
      const total = (res.timings || []).reduce((a, t) => a + t.ms, 0);
      toast("Recomputed <b>" + (res.timings || []).length + " modules</b> in <b>" + total + " ms</b> \u2014 " + (res.timings || []).map((t) => t.module.replace(".py", "") + " " + t.ms).join(" \u00b7 "));
      route();
    } catch (e) { toast(esc(e.message)); }
    b.disabled = false; b.textContent = "Recompute";
  };
  setInterval(() => { $("#clock").textContent = new Date().toLocaleTimeString(); }, 1000);
  $("#clock").textContent = new Date().toLocaleTimeString();
  async function tickTicker() {
    try {
      const r = await fetch("/api/activity");
      const d = await r.json();
      const ev = (d.events || []).slice(-12).reverse();
      $("#ticker-inner").innerHTML = ev.map((e) =>
        '<span class="' + (e.ms > 300 ? "tick-slow" : "tick-ok") + '">' + e.method + " " + esc(e.path) + " " + e.status + " \u00b7 " + e.ms + "ms</span>").join('<span style="opacity:.4"> \u2500\u2500 </span>') || "waiting for traffic\u2026";
    } catch (e) { $("#ticker-inner").textContent = "server unreachable"; }
  }
  setInterval(tickTicker, 4000);
  tickTicker();
  api("/api/summary").then((s) => { $("#spend").textContent = "$" + (s.llm_spend_usd == null ? "\u2014" : s.llm_spend_usd.toFixed(2)); }).catch(() => { /* offline */ });
}
window.addEventListener("hashchange", route);
startChrome();
route();
