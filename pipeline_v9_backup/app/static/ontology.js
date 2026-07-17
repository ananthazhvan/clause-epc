/* CLAUSE ontology views: Objects, Object-360, Globe. Loaded before app.js. */

async function ontoLoad() {
  const now = Date.now();
  if (window.__ONTO_CACHE && now - window.__ONTO_CACHE._at < 20000) return window.__ONTO_CACHE;
  const o = await api("/api/ontology");
  o._at = now;
  o.byId = {};
  (o.objects || []).forEach((x) => { o.byId[x.id] = x; });
  o.adj = {};
  (o.links || []).forEach((l) => {
    (o.adj[l.s] = o.adj[l.s] || []).push({ id: l.t, rel: l.rel, dir: "out" });
    (o.adj[l.t] = o.adj[l.t] || []).push({ id: l.s, rel: l.rel, dir: "in" });
  });
  window.__ONTO_CACHE = o;
  return o;
}

const O_BAD = new Set(["DEVIATION", "CRITICAL", "FAILED", "LATE", "EXCEPTION", "CUSTOMS_HOLD", "IN_TRANSIT_DELAYED", "OPEN"]);
const O_WARN = new Set(["NEEDS_REVIEW", "AMENDS", "STALE", "AT_RISK", "SUPERSEDED", "PENDING", "IN_TRANSIT"]);
function oBadge(st) {
  if (!st) return "";
  const c = O_BAD.has(st) ? "var(--bad)" : O_WARN.has(st) ? "var(--warn)" : "var(--ok)";
  return '<span class="mono" style="color:' + c + ';border:1px solid ' + c + ';border-radius:3px;padding:0 5px;font-size:11px">' + esc(st) + "</span>";
}
function oInr(v) { try { return fmtINR(v); } catch (e) { return "\u20b9" + Math.round(v).toLocaleString("en-IN"); } }
function oShort(x) { return esc((x.name || x.id).length > 46 ? (x.name || x.id).slice(0, 45) + "\u2026" : (x.name || x.id)); }
const O_TYPE_LABEL = { section: "Spec sections", package: "Submittals", po: "Purchase orders", vendor: "Vendors", shipment: "Shipments", activity: "Activities", cx: "Cx tests", quality: "Quality issues", addendum: "Addenda" };

