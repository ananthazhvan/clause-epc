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
function prov() { return ""; }

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
  { id: "objects", label: "Objects", icon: "overview", fn: vObjects, group: 1 },
  { id: "graph", label: "Graph", icon: "graph", fn: vGraph, group: 1 },
  { id: "globe", label: "Globe", icon: "facility", fn: vGlobe, group: 1 },
  { id: "review", label: "Ledger", icon: "review", fn: vReview, group: 2 },
  { id: "queue", label: "Queue", icon: "queue", fn: vQueue, group: 2 },
  { id: "cx", label: "Cx", icon: "cx", fn: vCx, group: 3 },
  { id: "ncr", label: "NCR", icon: "ncr", fn: vNcr, group: 3 },
  { id: "paperwork", label: "Paperwork", icon: "paperwork", fn: vPaperwork, group: 3 },
];
function renderTabs(activeId) {
  const nav = $("#tabs");
  let html = "", lastGroup = 0;
  for (const r of ROUTES) {
    if (r.group !== lastGroup) { html += '<span class="tab-sep"></span>'; lastGroup = r.group; }
    html += '<div class="tab' + (r.id === activeId ? " active" : "") + '" data-r="' + r.id + '">' + icon(r.icon) + '<span class="tab-label">' + r.label + "</span></div>";
  }
  html += '<span class="tab-sep"></span><div class="tab tab-copilot" id="tab-copilot" title="CLAUSE copilot - ask the ledger">' + icon("copilot") + '<span class="tab-label">Copilot</span></div>';
  nav.innerHTML = html;
  nav.querySelectorAll(".tab").forEach((t) => { t.onclick = () => { location.hash = "#" + t.dataset.r; }; });
  const ct = $("#tab-copilot");
  if (ct) ct.onclick = () => { if (window.openCopilot) window.openCopilot(); };
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
  const EXTRA = { settings: { id: "settings", fn: vSettings }, run: { id: "run", icon: "queue", fn: vRun }, object: { id: "objects", fn: vObject360 } };
  const r = ROUTES.find((x) => x.id === id) || EXTRA[id] || ROUTES[0];
  renderTabs(r.id);
  const view = $("#view");
  view.innerHTML = skeleton();
  if (r.id !== "hub" && r.id !== "settings" && r.id !== "run") {
    let p = null;
    try { p = await projectState(); } catch (e) { p = PROJECT; }
    if (p && p.running) { location.hash = "#run"; return; }
    if (p && !p.loaded) {
      view.innerHTML = '<div class="view"><div class="empty-wrap"><div class="empty-card card">' + icon(r.icon || "hub") +
        "<h1>nothing here yet</h1><p>No project is loaded. Nothing on this site is pre-loaded or replayed \u2014 every screen is computed from the documents you upload, by the real pipeline, on this machine.</p>" +
        '<button class="btn btn-primary" onclick="location.hash=\'#hub\'">Upload your project documents</button></div></div></div>';
      return;
    }
  }
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
let PROJECT = null;
async function projectState() {
  PROJECT = await api("/api/project");
  const chip = $("#model-chip");
  if (chip) chip.textContent = (PROJECT.model || "no model") + (PROJECT.has_key ? "" : " \u00b7 no key");
  const fab = $("#cp-fab");
  if (fab) fab.classList.toggle("hidden", !PROJECT.loaded);
  return PROJECT;
}
const SOURCES = [
  { key: "documents", label: "Project documents", route: "#review", count: (s) => (s.corpus_files || 0) + " files" },
  { key: "specs", label: "Specifications", route: "#lint", count: (s) => (s.rules || 0) + " rules" },
  { key: "schedule", label: "Schedule", route: "#clock", count: (s) => ((s.node_types || {}).activity || 0) + " activities" },
  { key: "procurement", label: "Procurement", route: "#vendors", count: (s) => ((s.node_types || {}).po || 0) + " POs" },
  { key: "quality", label: "Quality records", route: "#cx", count: (s) => (((s.node_types || {}).cx || 0)) + " tests \u00b7 " + (s.ncrs || 0) + " NCRs" },
  { key: "facility", label: "Facility profile", route: "#facility", count: (s) => (s.facility_rating ? s.facility_rating + " declared" : "Tier / TIA-942 scan") },
];
function kstamp(kind) {
  const m = { specification: "st-ok", submittal: "st-ok", addendum: "st-warn", register: "st-ok", reference: "", "project document": "", refused: "st-bad", error: "st-bad", skipped: "" };
  return '<span class="stamp ' + (m[kind] || "") + '">' + esc(kind) + "</span>";
}
function checksTotalOf(s) { return Object.values(s.verdicts_post || {}).reduce((a, b) => a + b, 0); }

async function vHub(view) {
  const p = await projectState();
  if (p.running) { location.hash = "#run"; return; }
  if (p.loaded) return hubLoaded(view, p);
  return hubEmpty(view, p);
}

function uploadCardHtml(big) {
  return '<div class="card">' +
    "<h2>" + icon("doc") + (big ? "upload your project documents" : "feed it more documents") + "</h2>" +
    '<div class="dropzone' + (big ? " dz-big" : "") + '" id="dz">' + icon("doc") +
    "<div><b>Drop files or a whole folder here</b>" +
    '<div class="form-note">specs \u00b7 vendor submittals \u00b7 client addenda \u00b7 registers (CSV) \u00b7 Primavera P6 schedules (XML) \u00b7 SAP purchase orders (OData JSON) \u00b7 shipment feeds (JSON) \u00b7 minutes, reports, correspondence</div></div>' +
    '<div class="row mt" style="justify-content:center"><button class="btn" id="pick-files">Choose files</button><button class="btn" id="pick-folder">Choose a folder</button></div></div>' +
    '<input id="dz-files" type="file" multiple style="display:none">' +
    '<input id="dz-folder" type="file" webkitdirectory style="display:none">' +
    '<div id="up-out"></div></div>';
}

function renderStaged(p) {
  const el = $("#staged-body");
  if (!el) return;
  el.innerHTML = !p.staged_total
    ? '<div class="form-note">no documents yet</div>'
    : Object.entries(p.staged || {}).map(([k, v]) => '<div class="d-kv"><span class="k mono">' + esc(k) + '/</span><span class="v">' + v + " file(s)</span></div>").join("");
  const run = $("#btn-run"), clr = $("#btn-clear");
  if (run) run.disabled = !p.staged_total;
  if (clr) clr.disabled = !p.staged_total;
}

function wireUploader(afterUpload) {
  const dz = $("#dz"), fi = $("#dz-files"), fo = $("#dz-folder"), out = $("#up-out");
  if (!dz) return;
  dz.onclick = () => fi.click();
  $("#pick-files").onclick = (e) => { e.stopPropagation(); fi.click(); };
  $("#pick-folder").onclick = (e) => { e.stopPropagation(); fo.click(); };
  ["dragover", "dragenter"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
  dz.addEventListener("drop", (e) => handleFiles(e.dataTransfer.files));
  fi.onchange = () => handleFiles(fi.files);
  fo.onchange = () => handleFiles(fo.files);
  async function handleFiles(fileList) {
    const files = Array.from(fileList || []).slice(0, 400);
    if (!files.length) return;
    out.innerHTML = '<div class="mt mono" style="font-size:11px;color:var(--ink3)">reading ' + files.length + " file(s)\u2026</div>";
    const payload = [];
    for (const f of files) {
      if (f.size > 40e6) { payload.push({ name: f.name, relpath: f.webkitRelativePath || f.name, b64: "" }); continue; }
      const b64 = await new Promise((res, rej) => {
        const rd = new FileReader();
        rd.onload = () => res(String(rd.result).split(",")[1] || "");
        rd.onerror = rej;
        rd.readAsDataURL(f);
      });
      payload.push({ name: f.name, relpath: f.webkitRelativePath || f.name, b64 });
    }
    let res;
    try { res = await post("/api/upload", { files: payload }); }
    catch (e) { out.innerHTML = '<div class="callout mt">' + esc(e.message) + "</div>"; return; }
    const ord = { error: 0, refused: 1 };
    const rows = (res.results || []).slice().sort((a, b) => ((ord[a.kind] !== undefined ? ord[a.kind] : 2) - (ord[b.kind] !== undefined ? ord[b.kind] : 2))).map((r) =>
      '<div class="up-row">' + kstamp(r.kind) + '<span class="fn">' + esc(r.name) + '</span><span class="note">' + esc(r.note || "") + "</span></div>").join("");
    const bad = (res.results || []).filter((r) => r.kind === "error").length;
    out.innerHTML = '<div class="mt">' + rows + "</div>" +
      '<div class="row mt"><span class="prov">' + (res.staged_total || 0) + " file(s) received" + (bad ? " \u00b7 <b>" + bad + " rejected</b>" : "") + "</span></div>";
    PROJECT = null;
    const np = await projectState();
    renderStaged(np);
    if (afterUpload) afterUpload(res, np);
  }
}

function hubEmpty(view, p) {
  view.innerHTML = '<div class="view">' +
    head("Load the project", "upload the project documents \u2014 every screen is computed from them by the pipeline") +
    '<div class="hub">' +
    uploadCardHtml(true) +
    "<div>" +
    '<div class="card mb"><h2>' + icon("queue") + 'documents ready</h2><div id="staged-body"></div>' +
    '<div class="row mt"><button class="btn btn-primary" id="btn-run">Run the pipeline</button><button class="btn" id="btn-clear">Clear</button></div>' +
    '<div class="form-note">the run streams live: parsing, rule compilation, claim extraction, verification, consequences. LLM stages use the model in Settings \u2014 prompts already in the local cache replay instantly and free; new prompts hit the endpoint and take real time.</div></div>' +
    '<div class="card"><h2>' + icon("paperwork") + "what it eats</h2>" +
    '<div class="d-kv"><span class="k">specifications</span><span class="v">PDF/HTML \u00b7 clause-numbered</span></div>' +
    '<div class="d-kv"><span class="k">vendor submittals</span><span class="v">PDF with a transmittal page</span></div>' +
    '<div class="d-kv"><span class="k">client addenda</span><span class="v">PDF \u2014 detected by content</span></div>' +
    '<div class="d-kv"><span class="k">registers</span><span class="v">CSV \u00b7 PO / schedule / Cx / RFI</span></div>' +
    '<div class="d-kv"><span class="k">anything else</span><span class="v">parsed as project documents</span></div>' +
    '<div class="row mt"><button class="btn" id="open-format">Document format guide</button></div>' +
    '<div class="form-note">answer keys and generator/ground-truth files are refused on upload \u2014 the pipeline must never see them.</div></div>' +
    "</div></div></div>";
  renderStaged(p);
  $("#btn-run").onclick = async () => { try { await post("/api/run"); PROJECT = null; location.hash = "#run"; } catch (e) { toast(esc(e.message)); } };
  $("#btn-clear").onclick = async () => { try { await post("/api/project/reset"); PROJECT = null; toast("Project cleared"); route(); } catch (e) { toast(esc(e.message)); } };
  $("#open-format").onclick = () => openGuide("CORPUS_FORMAT.md");
  wireUploader();
}

async function hubLoaded(view, p) {
  const s = await api("/api/summary");
  view.innerHTML = '<div class="view">' +
    head("The intelligence layer", "data-centre EPC delivery, one connected ledger \u2014 computed by the last run") +
    '<div class="hub">' +
    '<div class="card hub-canvas-card" style="min-height:460px"><canvas id="hub-canvas"></canvas>' +
    '<div class="hub-cap">one-line diagram \u00b7 click a source to open its ledger view \u00b7 ' + s.graph_nodes + " nodes / " + s.graph_edges + " edges in the full graph</div></div>" +
    "<div>" +
    '<div class="card mb"><h2>' + icon("hub") + "sources</h2>" +
    SOURCES.map((src) => '<div class="d-kv" style="cursor:pointer" data-r="' + src.route + '"><span class="k">' + esc(src.label) + '</span><span class="v mono">' + esc(src.count(s)) + "</span></div>").join("") +
    '<div class="d-kv"><span class="k">checks in the ledger</span><span class="v mono">' + fmtN(checksTotalOf(s)) + "</span></div></div>" +
    uploadCardHtml(false) +
    '<div class="card mt"><h2>' + icon("settings") + "project</h2>" +
    '<div class="d-kv"><span class="k">loaded</span><span class="v mono">' + esc(p.loaded_at || "") + "</span></div>" +
    '<div class="d-kv"><span class="k">model</span><span class="v mono">' + esc(p.model || "") + "</span></div>" +
    ((p.failed_stages || []).length ? '<div class="d-kv"><span class="k">skipped stages</span><span class="v mono">' + esc(p.failed_stages.join(", ")) + "</span></div>" : "") +
    '<div class="row mt"><button class="btn" id="btn-rerun">Re-run pipeline</button><button class="btn" id="btn-reset">Reset project</button></div>' +
    '<div class="form-note">new documents join the staged set \u2014 re-run to fold them into the ledger. A different model in Settings means cache misses: the run makes real LLM calls and takes real time.</div></div>' +
    "</div></div></div>";
  view.querySelectorAll("[data-r]").forEach((el) => { el.onclick = () => { location.hash = el.dataset.r; }; });
  $("#btn-rerun").onclick = async () => { try { await post("/api/run"); PROJECT = null; location.hash = "#run"; } catch (e) { toast(esc(e.message)); } };
  $("#btn-reset").onclick = async () => { try { await post("/api/project/reset"); PROJECT = null; toast("Project cleared"); route(); } catch (e) { toast(esc(e.message)); } };
  wireUploader();
  CLEANUP = initDiagram(s);
}

/* one-line diagram: sources on a bus, converging into the seal */
function initDiagram(s) {
  const canvas = $("#hub-canvas");
  if (!canvas) return null;
  const wrap = canvas.parentElement;
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let W = 0, H = 0, raf = 0, t = 0, hover = -1;
  const items = SOURCES.map((src) => ({ label: src.label, route: src.route, count: src.count(s), x: 0, y: 0, r: 27 }));
  function size(force) {
    const rect = wrap.getBoundingClientRect();
    const w = Math.max(320, Math.round(rect.width)), h = Math.max(380, Math.round(rect.height));
    if (!force && Math.abs(w - W) < 9 && Math.abs(h - H) < 9) return;
    W = w; H = h;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    const m = 78;
    items.forEach((it, i) => {
      it.x = m + (W - 2 * m) * (items.length === 1 ? 0.5 : i / (items.length - 1));
      it.y = 136;
    });
  }
  function draw() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const ink = "#211c14", ink3 = "#94886e", verm = "#c9442a";
    const busY = 46, collY = H - 122, sealW = 172, sealH = 58, sx = W / 2, sy = H - 78;
    ctx.lineWidth = 1.5; ctx.strokeStyle = ink; ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(items[0].x - 24, busY); ctx.lineTo(items[items.length - 1].x + 24, busY); ctx.stroke();
    [items[0].x - 24, items[items.length - 1].x + 24].forEach((x) => { ctx.beginPath(); ctx.moveTo(x, busY - 5); ctx.lineTo(x, busY + 5); ctx.stroke(); });
    ctx.font = "10px ui-monospace, Menlo, monospace";
    ctx.fillStyle = ink3; ctx.textAlign = "left";
    ctx.fillText("PROJECT DOCUMENTS IN", items[0].x - 24, busY - 12);
    items.forEach((it, i) => {
      ctx.strokeStyle = ink; ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(it.x, busY); ctx.lineTo(it.x, it.y - it.r); ctx.stroke();
      ctx.beginPath(); ctx.arc(it.x, it.y, it.r, 0, Math.PI * 2);
      ctx.fillStyle = hover === i ? "#e3d9c4" : "#faf7ef";
      ctx.fill(); ctx.stroke();
      if (hover === i) { ctx.beginPath(); ctx.arc(it.x, it.y, it.r + 3.5, 0, Math.PI * 2); ctx.stroke(); }
      const cparts = String(it.count).split(" ");
      ctx.fillStyle = ink; ctx.textAlign = "center";
      ctx.font = "600 12px ui-monospace, Menlo, monospace";
      ctx.fillText(cparts[0], it.x, it.y - 1);
      ctx.font = "8.5px ui-monospace, Menlo, monospace";
      ctx.fillStyle = ink3;
      ctx.fillText(cparts.slice(1).join(" ").slice(0, 15), it.x, it.y + 11);
      ctx.font = "11px Georgia, serif";
      ctx.fillStyle = ink;
      ctx.fillText(it.label.toLowerCase(), it.x, it.y + it.r + 16);
      ctx.strokeStyle = ink3;
      ctx.setLineDash([1.5, 6]); ctx.lineDashOffset = -t;
      ctx.beginPath();
      ctx.moveTo(it.x, it.y + it.r);
      ctx.lineTo(it.x, collY);
      ctx.lineTo(sx, collY);
      ctx.stroke();
      ctx.setLineDash([]);
    });
    ctx.strokeStyle = ink3; ctx.setLineDash([1.5, 6]); ctx.lineDashOffset = -t;
    ctx.beginPath(); ctx.moveTo(sx, collY); ctx.lineTo(sx, sy - sealH / 2); ctx.stroke();
    ctx.setLineDash([]);
    ctx.strokeStyle = ink; ctx.fillStyle = "#faf7ef";
    ctx.fillRect(sx - sealW / 2, sy - sealH / 2, sealW, sealH);
    ctx.strokeRect(sx - sealW / 2, sy - sealH / 2, sealW, sealH);
    ctx.strokeRect(sx - sealW / 2 + 4, sy - sealH / 2 + 4, sealW - 8, sealH - 8);
    ctx.textAlign = "center"; ctx.fillStyle = ink;
    ctx.font = "700 15px Georgia, serif";
    ctx.fillText("CLAUSE", sx, sy - 1);
    ctx.font = "8.5px ui-monospace, Menlo, monospace";
    ctx.fillStyle = ink3;
    ctx.fillText("REQUIREMENT LEDGER", sx, sy + 12);
    const dev = (s.verdicts_post || {}).DEVIATION || 0;
    ctx.fillStyle = dev ? verm : ink3;
    ctx.font = "9.5px ui-monospace, Menlo, monospace";
    ctx.fillText(fmtN(checksTotalOf(s)) + " checks \u00b7 " + dev + " deviations", sx, sy + sealH / 2 + 16);
  }
  function loop() { t += 0.3; draw(); raf = requestAnimationFrame(loop); }
  size(true); loop();
  const onResize = () => size(false);
  window.addEventListener("resize", onResize);
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    hover = items.findIndex((it) => (mx - it.x) * (mx - it.x) + (my - it.y) * (my - it.y) <= (it.r + 6) * (it.r + 6));
    canvas.style.cursor = hover >= 0 ? "pointer" : "default";
  };
  canvas.onclick = () => { if (hover >= 0) location.hash = items[hover].route; };
  return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); };
}

