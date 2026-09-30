# Installation

Use Python 3.11 or newer:

```console
git clone https://github.com/your-org/persistent-browser-bridge.git
cd persistent-browser-bridge
python -m pip install -e .
pbb doctor
```

Edge and Chrome system installations need no Playwright browser download. For fallback Chromium, run `python -m playwright install chromium`. PyPI installation is not available before the first published release.

