# Security notes

PBB is intended for normal automation on websites the user is authorized to operate. It does not bypass CAPTCHA, 2FA, anti-bot controls, or device confirmation. It does not export cookies or credentials. The daemon is loopback-only, and non-loopback configuration is rejected. See the root `SECURITY.md` for reporting instructions.