/* =========================================================== run console */
async function vRun(view) {
  view.innerHTML = '<div class="view" style="max-width:none">' +
    head("Pipeline run", "live stdout from the real modules \u2014 nothing replayed, nothing simulated") +
    '<div class="run-grid">' +
    '<div class="card"><h2>' + icon("queue") + 'stages</h2><div id="rail-body"><div class="form-note">waiting for the runner\u2026</div></div><div id="run-note"></div></div>' +
    '<div class="card runlog-card"><div class="runlog-head mono"><span id="log-state">connecting\u2026</span><span class="spacer"></span><span id="log-count"></span></div><pre id="runlog" class="mono"></pre></div>' +
    '</div><div id="run-done"></div></div>';
  let off = 0, stop = false, timer = 0;
  CLEANUP = () => { stop = true; clearTimeout(timer); };
  const pre = $("#runlog");
  function rail(st) {
    if (!st || !st.stages) return;
    $("#rail-body").innerHTML = st.stages.map((g) =>
      '<div class="rail-item ' + esc(g.status) + '"><span class="rail-dot"></span><span>' + esc(g.label) + "</span>" +
      (g.llm ? '<span class="llm-chip">LLM</span>' : "") +
      '<span class="rs">' + (g.status === "skipped" ? esc((g.note || "").slice(0, 24)) : (g.secs != null ? g.secs + "s" : "")) + "</span></div>").join("");
    const running = st.stages.find((g) => g.status === "running");
    $("#run-note").innerHTML = (running && running.llm)
      ? '<div class="callout mt"><b>LLM processing</b> \u2014 model <span class="mono">' + esc((PROJECT || {}).model || "") + '</span>. Prompts already in the local cache replay instantly; anything new goes to the endpoint and takes real time.</div>'
      : "";
  }
  async function poll() {
    let d;
    try { d = await api("/api/run/log?offset=" + off); }
    catch (e) { if (!stop) timer = setTimeout(poll, 1500); return; }
    if (d.text) {
      const nearBottom = pre.scrollHeight - pre.scrollTop - pre.clientHeight < 80;
      pre.textContent += d.text;
      if (nearBottom) pre.scrollTop = pre.scrollHeight;
    }
    off = d.offset || off;
    $("#log-count").textContent = off ? Math.round(off / 1024) + " KB" : "";
    rail(d.status);
    const st = d.status;
    if (!d.running && st && st.finished) {
      $("#log-state").textContent = st.ok ? "finished" : "failed";
      PROJECT = null;
      $("#run-done").innerHTML = st.ok
        ? '<div class="callout c-ok mt"><b>Run complete \u2014 the ledger is rebuilt from your documents.</b></div><div class="row mt"><button class="btn btn-primary" onclick="location.hash=\'#overview\'">Open the ledger</button><button class="btn" onclick="location.hash=\'#graph\'">See the connections</button><button class="btn" onclick="location.hash=\'#hub\'">Hub</button></div>'
        : '<div class="callout mt" style="border-color:var(--verm)"><b>Run failed:</b> ' + esc(st.error || "see the log above") + ' \u2014 fix the input (or the model settings) and run again.</div><div class="row mt"><button class="btn" onclick="location.hash=\'#hub\'">Back to the hub</button></div>';
      return;
    }
    if (!d.running && !st) {
      $("#log-state").textContent = "no run";
      $("#run-done").innerHTML = '<div class="callout mt">No run in progress. Stage documents in the hub, then run the pipeline.</div><div class="row mt"><button class="btn" onclick="location.hash=\'#hub\'">Hub</button></div>';
      return;
    }
    $("#log-state").textContent = d.running ? "running" : "\u2026";
    if (!stop) timer = setTimeout(poll, 600);
  }
  poll();
}

