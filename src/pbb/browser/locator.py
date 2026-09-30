"""Conservative target resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page

from pbb.browser.snapshot import SnapshotStore


class LocatorResolutionError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True)
class ResolvedLocator:
    locator: Locator
    metadata: dict[str, Any]


async def _unique(locator: Locator, label: str) -> ResolvedLocator | None:
    count = await locator.count()
    if count == 1:
        return ResolvedLocator(locator.first, {"strategy": label})
    if count > 1:
        matches: list[dict[str, str]] = []
        for index in range(min(count, 10)):
            item = locator.nth(index)
            matches.append(
                {
                    "tag": await item.evaluate("el => el.tagName.toLowerCase()"),
                    "text": (await item.inner_text())[:200],
                }
            )
        raise LocatorResolutionError(
            "ambiguous_target",
            f"Target matched {count} elements using {label}",
            {"matches": matches},
        )
    return None


async def resolve_locator(page: Page, store: SnapshotStore, target: str) -> ResolvedLocator:
    match = re.fullmatch(r"(?:(s_[0-9a-f]+):)?@(\d+)", target)
    if match:
        explicit_snapshot, raw_id = match.groups()
        if explicit_snapshot and explicit_snapshot != store.snapshot_id:
            raise LocatorResolutionError(
                "stale_snapshot", "Snapshot reference is no longer current"
            )
        item = store.get(int(raw_id))
        if item is None:
            raise LocatorResolutionError(
                "element_not_found", f"Snapshot element {target} was not found"
            )
        if page.url != store.page_url:
            raise LocatorResolutionError("stale_snapshot", "Page URL changed after the snapshot")
        locator = page.locator(item["selector"])
        if await locator.count() != 1:
            raise LocatorResolutionError(
                "stale_snapshot", "Snapshot element changed or disappeared"
            )
        current = await locator.first.evaluate(
            "el => ({name:(el.getAttribute('aria-label') || el.innerText || el.getAttribute('name') || el.getAttribute('placeholder') || '').replace(/\\s+/g,' ').trim(), role:el.getAttribute('role') || ''})"
        )
        expected_name = item.get("name", "")
        if expected_name and current["name"] and expected_name != current["name"]:
            raise LocatorResolutionError("stale_snapshot", "Snapshot element identity changed")
        return ResolvedLocator(
            locator.first, {"strategy": "snapshot", "snapshot_id": store.snapshot_id}
        )

    selector_error: PlaywrightError | None = None
    try:
        direct = await _unique(page.locator(target), "selector")
        if direct:
            return direct
    except PlaywrightError as exc:
        selector_error = exc
    if selector_error and target.startswith(("#", ".", "[", "//", "css=", "xpath=")):
        raise LocatorResolutionError(
            "invalid_selector", f"Invalid selector: {target}"
        ) from selector_error

    strategies = [
        (page.get_by_role("button", name=target, exact=True), "button role"),
        (page.get_by_role("link", name=target, exact=True), "link role"),
        (page.get_by_label(target, exact=True), "label"),
        (page.get_by_placeholder(target, exact=True), "placeholder"),
        (page.get_by_text(target, exact=True), "exact text"),
    ]
    for locator, label in strategies:
        result = await _unique(locator, label)
        if result:
            return result
    raise LocatorResolutionError("element_not_found", f"No element matched target: {target}")
