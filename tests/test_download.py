from pathlib import Path

from pbb.config import Settings


def test_download_path_can_be_configured(tmp_path: Path) -> None:
    settings = Settings(download_dir=tmp_path / "downloads")
    assert settings.download_dir == tmp_path / "downloads"
