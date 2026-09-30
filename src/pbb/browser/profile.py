"""Dedicated persistent-profile management."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from pbb.utils.paths import profiles_dir

PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class InvalidProfileName(ValueError):
    pass


def validate_profile_name(name: str) -> str:
    if not PROFILE_RE.fullmatch(name) or name in {".", ".."}:
        raise InvalidProfileName(
            "profile names must be 1-64 characters using letters, numbers, '.', '_' or '-'"
        )
    return name


def profile_path(name: str) -> Path:
    validate_profile_name(name)
    root = profiles_dir().resolve()
    path = (root / name).resolve()
    if path.parent != root:
        raise InvalidProfileName("profile path escapes the PBB profiles directory")
    return path


def create_profile(name: str) -> Path:
    path = profile_path(name)
    path.mkdir(parents=True, exist_ok=True)
    marker = path / ".pbb-profile"
    marker.touch(exist_ok=True)
    return path


def list_profiles() -> list[str]:
    root = profiles_dir()
    if not root.exists():
        return []
    return sorted(
        item.name for item in root.iterdir() if item.is_dir() and (item / ".pbb-profile").exists()
    )


def delete_profile(name: str) -> None:
    path = profile_path(name)
    if not (path / ".pbb-profile").exists():
        raise FileNotFoundError(f"PBB profile '{name}' does not exist")
    shutil.rmtree(path)
