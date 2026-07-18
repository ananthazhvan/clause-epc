"""CLAUSE copilot - a small agentic harness over the project ledger.

The AI layer on top of the connected data: natural-language questions answered
by a tool-calling model. Retrieval is exact-match/keyword (grep-style) because
project data is precise - rule IDs, PO numbers, clause numbers - plus direct
reads of the same JSON artifacts the site pages render, so the copilot sees
exactly what the user sees, never more.

Honesty contract:
  - the model may only state what tools return; the system prompt forbids
    invention and demands doc/page/ID citations
  - completions are disk-cached in .cache/ like every other LLM call
    (sha256 of model+conversation) so a scripted demo replays free;
    NEW questions require a live key in pipeline/.env
"""
import glob
import hashlib
import json
import os
import re
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PIPELINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PIPELINE, "out")
CACHE = os.path.join(PIPELINE, ".cache")
MAX_STEPS = 8


class AgentError(RuntimeError):
    pass


# ------------------------------------------------------------------- tools
def _load(path):
    p = os.path.join(OUT, path)
    return json.load(open(p)) if os.path.exists(p) else None


def _trunc(obj, list_cap=40, str_cap=400, depth=0):
    if isinstance(obj, dict):
        return {k: _trunc(v, list_cap, str_cap, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        extra = len(obj) - list_cap
        out = [_trunc(x, list_cap, str_cap, depth + 1) for x in obj[:list_cap]]
        if extra > 0:
            out.append(f"... {extra} more item(s) truncated")
        return out
    if isinstance(obj, str) and len(obj) > str_cap:
        return obj[:str_cap] + "..."
    return obj


def _docs():
    for p in sorted(glob.glob(os.path.join(OUT, "doc_*.json"))):
        try:
            d = json.load(open(p))
            yield d.get("doc") or os.path.basename(p)[4:-5], d.get("pages") or []
        except Exception:
            continue


def t_project_overview():
    s = _load("project.json") or {}
    onto = _load("ontology.json") or {}
    docs = [name for name, _ in _docs()]
    rules = sum(len((_load(os.path.basename(p)) or {}).get("rules", []))
                for p in glob.glob(os.path.join(OUT, "rulebook_*.json")))
    disp = (_load("dispositions.json") or {}).get("queue", [])
    totals = (onto.get("project") or {}).get("totals") or {}
    return {
        "documents_parsed": docs,
        "rules_compiled": rules,
        "open_deviations": len(disp),
        "ontology": {"totals": totals,
                     "object_types": {t.get("type"): t.get("count") for t in (onto.get("types") or [])},
                     "cert_readiness": onto.get("cert")},
        "model": s.get("model"),
        "site_pages": {
            "hub": "upload + project state + data sources",
            "objects": "every real-world object: sections, packages, POs, vendors, shipments, activities, cx tests, quality issues, RFIs",
            "graph": "the ontology graph - every node is an object, every edge a typed relationship",
            "globe": "shipments on the world globe: position, ETA, delays, addendum impact",
            "review": "the ledger: spec vs submittal, claim by claim",
            "queue": "deviation queue by severity",
            "cx": "commissioning readiness",
            "ncr": "non-conformance register",
            "paperwork": "drafted letters/RFIs/NCRs",
        },
        "note": "these are ALL the site pages; answer object questions with get_object / list_objects",
    }


def t_search_documents(query):
    terms = [t for t in re.split(r"\s+", (query or "").lower()) if t]
    if not terms:
        return {"hits": []}
    hits = []
    for name, pages in _docs():
        for pg in pages:
            lines = (pg.get("text") or "").split("\n")
            for i, ln in enumerate(lines):
                window = " ".join(lines[max(0, i - 1):i + 2]).lower()
                if all(t in window for t in terms):
                    snip = re.sub(r"\s+", " ", " / ".join(lines[max(0, i - 1):i + 2]))[:260]
                    hits.append({"doc": name, "page": pg.get("page"), "snippet": snip})
                    break  # one hit per page is enough
        if len(hits) >= 12:
            break
    return {"hits": hits[:12], "note": "keyword search over every parsed page"}


def t_read_document(doc, page=1):
    for name, pages in _docs():
        if name == doc or name.startswith(str(doc)):
            for pg in pages:
                if pg.get("page") == int(page):
                    return {"doc": name, "page": page, "pages_total": len(pages),
                            "text": (pg.get("text") or "")[:4000]}
            return {"error": f"{name} has {len(pages)} page(s)"}
    return {"error": "document not found", "documents": [n for n, _ in _docs()]}


def t_lookup_id(ident):
    ident = (ident or "").strip()
    found = []
    for p in glob.glob(os.path.join(OUT, "rulebook_*.json")):
        for r in (json.load(open(p)).get("rules") or []):
            if ident.lower() in str(r.get("rule_id", "")).lower():
                found.append({"kind": "rule", "record": _trunc(r, 10, 300)})
    for p in glob.glob(os.path.join(OUT, "claims_*.json")):
        d = json.load(open(p))
        for c in (d.get("claims") or []):
            if ident.lower() in json.dumps(c).lower()[:600]:
                found.append({"kind": "claim", "package": d.get("package"), "record": _trunc(c, 10, 300)})
            if len(found) > 10:
                break
    for item in (_load("dispositions.json") or {}).get("queue", []):
        if ident.lower() in json.dumps(item).lower()[:600]:
            found.append({"kind": "disposition", "record": _trunc(item, 10, 300)})
    g = _load("graph.json") or {}
    for n in g.get("nodes", []):
        if ident.lower() in str(n.get("id", "")).lower() or ident.lower() in str(n.get("label", "")).lower():
            found.append({"kind": "graph node", "record": n})
    return {"matches": found[:10] or "nothing in the ledger matches this identifier"}


def _ncr_rows():
    p = os.path.join(OUT, "ncr_register.csv")
    if not os.path.exists(p):
        return None
    import csv as _csv
    return {"ncrs": list(_csv.DictReader(open(p)))}


PAGE_ARTIFACTS = {
    "hub": lambda: t_project_overview(),
    "queue": lambda: _load("dispositions.json"),
    "review": lambda: _load("deviation_register.json"),
    "cx": lambda: _load("cx_packs.json"),
    "ncr": _ncr_rows,
    "paperwork": lambda: _load("paperwork_index.json"),
    "objects": lambda: _load("ontology.json"),
    "graph": lambda: _load("ontology.json"),
    "globe": lambda: _load("ontology.json"),
}


def t_get_page_data(page):
    fn = PAGE_ARTIFACTS.get((page or "").strip().lower())
    if not fn:
        return {"error": "unknown page", "pages": sorted(PAGE_ARTIFACTS)}
    return _trunc(fn() or {"note": "this page has no data in the current run"})


TOOL_IMPL = {
    "project_overview": lambda args: t_project_overview(),
    "search_documents": lambda args: t_search_documents(args.get("query", "")),
    "read_document": lambda args: t_read_document(args.get("doc", ""), args.get("page", 1)),
    "lookup_id": lambda args: t_lookup_id(args.get("id", "")),
    "get_page_data": lambda args: t_get_page_data(args.get("page", "")),
    "get_object": lambda args: t_get_object(args.get("id", "")),
    "list_objects": lambda args: t_list_objects(args.get("type", "")),
}

TOOLS = [
    {"type": "function", "function": {"name": "project_overview", "description": "What is loaded: documents, rule/deviation counts, ontology totals, certification readiness, and the full list of site pages with what each shows.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "search_documents", "description": "Keyword (grep-style) search across every parsed page of the uploaded documents. Use precise project vocabulary; all terms must co-occur.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "read_document", "description": "Read one page of a parsed document verbatim.", "parameters": {"type": "object", "properties": {"doc": {"type": "string"}, "page": {"type": "integer"}}, "required": ["doc"]}}},
    {"type": "function", "function": {"name": "lookup_id", "description": "Exact lookup of a rule ID, package ID, PO number, activity, test ID, or graph node.", "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {"name": "get_page_data", "description": "The exact JSON a site page renders. Pages: hub, queue, review, cx, ncr, paperwork, objects, graph, globe.", "parameters": {"type": "object", "properties": {"page": {"type": "string"}}, "required": ["page"]}}},
    {"type": "function", "function": {"name": "get_object", "description": "Open one ontology object (section, submittal package, PO, vendor, shipment, activity, cx test, quality issue, addendum) with all its properties, money, insights, and typed links to other objects. Pass an id like 'po:PO-4500012304' or any unique name fragment like 'CH-A2' or 'CryoCore'.", "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {"name": "list_objects", "description": "List ontology objects, optionally filtered by type: section, package, po, vendor, shipment, activity, cx, quality, rfi, addendum. Returns ids, statuses, money, and insight counts plus project totals.", "parameters": {"type": "object", "properties": {"type": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "investigate", "description": "Multi-agent orchestration: spawn up to 3 parallel subagents, each investigating one focused question over the ontology and documents (e.g. one per vendor, per shipment, per spec section). Use for broad questions that span several objects. Returns every agent's findings for you to merge.", "parameters": {"type": "object", "properties": {"tasks": {"type": "array", "items": {"type": "object", "properties": {"focus": {"type": "string"}, "question": {"type": "string"}}, "required": ["question"]}}}, "required": ["tasks"]}}},
]

SYSTEM = (
    "You are the CLAUSE copilot - the AI layer over a project ontology compiled ONLY from "
    "the user's uploaded documents and connected feeds (specifications, vendor submittals, "
    "addenda, registers, ERP purchase orders, logistics tracking, QMS issues). Every "
    "real-world thing is an object with typed links: spec sections, submittal packages, POs, "
    "vendors, shipments, schedule activities, commissioning tests, quality issues. For "
    "questions about a thing (where is it, does it comply, what does it cost, who supplies "
    "it, what does it affect), prefer get_object / list_objects and walk the links. Use "
    "search_documents / read_document for verbatim clause text. Never state a project fact a "
    "tool did not return; if the ontology has nothing, say so plainly. Cite object ids "
    "(po:PO-0113, ship:SHP-88121, package:SUB-263353-01-R0) and doc pages like "
    "(spec_26_33_53 p.2). For broad questions that span several objects, call investigate "
    "to fan out up to 3 parallel subagents and merge their findings. Engineering tone: "
    "short, concrete, no filler, no hedging. Prefer bullets. Currency is INR."
)


def t_get_object(oid):
    onto = _load("ontology.json") or {}
    objs = onto.get("objects", [])
    ql = str(oid).strip().lower()
    if not ql:
        return {"error": "pass an object id or name fragment"}
    hits = ([o for o in objs if o["id"].lower() == ql]
            or [o for o in objs if ql in o["id"].lower() or ql in str(o.get("name", "")).lower()])
    if not hits:
        return {"error": f"no ontology object matches '{oid}' - try list_objects"}
    x = json.loads(json.dumps(hits[0]))
    byid = {o["id"]: o for o in objs}
    x["links"] = []
    for l in onto.get("links", []):
        if l["s"] == x["id"] or l["t"] == x["id"]:
            other = l["t"] if l["s"] == x["id"] else l["s"]
            n = byid.get(other, {})
            x["links"].append({"rel": l["rel"], "dir": "out" if l["s"] == x["id"] else "in",
                               "id": other, "name": n.get("name"), "status": n.get("status")})
    if len(hits) > 1:
        x["other_matches"] = [o["id"] for o in hits[1:6]]
    return _trunc(x, list_cap=60)


def t_list_objects(otype=""):
    onto = _load("ontology.json") or {}
    objs = onto.get("objects", [])
    if otype:
        objs = [o for o in objs if o.get("type") == str(otype).strip()]
    return _trunc({"count": len(objs), "types": onto.get("types"),
                   "totals": (onto.get("project") or {}).get("totals"),
                   "cert": onto.get("cert"),
                   "objects": [{"id": o["id"], "name": o.get("name"), "status": o.get("status"),
                                "value_inr": (o.get("money") or {}).get("value_inr"),
                                "at_risk_inr": (o.get("money") or {}).get("at_risk_inr"),
                                "insights": len(o.get("insights") or [])} for o in objs]},
                  list_cap=150)


# ------------------------------------------------------------------- loop
def _post(url, payload, key, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _cached_completion(cfg, messages, tools=None):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256((cfg["model"] + "\x00agent\x00" + json.dumps(messages, sort_keys=True)).encode()).hexdigest()
    cpath = os.path.join(CACHE, "agent_" + key + ".json")
    if os.path.exists(cpath):
        return json.load(open(cpath)), True
    if not cfg.get("api_key"):
        raise AgentError("The copilot makes live model calls. Add your API key in Settings "
                         "(written to pipeline/.env). Previously asked questions replay from "
                         "the local cache without a key; new ones cannot.")
    payload = {"model": cfg["model"], "messages": messages,
               "tools": tools if tools is not None else TOOLS, "temperature": 0}
    data = _post(cfg["base_url"].rstrip("/") + "/chat/completions", payload, cfg["api_key"])
    msg = data["choices"][0]["message"]
    json.dump(msg, open(cpath, "w"))
    return msg, False


def _step_label(name, args):
    """Human-readable label for a tool call, shown live in the copilot UI."""
    if name == "project_overview":
        return "Reading the project overview"
    if name == "search_documents":
        q = str(args.get("query", ""))[:60]
        return f"Searching documents for \u201c{q}\u201d"
    if name == "read_document":
        doc = str(args.get("doc", "document"))
        return f"Reading {doc} \u00b7 page {args.get('page', 1)}"
    if name == "lookup_id":
        return f"Looking up \u201c{str(args.get('id', ''))[:40]}\u201d in the ledger"
    if name == "get_page_data":
        return f"Pulling the {args.get('page', '?')} page data"
    if name == "get_object":
        return f"Opening object \u201c{str(args.get('id', ''))[:40]}\u201d"
    if name == "list_objects":
        return f"Listing {args.get('type') or 'all'} objects"
    if name == "investigate":
        return f"Orchestrating {len(args.get('tasks') or [])} subagent(s)"
    return name


# ------------------------------------------------- multi-agent orchestration
SUB_SYSTEM = (
    "You are a CLAUSE subagent investigating ONE focused question over the project "
    "ontology and documents. Use tools to gather evidence, then answer in at most 6 "
    "bullets with object ids (po:..., ship:..., package:...) and doc/page citations. "
    "Only facts a tool returned. No filler."
)
SUB_TOOLS = [t for t in TOOLS if t["function"]["name"] in
             ("get_object", "list_objects", "search_documents", "read_document", "lookup_id")]
SUB_MAX_STEPS = 5


def _sub_agent(idx, task, cfg, send):
    focus = str(task.get("focus") or f"task {idx}")[:80]
    question = str(task.get("question") or focus)[:500]
    messages = [{"role": "system", "content": SUB_SYSTEM},
                {"role": "user", "content": question}]
    trace = []
    for _ in range(SUB_MAX_STEPS):
        try:
            msg, _cached = _cached_completion(cfg, messages, tools=SUB_TOOLS)
        except AgentError as e:
            return {"agent": idx, "focus": focus, "error": str(e)}
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"agent": idx, "focus": focus,
                    "findings": msg.get("content") or "(nothing found)", "steps": trace}
        messages.append(msg)
        for c in calls:
            name = c.get("function", {}).get("name", "")
            try:
                args = json.loads(c.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            label = f"Agent {idx} \u00b7 {_step_label(name, args)}"
            send({"event": "step_start", "tool": "subagent", "label": label, "args": focus})
            impl = TOOL_IMPL.get(name)
            result = impl(args) if impl else {"error": "unknown tool"}
            trace.append(_step_label(name, args))
            send({"event": "step_done", "tool": "subagent", "label": label,
                  "args": focus, "note": "", "cached": False})
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""),
                             "content": json.dumps(result)[:9000]})
    return {"agent": idx, "focus": focus,
            "findings": "(subagent hit its step limit - findings above are partial)", "steps": trace}


def _investigate(tasks, cfg, send):
    tasks = [t if isinstance(t, dict) else {"question": str(t)} for t in (tasks or [])][:3]
    if not tasks:
        return {"error": "pass 1-3 tasks: [{focus, question}]"}
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        results = list(ex.map(lambda p: _sub_agent(p[0] + 1, p[1], cfg, send), enumerate(tasks)))
    return {"subagents": results,
            "note": "merge these findings into one answer, keeping each agent's citations"}


def run_agent(message, history, cfg, emit=None, page=None):
    """history: [{role, content}...] (user/assistant only). Returns reply + tool trace.

    emit, when provided, receives live events so the UI can relay every tool
    call as it happens instead of staying silent until the final answer:
      {"event": "thinking"}                          - model is composing
      {"event": "step_start", "tool", "label", ...}  - tool call begins
      {"event": "step_done",  "tool", "label", ...}  - tool call finished
    The return value is unchanged, so the non-streaming /api/agent endpoint
    keeps working exactly as before.
    """
    _raw = emit or (lambda ev: None)
    _lk = threading.Lock()

    def send(ev):
        with _lk:
            _raw(ev)
    messages = [{"role": "system", "content": SYSTEM}]
    if page:
        messages.append({"role": "system",
                         "content": f"The user is currently looking at the '{page}' page of the site."})
    for h in (history or [])[-8:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({"role": "user", "content": str(message)[:2000]})
    steps = []
    for _ in range(MAX_STEPS):
        send({"event": "thinking"})
        msg, cached = _cached_completion(cfg, messages)
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"reply": msg.get("content") or "(no reply)", "steps": steps, "model": cfg["model"]}
        messages.append(msg)
        for c in calls:
            name = c.get("function", {}).get("name", "")
            try:
                args = json.loads(c.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            label = _step_label(name, args)
            arg_note = ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items())
            send({"event": "step_start", "tool": name, "label": label, "args": arg_note})
            if name == "investigate":
                result = _investigate(args.get("tasks") or [], cfg, send)
            else:
                impl = TOOL_IMPL.get(name)
                result = impl(args) if impl else {"error": "unknown tool"}
            note = ""
            if isinstance(result, dict):
                if "hits" in result:
                    note = f"{len(result['hits'])} hit(s)"
                elif "matches" in result and isinstance(result["matches"], list):
                    note = f"{len(result['matches'])} match(es)"
            step = {"tool": name, "label": label, "args": arg_note, "note": note, "cached": cached}
            steps.append(step)
            send({"event": "step_done", **step})
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""),
                             "content": json.dumps(result)[:12000]})
    return {"reply": "Stopped after " + str(MAX_STEPS) + " tool steps - ask a narrower question.",
            "steps": steps, "model": cfg["model"]}
