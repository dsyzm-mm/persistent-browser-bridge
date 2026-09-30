from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PBB_DOWNLOAD_DIR", str(tmp_path / "downloads"))
    if os.name == "nt":
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    else:
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return tmp_path
