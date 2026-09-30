# Contributing

Thanks for helping PBB. Open an issue before substantial changes so scope and safety expectations are clear.

```console
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
```

On macOS or Linux, activate with `source .venv/bin/activate`. Keep changes typed, focused, and tested. Never add credential extraction, CAPTCHA bypass, fingerprint spoofing, anti-detection, or scraping-evasion features. Do not place real profiles or credentials in fixtures.

Commits should describe coherent changes, for example `feat: add compact DOM snapshot` or `fix: reject stale profile references`. By participating, you agree to follow the Code of Conduct.

