"""Agent-friendly command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from pbb.browser.browser_detection import detect_browsers
from pbb.browser.locks import ProfileLock, ProfileLockedError
from pbb.browser.profile import create_profile, delete_profile, list_profiles, profile_path
from pbb.browser.snapshot import format_snapshot
from pbb.config import config_path, load_settings
from pbb.daemon.client import DaemonClient, DaemonUnavailable
from pbb.daemon.lifecycle import port_available as _port_available
from pbb.daemon.lifecycle import start_daemon
from pbb.utils.paths import profiles_dir

app = typer.Typer(no_args_is_help=True, help="Persistent, DOM-first browser control for AI agents.")
profile_app = typer.Typer(help="Manage dedicated PBB browser profiles.")
app.add_typer(profile_app, name="profile")
console = Console(stderr=False)
error_console = Console(stderr=True)


def emit(data: dict[str, Any], as_json: bool, title: str | None = None) -> None:
    if as_json:
        # Keep agent output valid even when a Windows console uses a legacy code page.
        sys.stdout.write(json.dumps(data, ensure_ascii=True, default=str) + "\n")
        sys.stdout.flush()
        if not data.get("success", False):
            raise typer.Exit(1)
        return
    if not data.get("success", False):
        error_console.print(f"[red]{data.get('error', 'error')}:[/red] {data.get('message', '')}")
        if data.get("details"):
            error_console.print_json(json.dumps(data["details"], default=str))
        raise typer.Exit(1)
    if title:
        console.print(f"[bold]{title}[/bold]")
    for key, value in data.items():
        if key not in {"success", "details"} and value is not None:
            console.print(f"{key.replace('_', ' ').title()}: {value}")


def call(path: str, payload: dict[str, Any] | None, as_json: bool, title: str) -> dict[str, Any]:
    try:
        data = DaemonClient(load_settings()).post(path, payload)
    except DaemonUnavailable as exc:
        data = {"success": False, "error": "daemon_not_running", "message": str(exc), "details": {}}
    emit(data, as_json, title)
    return data


@app.command()
def start(
    profile: str = typer.Option(None, help="Dedicated PBB profile name."),
    browser: str = typer.Option(None, help="edge, chrome, chromium, or auto."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Start the local daemon and persistent browser."""
    settings = load_settings()
    selected_profile = profile or settings.default_profile
    data = start_daemon(settings, selected_profile, browser)
    emit(data, json_output, "PBB started" if data.get("success") else None)


@app.command()
def status(json_output: bool = typer.Option(False, "--json")) -> None:
    """Show daemon, browser, profile, and current page status."""
    try:
        data = DaemonClient(load_settings()).status()
    except DaemonUnavailable as exc:
        data = {"success": False, "error": "daemon_not_running", "message": str(exc), "details": {}}
    emit(data, json_output, "PBB Status")


@app.command("open")
def open_url(url: str, json_output: bool = typer.Option(False, "--json")) -> None:
    """Navigate the active page to URL."""
    call("/navigate", {"url": url}, json_output, "Page opened")


@app.command()
def snapshot(
    json_output: bool = typer.Option(False, "--json"),
    selector: str | None = typer.Option(None, "--selector"),
    max_elements: int | None = typer.Option(None, "--max-elements"),
    max_chars: int | None = typer.Option(None, "--max-chars"),
) -> None:
    """Capture a compact, safe DOM snapshot."""
    try:
        data = DaemonClient(load_settings()).post("/snapshot", {"selector": selector, "max_elements": max_elements, "max_chars": max_chars})
    except DaemonUnavailable as exc:
        data = {"success": False, "error": "daemon_not_running", "message": str(exc), "details": {}}
    if data.get("success") and not json_output:
        console.print(format_snapshot(data))
        return
    emit(data, json_output)


@app.command()
def click(target: str, json_output: bool = typer.Option(False, "--json")) -> None:
    """Click a snapshot reference, selector, or semantic target."""
    call("/click", {"target": target}, json_output, "Click complete")


@app.command()
def fill(target: str, value: str, json_output: bool = typer.Option(False, "--json")) -> None:
    """Fill an input without echoing its value in output."""
    call("/fill", {"target": target, "value": value}, json_output, "Fill complete")


@app.command()
def text(target: str, json_output: bool = typer.Option(False, "--json")) -> None:
    """Read visible text from a target."""
    call("/text", {"target": target}, json_output, "Text")


