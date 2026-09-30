"""Platform-specific paths owned by PBB."""

from pathlib import Path

from platformdirs import PlatformDirs

from pbb.constants import APP_NAME


def dirs() -> PlatformDirs:
    return PlatformDirs(APP_NAME, appauthor=False, roaming=False)


def data_dir() -> Path:
    return Path(dirs().user_data_path)


def config_dir() -> Path:
    return Path(dirs().user_config_path)


def profiles_dir() -> Path:
    return data_dir() / "profiles"


def logs_dir() -> Path:
    return data_dir() / "logs"


def runtime_dir() -> Path:
    return data_dir() / "runtime"


def default_download_dir() -> Path:
    return Path.home() / "Downloads" / "PBB"


def ensure_app_dirs() -> None:
    for path in (data_dir(), config_dir(), profiles_dir(), logs_dir(), runtime_dir()):
        path.mkdir(parents=True, exist_ok=True)