/* =========================================================== overview */
async function vOverview(view) {
  const s = await api("/api/summary");
  const post_ = s.verdicts_post || {}, pre = s.verdicts_pre || {};
  const checks = Object.values(post_).reduce((a, b) => a + b, 0);
  const order = ["DEVIATION", "NEEDS_REVIEW", "COMPLY", "MISSING_EVIDENCE", "NOT_ADDRESSED"];
  const colors = { DEVIATION: "b-bad", NEEDS_REVIEW: "b-warn", COMPLY: "b-ok", MISSING_EVIDENCE: "", NOT_ADDRESSED: "" };
  const maxV = Math.max(...order.map((k) => post_[k] || 0), 1);
  const nAdd = s.addenda || 0;
  const vTitle = nAdd ? "verdicts \u00b7 after " + nAdd + " addend" + (nAdd === 1 ? "um" : "a") + ' <span class="right">baseline in grey</span>' : "verdicts";
  view.innerHTML = '<div class="view">' +
    head("Ledger overview", "computed from your documents by the last run") +
    '<div class="grid g4 mb">' +
    '<div class="card metric"><div class="num">' + fmtN(s.rules) + '</div><div class="lbl">rules compiled from specs</div></div>' +
    '<div class="card metric"><div class="num">' + fmtN(s.claims) + '</div><div class="lbl">claims extracted from submittals</div></div>' +
    '<div class="card metric"><div class="num">' + fmtN(checks) + '</div><div class="lbl">checks held in the ledger</div></div>' +
    '<div class="card metric"><div class="num num-bad">' + fmtN(post_.DEVIATION || 0) + '</div><div class="lbl">deviations, each with two quotes</div></div>' +
    "</div>" +
    (s.false_comply_post ? '<div class="callout mb">' + struckComply + " &nbsp;<b>" + s.false_comply_post + " claims were stamped \u201cComply\u201d by the vendor and are contradicted by the vendor\u2019s own datasheet.</b> The stamp was not earned \u2014 CLAUSE re-earns every stamp from evidence.</div>" : "") +
    '<div class="grid g2 mb">' +
    '<div class="card"><h2>' + icon("overview") + vTitle + '</h2><div class="vbars">' +
    order.map((k) => {
      const h = Math.round(((post_[k] || 0) / maxV) * 70) + 4;
      const hp = Math.round(((pre[k] || 0) / maxV) * 70) + 4;
      return '<div class="vbar" title="baseline: ' + (pre[k] || 0) + '"><span class="mono" style="font-size:11px">' + (post_[k] || 0) + '</span><div style="display:flex;gap:3px;width:100%;align-items:flex-end"><div class="col bar ' + (colors[k] || "") + '" style="height:' + h + 'px;flex:2"></div><div class="col" style="height:' + hp + 'px;flex:1;background:var(--raised)"></div></div><span class="vl">' + k.replace(/_/g, " ").toLowerCase() + "</span></div>";
    }).join("") +
    "</div></div>" +
    '<div class="card"><h2>' + icon("hub") + "built from</h2>" +
    Object.entries(s.staged || {}).map(([k, v]) => '<div class="d-kv"><span class="k mono">' + esc(k) + '/</span><span class="v">' + v + " file(s)</span></div>").join("") +
    '<div class="d-kv"><span class="k">model</span><span class="v mono">' + esc(s.model || "") + "</span></div>" +
    '<div class="form-note">every number on this page traces to these uploaded files \u2014 nothing else was read</div></div>' +
    "</div>" +
    '<div class="grid g3">' +
    (nAdd
      ? '<div class="card hoverable" onclick="location.hash=\'#blast\'"><h2>' + icon("blast") + "blast wave \u00b7 " + nAdd + " addend" + (nAdd === 1 ? "um" : "a") + "</h2>" +
        (s.blast ? '<div class="d-kv"><span class="k">rules amended</span><span class="v">' + s.blast.rules_amended + '</span></div><div class="d-kv"><span class="k">verdicts flipped</span><span class="v">' + s.blast.verdict_flips + '</span></div><div class="d-kv"><span class="k">POs invalidated</span><span class="v">' + s.blast.pos_invalidated + '</span></div><div class="d-kv"><span class="k">Cx tests stale</span><span class="v">' + s.blast.cx_tests_stale + "</span></div>" : "") + "</div>"
      : '<div class="card"><h2>' + icon("blast") + 'blast wave</h2><div class="form-note">no addenda on file \u2014 when the client issues one, upload the PDF from the hub and this card fills with its consequences</div></div>') +
    '<div class="card hoverable" onclick="location.hash=\'#clock\'"><h2>' + icon("clock") + 'next decision</h2><div class="metric"><div class="num num-verm">' + (s.days_to_decide != null ? s.days_to_decide + "d" : "\u2014") + '</div><div class="lbl">to decide concessions \u00b7 by ' + esc(s.decide_by || "\u2014") + "</div></div></div>" +
    '<div class="card hoverable" onclick="location.hash=\'#graph\'"><h2>' + icon("graph") + 'the graph</h2><div class="metric"><div class="num">' + fmtN(s.graph_nodes) + '</div><div class="lbl">nodes \u00b7 ' + fmtN(s.graph_edges) + " edges \u00b7 clause to package to PO to test, one connected record</div></div></div>" +
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
    (pkgs.length && pkgs.every((p) => p.reject_status === "EXPIRED") ? '<div class="callout mb"><b>The window to reject and re-order has passed for every package.</b> That is not a flaw in the plan \u2014 it is the truth of the calendar. The live choices are: accept with conditions (and price the consequence), or make the vendor rectify.</div>' : (pkgs.some((p) => p.reject_status === "EXPIRED") ? '<div class="callout mb"><b>' + pkgs.filter((p) => p.reject_status === "EXPIRED").length + " of " + pkgs.length + ' packages have a closed rejection window.</b> For those, the live choices are accept-with-conditions or rectify \u2014 the calendar already decided the rest.</div>' : "")) +
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
            : '<div class="quote"><span class="q-src">submittal</span><i>no governing evidence found for this parameter</i></div>') + "</div>" +
        (r.reason ? '<div class="reason">' + esc(r.reason) + "</div>" : "") + "</div>";
    }).join("");
    view.innerHTML = '<div class="view">' +
      head("Evidence review", "every stamp beside the two sentences that earned it") +
      '<div class="row mb"><select class="inline" id="pkg-sel">' + pkgs.map((p) => '<option' + (p === pkg ? " selected" : "") + ">" + esc(p) + "</option>").join("") + "</select>" +
      '<div class="seg"><button id="seg-pre" class="' + (mode === "pre" ? "on" : "") + '">baseline</button><button id="seg-post" class="' + (mode === "post" ? "on" : "") + '">current</button></div>' +
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
const NODE_COLORS = { section: "#355e8d", clause: "#7d8fae", package: "#a07416", po: "#3f7d4e", activity: "#6d5f92", cx: "#b0567f", addendum: "#c9442a", vendor: "#8a6d3b", shipment: "#2e7d84", quality: "#a04b3f" };
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
  let g = null;
  try {
    const _o = await api("/api/ontology");
    if ((_o.objects || []).length) {
      g = { nodes: _o.objects.map((x) => ({ id: x.id, type: x.type, label: x.name, status: x.status || "", meta: x.props || {} })),
            edges: (_o.links || []).map((l) => ({ s: l.s, t: l.t, type: l.rel })) };
      window.__ONTO_IDS = new Set(g.nodes.map((n) => n.id));
    }
  } catch (e) { window.__ONTO_IDS = null; }
  if (!g) { window.__ONTO_IDS = null; g = await api("/api/graph"); }
  (g.nodes || []).forEach((n) => { if (n.label == null) n.label = String(n.id || ""); });
  if ((g.nodes || []).length > 900) {
    const risky = new Set(["DEVIATION", "MISSING_EVIDENCE", "NEEDS_REVIEW", "CRITICAL", "INVALID", "STALE", "PENDING"]);
    const hot = new Set(g.nodes.filter((n) => risky.has(n.status)).map((n) => n.id));
    const keep = new Set(g.nodes.filter((n) => n.type === "section" || n.type === "package" || n.type === "addendum" || hot.has(n.id)).map((n) => n.id));
    g.edges.forEach((e) => { if (hot.has(e.s) || hot.has(e.t)) { keep.add(e.s); keep.add(e.t); } });
    g.nodes = g.nodes.filter((n) => keep.has(n.id));
    g.edges = g.edges.filter((e) => keep.has(e.s) && keep.has(e.t));
  }
  const nodes = (g.nodes || []).map((n) => Object.assign({}, n));
  const rawEdges = (g.edges || []).map((e) => ({ s: e.s || e.source, t: e.t || e.target, type: e.type }));
  view.innerHTML = '<div class="view" style="max-width:none">' +
    head("The ontology graph", nodes.length + " objects \u00b7 " + rawEdges.length + " typed relationships \u2014 every node is a real-world object \u00b7 click: open the object") +
    '<div class="graph-wrap"><div class="card graph-card"><canvas id="graph-canvas"></canvas></div>' +
    '<div class="graph-legend">' + Object.entries(NODE_COLORS).map(([k, c]) => '<div class="lg"><span class="sw" style="background:' + c + '"></span>' + k + "</div>").join("") +
    '<div class="lg"><span class="sw" style="background:transparent;border-color:var(--verm);box-shadow:0 0 0 1.5px var(--verm)"></span>flagged</div>' +
    '<div class="form-note" style="margin-top:6px;max-width:210px">typed relationships: <i>complies_with / deviates_from</i> \u00b7 vendor <i>supplies</i> PO \u00b7 shipment <i>delivers</i> PO \u00b7 PO <i>feeds</i> activity \u00b7 test <i>verifies</i> section \u00b7 addendum <i>amends</i> section \u00b7 quality issue <i>blocks</i></div></div>' +
    '<div class="graph-stats mono" id="g-stats"></div>' +
    '<div class="graph-tip" id="g-tip"></div><div id="g-dossier"></div></div></div>';
  const canvas = $("#graph-canvas"), wrap = canvas.parentElement;
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let W = 0, H = 0;
  function size(force) {
    const rect = wrap.getBoundingClientRect();
    const w = Math.max(360, Math.round(rect.width)), h = Math.max(380, Math.round(rect.height));
    if (!force && Math.abs(w - W) < 9 && Math.abs(h - H) < 9) return;
    W = w; H = h;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
  }
  size(true);
  let rsT = 0;
  const onResize = () => { clearTimeout(rsT); rsT = setTimeout(() => size(false), 120); };
  window.addEventListener("resize", onResize);
  // ---- deterministic init (seeded rings, then a d3-style force layout)
  const rng = mulberry32(1337);
  const RING = { section: 120, addendum: 200, clause: 340, vendor: 430, package: 520, po: 660, shipment: 760, activity: 800, quality: 880, cx: 940 };
  const byId = new Map();
  nodes.forEach((n) => {
    const r = (RING[n.type] || 700) * (0.85 + rng() * 0.3);
    const a = rng() * Math.PI * 2;
    n.x = Math.cos(a) * r; n.y = Math.sin(a) * r;
    n.vx = 0; n.vy = 0;
    byId.set(n.id, n);
  });
  const edges = rawEdges.filter((e) => byId.has(e.s) && byId.has(e.t));
  const adj = new Map();
  nodes.forEach((n) => adj.set(n.id, []));
  edges.forEach((e) => { adj.get(e.s).push({ id: e.t, type: e.type }); adj.get(e.t).push({ id: e.s, type: e.type }); });
  nodes.forEach((n) => {
    n.deg = adj.get(n.id).length;
    n.r = 2.4 + Math.sqrt(n.deg) * 1.05;        // radius grows with connectivity
    n.mass = 1 + Math.min(n.deg, 30) * 0.28;    // hubs push harder, their fans get room
  });
  edges.forEach((e) => {
    const da = byId.get(e.s).deg, db = byId.get(e.t).deg;
    e.k = 1 / Math.max(1, Math.min(da, db));    // d3 link-strength rule: weak springs on hubs
    e.bias = da / (da + db);                    // the heavier end moves less
  });
  // ---- physics. The old build capped repulsion below the spring force and
  // only looked one grid cell around, so springs + centering always won and
  // the layout slowly imploded. This is the plain d3-force model instead:
  // many-body repulsion, degree-normalised springs, gentle centering, all
  // scaled by a decaying alpha so the graph settles and then holds still.
  const SPRING_LEN = 84, MAX_VEL = 14, SETTLE = 2600, CHARGE = 160;
  let alpha = 1, tick = 0, raf = 0, fitted = false;
  const clamp = (v, m) => (v > m ? m : v < -m ? -m : v);
  function physics() {
    if (alpha < 0.004 || tick > SETTLE) return;
    tick++;
    alpha += (0.003 - alpha) * 0.02;
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const m = nodes[j];
        let dx = n.x - m.x, dy = n.y - m.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = rng() - 0.5; dy = rng() - 0.5; d2 = dx * dx + dy * dy + 0.01; }
        if (d2 > 1e6) continue;
        const w = (CHARGE * alpha) / d2;
        n.vx += dx * w * m.mass; n.vy += dy * w * m.mass;
        m.vx -= dx * w * n.mass; m.vy -= dy * w * n.mass;
      }
    }
    for (const e of edges) {
      const a = byId.get(e.s), b = byId.get(e.t);
      let dx = (b.x + b.vx) - (a.x + a.vx), dy = (b.y + b.vy) - (a.y + a.vy);
      const d = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const f = ((d - SPRING_LEN) / d) * e.k * alpha;
      dx *= f; dy *= f;
      b.vx -= dx * e.bias; b.vy -= dy * e.bias;
      a.vx += dx * (1 - e.bias); a.vy += dy * (1 - e.bias);
    }
    for (const n of nodes) {
      if (n === dragNode) { n.vx = 0; n.vy = 0; continue; }
      n.vx -= n.x * 0.018 * alpha; n.vy -= n.y * 0.018 * alpha;
      n.vx = clamp(n.vx * 0.6, MAX_VEL); n.vy = clamp(n.vy * 0.6, MAX_VEL);
      n.x += n.vx; n.y += n.vy;
      if (!isFinite(n.x) || !isFinite(n.y)) { n.x = (rng() - 0.5) * 400; n.y = (rng() - 0.5) * 400; n.vx = n.vy = 0; }
    }
  }
  // ---- camera + interaction
  const cam = { s: 0.35, tx: 0, ty: 0 };
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
      moved = true; alpha = Math.max(alpha, 0.35); tick = Math.min(tick, SETTLE - 900);
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
    cam.s = Math.min(5, Math.max(0.08, cam.s * (e.deltaY < 0 ? 1.12 : 0.89)));
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
  function fitView() {
    if (!nodes.length) return;
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    for (const n of nodes) { if (n.x < x0) x0 = n.x; if (n.x > x1) x1 = n.x; if (n.y < y0) y0 = n.y; if (n.y > y1) y1 = n.y; }
    const bw = Math.max(x1 - x0, 60), bh = Math.max(y1 - y0, 60);
    cam.s = Math.min(2.2, Math.max(0.1, Math.min(W / (bw + 140), H / (bh + 140)) * 0.94));
    cam.tx = W / 2 - ((x0 + x1) / 2) * cam.s;
    cam.ty = H / 2 - ((y0 + y1) / 2) * cam.s;
  }
  canvas.ondblclick = (e) => { e.preventDefault(); fitView(); };
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
    ctx.fillStyle = "rgba(33,28,20,.055)";
    const gs = 26;
    for (let gx = ((cam.tx % gs) + gs) % gs; gx < W; gx += gs)
      for (let gy = ((cam.ty % gs) + gs) % gs; gy < H; gy += gs)
        ctx.fillRect(gx - 0.7, gy - 0.7, 1.4, 1.4);
    if (!fitted && tick > 90) { fitted = true; fitView(); }
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
      const rBase = n.r || 3;
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
      if (n.id === focus) {
        ctx.strokeStyle = "rgba(201,68,42,.85)"; ctx.lineWidth = 1.5 / cam.s;
        ctx.beginPath(); ctx.arc(n.x, n.y, rBase + 3.2 / cam.s, 0, 7); ctx.stroke();
      }
      const isHub = n.type === "section" || n.type === "addendum" || n.type === "package";
      const fade = isHub ? (cam.s - 0.3) * 2.2 : (cam.s - 0.85) * 1.7;
      const lblA = act && act.has(n.id) ? 0.92 : Math.min(0.85, fade);
      if (lblA > 0.04 && inAct) {
        ctx.globalAlpha = lblA;
        ctx.fillStyle = "#211c14";
        ctx.font = ((isHub ? 11 : 10) / cam.s) + "px ui-monospace, Menlo, monospace";
        ctx.textAlign = "center";
        ctx.fillText(n.label.length > 26 ? n.label.slice(0, 25) + "\u2026" : n.label, n.x, n.y - rBase - 4.5 / cam.s);
      }
      ctx.globalAlpha = 1;
    }
    $("#g-stats").textContent = nodes.length + " nodes \u00b7 " + edges.length + " edges \u00b7 drag nodes \u00b7 double-click to fit";
    raf = requestAnimationFrame(draw);
  }
  raf = requestAnimationFrame(draw);
  CLEANUP = () => { cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); window.removeEventListener("mouseup", onUp); };
  // ---- dossier
  async function openDossier(id) {
    const box = $("#g-dossier");
    box.innerHTML = '<div class="dossier"><div class="skel" style="height:20px;width:200px"></div><div class="skel mt" style="height:120px"></div></div>';
    let d;
    if (window.__ONTO_IDS && window.__ONTO_IDS.has(id)) { location.hash = "#object/" + encodeURIComponent(id); return; }
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
    '<div class="callout c-ok mb"><b>' + (l.findings || []).length + " internal contradictions found in this spec.</b> Every finding quotes both conflicting sentences \u2014 check them yourself.</div>" + cards + "</div>";
  view.querySelectorAll("[data-doc]").forEach((btn) => { btn.onclick = () => openDoc(btn.dataset.doc); });
}

