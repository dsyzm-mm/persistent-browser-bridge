# Claude Code MCP integration

Use PBB as a stdio MCP server:

```yaml
command: pbb
args: [mcp]
```

Register this command using the current Claude Code MCP configuration workflow. Refer to Claude Code's current MCP documentation for the exact command or settings format; PBB does not depend on a Claude-specific transport. The recommended sequence is `browser_status`, `browser_start` when absent, `browser_open`, `browser_snapshot`, then precise DOM actions.

The server remains local and uses the existing PBB daemon, preserving the dedicated profile across Claude Code reconnects.