/* ============================================= Objects (the catalog) */
async function vObjects(view) {
  let o;
  try { o = await ontoLoad(); } catch (e) { view.innerHTML = '<div class="view">' + head("Objects", "") + '<div class="card">' + esc(e.message) + "</div></div>"; return; }
  const objs = o.objects || [];
  if (!objs.length) {
    view.innerHTML = '<div class="view">' + head("Objects", "nothing compiled yet") +
      '<div class="card">No ontology yet \u2014 run the pipeline (M16 compiles it as the final stage).</div></div>';
    return;
  }
  const t = (o.project || {}).totals || {};
  let fType = "", fText = "";
  const counts = {};
  objs.forEach((x) => { counts[x.type] = (counts[x.type] || 0) + 1; });
  const chips = Object.keys(O_TYPE_LABEL).filter((k) => counts[k]).map((k) =>
    '<button class="chip" data-t="' + k + '" style="cursor:pointer;margin:0 6px 6px 0;border:1px solid var(--raised);background:var(--panel);border-radius:14px;padding:3px 10px;font:inherit">' +
    (O_TYPE_LABEL[k] || k) + ' <span class="mono">' + counts[k] + "</span></button>").join("");
  view.innerHTML = '<div class="view">' +
    head("Objects", (t.objects || objs.length) + " objects \u00b7 " + (t.links || (o.links || []).length) + " typed links \u00b7 " +
      oInr(t.procurement_value_inr || 0) + " mapped \u00b7 " + oInr(t.value_at_risk_inr || 0) + " at risk") +
    '<div style="margin-bottom:10px"><input id="o-q" placeholder="search objects\u2026" style="width:240px;padding:5px 9px;border:1px solid var(--raised);background:var(--panel);border-radius:5px;font:inherit;margin-right:12px">' + chips + "</div>" +
    '<div id="o-list"></div></div>';
  const list = $("#o-list");
  function row(x) {
    const risk = (x.money || {}).at_risk_inr ? ' \u00b7 <span style="color:var(--bad)">' + oInr(x.money.at_risk_inr) + " at risk</span>" : "";
    const val = (x.money || {}).value_inr ? '<span class="mono">' + oInr(x.money.value_inr) + "</span>" + risk : "";
    const ins = (x.insights || []).length ? ' \u00b7 ' + (x.insights || []).length + " insight" + ((x.insights || []).length > 1 ? "s" : "") : "";
    const deg = ((o.adj[x.id] || []).length) + " links" + ins;
    return '<div class="card" data-id="' + esc(x.id) + '" style="cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:10px;padding:9px 13px;margin-bottom:6px">' +
      '<div><span class="mono" style="color:var(--ink3);margin-right:8px">' + esc(x.type) + "</span>" + oShort(x) +
      '<div class="form-note">' + deg + "</div></div>" +
      '<div style="text-align:right">' + val + " " + oBadge(x.status) + "</div></div>";
  }
  function paint() {
    const q = fText.toLowerCase();
    const rows = objs.filter((x) => (!fType || x.type === fType) &&
      (!q || (x.name + " " + x.id + " " + JSON.stringify(x.props)).toLowerCase().includes(q)));
    rows.sort((a, b) => ((b.money || {}).at_risk_inr || 0) - ((a.money || {}).at_risk_inr || 0) ||
      (b.insights || []).length - (a.insights || []).length);
    list.innerHTML = rows.slice(0, 400).map(row).join("") || '<div class="form-note">no objects match</div>';
    list.querySelectorAll("[data-id]").forEach((el) => {
      el.onclick = () => { location.hash = "#object/" + encodeURIComponent(el.getAttribute("data-id")); };
    });
  }
  view.querySelectorAll(".chip").forEach((c) => {
    c.onclick = () => {
      fType = fType === c.getAttribute("data-t") ? "" : c.getAttribute("data-t");
      view.querySelectorAll(".chip").forEach((k) => { k.style.background = k.getAttribute("data-t") === fType ? "var(--raised)" : "var(--panel)"; });
      paint();
    };
  });
  $("#o-q").oninput = (e) => { fText = e.target.value; paint(); };
  paint();
}

