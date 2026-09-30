"""Daemon process entry point."""

from __future__ import annotations

import argparse

import uvicorn

from pbb.config import load_settings
from pbb.daemon.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--browser")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    settings = load_settings()
    if args.port:
        settings.daemon_port = args.port
    app = create_app(settings, args.profile, args.browser)
    config = uvicorn.Config(
        app,
        host=settings.daemon_host,
        port=settings.daemon_port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    app.state.server = server
    server.run()


if __name__ == "__main__":
    main()