/* =========================================================== facility */
async function vFacility(view) {
  const f = await api("/api/facility");
  const t = f.tier || {};
  const stds = f.standards || [], red = f.redundancy || [], mets = f.metrics || [], chk = f.checklist || [];
  if (!t.declared && !stds.length && !red.length) {
    view.innerHTML = '<div class="view">' + head("Facility profile", "the data-centre-specific declarations in this corpus") +
      '<div class="empty-wrap"><div class="empty-card card">' + icon("facility") +
      "<h2>nothing data-centre-specific found</h2><p>no Tier / TIA-942 rating, redundancy topology (N+1, 2N) or DC standard reference was found in the uploaded documents. If this is a data-centre project, upload the electrical, cooling and telecom spec sections.</p></div></div></div>";
    return;
  }
  const plate = t.declared
    ? '<div class="card tier-plate"><div class="tp-big">' + esc(String(t.declared).toUpperCase()) + '</div>' +
      '<div class="lbl">declared availability rating \u00b7 ' + (t.all_mentions || 0) + ' mention(s) in the documents</div>' +
      (t.basis || []).slice(0, 2).map((b) => '<div class="quote q-req" style="margin-top:6px"><span class="q-src">' + esc(b.doc) + ' \u00b7 p' + b.page + '</span>' + esc(b.quote) + '</div>').join("") + '</div>'
    : '<div class="card tier-plate"><div class="tp-big">\u2014</div><div class="lbl">no Tier / Rated level declared in the uploaded documents</div></div>';
  const stdRows = stds.map((s) => '<div class="d-kv"><span class="k">' + esc(s.std) + '</span><span class="v mono">' + s.mentions + '\u00d7 \u00b7 ' + esc((s.sources || [])[0] || "") + '</span></div>').join("");
  const metRows = mets.map((m) => '<div class="d-kv"><span class="k">' + esc(m.name) + '</span><span class="v mono">' + esc(m.value) + ' \u00b7 ' + esc(m.doc) + ' p' + m.page + '</span></div>').join("");
  const redRows = red.map((r) => '<div class="ev-row"><div class="ev-head"><span class="chip mono">' + esc(r.topology) + '</span><span class="param">' + esc(r.system) + '</span><span class="spacer"></span><span class="mono" style="font-size:11px">' + esc(r.doc) + ' \u00b7 p' + r.page + (r.occurrences > 1 ? ' \u00b7 \u00d7' + r.occurrences : '') + '</span></div>' +
    '<div class="quote q-req">' + esc(r.quote) + '</div>' +
    (r.corroboration ? '<div class="reason">' + esc(r.corroboration) + '</div>' : '') + '</div>').join("");
  const chkRows = chk.map((c) => '<div class="d-kv"><span class="k">' + (c.status === "declared" ? '<span class="mono" style="color:var(--ok)">\u25a0 declared</span>' : '<span class="mono" style="color:var(--warn)">\u25a1 not found</span>') + ' \u00b7 ' + esc(c.item) + '</span><span class="v" style="max-width:46%">' + esc(String(c.detail || "")) + '</span></div>').join("");
  view.innerHTML = '<div class="view">' +
    head("Facility profile", "what makes this a data centre \u2014 rating, redundancy and standards, quoted from the documents") +
    '<div class="grid g3 mb">' + plate +
    '<div class="card"><h2>' + icon("facility") + 'standards invoked</h2>' + (stdRows || '<div class="form-note">none found</div>') + '</div>' +
    '<div class="card"><h2>' + icon("margins") + 'declared metrics</h2>' + (metRows || '<div class="form-note">none found</div>') + '</div>' +
    '</div>' +
    '<div class="card mb"><h2>' + icon("graph") + 'redundancy topology, by system</h2>' + (redRows || '<div class="form-note">no N+1 / 2N / 2N+1 language found</div>') + '</div>' +
    '<div class="card"><h2>' + icon("cx") + 'data-centre scorecard</h2>' + chkRows +
    '<div class="form-note">declared = stated in the uploaded documents, with the quote to prove it \u00b7 not found = the scan found no such declaration</div></div>' +
    '</div>';
}

