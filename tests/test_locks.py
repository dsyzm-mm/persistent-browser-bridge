import json
from pathlib import Path

import pytest

from pbb.browser.locks import ProfileLock, ProfileLockedError


def test_profile_lock_excludes_second_owner(tmp_path: Path) -> None:
    first = ProfileLock(tmp_path, "test")
    second = ProfileLock(tmp_path, "test")
    first.acquire()
    try:
        with pytest.raises(ProfileLockedError):
            second.acquire()
    finally:
        first.release()


def test_stale_lock_is_recovered(tmp_path: Path) -> None:
    path = tmp_path / "profile.lock"
    path.write_text(json.dumps({"pid": 99999999, "start_time": 0, "profile": "test"}))
    lock = ProfileLock(tmp_path, "test")
    assert lock.clear_stale()
    assert not path.exists()
