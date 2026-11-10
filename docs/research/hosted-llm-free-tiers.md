# Hosted free-tier LLM APIs as an `OpenAICompatibleProvider` fallback

Research for GitHub issue #7. Read on 2026-11-10 from official docs/pricing/rate-limit pages only (a few
help-center pages and one search-engine summary are flagged as such). No API was called, nothing was signed up for.
Anything not stated on an official page is marked **UNCONFIRMED**. Free-tier terms change often; re-check before relying on them.

## Summary

- **Use (1), recording demo responses: Google Gemini (OpenAI-compat endpoint) is the best fit.** Free of charge on every Flash/Flash-Lite model, accepts `image_url` (base64 data URL), `tools`, and schema-constrained output. Its free-tier data is used to improve Google products (not in EEA/CH/UK), which is harmless for synthetic demo prompts but means: never record real user data. Per-model free RPM/RPD are not published in the docs (only in the AI Studio console).
- **Use (1) alternative: Groq `openai/gpt-oss-20b` / `openai/gpt-oss-120b`** (fast, tools, strict `json_schema`), or `qwen/qwen3.8-27b` if vision is needed (Groq documents tools + JSON mode with images). Caveat: Groq does not support structured outputs together with tool use.
- **Use (2), reviewer-friendly default: Gemini first, Groq second.** Both are "create a key in a web console, set `base_url`, go". Neither official page states a credit-card requirement for the free plan (Groq: card only needed to upgrade; Gemini: billing only for the paid tier). Phone requirement is not documented for either (UNCONFIRMED).
- **Groq's classic 8B model is gone:** `llama-3.1-8b-instant` (and `llama-3.3-70b-versatile`) shut down on 2026-08-16, including free tier; Groq's stated replacement for the 8B is `openai/gpt-oss-20b`. Do not hard-code the Llama ids.
- **OpenRouter `:free` models are a poor default:** 20 RPM and only 50 requests/day unless you have bought >= $10 of credits (then 1,000/day); the free set is volatile, free listings often log/train on prompts, and the free tools-capable models seen were not 8B-class. Fine as a last-resort escape hatch.
- **Ruled out today:** GitHub Models (retired 2026-07-30), Hugging Face Inference Providers (free users get no credits), Together (no free trial, $15 minimum first purchase), Cerebras (needs a verified payment method; $5 credits expire in 30 days; "no permanently free tier"), Mistral (docs say free mode has no API access; the free "Experiment" plan could not be confirmed from official docs).
- **Also documented but second-tier:** SambaNova (free tier w/o payment method, but 20 RPD, 200K tokens/day; `strict` is a no-op), Cohere trial key (20 RPM, 1,000 calls/month), Cloudflare Workers AI (10,000 neurons/day; tools/`response_format` support not confirmed).
- **Provider-class design implications:** use `tool_choice: "auto"` only; never combine `tools` and `response_format` in one request (Groq and Cerebras reject/forbid it); send images as base64 data URLs; treat `strict` as advisory and validate with Pydantic; read `finish_reason` leniently; take model id and base URL from env.

## Comparison table

