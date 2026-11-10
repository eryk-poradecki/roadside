from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # Static until the photos ticket.
    llm_vision: bool = False
    max_photos: int = 5
    max_photo_bytes: int = 10 * 1024 * 1024

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
