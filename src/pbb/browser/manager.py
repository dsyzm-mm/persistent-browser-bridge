"""Own the Playwright persistent context for the daemon lifetime."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from playwright.async_api import (
    BrowserContext,
    Error,
    Page,
    Playwright,
    TimeoutError,
    async_playwright,
)

from pbb.browser.browser_detection import BrowserInstall, select_browser
from pbb.browser.locator import LocatorResolutionError, resolve_locator
from pbb.browser.locks import ProfileLock
from pbb.browser.profile import create_profile
from pbb.browser.snapshot import SnapshotStore, capture_snapshot
from pbb.config import Settings


class BrowserManager:
    def __init__(self, settings: Settings, profile: str, browser: str | None = None) -> None:
        self.settings = settings
        self.profile = profile
        self.preference = browser or settings.browser
        self.install: BrowserInstall | None = None
        self.playwright: Playwright | None = None
        self.context: BrowserContext | None = None
        self.active_page: Page | None = None
        self.store = SnapshotStore()
        self.lock = ProfileLock(create_profile(profile), profile)
        self.restarts = 0
        self._tab_ids: dict[int, str] = {}
        self._next_tab_id = 1

    async def start(self) -> None:
        if self.context:
            return
        self.lock.acquire()
        try:
            self.install = select_browser(self.preference)
            self.playwright = await async_playwright().start()
            options: dict[str, Any] = {
                "user_data_dir": str(create_profile(self.profile)),
                "headless": self.settings.headless,
                "accept_downloads": True,
                "downloads_path": str(self.settings.download_dir),
                "timeout": self.settings.timeout,
            }
            if self.install.channel:
                options["channel"] = self.install.channel
            elif self.install.executable:
                options["executable_path"] = self.install.executable
            self.context = await self.playwright.chromium.launch_persistent_context(**options)
            self.context.set_default_timeout(self.settings.timeout)
            self.active_page = (
                self.context.pages[-1] if self.context.pages else await self.context.new_page()
            )
        except Exception:
            self.lock.release()
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            raise

    async def close(self) -> None:
        try:
            if self.context:
                await self.context.close()
        finally:
            self.context = None
            self.active_page = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            self.lock.release()

    async def page(self) -> tuple[Page, bool]:
        if not self.context:
            await self.start()
            assert self.active_page is not None
            return self.active_page, True
        assert self.context is not None
        try:
            if not self.active_page or self.active_page.is_closed():
                pages = [page for page in self.context.pages if not page.is_closed()]
                self.active_page = pages[-1] if pages else await self.context.new_page()
                return self.active_page, True
            return self.active_page, False
        except Error:
            await self.close()
            self.restarts += 1
            await self.start()
            assert self.active_page is not None
            return self.active_page, True

    async def status(self) -> dict[str, Any]:
        page = self.active_page
        running = self.context is not None
        restarted = False
        if running and (page is None or page.is_closed()):
            page, restarted = await self.page()
        return {
            "success": True,
            "browser_running": running,
            "browser": self.install.name if self.install else None,
            "profile": self.profile,
            "url": page.url if page and not page.is_closed() else None,
            "title": await page.title() if page and not page.is_closed() else None,
            "tabs": len(self.context.pages) if self.context else 0,
            "browser_restarted": restarted,
        }

    async def navigate(self, url: str) -> dict[str, Any]:
        page, restarted = await self.page()
        started = time.perf_counter()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.settings.timeout)
        except TimeoutError as exc:
            raise LocatorResolutionError(
                "navigation_timeout", f"Navigation timed out: {url}"
            ) from exc
        return {
            "success": True,
            "url": page.url,
            "title": await page.title(),
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "browser_restarted": restarted,
        }

    async def snapshot(
        self,
        max_chars: int | None = None,
        max_elements: int | None = None,
        include_text: bool = True,
        selector: str | None = None,
    ) -> dict[str, Any]:
        page, restarted = await self.page()
        result = await capture_snapshot(
            page,
            self.store,
            max_chars if max_chars is not None else self.settings.snapshot_max_chars,
            max_elements=max_elements,
            include_text=include_text,
            selector=selector,
            active_tab_index=self._page_index(page),
        )
        result["browser_restarted"] = restarted
        return result

    async def click(self, target: str | dict[str, str]) -> dict[str, Any]:
        page, restarted = await self.page()
        resolved = await resolve_locator(page, self.store, target)
        started = time.perf_counter()
        before_pages = len(self.context.pages) if self.context else 0
        await resolved.locator.click()
        await asyncio.sleep(0.15)
        after_pages = len(self.context.pages) if self.context else before_pages
        return {
            "success": True,
            "action": "click",
            "target": target,
            "url": page.url,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "browser_restarted": restarted,
            "new_tab_opened": after_pages > before_pages,
            "new_tab_index": after_pages - 1 if after_pages > before_pages else None,
        }

    async def fill(self, target: str | dict[str, str], value: str) -> dict[str, Any]:
        page, restarted = await self.page()
        resolved = await resolve_locator(page, self.store, target)
        started = time.perf_counter()
        await resolved.locator.fill(value)
        input_type = await resolved.locator.get_attribute("type")
        return {
            "success": True,
            "action": "fill",
            "target": target,
            "value_redacted": input_type == "password",
            "url": page.url,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "browser_restarted": restarted,
        }

    async def text(self, target: str | dict[str, str]) -> dict[str, Any]:
        page, restarted = await self.page()
        resolved = await resolve_locator(page, self.store, target)
        return {
            "success": True,
            "text": await resolved.locator.inner_text(),
            "browser_restarted": restarted,
        }

    async def download(self, target: str | dict[str, str], output: Path | None = None) -> dict[str, Any]:
        page, restarted = await self.page()
        resolved = await resolve_locator(page, self.store, target)
        try:
            async with page.expect_download(timeout=self.settings.timeout) as info:
                await resolved.locator.click()
            download = await info.value
        except TimeoutError as exc:
            raise LocatorResolutionError(
                "download_not_triggered", "The target did not trigger a download before timeout"
            ) from exc
        destination = output or self.settings.download_dir
        destination = destination.expanduser().resolve()
        if destination.suffix and not destination.is_dir():
            destination.parent.mkdir(parents=True, exist_ok=True)
            saved_path = destination
        else:
            destination.mkdir(parents=True, exist_ok=True)
            saved_path = destination / download.suggested_filename
        await download.save_as(saved_path)
        return {
            "success": True,
            "filename": download.suggested_filename,
            "suggested_filename": download.suggested_filename,
            "saved_path": str(saved_path),
            "size": saved_path.stat().st_size,
            "browser_restarted": restarted,
        }

    def _page_index(self, page: Page) -> int:
        if not self.context:
            return 0
        pages = [item for item in self.context.pages if not item.is_closed()]
        return pages.index(page) if page in pages else 0

    def _tab_id(self, page: Page) -> str:
        key = id(page)
        if key not in self._tab_ids:
            self._tab_ids[key] = f"tab_{self._next_tab_id}"
            self._next_tab_id += 1
        return self._tab_ids[key]

    async def tabs(self) -> dict[str, Any]:
        page, restarted = await self.page()
        assert self.context is not None
        items: list[dict[str, Any]] = []
        for index, item in enumerate(candidate for candidate in self.context.pages if not candidate.is_closed()):
            items.append(
                {
                    "index": index,
                    "tab_id": self._tab_id(item),
                    "title": await item.title(),
                    "url": item.url,
                    "active": item == page,
                }
            )
        return {"success": True, "tabs": items, "browser_restarted": restarted}

    def _tab_index(self, index: int | None, tab_id: str | None, pages: list[Page]) -> int:
        if tab_id is not None:
            for candidate_index, page in enumerate(pages):
                if self._tab_id(page) == tab_id:
                    return candidate_index
            raise LocatorResolutionError("tab_not_found", f"Unknown tab: {tab_id}")
        if index is None or index < 0:
            raise LocatorResolutionError("tab_not_found", "A non-negative tab index or tab_id is required")
        return index

    async def switch_tab(self, index: int | None = None, tab_id: str | None = None) -> dict[str, Any]:
        await self.page()
        assert self.context is not None
        pages = [item for item in self.context.pages if not item.is_closed()]
        selected = self._tab_index(index, tab_id, pages)
        if selected >= len(pages):
            raise LocatorResolutionError("tab_not_found", f"Tab {selected} does not exist")
        self.active_page = pages[selected]
        await self.active_page.bring_to_front()
        return {
            "success": True,
            "index": selected,
            "tab_id": self._tab_id(self.active_page),
            "url": self.active_page.url,
            "title": await self.active_page.title(),
        }

    async def close_tab(self, index: int | None = None, tab_id: str | None = None) -> dict[str, Any]:
        page, _ = await self.page()
        assert self.context is not None
        pages = [item for item in self.context.pages if not item.is_closed()]
        selected = self._tab_index(index, tab_id, pages)
        if selected >= len(pages):
            raise LocatorResolutionError("tab_not_found", f"Tab {selected} does not exist")
        if len(pages) == 1:
            raise LocatorResolutionError("cannot_close_last_tab", "PBB keeps one tab open for a stable session")
        closing = pages[selected]
        await closing.close()
        self._tab_ids.pop(id(closing), None)
        if closing == page:
            remaining = [item for item in self.context.pages if not item.is_closed()]
            self.active_page = remaining[min(selected, len(remaining) - 1)]
            await self.active_page.bring_to_front()
        return {"success": True, "closed_index": selected, "tabs": len(self.context.pages)}

    async def screenshot(self, output: Path, full_page: bool) -> dict[str, Any]:
        page, restarted = await self.page()
        path = output.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=path, full_page=full_page)
        return {
            "success": True,
            "saved_path": str(path),
            "browser_restarted": restarted,
        }
