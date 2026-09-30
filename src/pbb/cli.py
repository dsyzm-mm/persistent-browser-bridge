"""Agent-friendly command-line interface."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
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
from pbb.utils.paths import logs_dir, profiles_dir

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


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


@app.command()
def start(
    profile: str = typer.Option(None, help="Dedicated PBB profile name."),
    browser: str = typer.Option(None, help="edge, chrome, chromium, or auto."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Start the local daemon and persistent browser."""
    settings = load_settings()
    selected_profile = profile or settings.default_profile
    client = DaemonClient(settings)
    try:
        current = client.status()
        current["message"] = "PBB already running"
        emit(current, json_output, "PBB already running")
        return
    except DaemonUnavailable:
        pass
    if not _port_available(settings.daemon_host, settings.daemon_port):
        emit(
            {
                "success": False,
                "error": "port_in_use",
                "message": f"Port {settings.daemon_port} is already in use",
                "details": {},
            },
            json_output,
        )
    create_profile(selected_profile)
    log_path = logs_dir() / "daemon.log"
    log_handle = log_path.open("a", encoding="utf-8")
    command = [sys.executable, "-m", "pbb.daemon.server", "--profile", selected_profile]
    if browser:
        command.extend(("--browser", browser))
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=log_handle,
        close_fds=True,
        creationflags=creationflags,
    )
    log_handle.close()
    deadline = time.monotonic() + 30
    last_error = "daemon startup timed out"
    while time.monotonic() < deadline:
        time.sleep(0.25)
        try:
            data = client.status()
            emit(data, json_output, "PBB started")
            return
        except DaemonUnavailable as exc:
            last_error = str(exc)
            if process.poll() is not None:
                last_error = f"daemon exited with code {process.returncode}"
                break
    emit(
        {
            "success": False,
            "error": "daemon_start_failed",
            "message": last_error,
            "details": {"log": str(log_path)},
        },
        json_output,
    )


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
def snapshot(json_output: bool = typer.Option(False, "--json")) -> None:
    """Capture a compact, safe DOM snapshot."""
    try:
        data = DaemonClient(load_settings()).post("/snapshot")
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
