"""Fill and submit a form through the PBB CLI."""

import subprocess

subprocess.run(["pbb", "fill", "Email", "hello@example.com"], check=True)
subprocess.run(["pbb", "click", "Submit"], check=True)
