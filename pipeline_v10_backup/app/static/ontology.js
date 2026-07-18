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
/* Hand-traced low-res world coastlines as [lon, lat] polylines - just enough
   to read the planet at a glance, stroked outlines only (creme atlas look). */
const WORLD = [
  [[-166,68],[-158,71],[-140,70],[-125,70],[-110,68],[-95,69],[-85,66],[-82,62],[-93,58],[-85,55],[-82,52],[-70,58],[-64,60],[-60,55],[-55,52],[-60,50],[-65,49],[-70,44],[-74,40],[-76,35],[-81,31],[-80,26],[-83,29],[-89,29],[-94,29],[-97,26],[-97,22],[-95,19],[-104,19],[-106,23],[-110,23],[-113,29],[-117,33],[-122,37],[-124,43],[-124,48],[-128,51],[-132,55],[-140,60],[-150,60],[-152,58],[-158,56],[-165,60],[-168,66],[-166,68]],
  [[-97,20],[-94,16],[-88,13],[-84,10],[-80,9],[-77,8]],
  [[-77,8],[-72,12],[-64,10],[-60,8],[-52,4],[-50,0],[-44,-3],[-37,-5],[-35,-8],[-39,-14],[-40,-20],[-48,-26],[-53,-33],[-58,-38],[-62,-40],[-65,-45],[-69,-50],[-68,-54],[-73,-52],[-73,-46],[-71,-38],[-71,-30],[-70,-22],[-72,-17],[-77,-12],[-81,-5],[-80,0],[-77,4],[-77,8]],
  [[-6,35],[3,37],[10,37],[20,32],[30,31],[33,31],[34,28],[36,22],[38,18],[43,11],[48,11],[51,10],[45,2],[41,-2],[40,-10],[36,-18],[33,-25],[28,-33],[20,-35],[18,-32],[15,-27],[12,-18],[11,-9],[9,-1],[9,4],[4,6],[-4,5],[-8,5],[-13,8],[-17,14],[-16,21],[-13,27],[-9,31],[-6,35]],
  [[-9,36],[-9,43],[-2,45],[0,47],[-4,48],[2,51],[4,53],[9,54],[8,56],[11,57],[10,59],[5,60],[5,62],[12,65],[16,68],[21,70],[28,71],[33,69],[40,66],[45,68],[55,69],[68,70],[73,68],[80,71],[95,76],[105,77],[113,74],[130,72],[140,72],[150,70],[160,69],[170,67],[178,66],[178,64],[170,60],[162,58],[160,53],[156,51],[150,59],[143,54],[141,52],[137,45],[131,43],[128,40],[126,38],[122,37],[121,32],[121,28],[117,23],[110,20],[108,15],[106,10],[104,2],[101,3],[98,8],[97,14],[94,17],[91,22],[88,22],[85,20],[80,16],[80,10],[77,8],[73,16],[70,21],[68,24],[66,25],[61,25],[57,26],[54,27],[50,30],[48,30],[50,26],[54,26],[57,24],[59,22],[57,19],[52,16],[48,14],[44,12],[43,16],[39,20],[36,26],[34,30],[34,33],[36,36],[30,36],[27,37],[26,39],[26,41],[23,40],[22,38],[23,36],[19,40],[16,42],[13,45],[14,42],[16,40],[17,39],[15,38],[13,41],[11,44],[9,44],[6,43],[3,42],[0,39],[-2,37],[-5,36],[-9,36]],
  [[-5,50],[-4,53],[-6,56],[-5,58],[-3,59],[-2,57],[0,53],[1,51],[-5,50]],
  [[-10,52],[-10,54],[-8,55],[-6,54],[-6,52],[-10,52]],
  [[-22,64],[-18,63],[-14,65],[-18,66],[-23,65],[-22,64]],
  [[-45,60],[-42,62],[-32,68],[-22,70],[-18,76],[-22,80],[-38,83],[-55,82],[-62,76],[-58,72],[-54,67],[-48,61],[-45,60]],
  [[130,31],[132,33],[135,34],[140,35],[141,38],[140,41],[141,45],[145,44],[143,42],[141,40],[137,36],[133,34],[131,32],[130,31]],
  [[120,14],[121,17],[122,18],[121,14],[120,14]],
  [[95,5],[99,2],[103,-2],[106,-5],[104,-5],[100,0],[96,4],[95,5]],
  [[105,-6],[110,-7],[114,-8],[112,-8],[106,-7],[105,-6]],
  [[109,1],[112,3],[117,4],[119,1],[116,-3],[112,-3],[109,1]],
  [[131,-1],[136,-2],[141,-3],[146,-6],[150,-9],[147,-9],[142,-8],[137,-5],[132,-2],[131,-1]],
  [[114,-22],[113,-25],[115,-32],[118,-35],[124,-33],[130,-32],[136,-35],[140,-38],[145,-38],[147,-39],[150,-37],[153,-32],[153,-27],[151,-24],[149,-20],[146,-19],[143,-14],[142,-11],[139,-17],[136,-12],[132,-12],[129,-15],[126,-14],[122,-18],[118,-20],[114,-22]],
  [[145,-41],[148,-41],[147,-43],[145,-42],[145,-41]],
  [[173,-35],[176,-38],[178,-38],[176,-40],[174,-41],[172,-40],[173,-35]],
  [[173,-41],[171,-42],[168,-44],[167,-46],[170,-46],[173,-43],[173,-41]],
  [[44,-12],[48,-14],[50,-16],[47,-25],[45,-25],[43,-21],[44,-16],[44,-12]],
  [[80,6],[82,7],[81,9],[80,8],[80,6]],
  [[-84,22],[-79,21],[-75,20],[-78,22],[-84,22]],
  [[28,41],[33,42],[41,42],[38,44],[33,45],[30,44],[28,41]],
  [[50,37],[54,39],[53,42],[50,45],[48,42],[49,38],[50,37]],
  [[-180,-71],[-150,-73],[-120,-72],[-90,-70],[-60,-68],[-58,-64],[-45,-72],[-20,-70],[10,-69],[40,-67],[70,-68],[100,-66],[130,-66],[160,-70],[180,-71]],
];
async function vGlobe(view) {
  let o;
  try { o = await ontoLoad(); } catch (e) { view.innerHTML = '<div class="view"><div class="card">' + esc(e.message) + "</div></div>"; return; }
  const ships = (o.objects || []).filter((x) => x.type === "shipment" && x.geo && x.geo.lat != null);
  view.innerHTML = '<div class="view" style="max-width:none">' +
    head("The globe", ships.length + " tracked shipments \u00b7 drag to spin \u00b7 scroll to zoom \u00b7 click a marker to open the object") +
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
  }).join("") || '<div class="card"><b>No shipment feed in this corpus.</b><div class="form-note" style="margin-top:6px">The globe plots shipment objects from the ontology. Include a logistics feed in your uploads \u2014 e.g. <span class="mono">supply_chain/fourkites_shipments.json</span> from the test corpus \u2014 and run the pipeline again.</div></div>';
  listEl.querySelectorAll("[data-id]").forEach((el) => {
    el.onclick = () => { location.hash = "#object/" + encodeURIComponent(el.getAttribute("data-id")); };
  });

  const cv = $("#globe-cv");
  if (!cv) return;
  const css = getComputedStyle(document.documentElement);
  const C = (n, fb) => (css.getPropertyValue(n) || fb).trim();
  const COL = { paper: C("--panel", "#faf7ef"), inset: C("--inset", "#ece4d2"), raised: C("--raised", "#e3d9c4"), ink: C("--ink", "#211c14"), ink3: C("--ink3", "#94886e"), ok: C("--ok", "#3f7d4e"), warn: C("--warn", "#a07416"), bad: C("--bad", "#b3382e") };
  const ctx = cv.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let W = 0, H = 0;
  function size() {
    W = cv.clientWidth; H = cv.clientHeight;
    cv.width = W * dpr; cv.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  size();
  let lon0 = 78, lat0 = 18, zoom = 1.12;
  if (ships.length) {
    lon0 = ships.reduce((a, s) => a + Number(s.geo.lon || 0), 0) / ships.length;
    lat0 = Math.max(-50, Math.min(55, ships.reduce((a, s) => a + Number(s.geo.lat || 0), 0) / ships.length));
  }
  let vLon = 0, vLat = 0, drag = null, hover = null, idle = 0;
  const D2R = Math.PI / 180;
  let R = 0, CX = 0, CY = 0;
  function proj(lat, lon) {
    const f = lat * D2R, l = (lon - lon0) * D2R, f0 = lat0 * D2R;
    const cosc = Math.sin(f0) * Math.sin(f) + Math.cos(f0) * Math.cos(f) * Math.cos(l);
    return [CX + R * Math.cos(f) * Math.sin(l),
            CY - R * (Math.cos(f0) * Math.sin(f) - Math.sin(f0) * Math.cos(f) * Math.cos(l)),
            cosc];
  }
  function strokeLonLat(pts) {
    ctx.beginPath();
    let pen = false;
    for (const p of pts) {
      const q = proj(p[1], p[0]);
      if (q[2] > 0.015) { if (pen) ctx.lineTo(q[0], q[1]); else { ctx.moveTo(q[0], q[1]); pen = true; } }
      else pen = false;
    }
    ctx.stroke();
  }
  function arc3(a, b, n) {
    const vec = (p) => { const f = p[0] * D2R, l = p[1] * D2R; return [Math.cos(f) * Math.cos(l), Math.cos(f) * Math.sin(l), Math.sin(f)]; };
    const A = vec(a), B = vec(b);
    const dot = Math.max(-1, Math.min(1, A[0] * B[0] + A[1] * B[1] + A[2] * B[2]));
    const w = Math.acos(dot) || 1e-6, sw = Math.sin(w) || 1e-6;
    const outPts = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n, k1 = Math.sin((1 - t) * w) / sw, k2 = Math.sin(t * w) / sw;
      const x = A[0] * k1 + B[0] * k2, y = A[1] * k1 + B[1] * k2, z = A[2] * k1 + B[2] * k2;
      outPts.push([Math.asin(Math.max(-1, Math.min(1, z))) / D2R, Math.atan2(y, x) / D2R]);
    }
    return outPts;
  }
  const markers = [];
  function draw() {
    R = (Math.min(W, H) / 2 - 16) * zoom; CX = W / 2; CY = H / 2;
    ctx.clearRect(0, 0, W, H);
    const gr = ctx.createRadialGradient(CX - R * 0.35, CY - R * 0.35, R * 0.15, CX, CY, R);
    gr.addColorStop(0, COL.paper); gr.addColorStop(1, COL.inset);
    ctx.beginPath(); ctx.arc(CX, CY, R, 0, Math.PI * 2);
    ctx.fillStyle = gr; ctx.fill();
    ctx.strokeStyle = COL.ink; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.strokeStyle = COL.raised; ctx.lineWidth = 0.7;
    for (let lo = -180; lo < 180; lo += 30) { const pts = []; for (let la = -85; la <= 85; la += 5) pts.push([lo, la]); strokeLonLat(pts); }
    for (let la = -60; la <= 60; la += 30) { const pts = []; for (let lo = -180; lo <= 180; lo += 5) pts.push([lo, la]); strokeLonLat(pts); }
    ctx.strokeStyle = COL.ink3; ctx.lineWidth = 1.15; ctx.lineJoin = "round";
    for (const c of WORLD) strokeLonLat(c);
    markers.length = 0;
    for (const s of ships) {
      const g = s.geo;
      if (g.origin && g.destination && g.origin[0] != null && g.destination[0] != null) {
        ctx.strokeStyle = COL.ink3; ctx.lineWidth = 1; ctx.setLineDash([2, 4]); ctx.globalAlpha = 0.8;
        ctx.beginPath();
        let pen = false;
        for (const p of arc3(g.origin, g.destination, 48)) {
          const q = proj(p[0], p[1]);
          if (q[2] > 0.015) { if (pen) ctx.lineTo(q[0], q[1]); else { ctx.moveTo(q[0], q[1]); pen = true; } }
          else pen = false;
        }
        ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
        const d = proj(g.destination[0], g.destination[1]);
        if (d[2] > 0.015) { ctx.fillStyle = COL.ink; ctx.fillRect(d[0] - 2, d[1] - 2, 4, 4); }
      }
      const m = proj(Number(g.lat), Number(g.lon));
      if (m[2] <= 0.015) continue;
      const st = (s.status || "").toUpperCase();
      const col = /DELAY|HOLD|EXCEPTION/.test(st) ? COL.bad : st === "DELIVERED" ? COL.ok : COL.warn;
      ctx.beginPath(); ctx.arc(m[0], m[1], 4.5, 0, Math.PI * 2);
      ctx.fillStyle = col; ctx.fill();
      ctx.strokeStyle = COL.paper; ctx.lineWidth = 1.2; ctx.stroke();
      if (st !== "DELIVERED") { ctx.beginPath(); ctx.arc(m[0], m[1], 8.5, 0, Math.PI * 2); ctx.strokeStyle = col; ctx.globalAlpha = 0.45; ctx.stroke(); ctx.globalAlpha = 1; }
      ctx.fillStyle = COL.ink; ctx.font = "10px ui-monospace, monospace";
      ctx.fillText((s.name || s.id).split(" \u00b7")[0].replace("ship:", ""), m[0] + 8, m[1] + 3);
      markers.push({ x: m[0], y: m[1], id: s.id, s: s });
    }
  }
  function frame() {
    if (!document.body.contains(cv)) return;
    if (!drag) {
      /* inertia - a thrown globe keeps spinning and eases out, google-earth feel */
      lon0 += vLon; lat0 = Math.max(-85, Math.min(85, lat0 + vLat));
      vLon *= 0.94; vLat *= 0.94;
      if (Math.abs(vLon) < 0.002 && Math.abs(vLat) < 0.002) { vLon = 0; vLat = 0; idle++; } else idle = 0;
      if (idle > 260 && !hover) lon0 += 0.04;
    }
    if (cv.clientWidth !== W || cv.clientHeight !== H) size();
    draw();
    requestAnimationFrame(frame);
  }
  cv.onmousedown = (e) => { drag = { x: e.clientX, y: e.clientY }; vLon = 0; vLat = 0; cv.style.cursor = "grabbing"; e.preventDefault(); };
  window.addEventListener("mousemove", (e) => {
    if (drag) {
      const k = 50 / R;
      const dLon = -(e.clientX - drag.x) * k;
      const dLat = (e.clientY - drag.y) * k;
      lon0 += dLon; lat0 = Math.max(-85, Math.min(85, lat0 + dLat));
      vLon = vLon * 0.4 + dLon * 0.6; vLat = vLat * 0.4 + dLat * 0.6;
      drag = { x: e.clientX, y: e.clientY };
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
  window.addEventListener("mouseup", () => { if (drag) { drag = null; cv.style.cursor = "grab"; } });
  cv.addEventListener("wheel", (e) => { e.preventDefault(); zoom = Math.max(0.9, Math.min(2.8, zoom * (e.deltaY < 0 ? 1.08 : 0.925))); }, { passive: false });
  cv.onclick = () => { if (hover) location.hash = "#object/" + encodeURIComponent(hover.id); };
  requestAnimationFrame(frame);
}
