"""Start a named profile; authentication remains a manual user action."""

import subprocess

subprocess.run(["pbb", "start", "--profile", "work"], check=True)
subprocess.run(["pbb", "open", "https://example.com/login"], check=True)
print("Complete authentication manually in the PBB browser, then continue with this profile.")
