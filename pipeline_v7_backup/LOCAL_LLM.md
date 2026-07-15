# Run CLAUSE on your own hardware

CLAUSE's intelligence layer is deliberately small: it asks a language model to
read one clause or one datasheet block at a time and return structured JSON.
That is **text parsing, not reasoning at scale** — which means small, open
models running on an ordinary laptop are enough. No cloud, no API bill, no
document ever leaving your machine.

The verification itself (M4) and everything downstream (blast wave, margins,
vendors, linting, commissioning packs) is **pure deterministic Python — the
LLM is only used at the edges** (compiling spec text into rules, extracting
claims from submittals). That is why a 4B–8B model is genuinely sufficient.

## Minimum system requirements

| Setup | Works with |
|---|---|
| 8 GB RAM laptop (MacBook Air M1, any modern x86) | 4B models, e.g. `gemma3:4b`, `qwen3:4b` |
| 16 GB RAM | 8B models — better JSON discipline, e.g. `qwen3:8b`, `llama3.1:8b` |
| Any machine, no GPU | Works on CPU — slower per clause, same output |

Disk: ~3–5 GB per model. No GPU required; Apple-silicon and CUDA are used
automatically when present.

## Step 1 — install Ollama (macOS / Windows / Linux)

- **macOS:** download from [ollama.com/download](https://ollama.com/download) and open the app, or `brew install ollama`
- **Windows:** download the installer from [ollama.com/download](https://ollama.com/download)
- **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`

## Step 2 — pull a small model

```bash
ollama pull qwen3:4b     # or: gemma3:4b
```

Ollama automatically serves an **OpenAI-compatible endpoint** at:

```
http://localhost:11434/v1
```

## Step 3 — point CLAUSE at it

In the CLAUSE app, open **Settings → Bring your own model** and enter:

| Field | Value |
|---|---|
| Base URL | `http://localhost:11434/v1` |
| API key | `ollama` (any non-empty string) |
| Model | `qwen3:4b` |

Press **Test connection** — you should see a round-trip time and the model's
reply. The config is stored in `out/llm_config.json` on your machine only.

For the pipeline scripts, the same settings work via environment variables:

```bash
export DEEPSEEK_BASE_URL=http://localhost:11434/v1
export DEEPSEEK_API_KEY=ollama
export DEEPSEEK_MODEL=qwen3:4b
python3 m2_rules.py && python3 m3_claims.py && python3 m4_verify.py
```

## Alternatives

- **LM Studio** (macOS/Windows/Linux GUI): start the local server, use
  `http://localhost:1234/v1`.
- **llama.cpp**: `llama-server -m model.gguf --port 8080`, use
  `http://localhost:8080/v1`.
- **Any OpenAI-compatible provider**: paste its base URL, key, and model name
  — CLAUSE is provider-agnostic by design.

## Privacy note

With a local model, the complete chain — parsing, rule compilation, claim
extraction, verification, consequence pricing — runs on your own hardware.
Only isolated clause snippets are ever sent to the model, and with Ollama
that model is on your laptop. Nothing leaves the machine.
