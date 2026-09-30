"""Invoke PBB's stable v0.1 CLI from Python."""

import json
import subprocess

result = subprocess.run(["pbb", "snapshot", "--json"], check=True, capture_output=True, text=True)
snapshot = json.loads(result.stdout)
print(snapshot["title"])
