"""DeepSeek client: OpenAI-compatible chat completions via stdlib urllib.

- temperature 0, JSON output mode, 3 retries with backoff
- every call disk-cached by sha256(model+system+user) => reruns are free
- token usage appended to pipeline/cost_log.jsonl
- reads DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL from pipeline/.env
- the API key is never printed and never written to any output file
"""
import hashlib
import json
import os
import time
import urllib.request

_PIPE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(_PIPE_DIR, ".cache")
COST_LOG = os.path.join(_PIPE_DIR, "cost_log.jsonl")


def _load_env():
    for envpath in (os.path.join(_PIPE_DIR, ".env"), ".env"):
        if os.path.exists(envpath):
            with open(envpath) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def _http_post(url, payload, headers, timeout=180):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def call(system, user):
    """Returns the assistant message content string. Disk-cached."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.sha256((MODEL + "\x00" + system + "\x00" + user).encode()).hexdigest()
    cpath = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["content"]
    if not API_KEY:
        raise RuntimeError(
            "DEEPSEEK_API_KEY not set. Copy .env.example to pipeline/.env and add your key."
        )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY,
    }
    last_err = None
    for attempt in range(3):
        try:
            data = _http_post(BASE_URL.rstrip("/") + "/chat/completions", payload, headers)
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            with open(COST_LOG, "a") as f:
                f.write(json.dumps({
                    "ts": time.time(),
                    "model": MODEL,
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                }) + "\n")
            with open(cpath, "w") as f:
                json.dump({"content": content}, f)
            return content
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 ** attempt * 2)
    raise RuntimeError(f"DeepSeek call failed after 3 attempts: {last_err}")


def _parse(content, key):
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        obj = json.loads(text)
    except Exception as e:  # noqa: BLE001
        return None, f"invalid JSON: {e}"
    if isinstance(obj, list):
        return obj, None
    items = obj.get(key)
    if items is None:
        return None, f"top-level object must contain key '{key}'"
    return items, None


def get_items(system, user, key, fields, label):
    """Call, parse, schema-validate; on failure re-prompt ONCE with the validator error."""
    from common import schemas

    content = call(system, user)
    items, err = _parse(content, key)
    if err is None:
        errs = schemas.validate_items(items, fields, label)
        err = "; ".join(errs[:6]) if errs else None
    if err is None:
        return items
    repair = (
        user
        + "\n\nYour previous output failed validation: "
        + err
        + '\nReturn corrected JSON only, as an object with the single key "'
        + key
        + '".'
    )
    content = call(system, repair)
    items, err = _parse(content, key)
    if err is None:
        errs = schemas.validate_items(items, fields, label)
        err = "; ".join(errs[:6]) if errs else None
    if err is None:
        return items
    raise RuntimeError(f"{label}: output invalid after repair attempt: {err}")


def get_checked_items(system, user, key, fields, label, source_text):
    """get_items + verbatim-quote verification with ONE repair re-prompt.

    Returns (good_items, dropped_items). Callers must quarantine dropped items
    loudly - never silently discard. The verbatim test lives in quotecheck and
    must never be loosened to make a failing run pass.
    """
    from common import quotecheck

    items = get_items(system, user, key, fields, label)
    bad = [it for it in items if it.get("quote") and not quotecheck.contains(source_text, it["quote"])]
    if not bad:
        return items, []
    repair = (
        user
        + "\n\nYour previous output contained quotes that are NOT verbatim excerpts of the provided text: "
        + json.dumps([b["quote"] for b in bad])
        + '\nEvery "quote" must be ONE contiguous verbatim excerpt copied exactly from the text between the --- markers.'
        + " Never use ellipsis (...) to join separate fragments; never quote this task description."
        + ' Return the FULL corrected JSON again, as an object with the single key "' + key + '".'
    )
    items = get_items(system, repair, key, fields, label)
    good = [it for it in items if not it.get("quote") or quotecheck.contains(source_text, it["quote"])]
    dropped = [it for it in items if it.get("quote") and not quotecheck.contains(source_text, it["quote"])]
    return good, dropped
