# Security policy

## Supported versions

Security fixes are provided for the latest released minor version.

## Design boundaries

PBB binds to loopback only, has no remote mode in v0.1, and includes no telemetry. It does not upload profiles, export cookies, read password managers, bypass CAPTCHA or 2FA, spoof fingerprints, or provide anti-detection behavior. Authentication must be completed by the user.

Dedicated PBB profiles contain sensitive browser state. Protect them using normal operating-system account controls. Do not sync or publish these directories. PBB lock recovery only removes `profile.lock`, a file created by PBB; it never removes browser-native lock files.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private security advisory flow for the repository. Include affected version, reproduction steps, impact, and any proposed mitigation. Maintainers should acknowledge a report within seven days.

