from app.integrations.llm.base import LLMProvider, LLMRequest, LLMResult, ProviderError
from app.integrations.llm.openai_compatible import OpenAICompatibleProvider
from app.settings import Settings


class NoRecordingsProvider:
    """Demo mode until the replay provider exists: every turn fails as a provider error.

    Never a silent fallback to a live model, and never an invented answer.
    """

    name = "replay"
    vision = False
    max_images = 0

    async def complete(self, request: LLMRequest) -> LLMResult:
        raise ProviderError("demo mode has no recorded answers yet")

    async def aclose(self) -> None:
        return None


def build_provider(settings: Settings) -> LLMProvider:
    if settings.demo_mode:
        return NoRecordingsProvider()
    # Settings validation guarantees these are set when demo mode is off.
    if not (settings.llm_base_url and settings.llm_api_key and settings.llm_model):
        raise RuntimeError("LLM settings are missing")
    return OpenAICompatibleProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        connect_timeout_s=settings.llm_connect_timeout_s,
        read_timeout_s=settings.llm_timeout_s,
        vision=settings.llm_vision,
        max_images=settings.llm_max_images,
        reasoning_effort=settings.llm_reasoning_effort,
    )
