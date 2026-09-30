# Troubleshooting

## Edge or Chrome not found

Run `pbb doctor`. Select an installed browser with `--browser edge` or `--browser chrome`. For fallback Chromium, run `python -m playwright install chromium`.

## Playwright not installed

Reinstall with `python -m pip install -e .`. A system Edge/Chrome does not remove the Python Playwright dependency.

## Profile locked

Check `pbb status`. If no daemon owns the profile, run `pbb recover`. Never delete browser-native lock files.

## Port already in use or daemon stale

Set another loopback port with `PBB_PORT`, or stop the process using the configured port. Inspect the daemon log in the PBB platform data directory under `logs/daemon.log`.

## Browser opens then closes

Inspect the daemon log, confirm the selected channel exists, and try the other installed browser. Security software may also terminate automated browser processes.

## Login session lost

Confirm the same `--profile` name is used. Site policy may expire sessions or require device verification; complete that manually.

## Download not triggered

Confirm the target starts a browser download rather than opening an inline preview. PBB reports `download_not_triggered` after the configured timeout.

## PowerShell says the target argument is missing

Quote snapshot references because PowerShell reserves `@` syntax: use `pbb click '@2'` and `pbb fill '@1' 'value'`.

## Daemon already running

This is safe: `pbb start` reports the existing profile and PID instead of launching another daemon.

## Windows Defender warning

Use source from the official repository, inspect it, and do not bypass organizational policy. PBB does not require administrator privileges.

## Proxy or VPN issues

The controlled browser uses its normal system/network configuration. Test the URL manually in that PBB profile and consult organizational proxy policy.

