import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.integrations.llm.base import (
    LLMImage,
    LLMMessage,
    LLMRequest,
    ProviderError,
    ProviderTimeoutError,
)
from app.integrations.llm.openai_compatible import OpenAICompatibleProvider

BASE = "https://llm.test/v1/"
URL = "https://llm.test/v1/chat/completions"


def completion(content: str = '{"ok": true}', model: str = "model-x-001") -> dict[str, object]:
    return {
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


REQUEST = LLMRequest(
    messages=(LLMMessage("system", "be brief"), LLMMessage("user", "hello")),
    schema={"type": "object"},
    schema_name="turn",
)


@pytest.fixture
async def provider() -> AsyncIterator[OpenAICompatibleProvider]:
    p = OpenAICompatibleProvider(
        base_url=BASE,
        api_key="sk-secret",
        model="model-x",
        temperature=0.2,
        connect_timeout_s=5,
        read_timeout_s=60,
        backoff_s=0.01,
        max_retry_wait_s=0.05,
    )
    yield p
    await p.aclose()


@respx.mock
async def test_sends_the_schema_and_returns_the_raw_text(
    provider: OpenAICompatibleProvider,
) -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=completion()))

    result = await provider.complete(REQUEST)

    assert result.text == '{"ok": true}'
    assert result.provider == "openai_compatible"
    assert result.model == "model-x-001"
    assert result.usage["total_tokens"] == 15
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer sk-secret"
    body = json.loads(sent.content)
    assert body["model"] == "model-x"
    assert body["temperature"] == 0.2
    assert body["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hello"},
    ]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "turn", "schema": {"type": "object"}},
    }


@respx.mock
async def test_images_go_as_base64_data_urls(provider: OpenAICompatibleProvider) -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=completion()))
    request = LLMRequest(
        messages=(LLMMessage("user", "look", (LLMImage("image/jpeg", "AAAA"),)),),
        schema={"type": "object"},
        schema_name="turn",
    )

    await provider.complete(request)

    content = json.loads(route.calls.last.request.content)["messages"][0]["content"]
    assert content == [
        {"type": "text", "text": "look"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}},
    ]


@pytest.mark.parametrize("status", [429, 500, 503])
@respx.mock
async def test_retries_once_on_429_and_5xx(provider: OpenAICompatibleProvider, status: int) -> None:
    route = respx.post(URL).mock(
        side_effect=[httpx.Response(status), httpx.Response(200, json=completion())]
    )

    result = await provider.complete(REQUEST)

    assert result.text == '{"ok": true}'
    assert route.call_count == 2


@respx.mock
async def test_gives_up_after_the_one_retry(provider: OpenAICompatibleProvider) -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(503))

    with pytest.raises(ProviderError):
        await provider.complete(REQUEST)
    assert route.call_count == 2


@respx.mock
async def test_honours_retry_after_up_to_the_cap(provider: OpenAICompatibleProvider) -> None:
    # A huge retry-after is capped (max_retry_wait_s), so the test stays fast.
    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "3600"}),
            httpx.Response(200, json=completion()),
        ]
    )

    await provider.complete(REQUEST)
    assert route.call_count == 2


@pytest.mark.parametrize("status", [400, 401, 404])
@respx.mock
async def test_no_retry_on_a_client_error(provider: OpenAICompatibleProvider, status: int) -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(status, json={"error": "bad"}))

    with pytest.raises(ProviderError):
        await provider.complete(REQUEST)
    assert route.call_count == 1


@respx.mock
async def test_read_timeout_is_a_timeout_error(provider: OpenAICompatibleProvider) -> None:
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(ProviderTimeoutError):
        await provider.complete(REQUEST)


@respx.mock
async def test_connect_timeout_is_a_timeout_error(provider: OpenAICompatibleProvider) -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectTimeout("unreachable"))

    with pytest.raises(ProviderTimeoutError):
        await provider.complete(REQUEST)


@respx.mock
async def test_connection_failure_is_a_provider_error(provider: OpenAICompatibleProvider) -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(ProviderError) as info:
        await provider.complete(REQUEST)
    assert not isinstance(info.value, ProviderTimeoutError)


async def test_timeouts_are_configured(provider: OpenAICompatibleProvider) -> None:
    timeout = provider.timeout
    assert timeout.connect == 5
    assert timeout.read == 60


@pytest.mark.parametrize(
    "body",
    [
        {"choices": []},
        {"choices": [{"message": {"role": "assistant", "content": None}}]},
        {"unexpected": True},
    ],
)
@respx.mock
async def test_a_reply_without_text_is_a_provider_error(
    provider: OpenAICompatibleProvider, body: dict[str, object]
) -> None:
    respx.post(URL).mock(return_value=httpx.Response(200, json=body))

    with pytest.raises(ProviderError):
        await provider.complete(REQUEST)


@respx.mock
async def test_error_messages_never_carry_the_api_key(
    provider: OpenAICompatibleProvider,
) -> None:
    respx.post(URL).mock(return_value=httpx.Response(401, text="invalid key sk-secret"))

    with pytest.raises(ProviderError) as info:
        await provider.complete(REQUEST)
    assert "sk-secret" not in str(info.value)


@respx.mock
async def test_reasoning_effort_is_sent_only_when_set(provider: OpenAICompatibleProvider) -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(200, json=completion()))
    await provider.complete(REQUEST)
    assert "reasoning_effort" not in json.loads(route.calls.last.request.content)

    quick = OpenAICompatibleProvider(
        base_url=BASE,
        api_key="k",
        model="m",
        temperature=0.2,
        connect_timeout_s=5,
        read_timeout_s=60,
        reasoning_effort="none",
    )
    try:
        await quick.complete(REQUEST)
    finally:
        await quick.aclose()
    assert json.loads(route.calls.last.request.content)["reasoning_effort"] == "none"


@respx.mock
async def test_output_cut_at_the_token_limit_fails_fast(provider: OpenAICompatibleProvider) -> None:
    body = completion('{"kind": "ans')
    body["choices"][0]["finish_reason"] = "length"  # type: ignore[index]
    respx.post(URL).mock(return_value=httpx.Response(200, json=body))

    with pytest.raises(ProviderError, match="cut off"):
        await provider.complete(REQUEST)


@respx.mock
async def test_the_provider_works_again_after_aclose(provider: OpenAICompatibleProvider) -> None:
    # A second app lifespan reuses the provider after the first one closed it.
    respx.post(URL).mock(return_value=httpx.Response(200, json=completion()))
    await provider.complete(REQUEST)
    await provider.aclose()

    assert (await provider.complete(REQUEST)).text == '{"ok": true}'