| Provider | Base URL | Free limits (documented) | tools | json_object / json_schema strict | Vision on free model | Card / phone | Free-tier data use |
|---|---|---|---|---|---|---|---|
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | Free of charge on Flash/Flash-Lite; RPM/RPD **not published** in docs | Yes (`tool_choice: "auto"` shown) | Schema output via `beta.chat.completions.parse`; json_object not documented there | Yes (base64 `image_url`) | Card: not stated; phone: UNCONFIRMED | Used to improve products (not EEA/CH/UK) |
| Groq | `https://api.groq.com/openai/v1` | Docs table shown is the Developer plan (gpt-oss: 30 RPM, 1K RPD, 8K TPM, 200K TPD); free numbers UNCONFIRMED | Yes, all models | json_object yes; strict `json_schema` on gpt-oss-20b/120b, qwen3.8-27b | `qwen/qwen3.8-27b` (3 imgs/request) | Card: not stated; phone: not stated | Not stated on pages read |
| OpenRouter | `https://openrouter.ai/api/v1` | `:free` models: 20 RPM; 50 RPD (<$10 credits) or 1,000 RPD | Per model (filter `supported_parameters=tools`) | `json_schema` per endpoint; json_object not documented on that page | Some (e.g. Inkling 2 Small free) | Not stated | Often logged/trained by provider; per-model |
| Mistral | `https://api.mistral.ai/v1` | Docs: free mode has no API access; Experiment plan UNCONFIRMED | Yes (`any`/`required`) | json_object + json_schema | Ministral 3 8B lists vision; API id not listed | Phone: only third-party claims | Studio/API opt-out toggle exists; default not stated |
| Cerebras | `https://api.cerebras.ai/v1` | Trial: 5 RPM, 30K uncached TPM, 1M tokens/day; $5 credits, 30 days | Yes (gpt-oss, qwen) | Both, strict on qwen-3.8-27b, gpt-oss-120b | `qwen-3.8-27b` (2 imgs) | Verified payment method required | Not read |
| GitHub Models | n/a | Retired 2026-07-30 | n/a | n/a | n/a | n/a | n/a |
| Together | `https://api.together.ai/v1` | No free trial; $15 minimum first purchase | n/a | n/a | n/a | Prepaid | Not read |
| SambaNova | `https://api.sambanova.ai/v1` | Free (no payment method linked): 20 RPM, 20 RPD, 200K TPD per model | Yes (`required` supported) | json_object, json_schema; `strict:true` no effect | Not confirmed | Card: not stated | Not read |
| HF Inference Providers | `https://router.huggingface.co/v1` | Free users: no credits | Per provider | Per provider | Per provider | Card to buy credits | n/a |

## Per provider

### Google Gemini
- OpenAI-compat base URL, beta status, function calling (`tools`, example uses `tool_choice: "auto"`), structured output, `image_url` base64, `reasoning_effort` mapping, chat model id `gemini-3.8-flash` in examples: https://aistudio.google.com/docs/openai (redirect from ai.google.dev/gemini-api/docs/openai).
- Pricing page lists "Free of charge" Standard tier for Gemini 3.5 Flash-Lite, 3.1 Flash-Lite, 2.5 Flash-Lite, 3.8 Flash, 3.6 Flash, 3 Flash Preview, 2.5 Flash; "Used to improve our products" is Yes on free, No on paid. 2.5 Flash is deprecated and routes to 3.5 Flash-Lite on 2026-12-01: https://aistudio.google.com/docs/pricing. Exact API id strings for the Flash-Lite models were not in the part of the page read (UNCONFIRMED); `gemini-3.8-flash` is confirmed only as an example id.
- Rate limits: per-project, not per-key; free RPM/TPM/RPD are shown only in the AI Studio rate-limit console page, not in the docs read: https://aistudio.google.com/docs/rate-limits. UNCONFIRMED numerically.
- Key: https://aistudio.google.com/apikey; new keys are "auth keys" by default since 2026-05-28; projects imported from Cloud may need verification for the free tier; card requirement not stated: https://aistudio.google.com/docs/api-key.
- Data: unpaid services content is used to improve Google products and may be read by human reviewers (disconnected from account/key); "Do not submit sensitive, confidential, or personal information". In EEA/CH/UK paid-service terms apply to all services, but API clients offered to users there may use Paid Services only: https://aistudio.google.com/docs/terms.
- Structured output uses `response_format` with a JSON-Schema subset; `minLength`/`maxLength` etc. are silently stripped; oversized schemas give `400 INVALID_ARGUMENT`; structured output plus function calling is documented for Gemini 3 (preview): https://aistudio.google.com/docs/structured-output.
- Fit for 8B-class: Flash-Lite tier (e.g. Gemini 3.5 Flash-Lite, 3.1 Flash-Lite per pricing page).

