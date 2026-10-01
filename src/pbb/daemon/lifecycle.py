"""Start or reuse the single local PBB daemon.

Both CLI and MCP use this module.  It deliberately starts the daemon process
instead of importing browser code, preserving one BrowserManager per profile.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from typing import Any

from pbb.browser.profile import create_profile
from pbb.config import Settings
from pbb.daemon.client import DaemonClient, DaemonUnavailable
from pbb.utils.paths import logs_dir


def port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def start_daemon(settings: Settings, profile: str, browser: str | None = None) -> dict[str, Any]:
    """Return current daemon status, starting it only when absent."""
    client = DaemonClient(settings)
    try:
        status = client.status()
        status["message"] = "PBB already running"
        return status
    except DaemonUnavailable:
        pass
    if not port_available(settings.daemon_host, settings.daemon_port):
        return {
            "success": False,
            "error": "port_in_use",
            "message": f"Port {settings.daemon_port} is already in use",
            "details": {},
        }
    create_profile(profile)
    log_path = logs_dir() / "daemon.log"
    log_handle = log_path.open("a", encoding="utf-8")
    command = [sys.executable, "-m", "pbb.daemon.server", "--profile", profile]
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
            return client.status()
        except DaemonUnavailable as exc:
            last_error = str(exc)
            if process.poll() is not None:
                last_error = f"daemon exited with code {process.returncode}"
                break
    return {
        "success": False,
        "error": "daemon_start_failed",
        "message": last_error,
        "details": {"log": str(log_path)},
    }