/* ============================================= Object 360 */
async function vObject360(view, arg) {
  let o;
  try { o = await ontoLoad(); } catch (e) { view.innerHTML = '<div class="view"><div class="card">' + esc(e.message) + "</div></div>"; return; }
  const x = o.byId[arg];
  if (!x) { view.innerHTML = '<div class="view">' + head("Object", "") + '<div class="card">Unknown object: ' + esc(arg) + '. <a href="#objects">Back to objects</a>.</div></div>'; return; }
  const m = x.money || {};
  let money = "";
  if (m.value_inr) money += '<div class="d-kv"><span class="k">money riding on this</span><span class="v mono">' + oInr(m.value_inr) + "</span></div>";
  if (m.at_risk_inr) money += '<div class="d-kv"><span class="k" style="color:var(--bad)">exposed if this fails</span><span class="v mono" style="color:var(--bad)">' + oInr(m.at_risk_inr) + "</span></div>" +
    (m.at_risk_why || []).map((w) => '<div class="form-note" style="color:var(--bad)">\u2022 ' + esc(w) + "</div>").join("");
  const props = Object.entries(x.props || {}).filter(([, v]) => v !== "" && v != null).map(([k, v]) =>
    '<div class="d-kv"><span class="k">' + esc(k.replace(/_/g, " ")) + '</span><span class="v" style="max-width:60%">' + esc(String(v)) + "</span></div>").join("");
  const insights = (x.insights || []).map((i) => {
    const c = i.severity === "bad" ? "var(--bad)" : i.severity === "warn" ? "var(--warn)" : "var(--ink2)";
    return '<div class="card" style="border-left:3px solid ' + c + ';padding:8px 12px;margin-bottom:6px">' + esc(i.text) + "</div>";
  }).join("");
  const byRel = {};
  (o.adj[x.id] || []).forEach((l) => {
    const rel = l.dir === "out" ? l.rel : "\u2190 " + l.rel;
    (byRel[rel] = byRel[rel] || []).push(l.id);
  });
  const links = Object.entries(byRel).map(([rel, ids]) =>
    '<div style="margin-bottom:8px"><div class="form-note mono">' + esc(rel) + "</div>" +
    ids.map((id) => {
      const n = o.byId[id] || { id: id, name: id, type: "?" };
      return '<a href="#object/' + encodeURIComponent(id) + '" class="card" style="display:inline-block;padding:4px 10px;margin:3px 6px 3px 0;text-decoration:none;color:inherit">' +
        '<span class="mono" style="color:var(--ink3)">' + esc(n.type) + "</span> " + oShort(n) + " " + oBadge(n.status) + "</a>";
    }).join("") + "</div>").join("") || '<div class="form-note">no links</div>';
  let geo = "";
  if (x.type === "shipment" && x.geo && x.geo.lat != null) {
    geo = '<div class="d-kv"><span class="k">last seen</span><span class="v">' + esc(x.props.last_position || "") + ' <span class="mono">(' +
      Number(x.geo.lat).toFixed(2) + ", " + Number(x.geo.lon).toFixed(2) + ')</span></span></div>' +
      '<div style="margin-top:8px"><a href="#globe" class="mono">\u25cf see it on the globe</a></div>';
  }
  view.innerHTML = '<div class="view">' +
    '<div class="form-note" style="margin-bottom:6px"><a href="#objects">\u2190 all objects</a></div>' +
    head(x.name || x.id, esc(x.type) + " object \u00b7 " + ((o.adj[x.id] || []).length) + " typed links") +
    '<div style="margin:-6px 0 12px">' + oBadge(x.status) + "</div>" +
    (insights ? '<h3 style="margin:6px 0">What the ontology knows</h3>' + insights : "") +
    '<div class="card" style="padding:10px 14px;margin-bottom:10px">' + money + props + geo + "</div>" +
    '<h3 style="margin:6px 0">Linked objects</h3>' + links + "</div>";
}

