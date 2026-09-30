from pathlib import Path

import pytest

from pbb.browser.profile import (
    InvalidProfileName,
    create_profile,
    delete_profile,
    list_profiles,
    profile_path,
)


def test_profile_lifecycle(isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pbb.browser.profile.profiles_dir", lambda: isolated_dirs / "profiles")
    path = create_profile("work")
    assert path.exists()
    assert (path / ".pbb-profile").exists()
    assert list_profiles() == ["work"]
    delete_profile("work")
    assert not path.exists()


@pytest.mark.parametrize("name", ["../escape", "with space", "", "a/b"])
def test_invalid_profile_names(name: str) -> None:
    with pytest.raises(InvalidProfileName):
        profile_path(name)
