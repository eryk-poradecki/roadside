# Recording with Claude Code

Issue #75 implements the development-only CLI transport from ADR 0004. Install and
log in to Claude Code on the host, then set these in `backend/.env`:

```dotenv
DEMO_MODE=false
PUBLIC_DEPLOY=false
LLM_PROVIDER=cli
LLM_RECORD=true
LLM_VISION=true
LLM_MAX_IMAGES=3
```

Run `make dev-api` and `make dev-web`, then make help requests as usual. The normal
assistant and damage-report pipelines build prompts, validate output and allow one
repair. `RecordingProvider` writes to `LLM_RECORDINGS_DIR` (default
`backend/recordings` when running the API with Make). Restart in demo mode with
`LLM_RECORD=false` to replay those answers.

No endpoint URL or API key is needed. Leave `LLM_MODEL` unset to use the CLI's
current default, or set it to a Claude model selector. Remove any Ollama/Gemini
model value left in `.env`. Recordings retain the actual model id from
`modelUsage`, rather than the selector. `LLM_TIMEOUT_S` caps each process and the
existing whole-turn budget covers repair too. A timeout or cancellation kills and
reaps the child. Errors omit CLI stdout/stderr, which could contain driver data.

The provider requires `LLM_RECORD=true` and `DEMO_MODE=false`. Public deployment
refuses `LLM_PROVIDER=cli` even in demo mode. The Dockerfile installs no Claude
binary or credentials; use the host development setup for recording.

## Live verification, 12 November 2026

Verified with Claude Code **2.1.322**, reporting **claude-opus-5-5**. These are
verification calls, not the final demo recording set.

- **Image input:** sent a generated 320 × 160 PNG containing a red square as a
  base64 image block in the stream-json user message, without file-reading tools.
  The reply described a solid red square on a white background, toward the left.
- **Instruction isolation:** ran with a temporary `CLAUDE_CONFIG_DIR` containing
  a `CLAUDE.md` with a unique verification marker and a symlink to the existing
  login credentials. Asked for the marker from user-level instructions. The
  provider returned `{"marker":"NONE"}`. As a positive control, removing
  `--safe-mode` and enabling the `user` settings source returned the exact marker.
  No permanent user instructions changed.
  `--safe-mode` explicitly disables CLAUDE.md discovery, plugins, skills and hooks;
  `--setting-sources ""` also disables user/project/local settings. This is stronger
  than relying on the original settings flag alone. Admin-managed policy still
  applies, as documented by `claude --help`.
- **Normal help request and recording:** created an incident through the HTTP API
  with no coordinates and a smoke/burning-smell note, then posted an English AI
  turn. Both requests returned 201. The advice passed normal validation, was
  urgent, led with 112, and produced one replay file tagged `cli` /
  `claude-opus-5-5` in a temporary recording directory. No verification incident or
  replay was added to the demo data.
- **Docker:** `docker run --rm --entrypoint python roadside-backend:latest -c
  'import shutil; assert shutil.which("claude") is None'` passed against the
  locally available runtime image. The Dockerfile remains unchanged and does
  not install the CLI.

The current CLI requires stream-json **output** for stream-json **input**, and
`--verbose` enables that output mode. The adapter reads the final `type=result`
event, checks `is_error` even on exit zero, and extracts text, model and integer
usage fields. It does not use `--json-schema`, which would introduce the synthetic
StructuredOutput tool. Instead the schema accompanies the supplied system prompt.
All built-in tools and MCP tools are disabled, the process runs in an empty
temporary working directory, and sessions are not persisted. `--bare` is avoided
because it excludes subscription authentication.

Offline tests use an executable fake and cover recording, image serialization,
missing binary, startup guards, malformed/error results, timeout and cancellation.
