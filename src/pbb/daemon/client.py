"""Synchronous local daemon client used by the CLI."""

from __future__ import annotations

from typing import Any

import httpx

from pbb.config import Settings


class DaemonUnavailable(RuntimeError):
    pass


class DaemonClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = f"http://{settings.daemon_host}:{settings.daemon_port}"
        self.timeout = max(settings.timeout / 1000 + 5, 10)

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method, f"{self.base_url}{path}", json=payload, timeout=self.timeout
            )
        except httpx.RequestError as exc:
            raise DaemonUnavailable("PBB daemon is not running. Run `pbb start` first.") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise DaemonUnavailable("PBB daemon returned an invalid response") from exc
        return data

    def status(self) -> dict[str, Any]:
        return self.request("GET", "/status")

    def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("POST", path, payload or {})
