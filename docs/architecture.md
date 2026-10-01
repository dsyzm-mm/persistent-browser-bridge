# Architecture

CLI and the stdio MCP server are short-lived clients. A loopback FastAPI daemon owns one `BrowserManager`, which owns the Playwright runtime, persistent context, active page, snapshot store, and profile lock. This keeps browser state alive across commands and MCP client reconnects.

`launch_persistent_context` receives only a PBB-owned profile path. Browser selection prefers Edge, then Chrome, then Playwright Chromium. Snapshot element selectors never leave the daemon; public references are validated against snapshot identity, URL, selector uniqueness, and accessible name before use.

The trust boundary is the local operating-system account. MCP is stdio-only in v0.2; it opens no new listener. The daemon remains loopback-only and there is no telemetry, remote service, or multi-agent isolation.

