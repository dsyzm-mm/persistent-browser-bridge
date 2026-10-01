"""Opt-in real MCP -> daemon -> Playwright acceptance coverage.

Run explicitly on a machine with Edge/Chrome:
PBB_RUN_BROWSER_INTEGRATION=1 python -m pytest tests/test_mcp_integration.py -q
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from pbb.config import load_settings
from pbb.daemon.lifecycle import start_daemon

pytestmark = pytest.mark.skipif(
    os.getenv("PBB_RUN_BROWSER_INTEGRATION") != "1",
    reason="set PBB_RUN_BROWSER_INTEGRATION=1 for real browser acceptance",
)


def result_data(result: object) -> dict[str, object]:
    content = result.content  # type: ignore[attr-defined]
    assert content
    return json.loads(content[0].text)


@pytest.mark.asyncio
async def test_mcp_stdio_reuses_daemon_and_operates_browser(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = (Path(__file__).parent / "fixtures" / "action_page.html").resolve().as_uri()
    monkeypatch.setenv("PBB_PORT", "19765")
    monkeypatch.setenv("PBB_PROFILE", "mcp-integration")
    monkeypatch.setenv("PBB_HEADLESS", "false")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "pbb.mcp.server"], env=dict(os.environ)
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            started = result_data(await session.call_tool("browser_start", {"browser": "edge"}))
            assert started["success"] is True
            opened = result_data(await session.call_tool("browser_open", {"url": fixture}))
            assert opened["success"] is True
            snapshot = result_data(await session.call_tool("browser_snapshot", {}))
            assert snapshot["success"] is True
            assert snapshot["snapshot_id"]
            assert snapshot["iframes"]
            assert result_data(await session.call_tool("browser_fill", {"target": "#message", "value": "MCP works"}))["success"] is True
            assert result_data(await session.call_tool("browser_click", {"target": "#submit"}))["success"] is True
            text = result_data(await session.call_tool("browser_text", {"target": "#result"}))
            assert text["text"] == "MCP works"
            opened_tab = result_data(await session.call_tool("browser_click", {"target": "#new-tab"}))
            assert opened_tab["new_tab_opened"] is True
            tabs = result_data(await session.call_tool("browser_tabs", {}))
            assert len(tabs["tabs"]) >= 2
            new_tab_index = int(opened_tab["new_tab_index"])
            assert result_data(await session.call_tool("browser_switch_tab", {"index": new_tab_index}))["success"] is True
            assert result_data(await session.call_tool("browser_close_tab", {"index": new_tab_index}))["success"] is True
            saved = result_data(await session.call_tool("browser_screenshot", {"path": str(isolated_dirs / "mcp.png")}))
            assert Path(str(saved["saved_path"])).exists()
            assert result_data(await session.call_tool("browser_close", {}))["success"] is True


@pytest.mark.asyncio
async def test_mcp_stdio_downloads_through_existing_daemon(
    isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = (Path(__file__).parent / "fixtures" / "action_page.html").resolve().as_uri()
    monkeypatch.setenv("PBB_PORT", "19766")
    monkeypatch.setenv("PBB_PROFILE", "mcp-download-integration")
    monkeypatch.setenv("PBB_HEADLESS", "false")
    assert start_daemon(load_settings(), "mcp-download-integration", "edge")["success"] is True
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "pbb.mcp.server"], env=dict(os.environ)
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        assert result_data(await session.call_tool("browser_start", {}))["success"] is True
        assert result_data(await session.call_tool("browser_open", {"url": fixture}))["success"] is True
        downloaded = result_data(
            await session.call_tool(
                "browser_download",
                {"target": "#download", "output_dir": str(isolated_dirs / "downloads")},
            )
        )
        assert downloaded["success"] is True, downloaded
        assert Path(str(downloaded["saved_path"])).exists()
        assert result_data(await session.call_tool("browser_close", {}))["success"] is True
