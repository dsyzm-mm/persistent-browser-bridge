# Agent integration

When browser interaction is required:

1. Run `pbb status`; start PBB only when needed.
2. Use `pbb snapshot --json` to inspect the current page.
3. Prefer `pbb click`, `pbb fill`, `pbb text`, and `pbb download`.
4. Reuse the current persistent browser profile and daemon.
5. Refresh the snapshot after navigation or a major DOM change.
6. Resolve `ambiguous_target` by choosing a more specific target; never guess.
7. Use screenshots or Computer Use only when DOM interaction cannot complete the task.
8. Never request, store, or echo user passwords.
9. Let the user complete authentication, CAPTCHA, 2FA, and device verification.
10. Continue with the same profile after the user finishes authentication.

