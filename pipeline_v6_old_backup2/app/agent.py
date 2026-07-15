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
import urllib.request

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
    fac = _load("facility.json") or {}
    docs = [name for name, _ in _docs()]
    rules = sum(len((_load(os.path.basename(p)) or {}).get("rules", []))
                for p in glob.glob(os.path.join(OUT, "rulebook_*.json")))
    disp = (_load("dispositions.json") or {}).get("queue", [])
    blast = _load("blast_wave.json") or {}
    return {
        "documents_parsed": docs,
        "rules_compiled": rules,
        "open_deviations": len(disp),
        "addendum_waves": len(blast.get("waves", [])),
        "facility_rating_declared": (fac.get("tier") or {}).get("declared"),
        "model": s.get("model"),
        "site_pages": {
            "hub": "upload + project state", "overview": "ledger totals",
            "queue": "deviation queue by severity", "review": "spec vs submittal, claim by claim",
            "clock": "decision windows from schedule float", "graph": "the connected ledger graph",
            "facility": "data-centre profile: tier, redundancy, standards",
            "blast": "what each addendum changed", "margins": "how close each claim is to its limit",
            "vendors": "per-vendor trust ledger", "paperwork": "drafted letters/RFIs/NCRs",
            "cx": "commissioning readiness", "ncr": "non-conformance register",
        },
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


PAGE_ARTIFACTS = {
    "overview": lambda: _load("dispositions.json"), "queue": lambda: _load("dispositions.json"),
    "clock": lambda: _load("options.json"), "margins": lambda: _load("margins.json"),
    "vendors": lambda: _load("vendors.json"), "blast": lambda: _load("blast_wave.json"),
    "cx": lambda: _load("cx_packs.json"), "lint": lambda: _load("lint.json"),
    "paperwork": lambda: _load("paperwork_index.json"), "facility": lambda: _load("facility.json"),
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
}

TOOLS = [
    {"type": "function", "function": {"name": "project_overview", "description": "What is loaded: documents, rule/deviation counts, facility rating, and what every site page shows.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "search_documents", "description": "Keyword (grep-style) search across every parsed page of the uploaded documents. Use precise project vocabulary; all terms must co-occur.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "read_document", "description": "Read one page of a parsed document verbatim.", "parameters": {"type": "object", "properties": {"doc": {"type": "string"}, "page": {"type": "integer"}}, "required": ["doc"]}}},
    {"type": "function", "function": {"name": "lookup_id", "description": "Exact lookup of a rule ID, package ID, PO number, activity, test ID, or graph node.", "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {"name": "get_page_data", "description": "The exact JSON a site page renders (queue, clock, margins, vendors, blast, cx, lint, paperwork, facility).", "parameters": {"type": "object", "properties": {"page": {"type": "string"}}, "required": ["page"]}}},
]

SYSTEM = (
    "You are the CLAUSE copilot - the AI layer over a data-centre EPC requirement ledger "
    "built ONLY from the user's uploaded project documents (specifications, vendor submittals, "
    "addenda, registers). Answer by calling tools. Never state a project fact a tool did not "
    "return; if the ledger has nothing, say so plainly. Cite sources inline like "
    "(spec_26_33_53 p.2) or by ID (R-26-33-53-07, PO-0113, CX-L4-012). When a site page shows "
    "the answer, name it (e.g. 'the margins page ranks these'). Engineering tone: short, "
    "concrete, no filler, no hedging. Prefer bullets. Currency is INR."
)


# ------------------------------------------------------------------- loop
def _post(url, payload, key, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _cached_completion(cfg, messages):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256((cfg["model"] + "\x00agent\x00" + json.dumps(messages, sort_keys=True)).encode()).hexdigest()
    cpath = os.path.join(CACHE, "agent_" + key + ".json")
    if os.path.exists(cpath):
        return json.load(open(cpath)), True
    if not cfg.get("api_key"):
        raise AgentError("The copilot makes live model calls. Add your API key in Settings "
                         "(written to pipeline/.env). Previously asked questions replay from "
                         "the local cache without a key; new ones cannot.")
    payload = {"model": cfg["model"], "messages": messages, "tools": TOOLS, "temperature": 0}
    data = _post(cfg["base_url"].rstrip("/") + "/chat/completions", payload, cfg["api_key"])
    msg = data["choices"][0]["message"]
    json.dump(msg, open(cpath, "w"))
    return msg, False


def run_agent(message, history, cfg):
    """history: [{role, content}...] (user/assistant only). Returns reply + tool trace."""
    messages = [{"role": "system", "content": SYSTEM}]
    for h in (history or [])[-8:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({"role": "user", "content": str(message)[:2000]})
    steps = []
    for _ in range(MAX_STEPS):
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
            impl = TOOL_IMPL.get(name)
            result = impl(args) if impl else {"error": "unknown tool"}
            arg_note = ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items())
            note = ""
            if isinstance(result, dict):
                if "hits" in result:
                    note = f"{len(result['hits'])} hit(s)"
                elif "matches" in result and isinstance(result["matches"], list):
                    note = f"{len(result['matches'])} match(es)"
            steps.append({"tool": name, "args": arg_note, "note": note, "cached": cached})
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""),
                             "content": json.dumps(result)[:12000]})
    return {"reply": "Stopped after " + str(MAX_STEPS) + " tool steps - ask a narrower question.",
            "steps": steps, "model": cfg["model"]}
