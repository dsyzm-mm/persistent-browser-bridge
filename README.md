# Persistent Browser Bridge

> Give AI coding agents a real persistent browser.

Persistent Browser Bridge (PBB) is a local browser-control layer built on Playwright. Instead of forcing AI agents to repeatedly inspect screenshots, PBB exposes lightweight DOM-first browser actions while preserving real browser sessions across runs.

**Persistent. DOM-first. Local-first. Agent-friendly. Low-context.**

PBB v0.2 adds first-class Model Context Protocol (MCP) support for normal, authorized browser automation. It is not a CAPTCHA bypass, anti-detection toolkit, credential collector, or scraping-evasion framework.

## Why PBB

Visual automation remains valuable when a page cannot be understood through the DOM. For routine forms, links, text, and downloads, a compact DOM snapshot is faster to inspect and less dependent on screen coordinates. A dedicated persistent browser profile also keeps cookies, local storage, IndexedDB, and login state between runs without touching your everyday browser profile.

| Feature | Computer Use | PBB |
|---|---|---|
| Interaction | Visual | DOM-first |
| Browser state | Depends on environment | Dedicated persistent profile |
| Login reuse | Environment dependent | Reuses its PBB profile |
| Element targeting | Vision and coordinates | DOM locators and snapshot references |
| Downloads | UI dependent | Playwright download events |
| Agent context | Visual-heavy | Compact DOM snapshot |
| Recovery | Agent dependent | Basic page and stale-lock recovery |
| Local-first | Depends | Yes |

PBB complements visual browser automation rather than replacing every use case.

## Architecture

```text
Codex / Claude Code / Cursor / Agent
                 |
            CLI or MCP
                 |
          PBB service boundary
                 |
       local browser daemon -> Playwright
                 |
     persistent Edge / Chrome profile -> website
```

The daemon binds to `127.0.0.1` by default and owns the only Playwright process, active page, snapshot references, and download handling. Both CLI and MCP are short-lived local clients of that daemon, so a browser is not restarted for each action or MCP reconnection.

## Installation

PBB requires Python 3.11 or newer. Edge is preferred, Chrome is supported, and Playwright Chromium is the fallback.

Install the published package:

```console
python -m pip install persistent-browser-bridge
```

Or install the latest repository checkout for development:

```console
cd persistent-browser-bridge
python -m pip install -e .
```

If no system browser is available, install Playwright Chromium with `python -m playwright install chromium`.

## Quick start

```console
pbb doctor
pbb profile create default
pbb start --profile default
pbb open https://example.com
pbb snapshot
pbb text h1
pbb close
```

The first start opens a visible browser. Sign in manually when needed. PBB never asks for or stores account passwords; CAPTCHA, 2FA, device confirmation, and reauthentication remain user actions.

## Profiles

PBB profiles are separate from daily Edge and Chrome profiles:

```console
pbb profile create work
pbb profile list
pbb profile path work
pbb profile delete work
```

Deletion requires confirmation (or explicit `--yes`) and only removes directories carrying PBB's own profile marker. PBB never deletes native Edge or Chrome lock files.

## CLI

| Command | Purpose |
|---|---|
| `pbb start --profile NAME` | Start the daemon and persistent browser |
| `pbb status` | Show process, profile, browser, page, and tabs |
| `pbb open URL` | Navigate and wait for `domcontentloaded` |
| `pbb snapshot` | Return a compact DOM snapshot |
| `pbb tabs` / `pbb tab INDEX` | List or switch persistent browser tabs |
| `pbb tab close INDEX` | Close one tab without closing the final session tab |
| `pbb click TARGET` | Click a reference, selector, or semantic target |
| `pbb fill TARGET VALUE` | Fill a field; password values are never returned |
| `pbb text TARGET` | Read visible element text |
| `pbb download TARGET` | Wait for a real download event and save the file |
| `pbb screenshot [PATH]` | Capture a supporting screenshot |
| `pbb recover` | Clear stale PBB-owned locks |
| `pbb close` | Close browser and daemon |

Every action supports `--json`. Failures use a stable shape:

```json
{"success": false, "error": "element_not_found", "message": "...", "details": {}}
```

## Snapshots and targets

Snapshot v2 returns the page title, URL, active tab, headings, form state, dialogs, iframe summary, table previews, bounded visible text, and interactive elements. It excludes scripts, styles, hidden elements, cookies, password values, and hidden tokens. Internal selectors remain inside the daemon. Use `--selector`, `--max-elements`, and `--max-chars` to bound a focused snapshot.

