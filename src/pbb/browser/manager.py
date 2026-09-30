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

    async def snapshot(self) -> dict[str, Any]:
        page, restarted = await self.page()
        result = await capture_snapshot(page, self.store, self.settings.snapshot_max_chars)
        result["browser_restarted"] = restarted
        return result

    async def click(self, target: str) -> dict[str, Any]:
        page, restarted = await self.page()
        resolved = await resolve_locator(page, self.store, target)
        started = time.perf_counter()
        await resolved.locator.click()
        await asyncio.sleep(0.15)
        return {
            "success": True,
            "action": "click",
            "target": target,
            "url": page.url,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "browser_restarted": restarted,
        }

    async def fill(self, target: str, value: str) -> dict[str, Any]:
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

    async def text(self, target: str) -> dict[str, Any]:
        page, restarted = await self.page()
        resolved = await resolve_locator(page, self.store, target)
        return {
            "success": True,
            "text": await resolved.locator.inner_text(),
            "browser_restarted": restarted,
        }

    async def download(self, target: str, output: Path | None = None) -> dict[str, Any]:
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
            "suggested_filename": download.suggested_filename,
            "saved_path": str(saved_path),
            "size": saved_path.stat().st_size,
            "browser_restarted": restarted,
        }

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
