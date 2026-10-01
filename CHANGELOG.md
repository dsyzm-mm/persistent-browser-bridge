# Changelog

All notable changes follow Keep a Changelog. This project uses Semantic Versioning.

## [Unreleased]

## [0.2.0]

### Added

- Local stdio MCP server with browser lifecycle, navigation, snapshot, action, download, screenshot, and tab tools.
- Snapshot v2 with form state, dialogs, table summaries, iframe summaries, scopes, and output limits.
- Tab listing, switching, and guarded closing for CLI, daemon API, and MCP.
- Agent integration documentation for generic MCP clients, Codex, Claude Code, and Cursor.

### Changed

- CLI and MCP now share the existing local daemon as the single browser service boundary.
- Locator resolution accepts structured role/name targets and protects stale snapshot references.

### Security

- MCP uses stdio only and never opens a new public listener.
- Sensitive input values remain excluded from responses, logs, and snapshots.

## [0.1.0] - 2026-09-30

### Added

- Persistent Edge, Chrome, and Chromium profiles.
- Local FastAPI daemon and Typer CLI.
- Compact safe DOM snapshots and guarded snapshot references.
- Navigation, click, fill, text, download, and screenshot actions.
- JSON output, profile locks, stale-lock recovery, tests, and documentation.