```json
{
  "success": true,
  "snapshot_id": "s_123abc",
  "elements": [
    {"id": 1, "role": "textbox", "name": "Email", "placeholder": "you@example.com"},
    {"id": 2, "role": "button", "name": "Sign in"}
  ]
}
```

Use `@1`, `@2`, or the explicit `s_123abc:@2` form. PBB rejects `stale_snapshot_reference` after navigation or when element identity changes. It resolves targets conservatively: snapshot reference, unique selector, exact role/name, label, placeholder, exact text, then an unambiguous partial text match. Multiple matches return `ambiguous_target`; PBB never chooses one at random. Basic iframe elements receive a `frame` field and remain usable through their snapshot reference.

PowerShell reserves `@` syntax, so quote references there: `pbb click '@2'`. Bash and similar shells accept `pbb click @2`.

## Downloads

```console
pbb download "Download PDF"
pbb download @5 --output ./downloads
```

PBB waits for Playwright's download event and uses `save_as`. A click that does not emit a download returns `download_not_triggered` rather than reporting false success. The default destination is `~/Downloads/PBB`.

## Configuration

PBB reads `config.toml` from the platform's application config directory. Supported keys are `browser`, `default_profile`, `daemon_host`, `daemon_port`, `download_dir`, `timeout`, `headless`, and `snapshot_max_chars`. v0.1 rejects non-loopback daemon hosts.

Environment overrides: `PBB_BROWSER`, `PBB_PROFILE`, `PBB_PORT`, `PBB_DOWNLOAD_DIR`, `PBB_TIMEOUT`, and `PBB_HEADLESS`.

## Privacy and security

PBB runs locally and includes no telemetry. Browser profiles remain on the device. PBB does not upload browsing history, cookies, credentials, or profiles; does not export cookies; and does not access a password manager. Treat the profile directory as sensitive local data. See [SECURITY.md](SECURITY.md).

## Agent integration

Recommended MCP flow: `browser_status`, `browser_start` if needed, `browser_open`, `browser_snapshot`, DOM actions, then another snapshot. Full guidance is in [docs/mcp.md](docs/mcp.md) and [docs/agent-integration.md](docs/agent-integration.md).

### Codex integration

Copy this prompt into a project instruction:

```text
Always prefer Persistent Browser Bridge for browser automation when it is available.

Browser strategy:
1. Run `pbb status` and start PBB if needed.
2. Use `pbb snapshot --json` to inspect the current page.
3. Prefer `pbb click`, `pbb fill`, `pbb text`, and `pbb download`.
4. Reuse the existing persistent browser profile. Do not launch another browser unless necessary.
5. Use screenshots or Computer Use only when DOM-based interaction fails.
6. Never request or store account passwords.
7. Let the user manually complete authentication, CAPTCHA, 2FA, or device verification.
8. Continue using the same profile after authentication.
```

## MCP

Run the standard-input/output MCP server with:

```console
pbb mcp
```

The generic client configuration is `command: pbb`, `args: ["mcp"]`. It exposes `browser_start`, `browser_status`, `browser_open`, `browser_snapshot`, `browser_click`, `browser_fill`, `browser_text`, `browser_download`, `browser_screenshot`, `browser_tabs`, `browser_switch_tab`, `browser_close_tab`, and `browser_close`. It does not open a public MCP port. See [docs/mcp.md](docs/mcp.md), plus setup notes for [Codex](docs/integrations/codex.md), [Claude Code](docs/integrations/claude-code.md), and [Cursor](docs/integrations/cursor.md).

| Interface | Best for |
|---|---|
| CLI | scripts and shell-based agents |
| MCP | native agent tool integration |

## Limitations

- Snapshot references are daemon-memory state and do not survive daemon restarts.
- Canvas-only controls and highly virtualized UIs may need direct selectors or visual automation. Playwright's normal locator support is used for Shadow DOM and frames; pages that restrict access return a normal action error.
- Recovery recreates a closed active tab and retains a daemon-owned profile across MCP client reconnects. It does not replay arbitrary in-progress work after a browser crash.
- One daemon controls one profile at a time in v0.2.
- Benchmarks are not published. PBB is designed to reduce repeated visual context usage, but no token or cost savings are claimed.

## Benchmark framework

The [benchmarks](benchmarks/README.md) directory defines a future comparison schema. Results are coming soon; no fabricated figures are included.

## Roadmap, contributing, and license

See [ROADMAP.md](ROADMAP.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the [MIT License](LICENSE).

