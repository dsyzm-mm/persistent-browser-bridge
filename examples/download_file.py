"""Download through a Playwright download event."""

import subprocess

subprocess.run(["pbb", "download", "Download PDF", "--output", "downloads"], check=True)
