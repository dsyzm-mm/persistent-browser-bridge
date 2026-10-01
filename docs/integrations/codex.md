# Codex MCP integration

Start PBB's MCP server with the generic command below:

```yaml
command: pbb
args: [mcp]
```

Add that command through the MCP-server configuration mechanism supported by your current Codex environment. Configuration formats change between clients and releases, so PBB intentionally does not invent a product-specific key here. Once connected, begin with `browser_status`, then `browser_start` only if necessary, and use `browser_snapshot` before DOM actions.

PBB's MCP process does not own the browser. It reconnects to the existing local daemon and PBB profile, so restarting the MCP client does not discard an authenticated profile.