/* =========================================================== blast */
async function vBlast(view) {
  const b = await api("/api/blastwave");
  const waves = (b.waves && b.waves.length) ? b.waves.slice().reverse() : [];
  if (!waves.length) {
    view.innerHTML = '<div class="view">' + head("Blast wave", "what one client letter knocks over") +
      '<div class="empty-wrap"><div class="empty-card card">' + icon("blast") +
      "<h1>no addenda on file</h1><p>When the client issues an addendum, upload the PDF from the hub like any other document. The pipeline detects it by content, amends the rulebook, re-verifies every package, and this page fills with the consequences: flipped verdicts, invalidated purchase orders, stale test procedures.</p>" +
      '<button class="btn btn-primary" onclick="location.hash=\'#hub\'">Upload documents</button></div></div></div>';
    return;
  }
  const secs = waves.map((w) => {
    const ws = w.summary || {};
    const id = w.addendum || w.id || "addendum";
    const flips = (w.verdict_flips || []).map((f) =>
      '<tr><td class="mono">' + esc(f.package) + '</td><td class="mono">' + esc(f.rule_id || "") + "</td><td>" + esc(f.parameter || "") + "</td><td>" + stamp(f.verdict_before, "straight") + " \u2192 " + stamp(f.verdict_after, "straight") + "</td></tr>").join("");
    const pos = (w.pos_invalidated || []).map((p) =>
      '<tr><td class="mono">' + esc(p.po_number) + "</td><td>" + esc(p.vendor || "") + "</td><td>" + esc((p.item_description || "").slice(0, 46)) + '</td><td class="mono r">' + fmtINR(p.value_inr) + "</td><td>" + esc(p.delivery_status || "") + "</td><td>" + stamp(p.ledger_status) + "</td></tr>").join("");
    const stale = (w.cx_tests_stale || []).map((t) =>
      '<div class="ev-row"><div class="ev-head">' + stamp("STALE") + '<span class="param mono">' + esc(t.test_id) + '</span><span class="chip">' + esc(t.spec_clause || "") + '</span></div><div class="quote">' + esc(t.acceptance_criteria || "") + '</div><div class="reason">' + esc(t.ledger_reason || "") + "</div></div>").join("");
    const totalInr = (w.pos_invalidated || []).reduce((a, p) => a + (Number(p.value_inr) || 0), 0);
    return '<div class="card mb"><div class="row">' + stamp("AMENDS", "straight") + '<b class="mono">' + esc(id) + "</b>" + (w.date ? '<span class="chip">' + esc(w.date) + "</span>" : "") +
      '<span class="chip">' + (ws.rules_amended || 0) + ' rules amended</span><span class="chip">' + (w.verdict_flips || []).length + ' verdicts flipped</span><span class="chip">' + (w.pos_invalidated || []).length + " POs \u00b7 " + fmtINR(totalInr) + '</span><span class="chip">' + (w.cx_tests_stale || []).length + ' tests stale</span><span class="spacer"></span>' +
      '<button class="btn" data-graph="add:' + esc(id) + '">Graph</button></div>' +
      '<div class="grid g2 mt">' +
      "<div>" + (flips ? "<table><tr><th>package</th><th>rule</th><th>parameter</th><th>flip</th></tr>" + flips + "</table>" : '<div class="form-note">no verdicts flipped</div>') + "</div>" +
      "<div>" + (pos ? '<table><tr><th>po</th><th>vendor</th><th>item</th><th class="r">value</th><th>delivery</th><th>ledger</th></tr>' + pos + "</table>" : '<div class="form-note">no purchase orders invalidated</div>') + "</div></div>" +
      (stale ? '<div class="mt">' + stale + "</div>" : "") + "</div>";
  }).join("");
  view.innerHTML = '<div class="view">' +
    head("Blast wave", waves.length + " addend" + (waves.length === 1 ? "um" : "a") + " applied in date order \u2014 each with the dominoes it knocked over") + secs + "</div>";
  view.querySelectorAll("[data-graph]").forEach((btn) => { btn.onclick = () => { location.hash = "#graph/" + encodeURIComponent(btn.dataset.graph); }; });
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
    head("Paperwork", "drafts grounded in ledger evidence \u2014 review before issuing") +
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
    head("Commissioning packs", "test readiness, tracked against the ledger") +
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
  let cfg = { base_url: "", model: "", api_key_masked: "", configured: false, keys_count: 0, workers: 0 };
  try { cfg = await api("/api/llm/config"); } catch (e) { /* server offline for config */ }
  view.innerHTML = '<div class="view">' +
    head("Settings", "own the whole chain \u2014 bring any OpenAI-compatible model, or run one on this laptop") +
    '<div class="grid g2">' +
    '<div class="card"><h2>' + icon("chip") + "bring your own model</h2>" +
    '<div class="field"><label>base URL (OpenAI-compatible)</label><input id="llm-base" placeholder="http://localhost:11434/v1" value="' + esc(cfg.base_url || "") + '"></div>' +
    '<div class="field"><label>API key(s) \u2014 one per line' + (cfg.keys_count ? " (saved: " + cfg.keys_count + " key" + (cfg.keys_count > 1 ? "s" : "") + ", " + esc(cfg.api_key_masked || "") + (cfg.keys_count > 1 ? " \u2026" : "") + ")" : "") + '</label><textarea id="llm-keys" rows="3" placeholder="' + (cfg.keys_count ? "leave blank to keep the saved key pool" : "sk-\u2026 or any string for local models\u000aadd more keys, one per line, to fan out") + '"></textarea></div>' +
    '<div class="field"><label>parallel workers (0 = one per key)</label><input id="llm-workers" type="number" min="0" max="64" value="' + (cfg.workers || 0) + '" style="width:110px"></div>' +
    '<div class="field"><label>model</label><input id="llm-model" placeholder="qwen3:4b" value="' + esc(cfg.model || "") + '"></div>' +
    '<div class="row"><button class="btn btn-primary" id="llm-save">Save</button><button class="btn" id="llm-test">Test connection</button>' + (cfg.configured ? stamp("OK", "straight") : "") + "</div>" +
    '<div id="llm-result"></div>' +
    '<div class="form-note">Written to <code>pipeline/.env</code> \u2014 the exact file the pipeline modules read; there is no second config. <b>Scale-out:</b> paste N API keys (one per line) and the LLM stages fan out across N parallel workers, round-robin over the keys \u2014 N keys \u2248 N\u00d7 throughput on rule compilation and claim extraction, because every call is one independent clause or page. Output artifacts stay byte-identical regardless of worker count. Change the model and the LLM cache stops matching: the next run makes real calls to your endpoint and takes real time. Same model, same prompts \u2192 cached responses replay instantly and free. The pipeline sends isolated clause snippets \u2014 never whole documents \u2014 and with a local model nothing leaves your laptop at all.</div></div>' +
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
      const body = { base_url: $("#llm-base").value, model: $("#llm-model").value, workers: parseInt($("#llm-workers").value || "0", 10) || 0 };
      if ($("#llm-keys").value.trim()) body.api_keys = $("#llm-keys").value;
      const r = await post("/api/llm/config", body);
      toast("Saved to pipeline/.env \u2014 takes effect on the next pipeline run"); projectState().catch(() => {});
    } catch (e) { toast(esc(e.message)); }
  };
  $("#llm-test").onclick = async () => {
    const out = $("#llm-result");
    out.innerHTML = '<div class="test-result">testing round-trip\u2026</div>';
    try {
      const firstKey = ($("#llm-keys").value.trim().split(/[\s,]+/)[0]) || "";
      const r = await post("/api/llm/test", { base_url: $("#llm-base").value, api_key: firstKey, model: $("#llm-model").value });
      out.innerHTML = r.ok
        ? '<div class="test-result ok">\u2713 ' + r.ms + " ms \u00b7 " + esc(r.model || "") + " \u00b7 reply: \u201c" + esc(r.reply || "") + "\u201d</div>"
        : '<div class="test-result err">\u2717 ' + esc(r.error || "failed") + "</div>";
    } catch (e) { out.innerHTML = '<div class="test-result err">\u2717 ' + esc(e.message) + "</div>"; }
  };
  try {
    const meta = await api("/api/meta");
    $("#meta-body").innerHTML = "Python " + esc(meta.python) + " \u00b7 server up since " + esc(meta.server_started) + " \u00b7 " + Object.keys(meta.artifacts || {}).length + " artifacts on disk \u00b7 " + (meta.corpus_files || 0) + " staged documents \u00b7 server clock " + esc(meta.now);
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
    if (PROJECT && PROJECT.running) { location.hash = "#run"; return; }
    try { await post("/api/run"); PROJECT = null; location.hash = "#run"; }
    catch (e) { toast(esc(e.message)); }
  };
  setInterval(() => { $("#clock").textContent = new Date().toLocaleTimeString(); }, 1000);
  $("#clock").textContent = new Date().toLocaleTimeString();
  projectState().catch(() => { /* offline */ });
}
window.addEventListener("hashchange", route);
startChrome();
route();