@app.command()
def download(
    target: str,
    output: Path = typer.Option(None, help="Destination directory or file."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Click a target and save the resulting Playwright download."""
    call(
        "/download",
        {"target": target, "output": str(output) if output else None},
        json_output,
        "Download complete",
    )


@app.command()
def screenshot(
    output: Path = typer.Argument(Path("pbb-screenshot.png")),
    full_page: bool = typer.Option(False, "--full-page"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Save a screenshot as a secondary inspection aid."""
    call(
        "/screenshot",
        {"output": str(output), "full_page": full_page},
        json_output,
        "Screenshot saved",
    )


@app.command()
def close(json_output: bool = typer.Option(False, "--json")) -> None:
    """Close the browser and stop the daemon."""
    call("/shutdown", {}, json_output, "PBB closed")


@app.command()
def tabs(json_output: bool = typer.Option(False, "--json")) -> None:
    """List open persistent browser tabs."""
    try:
        data = DaemonClient(load_settings()).request("GET", "/tabs")
    except DaemonUnavailable as exc:
        data = {"success": False, "error": "daemon_not_running", "message": str(exc), "details": {}}
    emit(data, json_output, "PBB Tabs")


tab_app = typer.Typer(help="Switch or close persistent browser tabs.")
app.add_typer(tab_app, name="tab")


@tab_app.callback(invoke_without_command=True)
def tab_switch(index: int = typer.Argument(None), json_output: bool = typer.Option(False, "--json")) -> None:
    """Switch to tab INDEX, such as `pbb tab 1`."""
    if index is None:
        return
    call("/tabs/switch", {"index": index}, json_output, "Tab switched")


@tab_app.command("close")
def tab_close(index: int, json_output: bool = typer.Option(False, "--json")) -> None:
    """Close a tab without ending the last remaining session tab."""
    call("/tabs/close", {"index": index}, json_output, "Tab closed")


@app.command()
def mcp() -> None:
    """Run the PBB stdio Model Context Protocol server."""
    from pbb.mcp.server import main

    main()


@app.command()
def shutdown(json_output: bool = typer.Option(False, "--json")) -> None:
    """Alias for close."""
    close(json_output)


@app.command()
def recover(json_output: bool = typer.Option(False, "--json")) -> None:
    """Remove stale PBB-owned profile locks only."""
    cleared: list[str] = []
    for name in list_profiles():
        lock = ProfileLock(profile_path(name), name)
        if lock.clear_stale():
            cleared.append(name)
    emit({"success": True, "cleared_profiles": cleared}, json_output, "Recovery complete")


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")) -> None:
    """Check Python, browsers, directories, and daemon port."""
    settings = load_settings()
    browsers = [item.as_dict() for item in detect_browsers()]
    result = {
        "success": True,
        "python": sys.version.split()[0],
        "playwright": "installed",
        "mcp_sdk": "installed",
        "mcp_server": "available",
        "browsers": browsers,
        "profiles_directory": str(profiles_dir()),
        "config": str(config_path()),
        "daemon_port": settings.daemon_port,
        "port_available": _port_available(settings.daemon_host, settings.daemon_port),
    }
    emit(result, json_output, "Persistent Browser Bridge Doctor")


@profile_app.command("create")
def profile_create(name: str, json_output: bool = typer.Option(False, "--json")) -> None:
    path = create_profile(name)
    emit({"success": True, "profile": name, "path": str(path)}, json_output, "Profile ready")


@profile_app.command("list")
def profile_list(json_output: bool = typer.Option(False, "--json")) -> None:
    names = list_profiles()
    if json_output:
        emit({"success": True, "profiles": names}, True)
        return
    table = Table(title="PBB Profiles")
    table.add_column("Name")
    table.add_column("Path")
    for name in names:
        table.add_row(name, str(profile_path(name)))
    console.print(table)


@profile_app.command("path")
def profile_show_path(name: str) -> None:
    console.print(str(profile_path(name)))


@profile_app.command("delete")
def profile_delete(
    name: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm deletion."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    if not yes and not typer.confirm(f"Delete PBB profile '{name}' and its browser data?"):
        raise typer.Abort()
    try:
        lock = ProfileLock(profile_path(name), name)
        if lock.path.exists() and not lock.is_stale():
            raise ProfileLockedError(f"Profile '{name}' is currently in use")
        delete_profile(name)
        emit({"success": True, "deleted": name}, json_output, "Profile deleted")
    except (FileNotFoundError, ProfileLockedError) as exc:
        emit(
            {"success": False, "error": "profile_locked", "message": str(exc), "details": {}},
            json_output,
        )


if __name__ == "__main__":
    app()
