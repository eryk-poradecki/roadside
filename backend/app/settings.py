from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Cloudflare Tunnel ends proxied requests at ~100 s (HTTP 524), so a turn must finish first.
TURN_BUDGET_CEILING_S = 100


class Settings(BaseSettings):
    """One flat settings class, validated at startup (fail fast)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: Path = Path("data/roadside.db")
    upload_dir: Path = Path("data/uploads")
    # Single switch for replay mode. True by default so `docker compose up` needs no keys.
    demo_mode: bool = True
    frontend_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    log_level: str = "INFO"
    max_body_bytes: int = 12 * 1024 * 1024
    max_photos: int = 5
    max_photo_bytes: int = 10 * 1024 * 1024

    # The live model (ADR 0004, 0007). Read only when demo mode is off; then the first three
    # are required and startup fails without them, never falling back to replay.
    llm_provider: Literal["openai_compatible"] = "openai_compatible"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_vision: bool = False
    llm_max_images: Annotated[int, Field(ge=0, le=5)] = 3
    llm_temperature: Annotated[float, Field(ge=0, le=2)] = 0.2
    # Sent as `reasoning_effort` only when set; "none" turns thinking off where supported.
    llm_reasoning_effort: Literal["none", "low", "medium", "high"] | None = None
    llm_connect_timeout_s: Annotated[float, Field(gt=0)] = 5.0
    llm_timeout_s: Annotated[float, Field(gt=0)] = 60.0
    # The whole turn: the call, its one retry and the one repair call.
    llm_turn_budget_s: Annotated[float, Field(gt=0, lt=TURN_BUDGET_CEILING_S)] = 90.0

    # Location context (ADR 0004). Never called in demo mode.
    nominatim_url: str = "https://nominatim.openstreetmap.org/"
    osm_user_agent: str = "Roadside/0.1.0 (+https://github.com/eryk-poradecki/roadside)"
    nominatim_timeout_s: Annotated[float, Field(gt=0)] = 3.0
    # road_class is forced to unknown past either limit; to be tuned.
    location_max_gps_accuracy_m: Annotated[float, Field(gt=0)] = 150.0
    location_max_road_distance_m: Annotated[float, Field(gt=0)] = 50.0

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("frontend_origins")
    @classmethod
    def _no_wildcard(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError("FRONTEND_ORIGINS must list explicit origins, never '*'")
        return v

    @model_validator(mode="after")
    def _live_model_is_configured(self) -> Self:
        if self.demo_mode:
            return self
        key = self.llm_api_key.get_secret_value() if self.llm_api_key else ""
        values = {
            "llm_base_url": self.llm_base_url,
            "llm_api_key": key,
            "llm_model": self.llm_model,
        }
        missing = [name.upper() for name, value in values.items() if not value]
        if missing:
            raise ValueError(
                f"DEMO_MODE=false needs {', '.join(missing)} (see backend/.env.example)"
            )
        return self
