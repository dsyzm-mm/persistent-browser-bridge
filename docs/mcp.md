# MCP server

PBB v0.2 provides a standard MCP server over stdio. It is a small client of the existing local PBB daemon: it never creates a `BrowserManager`, a Playwright context, a profile, or a second browser of its own.

## Install and start

```console
python -m pip install persistent-browser-bridge
pbb mcp
```

Use this generic client entry:

```yaml
command: pbb
args: [mcp]
```

The exact configuration file and UI vary by MCP client. The server uses stdio and opens no network port. If a daemon is already running, `browser_start` reuses it; if the MCP process exits, the daemon and its persistent profile remain available to a later MCP client.

## Tool reference

All tools return an object with `success`. Failed operations return `error`, `message`, and `details`; they do not return bulky daemon logs.

| Tool | Input | Result / common errors | Example |
|---|---|---|---|
| `browser_start` | optional `profile`, `browser` | daemon/browser/profile/pid; `port_in_use` | `{"profile":"work"}` |
| `browser_status` | none | daemon, browser, page, tabs, capabilities | `{}` |
| `browser_open` | `url` | URL, title, duration; `navigation_timeout` | `{"url":"https://example.com"}` |
| `browser_snapshot` | optional `max_chars`, `max_elements`, `include_text`, `selector` | Snapshot v2; `daemon_not_running` | `{"selector":"#main"}` |
| `browser_click` | `target` | URL, duration, optional new tab; `ambiguous_target`, `stale_snapshot_reference` | `{"target":"@2"}` |
| `browser_fill` | `target`, `value` | redaction flag, URL; locator errors | `{"target":{"label":"Email"},"value":"me@example.com"}` |
| `browser_text` | `target` | visible `text`; locator errors | `{"target":"h1"}` |
| `browser_download` | `target`, optional `output_dir` | saved path, filename, size; `download_not_triggered` | `{"target":"Download PDF"}` |
| `browser_screenshot` | optional `path`, `full_page` | saved path | `{"full_page":true}` |
| `browser_tabs` | none | current tab index, stable-in-session id, title, URL, active | `{}` |
| `browser_switch_tab` | `index` or `tab_id` | selected tab; `tab_not_found` | `{"index":1}` |
| `browser_close_tab` | `index` or `tab_id` | remaining tab count; `cannot_close_last_tab` | `{"index":1}` |
| `browser_close` | none | daemon shutdown acknowledgement | `{}` |

`target` may be a snapshot reference, unique selector, exact text, or a structured role/name, label, placeholder, or text object. PBB refuses ambiguous matches rather than selecting a nearby element.

## Snapshot, profiles, and safety

Snapshots are compact DOM views, not HTML dumps. They omit password values, hidden inputs, and token-like hidden data. A password may be supplied to `browser_fill`, but PBB neither logs nor returns it. Snapshot references are tied to the current page and element fingerprint; on a meaningful change PBB returns `stale_snapshot_reference`, and the agent should call `browser_snapshot` again.

PBB profiles are dedicated local browser directories. Authentication, CAPTCHA, 2FA, and device confirmation stay user-driven. PBB does not read a password manager, export cookies, or expose a public browser-control service.

## Troubleshooting

- Call `browser_status` first. Use `browser_start` only when the daemon is absent.
- If a reference is stale, get a fresh snapshot rather than retrying it.
- If a target is ambiguous, use a snapshot reference or a more specific selector/role-name object.
- A download must trigger a browser download event; inline previews can return `download_not_triggered`.
- `browser_close` stops the daemon; closing a tab is instead `browser_close_tab`.