/* ============================================= Globe */
const O_LAND = [
  [7, 32, 68, 90], [20, 45, 95, 125], [10, 23, 98, 109], [-10, 6, 95, 141], [31, 43, 129, 145],
  [45, 70, 60, 179], [50, 70, 28, 60], [36, 55, -9, 30], [55, 70, 4, 31], [36, 43, -9, 3],
  [13, 36, -16, 34], [0, 13, -16, 50], [-35, 0, 10, 41], [13, 33, 34, 59],
  [26, 49, -124, -68], [49, 70, -165, -88], [60, 82, -70, -22], [14, 26, -106, -88], [7, 12, -85, -77],
  [-4, 11, -79, -51], [-24, -4, -75, -39], [-55, -24, -73, -56], [-38, -12, 113, 153], [-46, -34, 166, 178],
];
function oLand(lat, lon) {
  for (const r of O_LAND) if (lat >= r[0] && lat <= r[1] && lon >= r[2] && lon <= r[3]) return true;
  return false;
}
async function vGlobe(view) {
  let o;
  try { o = await ontoLoad(); } catch (e) { view.innerHTML = '<div class="view"><div class="card">' + esc(e.message) + "</div></div>"; return; }
  const ships = (o.objects || []).filter((x) => x.type === "shipment" && x.geo && x.geo.lat != null);
  view.innerHTML = '<div class="view" style="max-width:none">' +
    head("The globe", ships.length + " tracked shipments \u00b7 drag to spin \u00b7 click a marker to open the object") +
    '<div style="display:flex;gap:14px;flex-wrap:wrap">' +
    '<div class="card" style="flex:1 1 480px;min-height:480px;position:relative"><canvas id="globe-cv" style="width:100%;height:480px;display:block;cursor:grab"></canvas>' +
    '<div id="globe-tip" class="mono form-note" style="position:absolute;left:12px;bottom:8px"></div></div>' +
    '<div style="flex:1 1 300px;max-width:430px" id="globe-list"></div></div></div>';
  const listEl = $("#globe-list");
  listEl.innerHTML = ships.map((s) => {
    const eta = s.props.current_eta || "";
    const plan = s.props.scheduled_eta || "";
    const slip = eta && plan && eta !== plan;
    const affected = (s.insights || []).find((i) => /addendum|ADD-/i.test(i.text));
    return '<div class="card" data-id="' + esc(s.id) + '" style="cursor:pointer;padding:9px 13px;margin-bottom:7px">' +
      '<div style="display:flex;justify-content:space-between;gap:8px"><b>' + oShort(s) + "</b>" + oBadge(s.status) + "</div>" +
      '<div class="form-note">' + esc(s.props.last_position || "position unknown") + "</div>" +
      (eta ? '<div class="form-note">ETA <span class="mono"' + (slip ? ' style="color:var(--warn)"' : "") + ">" + esc(eta) + "</span>" + (slip ? " (plan " + esc(plan) + ")" : "") + "</div>" : "") +
      (s.props.delay_reason ? '<div class="form-note" style="color:var(--bad)">' + esc(s.props.delay_reason) + "</div>" : "") +
      (affected ? '<div class="form-note" style="color:var(--warn)">\u26a0 ' + esc(affected.text) + "</div>" : "") + "</div>";
  }).join("") || '<div class="card">No shipment feed found in the corpus.</div>';
  listEl.querySelectorAll("[data-id]").forEach((el) => {
    el.onclick = () => { location.hash = "#object/" + encodeURIComponent(el.getAttribute("data-id")); };
  });

  const cv = $("#globe-cv");
  if (!cv) return;
  const css = getComputedStyle(document.documentElement);
  const C = (n, fb) => (css.getPropertyValue(n) || fb).trim();
  const COL = { paper: C("--panel", "#faf7ef"), inset: C("--inset", "#ece4d2"), raised: C("--raised", "#e3d9c4"), ink: C("--ink", "#211c14"), ink3: C("--ink3", "#94886e"), ok: C("--ok", "#3f7d4e"), warn: C("--warn", "#a07416"), bad: C("--bad", "#b3382e"), verm: C("--verm", "#c9442a") };
  const ctx = cv.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let W = 0, H = 0;
  function size() {
    W = cv.clientWidth; H = cv.clientHeight;
    cv.width = W * dpr; cv.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  size();
  const dots = [];
  for (let lat = -55; lat <= 72; lat += 3)
    for (let lon = -180; lon < 180; lon += 3)
      if (oLand(lat, lon)) dots.push([lat, lon]);
  const meanLon = ships.length ? ships.reduce((a, s) => a + Number(s.geo.lon || 0), 0) / ships.length : 78;
  let lam = -meanLon * Math.PI / 180, phi = -0.32, spin = true, drag = null, hover = null;
  const D2R = Math.PI / 180;
  function proj(lat, lon, R) {
    const la = lat * D2R, lo = lon * D2R + lam;
    const x1 = Math.cos(la) * Math.sin(lo);
    const y1 = Math.sin(la);
    const z1 = Math.cos(la) * Math.cos(lo);
    const y2 = y1 * Math.cos(phi) - z1 * Math.sin(phi);
    const z2 = y1 * Math.sin(phi) + z1 * Math.cos(phi);
    return [W / 2 + R * x1, H / 2 - R * y2, z2 > 0];
  }
  function slerpPts(a, b, n) {
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      pts.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t + Math.sin(t * Math.PI) * 8]);
    }
    return pts;
  }
  const markers = [];
  function draw() {
    const R = Math.min(W, H) / 2 - 18;
    ctx.clearRect(0, 0, W, H);
    ctx.beginPath(); ctx.arc(W / 2, H / 2, R, 0, Math.PI * 2);
    ctx.fillStyle = COL.inset; ctx.fill();
    ctx.strokeStyle = COL.ink; ctx.lineWidth = 1.4; ctx.stroke();
    ctx.fillStyle = COL.ink3;
    for (const [lat, lon] of dots) {
      const [x, y, v] = proj(lat, lon, R);
      if (v) { ctx.globalAlpha = 0.75; ctx.fillRect(x - 1, y - 1, 2, 2); }
    }
    ctx.globalAlpha = 1;
    markers.length = 0;
    for (const s of ships) {
      const g = s.geo;
      if (g.origin && g.destination && g.origin[0] != null && g.destination[0] != null) {
        ctx.strokeStyle = COL.raised; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
        ctx.beginPath();
        let started = false;
        for (const [la, lo] of slerpPts(g.origin, g.destination, 36)) {
          const [x, y, v] = proj(la, lo, R);
          if (!v) { started = false; continue; }
          if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
        }
        ctx.stroke(); ctx.setLineDash([]);
        const [dx, dy, dv] = proj(g.destination[0], g.destination[1], R);
        if (dv) { ctx.fillStyle = COL.ink; ctx.fillRect(dx - 2, dy - 2, 4, 4); }
      }
      const [x, y, v] = proj(Number(g.lat), Number(g.lon), R);
      if (!v) continue;
      const st = (s.status || "").toUpperCase();
      const col = /DELAY|HOLD|EXCEPTION/.test(st) ? COL.bad : st === "DELIVERED" ? COL.ok : COL.warn;
      ctx.beginPath(); ctx.arc(x, y, 4.5, 0, Math.PI * 2);
      ctx.fillStyle = col; ctx.fill();
      ctx.strokeStyle = COL.paper; ctx.lineWidth = 1.2; ctx.stroke();
      if (st !== "DELIVERED") { ctx.beginPath(); ctx.arc(x, y, 8.5, 0, Math.PI * 2); ctx.strokeStyle = col; ctx.globalAlpha = 0.45; ctx.stroke(); ctx.globalAlpha = 1; }
      ctx.fillStyle = COL.ink; ctx.font = "10px ui-monospace, monospace";
      ctx.fillText((s.name || s.id).split(" \u00b7")[0].replace("ship:", ""), x + 8, y + 3);
      markers.push({ x: x, y: y, id: s.id, s: s });
    }
  }
  function frame() {
    if (!document.body.contains(cv)) return;
    if (spin && !drag && !hover) lam += 0.0016;
    if (cv.clientWidth !== W || cv.clientHeight !== H) size();
    draw();
    requestAnimationFrame(frame);
  }
  cv.onmousedown = (e) => { drag = { x: e.clientX, y: e.clientY, lam: lam, phi: phi }; cv.style.cursor = "grabbing"; };
  window.addEventListener("mousemove", (e) => {
    if (drag) {
      lam = drag.lam + (e.clientX - drag.x) * 0.006;
      phi = Math.max(-1.2, Math.min(1.2, drag.phi - (e.clientY - drag.y) * 0.006));
      return;
    }
    const r = cv.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    hover = null;
    for (const mk of markers) if ((mk.x - mx) ** 2 + (mk.y - my) ** 2 < 170) hover = mk;
    cv.style.cursor = hover ? "pointer" : "grab";
    const tip = $("#globe-tip");
    if (tip) tip.textContent = hover ? (hover.s.name + " \u00b7 " + (hover.s.status || "") + " \u00b7 " + (hover.s.props.last_position || "")) : "";
  });
  window.addEventListener("mouseup", () => { drag = null; cv.style.cursor = "grab"; });
  cv.onclick = () => { if (hover) location.hash = "#object/" + encodeURIComponent(hover.id); };
  frame();
}
