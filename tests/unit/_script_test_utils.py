from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_python_script(script_path: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
