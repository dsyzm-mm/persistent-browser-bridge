"""Configuration loading with TOML and environment overrides."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from pbb.constants import DEFAULT_HOST, DEFAULT_PORT
from pbb.utils.paths import config_dir, default_download_dir, ensure_app_dirs


class Settings(BaseModel):
    browser: str = "auto"
    default_profile: str = "default"
    daemon_host: str = DEFAULT_HOST
    daemon_port: int = Field(DEFAULT_PORT, ge=1024, le=65535)
    download_dir: Path = Field(default_factory=default_download_dir)
    timeout: int = Field(15_000, ge=1000, le=300_000)
    headless: bool = False
    snapshot_max_chars: int = Field(5000, ge=500, le=100_000)

    @field_validator("daemon_host")
    @classmethod
    def localhost_only(cls, value: str) -> str:
        if value not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("v0.1 only permits a loopback daemon host")
        return value

    @field_validator("browser")
    @classmethod
    def known_browser(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"edge", "chrome", "chromium", "auto"}:
            raise ValueError("browser must be edge, chrome, chromium, or auto")
        return normalized


def str_to_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


ENV_MAP: dict[str, tuple[str, Callable[[str], Any]]] = {
    "PBB_BROWSER": ("browser", str),
    "PBB_PROFILE": ("default_profile", str),
    "PBB_PORT": ("daemon_port", int),
    "PBB_DOWNLOAD_DIR": ("download_dir", Path),
    "PBB_TIMEOUT": ("timeout", int),
    "PBB_HEADLESS": ("headless", str_to_bool),
}


def config_path() -> Path:
    return config_dir() / "config.toml"


def load_settings() -> Settings:
    ensure_app_dirs()
    values: dict[str, Any] = {}
    path = config_path()
    if path.exists():
        with path.open("rb") as handle:
            values.update(tomllib.load(handle))
    for env_name, (field_name, converter) in ENV_MAP.items():
        raw = os.getenv(env_name)
        if raw is not None:
            values[field_name] = converter(raw)
    return Settings.model_validate(values)
