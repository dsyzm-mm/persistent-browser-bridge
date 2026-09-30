"""Detect installed Edge, Chrome, or Chromium browsers."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class BrowserInstall:
    name: str
    channel: str | None
    executable: str | None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def _windows_candidates() -> list[BrowserInstall]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    return [
        BrowserInstall(
            "Microsoft Edge",
            "msedge",
            str(
                Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
                / "Microsoft/Edge/Application/msedge.exe"
            ),
        ),
        BrowserInstall(
            "Microsoft Edge",
            "msedge",
            str(
                Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
                / "Microsoft/Edge/Application/msedge.exe"
            ),
        ),
        BrowserInstall(
            "Microsoft Edge", "msedge", str(local / "Microsoft/Edge/Application/msedge.exe")
        ),
        BrowserInstall(
            "Google Chrome",
            "chrome",
            str(
                Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
                / "Google/Chrome/Application/chrome.exe"
            ),
        ),
        BrowserInstall(
            "Google Chrome",
            "chrome",
            str(
                Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
                / "Google/Chrome/Application/chrome.exe"
            ),
        ),
        BrowserInstall(
            "Google Chrome", "chrome", str(local / "Google/Chrome/Application/chrome.exe")
        ),
    ]


def detect_browsers() -> list[BrowserInstall]:
    candidates: list[BrowserInstall] = []
    if sys.platform == "win32":
        candidates.extend(_windows_candidates())
    elif sys.platform == "darwin":
        candidates.extend(
            [
                BrowserInstall(
                    "Microsoft Edge",
                    "msedge",
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                ),
                BrowserInstall(
                    "Google Chrome",
                    "chrome",
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                ),
            ]
        )
    else:
        for name, channel, command in (
            ("Microsoft Edge", "msedge", "microsoft-edge"),
            ("Google Chrome", "chrome", "google-chrome"),
            ("Chromium", None, "chromium"),
            ("Chromium", None, "chromium-browser"),
        ):
            candidates.append(BrowserInstall(name, channel, shutil.which(command)))
    seen: set[tuple[str, str]] = set()
    found: list[BrowserInstall] = []
    for item in candidates:
        if item.executable and Path(item.executable).is_file():
            key = (item.name, str(Path(item.executable).resolve()).lower())
            if key not in seen:
                seen.add(key)
                found.append(item)
    return found


def select_browser(preference: str) -> BrowserInstall:
    installed = detect_browsers()
    aliases = {"edge": "Microsoft Edge", "chrome": "Google Chrome", "chromium": "Chromium"}
    if preference != "auto":
        wanted = aliases[preference]
        for browser in installed:
            if browser.name == wanted:
                return browser
        if preference == "chromium":
            return BrowserInstall("Playwright Chromium", None, None)
        raise FileNotFoundError(f"Requested browser '{preference}' was not found")
    if installed:
        return installed[0]
    return BrowserInstall("Playwright Chromium", None, None)
