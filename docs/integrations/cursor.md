# Cursor MCP integration

Configure a stdio MCP server with:

```yaml
command: pbb
args: [mcp]
```

Add it through the current Cursor MCP settings experience and consult Cursor's current documentation for its exact settings schema. PBB does not start an HTTP endpoint. Use `browser_snapshot` for normal inspection and refresh it after navigation or a major page change before using `@` references.
