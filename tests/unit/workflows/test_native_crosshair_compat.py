"""Exercise the pinned CrossHair binary used for independent contracts review."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
SUBJECT = """\
from pathlib import Path
from icontract import ensure
from crosshair.core import get_constructor_signature

print("candidate import output")

class Example:
    def __new__(cls, *values: int, flag: bool = False, **named: int):
        return super().__new__(cls)

    def __init__(self, *values: int, flag: bool = False, **named: int):
        self.values = values
        self.flag = flag
        self.named = named

signature = get_constructor_signature(Example)
assert tuple(signature.parameters) == ("values", "flag", "named")
assert signature.bind(1, 2, flag=True, extra=3).arguments["values"] == (1, 2)
assert get_constructor_signature(Path).bind("example", "child")

@ensure(lambda result: result >= 0)
def checked(value: int) -> int:
    print("candidate contract output")
    return -1
"""


@pytest.fixture
def isolated_crosshair(tmp_path: Path) -> Path:
    """Copy real installed CrossHair Python files without mutating the test environment."""
    installed = find_spec("crosshair")
    assert installed is not None and installed.origin is not None
    shutil.copytree(Path(installed.origin).parent, tmp_path / "crosshair", ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def _apply_patch(site: Path) -> subprocess.CompletedProcess[str]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/native-pr-review.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["independent-review"]["steps"]
    script = next(step["run"] for step in steps if step.get("name") == "Apply verified CrossHair compatibility patch")
    python = site / "native-independent-review" / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_PURELIB"\n', encoding="utf-8")
    python.chmod(0o755)
    return subprocess.run(
        ["bash", "-c", script],
        env={**os.environ, "GITHUB_WORKSPACE": str(ROOT), "RUNNER_TEMP": str(site), "TEST_PURELIB": str(site)},
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )


def test_pinned_crosshair_analyzes_variadic_constructor(isolated_crosshair: Path) -> None:
    patch = _apply_patch(isolated_crosshair)
    assert patch.returncode == 0, patch.stdout + patch.stderr
    subject = isolated_crosshair / "constructor_subject.py"
    subject.write_text(SUBJECT, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "crosshair", "check", str(subject)],
        cwd=isolated_crosshair,
        env={**os.environ, "PYTHONPATH": str(isolated_crosshair)},
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, result.stderr
    assert "false when calling checked" in result.stdout, result.stderr
    assert "candidate import output" not in result.stdout
    assert "candidate contract output" not in result.stdout
    assert "candidate import output" in result.stderr
    assert "candidate contract output" in result.stderr


def test_native_crosshair_patch_rejects_unexpected_input(isolated_crosshair: Path) -> None:
    package = isolated_crosshair / "crosshair"
    altered = package / "main.py"
    altered.write_bytes(altered.read_bytes() + b"# unexpected upstream bytes\n")
    original = (package / "core.py").read_bytes()
    result = _apply_patch(isolated_crosshair)
    assert result.returncode != 0
    assert (package / "core.py").read_bytes() == original
