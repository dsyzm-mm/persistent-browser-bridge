"""stdio MCP server backed exclusively by the local PBB daemon."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from pbb.config import load_settings
from pbb.daemon.client import DaemonClient, DaemonUnavailable
from pbb.daemon.lifecycle import start_daemon

mcp = FastMCP(
    "Persistent Browser Bridge",
    instructions=(
        "Use browser_snapshot before DOM actions. PBB maintains a local persistent browser "
        "profile through one shared daemon; snapshot references become stale after page changes."
    ),
)


def _error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": False, "error": code, "message": message, "details": details or {}}


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        client = DaemonClient(load_settings())
        return client.request(method, path, payload)
    except DaemonUnavailable as exc:
        return _error("daemon_not_running", str(exc))


@mcp.tool(description="Start or reuse the local PBB daemon and its persistent browser session. Never starts a second browser when PBB is already running.")
def browser_start(profile: str | None = None, browser: str | None = None) -> dict[str, Any]:
    settings = load_settings()
    return start_daemon(settings, profile or settings.default_profile, browser)


@mcp.tool(description="Return local daemon, persistent browser, active page, capability, and tab status.")
def browser_status() -> dict[str, Any]:
    return _request("GET", "/status")


@mcp.tool(description="Navigate the active PBB browser tab to a URL.")
def browser_open(url: str) -> dict[str, Any]:
    return _request("POST", "/navigate", {"url": url})


@mcp.tool(description="Return a compact, agent-friendly representation of the active page. Prefer this over screenshots for routine DOM inspection.")
def browser_snapshot(max_chars: int | None = None, include_text: bool = True, max_elements: int | None = None, selector: str | None = None) -> dict[str, Any]:
    return _request("POST", "/snapshot", {"max_chars": max_chars, "include_text": include_text, "max_elements": max_elements, "selector": selector})


@mcp.tool(description="Click a DOM element by snapshot reference, unique selector, role/name object, label, placeholder, or exact text.")
def browser_click(target: str | dict[str, str]) -> dict[str, Any]:
    return _request("POST", "/click", {"target": target})


@mcp.tool(description="Fill a DOM input. Password values are sent to the browser but never returned, logged, or included in snapshots.")
def browser_fill(target: str | dict[str, str], value: str) -> dict[str, Any]:
    return _request("POST", "/fill", {"target": target, "value": value})


@mcp.tool(description="Read visible text from one uniquely resolved DOM element.")
def browser_text(target: str | dict[str, str]) -> dict[str, Any]:
    return _request("POST", "/text", {"target": target})


@mcp.tool(description="Trigger and capture a Playwright download, then save it to the local filesystem.")
def browser_download(target: str | dict[str, str], output_dir: str | None = None) -> dict[str, Any]:
    return _request("POST", "/download", {"target": target, "output": output_dir})


@mcp.tool(description="Save a screenshot of the active PBB tab. Use it only when a compact DOM snapshot is insufficient.")
def browser_screenshot(path: str | None = None, full_page: bool = False) -> dict[str, Any]:
    return _request("POST", "/screenshot", {"output": path or "pbb-screenshot.png", "full_page": full_page})


@mcp.tool(description="List all open PBB browser tabs, including their stable-in-session index, title, URL, and active flag.")
def browser_tabs() -> dict[str, Any]:
    return _request("GET", "/tabs")


@mcp.tool(description="Make a PBB tab active using its index or tab_id returned by browser_tabs.")
def browser_switch_tab(index: int | None = None, tab_id: str | None = None) -> dict[str, Any]:
    return _request("POST", "/tabs/switch", {"index": index, "tab_id": tab_id})


@mcp.tool(description="Close one PBB tab by index or tab_id. PBB refuses to close the last tab so the persistent session remains usable.")
def browser_close_tab(index: int | None = None, tab_id: str | None = None) -> dict[str, Any]:
    return _request("POST", "/tabs/close", {"index": index, "tab_id": tab_id})


@mcp.tool(description="Stop the PBB daemon and close its persistent browser session. Use browser_close_tab to close only one tab.")
def browser_close() -> dict[str, Any]:
    return _request("POST", "/shutdown", {})


def main() -> None:
    """Run only stdio MCP transport; no network listener is opened."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