### Groq
- Base URL; unsupported: `logprobs`, `logit_bias`, `top_logprobs`, `messages[].name`, `n != 1` (all 400); `temperature: 0` becomes `1e-8`: https://console.groq.com/docs/openai.
- Limits: the table on the rate-limits page is explicitly the Developer plan; Free plan numbers were not available. Rows: gpt-oss-120b/20b and qwen3.8-27b 30 RPM, 1K RPD, 8K TPM, 200K TPD. HTTP 429 with `retry-after`; `x-ratelimit-*` headers: https://console.groq.com/docs/rate-limits. Free-plan values: UNCONFIRMED (shown in the console limits page).
- Free vs Developer: upgrade requires a payment method (card, US bank, SEPA); free plan card requirement not stated: https://console.groq.com/docs/billing-faqs. Phone: not stated (https://console.groq.com/docs/quickstart covers only key creation).
- Models: production `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`; preview `qwen/qwen3.8-27b` etc.: https://console.groq.com/docs/models. **Both Llama ids shut down 2026-08-16 (applies to free and developer tiers); replacements `openai/gpt-oss-20b` and `openai/gpt-oss-120b`/`qwen3.6-27b`:** https://console.groq.com/docs/deprecations (the models page still lists them; trust the deprecation page).
- Tool use: all models; gpt-oss models have no parallel tool use; `tool_choice` values and `strict` for tools not stated: https://console.groq.com/docs/tool-use.
- Structured outputs: `strict: true` on gpt-oss-20b/120b, qwen3.8-27b, muse-spark-open; best-effort otherwise; `json_object` on other models; "Streaming and tool use are not currently supported with Structured Outputs": https://console.groq.com/docs/structured-outputs.
- Vision: `qwen/qwen3.8-27b` (20 MB, 3 images/request, tools + JSON mode supported with images); muse-spark-open is limited preview: https://console.groq.com/docs/vision.
- Data-use terms for the free plan: not on pages read (UNCONFIRMED).

### OpenRouter
- Free model limits (`:free` ids): 20 RPM; 50 RPD with < $10 credits purchased, 1,000 RPD with >= $10; 429 on exceed; not stated whether failed requests count: https://openrouter.ai/docs/api-reference/limits.
- Base URL: https://openrouter.ai/docs/quickstart. `tool_choice`: auto, none, specific function; `parallel_tool_calls`: https://openrouter.ai/docs/guides/features/tool-calling (no "required" listed).
- Structured outputs: `json_schema` with `strict`; support is per endpoint, not per model; use `require_parameters: true`; json_object not mentioned: https://openrouter.ai/docs/guides/features/structured-outputs.
- Free-model snapshot (volatile): tools-capable `thinkingmachines/inkling-2-small:free` (text+image) and `liquid/lfm-3-1.7b:free` (1.7B, text only); no ~8B free tools model seen: https://openrouter.ai/models?max_price=0&supported_parameters=tools. `openrouter/free` router picks a free model automatically: https://openrouter.ai/docs/faq.
- Data: prompts not logged by OpenRouter by default; providers that log are skipped unless the training toggle is on: https://openrouter.ai/docs/faq. Free listings often state prompts are logged/trained by the provider (search summary of https://openrouter.ai/openrouter/free and https://openrouter.ai/collections/free-models; not verified page by page).
- Card requirement for free use: not stated.

### Mistral
- Docs: "Free mode" does not include API access; API keys require billing activation: https://docs.mistral.ai/admin/billing-usage/usage-limits. Third-party aggregators describe a free "Experiment" plan with SMS verification and training opt-in; the Mistral help-center articles on it returned 404. **Treat the free API tier as UNCONFIRMED.**
- API: `https://api.mistral.ai/v1/chat/completions`; `tool_choice` auto/none/any/required or named function; `response_format` json_object (must also prompt for JSON) and json_schema; `finish_reason` values and image_url not listed there: https://docs.mistral.ai/api/.
- Function-calling models include `ministral-8b-latest`, `ministral-3b-latest`, `mistral-small-latest`: https://docs.mistral.ai/capabilities/function_calling. Models overview: Ministral 3 8B lists vision; older `ministral-8b-2410` retired 2025-12-31: https://docs.mistral.ai/models/overview.
- Training opt-out for Studio/API via Admin > Privacy > "Anonymous improvement data"; default not stated: https://help.mistral.ai/en/articles/455207-can-i-opt-out-of-my-input-or-output-data-being-used-for-training.

