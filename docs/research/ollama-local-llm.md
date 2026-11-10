# Ollama on an RTX 4060 (8 GB): structured output, tool calling, vision

Research for GitHub issue #6. Read on 2026-11-10 from primary sources only (Ollama docs and source code, Ollama blog, Ollama model library). Library pages change often; re-check tags before pinning a model. "Not confirmed" marks anything no primary source states.

## Summary

- Text + tools shortlist for an 8 GB card: `qwen3:4b` (2.5 GB), `qwen3:8b` (5.2 GB), `llama3.1:8b` (4.9 GB), `qwen2.5:7b` (4.7 GB), `phi4-mini` (2.5 GB), `llama3.2:3b` (2.0 GB). All carry the library `tools` tag.
- One model with tools AND vision (both library tags): `qwen3-vl:4b` (3.3 GB) or `qwen3-vl:8b` (6.2 GB), `qwen3.5:4b` or `qwen3.5:9b` (6.6-7.6 GB, tight), `ministral-3:3b` (3.0 GB) or `ministral-3:8b` (6.0 GB), `gemma4:e4b`. `gemma3`, `qwen2.5vl`, `llama3.2-vision` (7.8 GB) and `moondream` (2K context) are vision-only (no `tools` tag).
- Structured output works on both endpoints. `/v1/chat/completions` accepts `response_format` `json_schema`, but Ollama reads only `json_schema.schema` (`name` and `strict` are dropped, per `openai.go`). Native `/api/chat` `format=<schema>` is the documented primary path. Docs advise also putting the schema in the prompt and using temperature 0.
- Tools work on both endpoints, but `tool_choice` is explicitly unsupported on `/v1` and undocumented natively. You cannot force a tool call; prompt for it and validate in the client.
- Vision works on both endpoints, base64 only. `/v1` takes `image_url` as a `data:image/{png,jpeg,jpg,webp};base64,...` data URL (http(s) URLs are rejected); native takes a base64 `images` array. No vision VRAM or latency numbers are documented.
- Defaults to override: context is 4096 tokens on <24 GiB VRAM, models unload after 5 minutes idle, and `/v1` cannot set `num_ctx` or `keep_alive` per request (use a Modelfile or env vars). No server-side request timeout is documented; set the client timeout yourself.
- Recommended: build `OpenAICompatibleProvider` on `/v1` (portable), configure model, `num_ctx` (8K-16K) and `OLLAMA_KEEP_ALIVE` server-side, use `stream: false` for structured calls, and keep a native `/api/chat` path as a fallback if `/v1` gaps bite.

## 1. Endpoint capabilities: `/v1/chat/completions` vs `/api/chat`