/* =========================================================== copilot */
/* Core feature: full-height drawer, every tool call relayed live (NDJSON
   stream from /api/agent/stream), answers rendered as real markdown via the
   same md2html used for the guides. Falls back to POST /api/agent if the
   stream cannot be read. */
function wireCopilot() {
  const fab = $("#cp-fab"), panel = $("#cp-panel"), log = $("#cp-log");
  if (!fab || !panel) return;
  $("#cp-fab-ic").innerHTML = icon("copilot");
  $("#cp-close").innerHTML = icon("x");
  window.openCopilot = () => { panel.classList.remove("hidden"); $("#cp-in").focus(); };
  fab.onclick = () => { panel.classList.toggle("hidden"); if (!panel.classList.contains("hidden")) $("#cp-in").focus(); };
  $("#cp-close").onclick = () => panel.classList.add("hidden");
  $("#cp-wide").onclick = () => panel.classList.toggle("wide");
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") panel.classList.add("hidden"); });
  const hist = [];
  const scroll = () => { log.scrollTop = log.scrollHeight; };

  function stepRow(box, ev) {
    const row = document.createElement("div");
    row.className = "cp-step";
    row.innerHTML = '<span class="cp-spin"></span><span class="cp-lbl"></span><span class="cp-note"></span>';
    row.querySelector(".cp-lbl").textContent = ev.label || ev.tool;
    box.appendChild(row);
    scroll();
    return row;
  }
  function finishRow(row, ev) {
    if (!row) return;
    const sp = row.querySelector(".cp-spin");
    if (sp) sp.outerHTML = '<span class="cp-tick">\u2713</span>';
    row.classList.add("done");
    const note = [ev.note, ev.cached ? "cached" : ""].filter(Boolean).join(" \u00b7 ");
    if (note) row.querySelector(".cp-note").textContent = "\u00b7 " + note;
  }

  async function askStream(q, onEvent) {
    const r = await fetch("/api/agent/stream", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, history: hist.slice(-8), page: (location.hash || "#hub").slice(1) }),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.error === "no_project" ? (j.hint || j.error) : (j.error || j.hint || "HTTP " + r.status));
    }
    if (!r.body || !r.body.getReader) throw new Error("__no_stream__");
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let buf = "", got = false;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (!line) continue;
        try { onEvent(JSON.parse(line)); got = true; } catch (e) { /* partial line noise */ }
      }
    }
    if (!got) throw new Error("__no_stream__");
  }

  async function askPlain(q) {
    const r = await fetch("/api/agent", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, history: hist.slice(-8), page: (location.hash || "#hub").slice(1) }),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || j.hint || "HTTP " + r.status);
    return j;
  }

  $("#cp-form").onsubmit = async (e) => {
    e.preventDefault();
    const inp = $("#cp-in"), q = inp.value.trim();
    if (!q) return;
    inp.value = "";
    log.insertAdjacentHTML("beforeend", '<div class="cp-msg cp-user"></div>');
    log.lastElementChild.textContent = q;
    const steps = document.createElement("div");
    steps.className = "cp-steps";
    log.appendChild(steps);
    const think = stepRow(steps, { label: "reading the ledger\u2026" });
    scroll();
    let cur = null, replied = false;
    const showReply = (r) => {
      replied = true;
      finishRow(think, {});
      think.remove();
      if (!steps.children.length) steps.remove();
      log.insertAdjacentHTML("beforeend", '<div class="cp-msg cp-ai cp-md">' + md2html(r.reply || "") + "</div>");
      hist.push({ role: "user", content: q }, { role: "assistant", content: r.reply || "" });
      scroll();
    };
    const showErr = (msg) => {
      think.remove();
      if (!steps.children.length) steps.remove();
      log.insertAdjacentHTML("beforeend", '<div class="cp-msg cp-err"></div>');
      log.lastElementChild.textContent = msg;
      scroll();
    };
    try {
      await askStream(q, (ev) => {
        if (ev.event === "thinking") { think.querySelector(".cp-lbl").textContent = steps.children.length > 1 ? "composing\u2026" : "reading the ledger\u2026"; steps.appendChild(think); scroll(); }
        else if (ev.event === "step_start") { cur = stepRow(steps, ev); steps.appendChild(think); }
        else if (ev.event === "step_done") { finishRow(cur, ev); cur = null; }
        else if (ev.event === "reply") showReply(ev);
        else if (ev.event === "error") showErr(ev.error || "copilot error");
      });
      if (!replied && !cur) { /* stream ended without reply event */ }
    } catch (err) {
      if (String(err.message) === "__no_stream__") {
        try { showReply(await askPlain(q)); }
        catch (e2) { showErr(e2.message || String(e2)); }
      } else if (!replied) {
        showErr(err.message || String(err));
      }
    }
  };
}
wireCopilot();

