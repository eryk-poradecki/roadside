from app.assist.prompt import PROMPT_VERSION
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.openai_compatible import OpenAICompatibleProvider
from app.integrations.llm.recording import RecordingProvider
from app.integrations.llm.replay import ReplayProvider
from app.settings import Settings


def build_provider(settings: Settings) -> LLMProvider:
    """Replay in demo mode; otherwise the live model, recorded when `LLM_RECORD` is on.

    Settings validation has already refused the unsafe mixes (ADR 0004, 0011), and there is
    never a silent fallback from a live model to replay.
    """
    if settings.demo_mode:
        return ReplayProvider.from_dir(
            settings.llm_recordings_dir,
            vision=settings.llm_vision,
            max_images=settings.llm_max_images,
        )
    if not (settings.llm_base_url and settings.llm_api_key and settings.llm_model):
        raise RuntimeError("LLM settings are missing")
    live = OpenAICompatibleProvider(
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
    if settings.llm_record:
        return RecordingProvider(live, settings.llm_recordings_dir, prompt_version=PROMPT_VERSION)
    return live
