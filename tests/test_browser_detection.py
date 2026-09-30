from pbb.browser.browser_detection import BrowserInstall, detect_browsers


def test_detection_returns_unique_existing_paths() -> None:
    found = detect_browsers()
    assert all(isinstance(item, BrowserInstall) for item in found)
    paths = [item.executable.lower() for item in found if item.executable]
    assert len(paths) == len(set(paths))
