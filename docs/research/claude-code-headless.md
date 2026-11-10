# Headless Claude Code (`claude -p`) as a bare model for `CLIProvider`

Ticket: [#31](https://github.com/eryk-poradecki/roadside/issues/31) (part of #4). Requirements come from ADR 0004 (branch `docs/ai-design`): no tools, empty temp cwd, no settings/CLAUDE.md/skills/hooks/MCP, Pydantic validation afterwards, images without enabling tools.

Verified on Claude Code **2.1.322**, 2026-11-10, Linux, subscription (claude.ai OAuth) login. 5 real calls, all from an empty temp directory. Anything not run or not shown in a source is marked UNCONFIRMED.

## Summary and recommendation

**Yes, `claude -p` can serve as a dev-only `CLIProvider`, with caveats.**

- **Tool-less, settings-less run:** `--tools ""` removes every built-in tool; add `--disallowedTools "mcp__*" --strict-mcp-config --setting-sources "" --disable-slash-commands --no-session-persistence --system-prompt "<prompt>"` and run from an empty temp dir. Verified (tests 1, 2): the `system/init` event listed `mcp_servers: []`, `skills: []`, `slash_commands: []`, and `tools: ["StructuredOutput"]` only when a schema was given (see below).
- **Do not rely on `--bare`.** The docs call it the recommended mode for scripted calls, but it never reads OAuth/keychain and needs `ANTHROPIC_API_KEY` (or an `apiKeyHelper`). With a subscription login it is unusable. `--bare` also says "Claude has access to Bash, file read, and file edit tools", so it would still need `--tools ""`. Alternative: `--safe-mode` (in `claude --help` 2.1.322) disables CLAUDE.md, skills, plugins, hooks, MCP and auto memory and keeps OAuth. It was not tested; add it as belt-and-braces (UNCONFIRMED effect on top of the flags above).
- **Images work without any tool.** Use `--input-format stream-json` and send a `user` message whose `content` has a `text` block plus a base64 `image` block on stdin. Verified: with `--tools ""`, a 32x32 solid red PNG was answered "Red". Plain-text stdin cannot carry images (the docs say single-message mode does not support direct image attachments).
- **A JSON schema can be enforced:** `--json-schema '<schema>'` (print mode only). The validated object arrives in `structured_output` in the final `result` message. Caveat: Claude Code injects a synthetic `StructuredOutput` tool that the model "calls". It is not a filesystem/shell tool, but "all tools disabled" is then literally false (init shows `tools: ["StructuredOutput"]`). Still validate with Pydantic. The docs say `format` is only an annotation, and `structured_output` can be absent when the run "ends without valid structured output".
- **Model and id:** `--model sonnet|opus|haiku|fable` or a full name. The reported id appears as the key of `modelUsage` in `json` output and in `system/init.model` / `assistant.message.model` in `stream-json`. The alias `sonnet` resolved to `claude-sonnet-5-5`.
- **Latency:** about 2-3 s for a trivial reply. A ~350-word prompt (803 output tokens) took 8.0 s (`ttft_ms` 7975). Expect roughly 5-10 s for a 500-token answer; one sample only.
- **Errors:** exit 0 on success. An invalid model gave **exit 1** with a normal `result` JSON on **stdout** (`is_error: true`, `api_error_status: 404`, `terminal_reason: "api_error"`) and a short tag on stderr. Always check `is_error`, not only the exit code.
- **Caveats for dev-only use:** usage counts against the subscription's windows (the stream carries `rate_limit_event`). The CLI is a coding-agent product, so use `--system-prompt` (replaces the default prompt), not `--append-system-prompt`. Four built-in plugins (`cc-plugin-agents-md`, `-telemetry`, `-privacy`, `-plugin-authoring`) still load and no flag was found to turn them off. Whether Anthropic's terms allow using a consumer-subscription CLI as a model backend for an app is UNCONFIRMED (not checked); for a recorded-demo dev tool it is low risk, but do not expose it to end users.

## Findings per question

### 1. Disabling tools, settings and context

| Need | Flag | Source |
| - | - | - |
| All built-in tools off | `--tools ""` ("Use `""` to disable all tools") | `claude --help`; [CLI reference](https://code.claude.com/docs/en/cli-reference) |
| MCP tools off | `--disallowedTools "mcp__*"`; `--tools` "doesn't affect MCP tools" | CLI reference |
| Only `--mcp-config` servers (none given) | `--strict-mcp-config` | CLI reference |
| No user/project/local settings | `--setting-sources ""` (list of `user,project,local`; empty = none). Accepted, exit 0. | CLI reference; test 1 |
| No skills / slash commands | `--disable-slash-commands` | CLI reference; init showed `skills: []`, `slash_commands: []` |
| Replace default system prompt | `--system-prompt` ("Replaces the entire default prompt"); also drops the git-status snapshot | [headless](https://code.claude.com/docs/en/headless#customize-the-system-prompt) |
| No transcript on disk | `--no-session-persistence` (print mode only) | CLI reference |
| Spend cap | `--max-budget-usd` (print mode only; client-side estimate) | CLI reference |
| Extra "everything off" switch | `--safe-mode` (CLAUDE.md, skills, plugins, hooks, MCP, auto memory off; auth, model, built-in tools still work) | `claude --help`; CLI reference. Not run. |
| Stricter sandbox | `--restricted` (removes command/code tools and WebFetch, ignores user/project/local settings, confines file tools) | `claude --help`. Not run; it keeps file tools, so `--tools ""` is still needed. |
| Minimal mode | `--bare` (skips hooks, skills, plugins, MCP, auto memory, CLAUDE.md discovery) | [headless: bare mode](https://code.claude.com/docs/en/headless#start-faster-with-bare-mode). Needs `ANTHROPIC_API_KEY`; keeps Bash/Read/Edit. |

Notes:
- Without `--bare`, a `-p` run "discovers and loads" hooks, skills and MCP "including anything configured in the working directory or `~/.claude`" and shows no trust dialog (headless docs). An empty cwd removes project content; the flags above handle the user-level parts we could observe.
- Debug log (`--debug-file`) of the recommended command: "project memory is off", `Loaded 0 unique skills`, `Registered 0 hooks from 4 plugins`. The user skills directory is still scanned but contributed 0. Whether a user-level `~/.claude/CLAUDE.md` is excluded by these flags is UNCONFIRMED (not tested). Add `--safe-mode`, or point `CLAUDE_CONFIG_DIR` at an empty dir (not tested, UNCONFIRMED), if that matters.
- The four built-in plugins (`path: builtin`) appear in `system/init.plugins`; they registered 0 user hooks. How to disable them is UNCONFIRMED.

### 2. Structured output

- `--output-format text|json|stream-json` ([headless](https://code.claude.com/docs/en/headless#get-structured-output)). `stream-json` with `-p` needs `--verbose` (docs example; used in test 2).
- `--json-schema` exists and is enforced: "use `--output-format json` with `--json-schema` ... structured output in the `structured_output` field"; an invalid schema makes `claude` exit with `Error: --json-schema is not a valid JSON Schema`; a missing `structured_output` means no valid output (headless docs).
- Verified in `stream-json` (test 2): the assistant message held a `tool_use` named `StructuredOutput` with `input: {"colour":"Red"}`, and the final `result` carried both `"result": "{\"colour\":\"Red\"}"` and `"structured_output": {"colour": "Red"}`. `json` output with a schema was not run separately (docs say the same field). Supported schema keywords beyond what the docs say are UNCONFIRMED. ADR 0004's flat schema (no `oneOf`, `minItems`, `maxLength`) is the safe choice here too.
- `json` envelope (test 1), one object with: `type: "result"`, `subtype: "success"`, `is_error`, `result` (the model's text), `structured_output` (only with a schema), `session_id`, `stop_reason`, `terminal_reason` (`completed`), `num_turns`, `duration_ms`, `duration_api_ms`, `ttft_ms`, `total_cost_usd`, `usage{input_tokens, output_tokens, cache_*}`, `modelUsage{"<model id>": {...costUSD...}}`, `permission_denials`, `api_error_status`.
- **Model text:** `result`. **Model id:** key of `modelUsage` (e.g. `claude-sonnet-5-5`); in `stream-json` also `system/init.model` and `assistant.message.model`.

### 3. Images without the Read tool

- Docs: streaming input mode supports "Image uploads: attach images directly to messages"; single-message mode does "not support ... direct image attachments" ([Streaming input](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode)). The CLI exposes this as `--input-format stream-json` (`claude --help`; CLI reference example `claude -p --input-format stream-json --output-format stream-json --verbose`).
- Message shape from the docs (Python example), one JSON object per stdin line:
  `{"type":"user","message":{"role":"user","content":[{"type":"text","text":"..."},{"type":"image","source":{"type":"base64","media_type":"image/png","data":"<base64>"}}]}}`
- Verified (test 2): that line on stdin with `--tools ""` gave `"Red"` for a solid red PNG. No Read tool needed, so the no-tools rule holds. Several images: UNCONFIRMED (presumably more `image` blocks). Image size limits: UNCONFIRMED (piped stdin is capped at 10 MB per the headless docs).
- A bad image block does not raise an error: Claude gets a text note such as `[Image could not be processed: image block has no source object]` (streaming-input docs). Validate images in our code first.
- Send one line and close stdin (a shell redirect does that); the process reads messages until stdin closes.

### 4. Model selection, latency, errors

- `--model <alias|full name>`; aliases `sonnet`, `opus`, `haiku`, `fable` (CLI reference, `--help`). `--fallback-model` also exists. Reported id: see section 2.
- Latency (this machine, single samples): trivial reply 1.9 s `duration_ms` (3.1 s wall incl. startup); image + schema call 1.0 s (`duration_ms`, 1.9 s wall); 803-token answer 8.0 s (8.8 s wall). Startup overhead about 1 s.
- Exit codes ([headless](https://code.claude.com/docs/en/headless#basic-usage)): 0 on success, non-zero on failure; invalid flags report to stderr before the run; in-run failures such as missing auth are printed "as the result on stdout". SIGTERM exits 143. Verified: an unknown model gave exit 1, stdout `result` = "There's an issue with the selected model (nonexistent-model). It may not exist or you may not have access to it. ...", `is_error: true`, `api_error_status: 404`, `terminal_reason: "api_error"`; stderr `[claude-code:unrecognized_model] {...}`.
- Rate limits: `stream-json` includes a `rate_limit_event` (`status`, `rateLimitType: "five_hour"`, `unifiedWindows` utilisation). Retries emit `system/api_retry` with `error` categories including `rate_limit`, `overloaded`, `billing_error`. A real rate-limit failure was not triggered (final shape UNCONFIRMED; presumably `is_error: true` with a message).

### 5. Auth and automated-use notes

- `--bare`: Anthropic auth is "strictly `ANTHROPIC_API_KEY` or `apiKeyHelper`"; OAuth and keychain never read (`--help`, headless docs).
- Non-bare `-p` uses the existing login (here `authMethod: claude.ai`); the subscription's usage windows apply. `claude setup-token` makes a long-lived token (`--help`: "requires Claude subscription"). Not tested.
- `-p` skips the workspace trust dialog (`--help`), which is why an empty temp dir and the isolation flags matter.
- `-p` runs start in Manual permission mode (v2.1.302+), and unapproved calls are denied; moot with no tools.
- The changelog was not separately read; flag availability comes from `claude --help` 2.1.322 and version notes in the docs (e.g. `--permission-prompts` needs 2.1.259+). Pin a minimum version in the dev docs.

## Working command lines (tested)

Run from a fresh empty directory (`mktemp -d`), never the repo. From Python use `subprocess.run([...], cwd=tmpdir, ...)` with an argument list.

Common flags (A):

```
--tools "" --disallowedTools "mcp__*" --strict-mcp-config --setting-sources "" \
--disable-slash-commands --no-session-persistence --system-prompt "<system prompt>" --model sonnet
```

### Text only (tested, test 1)

```
claude -p "<user prompt>" <A> --output-format json
```

stdin: none (the prompt is the argument). Output (trimmed): `{"type":"result","subtype":"success","is_error":false,"result":"pong","session_id":"...","total_cost_usd":0.00244,"duration_ms":1872,"usage":{...},"modelUsage":{"claude-sonnet-5-5":{...}},"permission_denials":[],"terminal_reason":"completed",...}`. Exit 0. Read `result`.

### With one image, schema enforced (tested, test 2)

```
claude -p --input-format stream-json --output-format stream-json --verbose <A> \
  --json-schema '{"type":"object","properties":{"colour":{"type":"string"}},"required":["colour"]}' < msg.jsonl
```

stdin (one line, then EOF):

```
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"What is the dominant colour of this image? Answer with one word."},{"type":"image","source":{"type":"base64","media_type":"image/png","data":"<base64 PNG>"}}]}}
```

stdout is NDJSON, in order: `system/init` (`tools: ["StructuredOutput"]`, `mcp_servers: []`, `skills: []`, `model: "claude-sonnet-5-5"`, `cwd` = the temp dir), `assistant` (`tool_use` `StructuredOutput`), `user` (tool_result), `rate_limit_event`, and last `result` (`"result": "{\"colour\":\"Red\"}"`, `"structured_output": {"colour":"Red"}`, `is_error:false`). Take the last line with `type == "result"`; read `structured_output` when a schema is given, else `result`, then validate with Pydantic. An image call without `--json-schema` was not run (UNCONFIRMED, expected to work the same with `tools: []`).

## Open questions

- Is a user-level `~/.claude/CLAUDE.md` or auto memory excluded by `--setting-sources ""` + `--system-prompt`? Test with a canary line, or confirm `--safe-mode` / a clean `CLAUDE_CONFIG_DIR`.
- How to disable the four built-in plugins (telemetry/privacy hooks), if wanted.
- Whether the synthetic `StructuredOutput` tool is acceptable under ADR 0004's "all tools disabled". Alternative: no `--json-schema`, schema in the prompt, Pydantic validation plus the existing one repair call.
- Exact error shape on a real rate limit or logged-out state; behaviour with several images; image size limits.
- Whether subscription usage for a recording tool is within Anthropic's terms; an API key with `--bare` (plus `--tools ""`) is the unambiguous route.
- Determinism for demo recording: `--help` shows no temperature/seed flag; replays should store the validated output, not rely on regeneration.
