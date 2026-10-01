# Persistent Browser Bridge

> Give AI coding agents a real persistent browser.

Persistent Browser Bridge (PBB) is a local browser-control layer built on Playwright. Instead of forcing AI agents to repeatedly inspect screenshots, PBB exposes lightweight DOM-first browser actions while preserving real browser sessions across runs.

**Persistent. DOM-first. Local-first. Agent-friendly. Low-context.**

PBB is an early v0.1 release for normal, authorized browser automation. It is not a CAPTCHA bypass, anti-detection toolkit, credential collector, or scraping-evasion framework.

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
AI agent -> pbb CLI -> localhost daemon -> Playwright
         -> real Edge/Chrome -> dedicated persistent profile -> website
```

The daemon binds to `127.0.0.1` by default and owns the Playwright process, active page, snapshot references, and download handling. CLI commands talk only to that local daemon, so a browser is not restarted for each action.

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

`pbb snapshot --json` returns the page title, URL, headings, bounded visible text, and interactive elements. It excludes scripts, styles, hidden elements, cookies, password values, and hidden tokens. Internal selectors remain inside the daemon.

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

Use `@1`, `@2`, or the explicit `s_123abc:@2` form. PBB rejects stale references after navigation or when element identity changes. It resolves targets conservatively: snapshot reference, unique selector, exact button/link role, label, placeholder, then exact text. Multiple matches return `ambiguous_target`; PBB never chooses one at random.

PowerShell reserves `@` syntax, so quote references there: `pbb click '@2'`. Bash and similar shells accept `pbb click @2`.

## Downloads

```console
pbb download "Download PDF"
pbb download @5 --output ./downloads
```

PBB waits for Playwright's download event and uses `save_as`. A click that does not emit a download returns `download_not_triggered` rather than reporting false success. The default destination is `~/Downloads/PBB`.

## Configuration

PBB reads `config.toml` from the platform's application config directory. Supported keys are `browser`, `default_profile`, `daemon_host`, `daemon_port`, `download_dir`, `timeout`, `headless`, and `snapshot_max_chars`. v0.1 rejects non-loopback daemon hosts.

Environment overrides: `PBB_BROWSER`, `PBB_PROFILE`, `PBB_PORT`, `PBB_DOWNLOAD_DIR`, and `PBB_TIMEOUT`.

## Privacy and security

PBB runs locally and includes no telemetry. Browser profiles remain on the device. PBB does not upload browsing history, cookies, credentials, or profiles; does not export cookies; and does not access a password manager. Treat the profile directory as sensitive local data. See [SECURITY.md](SECURITY.md).

## Agent integration

Recommended flow: check status, start if needed, inspect `snapshot --json`, use DOM actions, and only fall back to screenshots or Computer Use when the DOM is insufficient. Full guidance is in [docs/agent-integration.md](docs/agent-integration.md).

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

## Python SDK and MCP

A stable Python SDK and MCP server are planned for v0.2. The daemon's local HTTP API is an implementation detail in v0.1 and may change. No SDK or MCP support is claimed in this release.

## Limitations

- Snapshot references are daemon-memory state and do not survive daemon restarts.
- Shadow DOM, canvas-only controls, cross-origin frames, and highly virtualized UIs may need direct selectors or visual automation.
- Recovery covers closed pages and stale PBB locks; full crash replay is planned.
- One daemon controls one profile at a time in v0.1.
- Benchmarks are not published. PBB is designed to reduce repeated visual context usage, but no token or cost savings are claimed.

## Benchmark framework

The [benchmarks](benchmarks/README.md) directory defines a future comparison schema. Results are coming soon; no fabricated figures are included.

## Roadmap, contributing, and license

See [ROADMAP.md](ROADMAP.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the [MIT License](LICENSE).