/* =========================================================== intel */
async function vIntel(view) {
  const d = await api("/api/intel");
  const fs = d.findings || [];
  const cards = fs.map((f) => '<div class="ev-row"><div class="ev-head">' +
    '<span class="chip">' + esc(f.severity || "") + '</span>' +
    '<span class="param">' + esc(f.title || "") + '</span><span class="spacer"></span>' +
    '<span class="chip">' + (f.ai ? "read across sources" : "computed") + '</span></div>' +
    '<div class="quote">' + esc(f.narrative || "") + '</div>' +
    '<div class="row mt">' + (f.entities || []).slice(0, 12).map((e) => '<span class="chip mono">' + esc(e) + '</span>').join(" ") + '</div></div>').join("");
  view.innerHTML = '<div class="view">' +
    head("Intelligence", "what the documents say when read together") +
    (fs.length ? cards : '<div class="callout c-ok mb">no cross-document findings yet \u2014 run the pipeline first.</div>') + '</div>';
}

/* =========================================================== supply */
async function vSupply(view) {
  const s = await api("/api/supply");
  const items = s.items || [], alerts = s.alerts || [], un = s.unlinked || [];
  const n = (k) => (s.summary || {})[k] || 0;
  const alertCards = alerts.map((a) => '<div class="ev-row"><div class="ev-head">' +
    '<span class="chip">' + esc(a.severity || "") + '</span>' +
    '<span class="param">' + esc((a.po || "") + " \u00b7 " + (a.item || "")) + '</span><span class="spacer"></span>' +
    '<span class="chip mono">' + esc(a.activity || "") + '</span></div>' +
    '<div class="quote">' + esc(a.vendor || "") + ' \u00b7 needed on site ' + esc(a.needed_on_site || "") +
    ' \u00b7 projected arrival ' + esc(a.projected_arrival || "") + ' \u00b7 margin ' + a.margin_days +
    'd \u00b7 days left to act: ' + a.days_to_act + (a.schedule_float_absorbs ? ' \u00b7 schedule float absorbs it' : '') + '</div></div>').join("");
  const rows = items.map((r) => '<div class="d-kv"><span class="k mono">' + esc(r.po || "") + '</span><span class="v">' +
    esc(((r.item || "").slice(0, 64)) + " \u00b7 " + (r.vendor || "") + " \u00b7 " + (r.status || "")) +
    (r.margin_days != null ? " \u00b7 margin " + r.margin_days + "d" : "") + '</span></div>').join("");
  view.innerHTML = '<div class="view">' +
    head("Supply chain", "every purchase order joined to the schedule activity that needs it") +
    '<div class="callout c-ok mb"><b>' + items.length + ' POs joined to the schedule \u00b7 ' + n("LATE") + ' late \u00b7 ' +
    n("AT_RISK") + ' at risk \u00b7 ' + n("WATCH") + ' on watch' + (un.length ? ' \u00b7 ' + un.length + ' not linkable' : '') + '.</b></div>' +
    (s.brief_md ? '<div class="card mb cp-md">' + md2html(s.brief_md) + '</div>' : '') +
    alertCards + '<div class="card mt">' + (rows || '<div class="form-note">no purchase orders found</div>') + '</div></div>';
}