### Cerebras
- Free Trial: 5 RPM, 30K uncached TPM, 90K total TPM, 1M TPH and TPD for `gpt-oss-120b` and `qwen-3.8-27b`; "$5 in credits after adding a verified payment method"; credits expire after 30 days; API stays inactive until a payment method is added; "no permanently free tier": https://inference-docs.cerebras.ai/support/rate-limits.
- Base URL `https://api.cerebras.ai/v1`; `n` only 1; `gpt-oss-120b` rejects `tools` + `response_format` together; external image URLs unsupported (base64 only): https://inference-docs.cerebras.ai/resources/openai.
- Strict `json_schema` on `qwen-3.8-27b` and `gpt-oss-120b` (needs `additionalProperties:false`, no `oneOf`/`pattern`/`minItems`): https://inference-docs.cerebras.ai/capabilities/structured-outputs.
- Verdict: the payment-method gate fails the "stranger in minutes" test.

### GitHub Models
- Retired: as of 2026-07-30 the playground, catalog, inference API and BYOK are unavailable to all customers: https://docs.github.com/en/github-models/prototyping-with-ai-models.

### Together
- "Does not currently offer free trials"; first purchase >= $15 (later >= $5); prepaid: https://docs.together.ai/docs/billing-credits. Base URL `https://api.together.ai/v1`: https://docs.together.ai/docs/quickstart. A search result suggested some free-priced catalog models exist (unverified; not read directly).

### SambaNova
- Free tier applies when no payment method is linked; per model (DeepSeek-V3.1, Meta-Llama-3.3-70B-Instruct, gpt-oss-120b, DeepSeek-V3.2, gemma-4-31B-it): 20 RPM, 20 RPD, 200,000 TPD: https://docs.sambanova.ai/docs/en/models/rate-limits.
- Base URL `https://api.sambanova.ai/v1`, keys at cloud.sambanova.ai/apis: https://docs.sambanova.ai/docs/en/get-started/api-keys-urls.
- Function calling models: Llama-3.3-70B, gpt-oss-120b, DeepSeek-V3.1/V3.2, MiniMax-M3, gemma-4-31B-it; `tool_choice` auto/required/none/named; `strict:true` accepted but no effect; json_object errors on invalid JSON: https://docs.sambanova.ai/docs/en/features/function-calling.
- `n>1` with tools is a 400; penalties ignored: https://docs.sambanova.ai/docs/en/features/openai-compatibility. No 8B-class free model listed; 20 requests/day is too tight for recording sessions.

### Hugging Face Inference Providers
- Base URL `https://router.huggingface.co/v1`; free users get no monthly credits (PRO $2/month): https://huggingface.co/docs/inference-providers/pricing and https://huggingface.co/docs/inference-providers/index. Not a free tier.

### Others with a documented free allotment
- **Cohere** (`https://api.cohere.ai/compatibility/v1`): tools with `strict`, structured outputs, `reasoning_effort` only `none`/`high`; unsupported `parallel_tool_calls`, `n`, `logit_bias`; `tool_choice` not mentioned: https://docs.cohere.com/docs/compatibility-api. Trial keys: 20 RPM chat, 1,000 calls/month; commercial use not stated: https://docs.cohere.com/docs/rate-limits. Vision and sign-up friction not confirmed.
- **Cloudflare Workers AI** (`https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1`): 10,000 neurons/day free: https://developers.cloudflare.com/workers-ai/platform/pricing/; compat endpoints listed, tools/`response_format` support not stated: https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/. Account id in the URL is awkward for one-line config.

## OpenAI-compat gotchas

