# Architecture

The CLI is a short-lived client. A loopback FastAPI daemon owns one `BrowserManager`, which owns the Playwright runtime, persistent context, active page, snapshot store, and profile lock. This keeps browser state alive across commands.

`launch_persistent_context` receives only a PBB-owned profile path. Browser selection prefers Edge, then Chrome, then Playwright Chromium. Snapshot element selectors never leave the daemon; public references are validated against snapshot identity, URL, selector uniqueness, and accessible name before use.

The trust boundary is the local operating-system account. v0.1 has no remote listener, authentication protocol, telemetry, MCP server, or multi-agent isolation.

