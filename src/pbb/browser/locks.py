"""PBB-owned profile lock files."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil


class ProfileLockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class LockInfo:
    pid: int
    start_time: float
    profile: str


class ProfileLock:
    def __init__(self, profile_path: Path, profile: str) -> None:
        self.path = profile_path / "profile.lock"
        self.profile = profile
        self.acquired = False

    def read(self) -> LockInfo | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return LockInfo(**raw)
        except (OSError, ValueError, TypeError):
            return None

    def is_stale(self) -> bool:
        info = self.read()
        if info is None:
            return self.path.exists()
        if not psutil.pid_exists(info.pid):
            return True
        try:
            return abs(psutil.Process(info.pid).create_time() - info.start_time) > 2
        except (psutil.Error, OSError):
            return True

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            info = self.read()
            if not self.is_stale():
                owner = info.pid if info else "unknown"
                raise ProfileLockedError(
                    f"Profile '{self.profile}' is already in use by PID {owner}."
                )
            self.path.unlink(missing_ok=True)
        info = LockInfo(os.getpid(), psutil.Process().create_time(), self.profile)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(self.path, flags)
        except FileExistsError as exc:
            raise ProfileLockedError(f"Profile '{self.profile}' is already in use.") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(info), handle)
        self.acquired = True

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False

    def clear_stale(self) -> bool:
        if self.path.exists() and self.is_stale():
            self.path.unlink()
            return True
        return False
