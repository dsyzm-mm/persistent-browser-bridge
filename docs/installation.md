# Installation

Use Python 3.11 or newer. Install the released package from PyPI:

```console
python -m pip install persistent-browser-bridge
pbb doctor
```

For development from a repository checkout:

```console
cd persistent-browser-bridge
python -m pip install -e .
pbb doctor
```

Edge and Chrome system installations need no Playwright browser download. For fallback Chromium, run `python -m playwright install chromium`.

