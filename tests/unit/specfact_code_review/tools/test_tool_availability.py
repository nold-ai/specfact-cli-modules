"""Unit tests for review tool PATH / import skip helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from specfact_code_review.tools.tool_availability import (
    REVIEW_TOOL_PIP_PACKAGES,
    skip_if_pytest_unavailable,
    skip_if_tool_missing,
)


def test_skip_if_tool_missing_empty_when_executable_present() -> None:
    with patch("specfact_code_review.tools.tool_availability.shutil.which", return_value="/usr/bin/ruff"):
        assert skip_if_tool_missing("ruff", Path("x.py")) == []


def test_skip_if_tool_missing_finds_single_finding_when_absent() -> None:
    with patch("specfact_code_review.tools.tool_availability.shutil.which", return_value=None):
        findings = skip_if_tool_missing("ruff", Path("src/m.py"))
    assert len(findings) == 1
    assert findings[0].tool == "ruff"
    assert "ruff" in findings[0].message.lower()


def test_skip_if_pytest_unavailable_when_pytest_missing() -> None:
    with patch("importlib.util.find_spec", return_value=None):
        findings = skip_if_pytest_unavailable(Path("tests/test_x.py"))
    assert len(findings) == 1
    assert findings[0].tool == "pytest"


def test_review_tool_pip_packages_covers_each_tool_id() -> None:
    assert set(REVIEW_TOOL_PIP_PACKAGES) == {
        "ruff",
        "radon",
        "semgrep",
        "basedpyright",
        "pylint",
        "crosshair",
        "pytest",
    }