- **`tools` + `response_format` in one request:** Groq says structured outputs do not work with tool use (https://console.groq.com/docs/structured-outputs); Cerebras `gpt-oss-120b` rejects the combo and recommends two requests (https://inference-docs.cerebras.ai/resources/openai). Safest: let the agent finish its tool loop, then emit the final structured answer via a separate JSON-mode/schema call, or via a "final_answer" tool.
- **`tool_choice`:** Gemini docs only show `"auto"`; Groq docs do not list values; OpenRouter lists auto/none/named (no `required`); Mistral accepts `any` and `required`; SambaNova supports `required`. Do not rely on `required`.
- **`strict`:** real constrained decoding on Groq (select models), Cerebras (qwen/gpt-oss), Cohere; SambaNova accepts and ignores it; OpenRouter says enforcement varies by endpoint; Gemini silently drops some keywords. Always re-validate.
- **Strict schema subset:** Cerebras requires `additionalProperties:false` everywhere and rejects `oneOf`, `pattern`, `format`, `minItems`; keep one conservative schema.
- **`finish_reason`:** OpenRouter normalizes to `tool_calls`/`stop`/`length`/`content_filter`/`error` and exposes `native_finish_reason`; errors can appear inside a 200 body; unsupported params are silently ignored (https://openrouter.ai/docs/api-reference/overview). Other providers' value sets are not documented on pages read; accept any string.
- **Errors/rate limits:** Groq 429 with `retry-after` and `x-ratelimit-*`; OpenRouter 429 with `X-RateLimit-*`; Cerebras 429 naming uncached vs total token limit; Gemini invalid/oversized schema is `400 INVALID_ARGUMENT`. Provider class should retry 429 with backoff and surface 400s.
- **Unsupported params give 400 on Groq** (`logprobs`, `logit_bias`, `top_logprobs`, `messages[].name`, `n != 1`); Cerebras `n` only 1; SambaNova `n>1` with tools is 400. Never send `n`, `name`, or logprobs.
- **Images:** Cerebras accepts base64 data URIs only; Gemini examples use base64; send data URLs everywhere. Image counts per request are low (Groq qwen3.8: 3; Cerebras: 2).
- **Reasoning models:** gpt-oss and Gemini reasoning options (`reasoning_effort`, `reasoning_format`) are provider-specific; Cohere only `none`/`high`. Pass via `extra_body`, default off.
- **Model churn:** Groq retired Llama 3.1 8B in Aug 2026; Gemini 2.5 Flash reroutes 2026-12-01; the OpenRouter free list changes. Make the model id an env var and store the model id used in recorded fixtures.
- **Beta label:** Gemini's OpenAI compatibility is documented as beta; its page also contains inconsistent examples (nested `extra_body`, base URL without `/openai/`).

## Sources

- https://aistudio.google.com/docs/openai
- https://aistudio.google.com/docs/pricing
- https://aistudio.google.com/docs/rate-limits
- https://aistudio.google.com/docs/api-key
- https://aistudio.google.com/docs/terms
- https://aistudio.google.com/docs/structured-output
- https://console.groq.com/docs/openai
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/models
- https://console.groq.com/docs/deprecations
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/tool-use
- https://console.groq.com/docs/vision
- https://console.groq.com/docs/billing-faqs
- https://console.groq.com/docs/quickstart
- https://openrouter.ai/docs/api-reference/limits
- https://openrouter.ai/docs/api-reference/overview
- https://openrouter.ai/docs/quickstart
- https://openrouter.ai/docs/faq
- https://openrouter.ai/docs/guides/features/tool-calling
- https://openrouter.ai/docs/guides/features/structured-outputs
- https://openrouter.ai/models?max_price=0&supported_parameters=tools
- https://docs.mistral.ai/api/
- https://docs.mistral.ai/admin/billing-usage/usage-limits
- https://docs.mistral.ai/capabilities/function_calling
- https://docs.mistral.ai/models/overview
- https://help.mistral.ai/en/articles/455207-can-i-opt-out-of-my-input-or-output-data-being-used-for-training
- https://inference-docs.cerebras.ai/support/rate-limits
- https://inference-docs.cerebras.ai/resources/openai
- https://inference-docs.cerebras.ai/capabilities/structured-outputs
- https://docs.github.com/en/github-models/prototyping-with-ai-models
- https://docs.together.ai/docs/billing-credits
- https://docs.together.ai/docs/quickstart
- https://docs.sambanova.ai/docs/en/models/rate-limits
- https://docs.sambanova.ai/docs/en/get-started/api-keys-urls
- https://docs.sambanova.ai/docs/en/features/function-calling
- https://docs.sambanova.ai/docs/en/features/openai-compatibility
- https://huggingface.co/docs/inference-providers/pricing
- https://huggingface.co/docs/inference-providers/index
- https://docs.cohere.com/docs/compatibility-api
- https://docs.cohere.com/docs/rate-limits
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/
