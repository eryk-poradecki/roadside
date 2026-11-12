"""Development-only Claude Code transport for recording (ADR 0004)."""

import asyncio
import json
import shutil
import tempfile
from typing import Any

from app.integrations.llm.base import (
    LLMRequest,
    LLMResult,
    ProviderError,
    ProviderTimeoutError,
)


class CLIProvider:
    name = "cli"

    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_s: float = 60,
        vision: bool = False,
        max_images: int = 0,
    ) -> None:
        executable = shutil.which("claude")
        if executable is None:
            raise RuntimeError("LLM_PROVIDER=cli needs the claude binary on PATH")
        self._executable = executable
        self._model = model
        self._timeout_s = timeout_s
        self.vision = vision
        self.max_images = max_images if vision else 0

    async def aclose(self) -> None:
        pass

    async def complete(self, request: LLMRequest) -> LLMResult:
        system = "\n\n".join(m.text for m in request.messages if m.role == "system")
        system += (
            "\n\nReturn only a raw JSON object, without Markdown fences or commentary, "
            "matching this schema:\n" + json.dumps(request.schema)
        )
        content: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role == "system":
                continue
            content.append({"type": "text", "text": f"{message.role}:\n{message.text}"})
            for image in message.images:
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image.media_type,
                            "data": image.data_b64,
                        },
                    }
                )
        payload = json.dumps({"type": "user", "message": {"role": "user", "content": content}})
        args = [
            self._executable,
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--tools",
            "",
            "--disallowedTools",
            "mcp__*",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--system-prompt",
            system,
            # setting-sources alone does not disable CLAUDE.md discovery.
            "--safe-mode",
        ]
        if self._model:
            args += ["--model", self._model]
        with tempfile.TemporaryDirectory(prefix="llm-cli-") as directory:
            try:
                process = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=directory,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except OSError as exc:
                raise ProviderError("Claude CLI could not start") from exc
            try:
                async with asyncio.timeout(self._timeout_s):
                    stdout, _ = await process.communicate((payload + "\n").encode())
            except (TimeoutError, asyncio.CancelledError) as exc:
                if process.returncode is None:
                    process.kill()
                await process.wait()
                if isinstance(exc, asyncio.CancelledError):
                    raise
                raise ProviderTimeoutError("Claude CLI timed out") from exc
        if process.returncode != 0:
            raise ProviderError("Claude CLI exited unsuccessfully")
        return self._parse(stdout)

    def _parse(self, stdout: bytes) -> LLMResult:
        try:
            events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            data = next(event for event in reversed(events) if event.get("type") == "result")
            if data.get("is_error"):
                raise ProviderError("Claude CLI reported a model error")
            text = data["result"]
            model = next(iter(data["modelUsage"]))
            if not isinstance(text, str) or not text or not isinstance(model, str):
                raise ValueError
            usage = data.get("usage", {})
            return LLMResult(
                text=text,
                provider=self.name,
                model=model,
                usage={k: v for k, v in usage.items() if isinstance(v, int)},
            )
        except (ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
            raise ProviderError("Claude CLI sent an unexpected body") from exc