OpenAI-compatibility page ([docs](https://docs.ollama.com/api/openai-compatibility), source [openai-compatibility.mdx](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx)) lists for `/v1/chat/completions`:

- Supported features: chat completions, streaming, JSON mode, reproducible outputs, vision, tools, reasoning/thinking control. Not supported: logprobs.
- Supported fields: `model`, `messages` (text, base64 image, content-part arrays), `frequency_penalty`, `presence_penalty`, `response_format`, `seed`, `stop`, `stream`, `stream_options.include_usage`, `temperature`, `top_p`, `max_tokens`, `tools`, `reasoning_effort`, `reasoning.effort`.
- Unsupported: `tool_choice`, `logit_bias`, `user`, `n`, and image URLs.

How `response_format` is handled ([openai/openai.go](https://github.com/ollama/ollama/blob/main/openai/openai.go)): `json_object` becomes native `format: "json"`; `json_schema` becomes native `format: <json_schema.schema>`; other types are ignored. The `JsonSchema` struct has only a `schema` field, so `name` and `strict` are discarded (my reading of the struct; the docs never mention `strict`). Treat strictness as always on via constrained decoding, not as a toggle.

Native `/api/chat` ([docs](https://docs.ollama.com/api/chat)): `format` is "`json` or a JSON schema"; `tools` is a function-tool array; `options` carries `num_ctx`, `num_predict`, `temperature`, `seed`; `keep_alive`, `think`, `stream` (default true) are request fields. Message fields: `images` (base64), `tool_calls`, and `tool_name` on tool results (shown on the [tool calling](https://docs.ollama.com/capabilities/tool-calling) page).

| Need | `/v1/chat/completions` | `/api/chat` |
|---|---|---|
| JSON schema output | Works, mapped to `format`. Blog shows `client.beta.chat.completions.parse` with Pydantic ([blog](https://ollama.com/blog/structured-outputs)). | Documented primary path ([structured outputs](https://docs.ollama.com/capabilities/structured-outputs)). |
| Tools | Supported ([tool support blog](https://ollama.com/blog/tool-support)); arguments are a JSON string. | Documented primary path; arguments are a JSON object. |
| `tool_choice` | Unsupported. | Not documented; blog lists "tool choice" as future work. |
| Per-request `num_ctx`, `keep_alive` | No. Docs: use a Modelfile `PARAMETER num_ctx`. | Yes (`options.num_ctx`, `keep_alive`). |
| Streaming + tools | Streaming supported; tool streaming not confirmed for `/v1`. | Documented ([blog](https://ollama.com/blog/streaming-tool)): accumulate `thinking`, `content`, `tool_calls`. |

Verdict: native is better documented and more complete; `/v1` is adequate for a single-agent MVP and keeps provider portability. No primary source compares their reliability, so this is a judgement from documentation completeness, not a measurement.

Not confirmed: whether `tools` and a `format` schema can be combined in one request with predictable behaviour; no doc addresses it. Safer: run the tool loop, then get the final answer as a schema-constrained call (or parse and validate against the schema).

## 2. Model candidates for <= 8 GB VRAM

From library pages (`https://ollama.com/library/<model>`), read 2026-11-10. Download size is the default-quant weights file; runtime VRAM is larger (KV cache, vision encoder). Context is the model maximum, not Ollama's default (section 4).

| Model | Tag | Download | Context | Tools | Vision |
|---|---|---|---|---|---|
| Qwen3 | `qwen3:4b` | 2.5 GB | 256K | yes | no |
| Qwen3 | `qwen3:8b` (latest) | 5.2 GB | 40K | yes | no |
| Llama 3.1 | `llama3.1:8b` (latest) | 4.9 GB | 128K | yes | no |
| Qwen2.5 | `qwen2.5:7b` | 4.7 GB | 32K | yes | no |
| Mistral 7B v0.3 | `mistral:7b` | 4.4 GB | 32K | yes | no |
| Phi-4-mini | `phi4-mini:3.8b` | 2.5 GB | 128K | yes | no |
| Llama 3.2 | `llama3.2:3b` | 2.0 GB | 128K | yes | no |
| Gemma 3 | `gemma3:4b` (latest) | 3.4 GB | 128K | no tag | yes |
| Gemma 3 | `gemma3:12b` | 8.2 GB | 128K | no tag | yes (too big) |
| Gemma 4 | `gemma4:e4b` | 6.6-9.5 GB (range as shown) | 128K | yes | yes |
| Qwen3-VL | `qwen3-vl:4b` | 3.3 GB | 256K | yes | yes |
| Qwen3-VL | `qwen3-vl:8b` (latest) | 6.2 GB | 256K | yes | yes |
| Qwen3.5 | `qwen3.5:4b` | 3.3-4.0 GB | 256K | yes | yes |
| Qwen3.5 | `qwen3.5:9b` (latest) | 6.6-7.6 GB | 256K | yes | yes |
| Ministral 3 | `ministral-3:3b` | 3.0 GB | 256K | yes | yes |
| Ministral 3 | `ministral-3:8b` (latest) | 6.0 GB | 256K | yes | yes |
| Qwen2.5-VL | `qwen2.5vl:7b` | 6.0 GB | 125K | no tag | yes |
| Llama 3.2 Vision | `llama3.2-vision:11b` | 7.8 GB | 128K | no tag | yes (too big) |
| Moondream | `moondream:1.8b` | 1.7 GB | 2K | no tag | yes |

Pages: [qwen3](https://ollama.com/library/qwen3), [llama3.1](https://ollama.com/library/llama3.1), [qwen2.5](https://ollama.com/library/qwen2.5), [mistral](https://ollama.com/library/mistral), [phi4-mini](https://ollama.com/library/phi4-mini), [llama3.2](https://ollama.com/library/llama3.2), [gemma3](https://ollama.com/library/gemma3), [gemma4](https://ollama.com/library/gemma4), [qwen3-vl](https://ollama.com/library/qwen3-vl), [qwen3.5](https://ollama.com/library/qwen3.5), [ministral-3](https://ollama.com/library/ministral-3), [qwen2.5vl](https://ollama.com/library/qwen2.5vl), [llama3.2-vision](https://ollama.com/library/llama3.2-vision), [moondream](https://ollama.com/library/moondream).

Caveats:

- Fit: weights plus KV cache must fit in 8 GB, so aim for a download of about 5-6 GB or less with a 4-16K context. Ollama "evaluates the required VRAM for the model against what is currently available" and splits to CPU if needed; `ollama ps` shows the split ([FAQ](https://docs.ollama.com/faq), [context length](https://docs.ollama.com/context-length)). No primary source gives per-model VRAM for the 4060, so exact fit is not confirmed.
- `qwen3` and `qwen3.5` carry a `thinking` tag; thinking is controllable (`think` natively, `reasoning_effort` on `/v1`). Interaction of thinking with `format` is undocumented; test it.
- The `tools` tag is the only primary signal for tool support. "Reliable JSON" has no tag; schema enforcement is an engine feature, not per model, but content quality still varies. No per-model reliability benchmark from Ollama was found.
- `mistral:latest` is v0.3 from 05/22/2024, the oldest entry. Gemma 4, Qwen3.5 and Ministral 3 were read from library tags only; check their pages (licence, notes) before adopting.
- The qwen3 library page shows `4b` at 256K and `8b` at 40K; the reason is not stated on the page.

## 3. Vision

Models with the `vision` tag are in the table. Tools plus vision in one model: qwen3-vl, qwen3.5, ministral-3, gemma4. Note: llama3.2-vision states "for image+text applications, English is the only language supported" ([page](https://ollama.com/library/llama3.2-vision)).

- Native `/api/chat`: `images: ["<base64>"]` on the message; REST needs base64, SDKs take paths or bytes ([vision docs](https://docs.ollama.com/capabilities/vision)). Size/resolution limits: not documented.
- `/v1/chat/completions`: content part `image_url` with a base64 data URL. The docs' example passes `image_url` as a bare string; the code accepts both a bare string and `{"url": ...}`, rejects http(s) with "image URLs are not currently supported, please use base64 encoded data instead", and accepts only `data:;base64,` or `data:image/{jpeg,jpg,png,webp};base64,` prefixes (`decodeImageURL` in [openai.go](https://github.com/ollama/ollama/blob/main/openai/openai.go)). The `openai` SDK's object form works.
- Vision with `format` is documented (a `gemma4` example on the structured-outputs page).
- Images per message: not documented.
- VRAM/latency: no primary numbers. On 8 GB, 3-4B vision models (`qwen3-vl:4b`, `ministral-3:3b`) are the realistic choice; 6-7.6 GB models will likely spill to CPU at useful context (inference, not documented). Measure with `load_duration`, `prompt_eval_duration`, `eval_duration` in native responses ([chat API](https://docs.ollama.com/api/chat)).

## 4. Timeouts, streaming, context, keep-alive

- `keep_alive`: default 5 minutes; `0` unloads at once; negative keeps loaded; per-request value on `/api/chat` and `/api/generate` overrides `OLLAMA_KEEP_ALIVE` ([FAQ](https://docs.ollama.com/faq)). `/v1` does not list it, so set `OLLAMA_KEEP_ALIVE` server-side to avoid cold reloads. Cold-load time: not documented.
- `num_ctx`: default 4096 ([FAQ](https://docs.ollama.com/faq)); by VRAM: <24 GiB 4k, 24-48 GiB 32k, >=48 GiB 256k ([context length](https://docs.ollama.com/context-length)). Override: `OLLAMA_CONTEXT_LENGTH`, `options.num_ctx` (native), or Modelfile `PARAMETER num_ctx` (only per-model route for `/v1`). Tool-calling blog: "using a context window of 32k or higher improves the performance of tool calling", with higher memory use ([blog](https://ollama.com/blog/streaming-tool)); on 8 GB try 8K-16K.
- Memory levers: `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE` (default `f16`; `q8_0`, `q4_0` reduce it). `OLLAMA_NUM_PARALLEL` default 1 and context memory scales with it; `OLLAMA_MAX_QUEUE` default 512, then HTTP 503 ([FAQ](https://docs.ollama.com/faq)).
- Timeouts: none documented server-side. Set client timeouts (generous read timeout to cover cold load plus generation, short connect timeout). Not confirmed: any Ollama default timeout.
- Streaming: native `stream` defaults to true (NDJSON); `/v1` follows the OpenAI default. Structured-output docs and blog only show `"stream": false`, and the streaming page says non-streaming suits structured outputs ([streaming](https://docs.ollama.com/api/streaming)). Streaming with `format` is not documented; use `stream: false` for structured calls. Tool calls with streaming are supported natively.
- Python: `openai` SDK with `base_url="http://localhost:11434/v1/"`, `api_key="ollama"` (required, ignored); set `timeout` and `max_retries`. httpx is fine for `/api/chat`. Do not send `tool_choice`, `n`, `logit_bias`, `user` or http image URLs. Handle a missing `tool_calls[].id` defensively (the code copies the id from the native call; presence is not confirmed). Check `finish_reason == "length"` for truncated JSON (the blog's example does).

## Request shapes that work

Base URL `http://localhost:11434`; `MODEL` is a tag from section 2. Shapes follow what `openai.go` parses; the OpenAI API reference page (https://platform.openai.com/docs/api-reference/chat/create) returned HTTP 403 to my fetch, so OpenAI-side shapes were not re-read from it.

### (a) Structured output

OpenAI-compatible, `POST /v1/chat/completions`:

```json
{
  "model": "MODEL",
  "messages": [{"role": "user", "content": "Classify: flat tyre on A4 near Krakow. Reply as JSON."}],
  "temperature": 0,
  "stream": false,
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "incident",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {"category": {"type": "string"}, "urgent": {"type": "boolean"}},
        "required": ["category", "urgent"]
      }
    }
  }
}
```

Native, `POST /api/chat`:

```json
{
  "model": "MODEL",
  "messages": [{"role": "user", "content": "Classify: flat tyre on A4 near Krakow. Reply as JSON."}],
  "stream": false,
  "options": {"temperature": 0, "num_ctx": 8192},
  "format": {
    "type": "object",
    "properties": {"category": {"type": "string"}, "urgent": {"type": "boolean"}},
    "required": ["category", "urgent"]
  }
}
```

### (b) Tool call round trip

Request 1 is the user message plus `tools`; the model replies with `tool_calls`. Request 2 (below) appends the assistant message and the tool result.

OpenAI-compatible (`arguments` is a JSON string, result linked by `tool_call_id`, no `tool_choice`):

```json
{
  "model": "MODEL",
  "stream": false,
  "tools": [{"type": "function", "function": {
    "name": "find_garage", "description": "Find nearest garage",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}],
  "messages": [
    {"role": "user", "content": "Garage near Krakow?"},
    {"role": "assistant", "content": "", "tool_calls": [
      {"id": "call_1", "type": "function", "function": {"name": "find_garage", "arguments": "{\"city\":\"Krakow\"}"}}]},
    {"role": "tool", "tool_call_id": "call_1", "content": "AutoFix, 2 km"}
  ]
}
```

Native (`arguments` is an object, result linked by `tool_name`):

```json
{
  "model": "MODEL",
  "stream": false,
  "tools": [{"type": "function", "function": {
    "name": "find_garage", "description": "Find nearest garage",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}],
  "messages": [
    {"role": "user", "content": "Garage near Krakow?"},
    {"role": "assistant", "content": "", "tool_calls": [
      {"type": "function", "function": {"index": 0, "name": "find_garage", "arguments": {"city": "Krakow"}}}]},
    {"role": "tool", "tool_name": "find_garage", "content": "AutoFix, 2 km"}
  ]
}
```

### (c) Image message

OpenAI-compatible:

```json
{
  "model": "MODEL",
  "stream": false,
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "What damage is visible on this car?"},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<BASE64>"}}
  ]}]
}
```

Native:

```json
{
  "model": "MODEL",
  "stream": false,
  "messages": [{"role": "user", "content": "What damage is visible on this car?", "images": ["<BASE64>"]}]
}
```

## Not confirmed from primary sources

- Per-model VRAM use and tokens/s on an RTX 4060; vision latency; cold-load time.
- Any per-model structured-output or tool-call reliability measure.
- `tools` plus `format` in one request; thinking models with `format`.
- `/v1` streaming behaviour with tools and with `response_format`.
- Any default request timeout; image size and count limits; id presence on every `/v1` tool call.
- `tool_choice` on the native endpoint (undocumented; assume unsupported).
- OpenAI-side request shapes verified against the OpenAI reference (fetch blocked).

## Sources

- https://docs.ollama.com/api/openai-compatibility and https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx
- https://github.com/ollama/ollama/blob/main/openai/openai.go
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/api/streaming
- https://docs.ollama.com/capabilities/structured-outputs
- https://docs.ollama.com/capabilities/tool-calling
- https://docs.ollama.com/capabilities/vision
- https://docs.ollama.com/context-length
- https://docs.ollama.com/faq and https://github.com/ollama/ollama/blob/main/docs/faq.mdx
- https://ollama.com/blog/structured-outputs (2024-12-06)
- https://ollama.com/blog/tool-support (2024-07-25)
- https://ollama.com/blog/streaming-tool (2025-05-28)
- Library pages under https://ollama.com/library/ for the models in section 2; https://ollama.com/search?c=tools
