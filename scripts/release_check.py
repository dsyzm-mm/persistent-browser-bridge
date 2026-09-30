"""Run deterministic release checks; browser acceptance remains a manual/local step."""

import subprocess
import sys

commands = [
    [sys.executable, "-m", "ruff", "check", "."],
    [sys.executable, "-m", "pytest"],
    [sys.executable, "-m", "build"],
]
for command in commands:
    subprocess.run(command, check=True)
