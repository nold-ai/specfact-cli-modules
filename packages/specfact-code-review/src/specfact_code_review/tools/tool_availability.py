"""Resolve external review-tool executables and emit skip findings when missing."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Literal

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import tool_error
from specfact_code_review.run.findings import ReviewFinding


ReviewToolId = Literal[
    "ruff",
    "radon",
    "semgrep",
    "basedpyright",
    "pylint",
    "crosshair",
    "pytest",
]

# tool_id -> pip distribution name(s) declared on module-package.yaml
REVIEW_TOOL_PIP_PACKAGES: dict[ReviewToolId, str] = {
    "ruff": "ruff",
    "radon": "radon",
    "semgrep": "semgrep",
    "basedpyright": "basedpyright",
    "pylint": "pylint",
    "crosshair": "crosshair-tool",
    "pytest": "pytest",
}

# Pytest is listed in REVIEW_TOOL_PIP_PACKAGES for documentation parity with module-package.yaml, but it is
# intentionally omitted here: skip_if_tool_missing() only consults _EXECUTABLE_ON_PATH and would treat a
# stray `pytest` script on PATH as “tool present” even when the review interpreter cannot import pytest.
# TDD coverage instead uses skip_if_pytest_unavailable(), which probes importlib.util.find_spec("pytest")
# and importlib.util.find_spec("pytest_cov") for the active Python environment.
_EXECUTABLE_ON_PATH: dict[ReviewToolId, str] = {
    "ruff": "ruff",
    "radon": "radon",
    "semgrep": "semgrep",
    "basedpyright": "basedpyright",
    "pylint": "pylint",
    "crosshair": "crosshair",
}


def _skip_message(tool_id: ReviewToolId) -> str:
    pip_name = REVIEW_TOOL_PIP_PACKAGES[tool_id]
    return (
        f"Review checks for {tool_id} were skipped: executable not found on PATH. "
        f"Install the `{pip_name}` package (declared on the code-review module) so the tool is available."
    )


@beartype
@require(lambda tool_id: tool_id in REVIEW_TOOL_PIP_PACKAGES)
@ensure(lambda result: isinstance(result, list))
def skip_if_tool_missing(tool_id: ReviewToolId, file_path: Path) -> list[ReviewFinding]:
    """Return a single tool_error when the CLI is absent; otherwise return an empty list."""
    exe = _EXECUTABLE_ON_PATH.get(tool_id)
    if exe is not None and shutil.which(exe) is None:
        return [
            tool_error(
                tool=tool_id,
                file_path=file_path,
                message=_skip_message(tool_id),
                severity="warning",
            )
        ]
    return []


@beartype
@require(lambda file_path: isinstance(file_path, Path))
@ensure(lambda result: isinstance(result, list))
def skip_if_pytest_unavailable(file_path: Path) -> list[ReviewFinding]:
    """Skip TDD gate when pytest cannot be imported in the current interpreter."""
    if importlib.util.find_spec("pytest") is None:
        return [
            tool_error(
                tool="pytest",
                file_path=file_path,
                message=(
                    "Review checks for pytest were skipped: pytest is not importable in this environment. "
                    "Install `pytest` and `pytest-cov` (declared on the code-review module)."
                ),
                severity="warning",
            )
        ]
    if importlib.util.find_spec("pytest_cov") is None:
        return [
            tool_error(
                tool="pytest",
                file_path=file_path,
                message=(
                    "Review checks for pytest coverage were skipped: pytest-cov is not importable. "
                    "Install `pytest-cov` (declared on the code-review module)."
                ),
                severity="warning",
            )
        ]
    return []
