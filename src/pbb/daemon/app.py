"""FastAPI application served only on loopback."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from playwright.async_api import Error as PlaywrightError
from pydantic import BaseModel

from pbb.browser.locator import LocatorResolutionError
from pbb.browser.manager import BrowserManager
from pbb.config import Settings
from pbb.constants import API_VERSION, __version__


class NavigateRequest(BaseModel):
    url: str


class TargetRequest(BaseModel):
    target: str | dict[str, str]


class FillRequest(TargetRequest):
    value: str


class DownloadRequest(TargetRequest):
    output: str | None = None


class ScreenshotRequest(BaseModel):
    output: str = "pbb-screenshot.png"
    full_page: bool = False


class SnapshotRequest(BaseModel):
    max_chars: int | None = None
    max_elements: int | None = None
    include_text: bool = True
    selector: str | None = None


class TabRequest(BaseModel):
    index: int | None = None
    tab_id: str | None = None


def error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": False, "error": code, "message": message, "details": details or {}}


def create_app(settings: Settings, profile: str, browser: str | None = None) -> FastAPI:
    manager = BrowserManager(settings, profile, browser)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await manager.start()
        try:
            yield
        finally:
            await manager.close()

    app = FastAPI(
        title="Persistent Browser Bridge",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.manager = manager
    app.state.server = None

    @app.exception_handler(LocatorResolutionError)
    async def locator_error(_request: Request, exc: LocatorResolutionError) -> JSONResponse:
        return JSONResponse(error(exc.code, str(exc), exc.details), status_code=400)

    @app.exception_handler(PlaywrightError)
    async def playwright_error(_request: Request, exc: PlaywrightError) -> JSONResponse:
        message = str(exc)
        lowered = message.lower()
        code = "page_closed" if "closed" in lowered else "browser_disconnected"
        return JSONResponse(error(code, message), status_code=409)

    @app.exception_handler(Exception)
    async def internal_error(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(error("internal_error", str(exc)), status_code=500)

    @app.get("/status")
    async def status() -> dict[str, Any]:
        result = await manager.status()
        result.update(
            {
                "daemon_running": True,
                "pid": os.getpid(),
                "pbb_version": __version__,
                "api_version": API_VERSION,
                "capabilities": ["snapshot_v2", "tabs", "download", "screenshot", "mcp", "iframe_basic"],
            }
        )
        return result

    @app.post("/start")
    async def start() -> dict[str, Any]:
        await manager.start()
        return await status()

    @app.post("/navigate")
    async def navigate(request: NavigateRequest) -> dict[str, Any]:
        return await manager.navigate(request.url)

    @app.post("/snapshot")
    async def snapshot(request: SnapshotRequest | None = None) -> dict[str, Any]:
        request = request or SnapshotRequest()
        return await manager.snapshot(
            request.max_chars, request.max_elements, request.include_text, request.selector
        )

    @app.post("/click")
    async def click(request: TargetRequest) -> dict[str, Any]:
        return await manager.click(request.target)

    @app.post("/fill")
    async def fill(request: FillRequest) -> dict[str, Any]:
        return await manager.fill(request.target, request.value)

    @app.post("/text")
    async def text(request: TargetRequest) -> dict[str, Any]:
        return await manager.text(request.target)

    @app.post("/download")
    async def download(request: DownloadRequest) -> dict[str, Any]:
        output = Path(request.output) if request.output else None
        return await manager.download(request.target, output)

    @app.post("/screenshot")
    async def screenshot(request: ScreenshotRequest) -> dict[str, Any]:
        return await manager.screenshot(Path(request.output), request.full_page)

    @app.get("/tabs")
    async def tabs() -> dict[str, Any]:
        return await manager.tabs()

    @app.post("/tabs/switch")
    async def switch_tab(request: TabRequest) -> dict[str, Any]:
        return await manager.switch_tab(request.index, request.tab_id)

    @app.post("/tabs/close")
    async def close_tab(request: TabRequest) -> dict[str, Any]:
        return await manager.close_tab(request.index, request.tab_id)

    @app.post("/close")
    async def close() -> dict[str, Any]:
        await manager.close()
        return {"success": True, "browser_running": False}

    @app.post("/shutdown")
    async def stop() -> dict[str, Any]:
        async def request_exit() -> None:
            await asyncio.sleep(0.1)
            if app.state.server is not None:
                app.state.server.should_exit = True

        asyncio.create_task(request_exit())
        return {"success": True, "message": "PBB daemon is shutting down"}

    return app
