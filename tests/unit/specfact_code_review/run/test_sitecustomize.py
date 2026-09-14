"""Native Python CLI startup must fail before user code when runtime context is absent."""

import os
import subprocess
import sys
from pathlib import Path

from specfact_code_review.run import target_bootstrap


def test_project_python_fails_closed_before_executing_code_without_descriptor() -> None:
    env = {**os.environ, "PYTHONPATH": str(Path(target_bootstrap.__file__).parent), "SPECFACT_PROJECT_PYTHON": "1"}
    result = subprocess.run(
        [sys.executable, "-s", "-c", 'print("MUST_NOT_EXECUTE")'], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 78
    assert not result.stdout
