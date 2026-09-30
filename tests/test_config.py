from pathlib import Path

import pytest

from pbb.config import Settings, load_settings


def test_defaults_are_local_only() -> None:
    settings = Settings()
    assert settings.daemon_host == "127.0.0.1"
    assert settings.daemon_port == 8765
    assert settings.browser == "auto"


def test_rejects_remote_bind() -> None:
    with pytest.raises(ValueError, match="loopback"):
        Settings(daemon_host="0.0.0.0")


def test_environment_overrides(isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PBB_PORT", "9876")
    monkeypatch.setenv("PBB_BROWSER", "chrome")
    settings = load_settings()
    assert settings.daemon_port == 9876
    assert settings.browser == "chrome"
    assert settings.download_dir == isolated_dirs / "downloads"
