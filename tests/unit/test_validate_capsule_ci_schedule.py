"""Capsule-safe coverage for the indexed workflow byte contract."""

from __future__ import annotations

import runpy
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import validate_capsule_ci_schedule as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/validate_capsule_ci_schedule.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/pr-orchestrator.yml"


def test_reviewed_workflow_bytes_are_accepted():
    validator.validate_schedule(WORKFLOW_PATH.read_bytes())


@pytest.mark.parametrize("suffix", [b" ", b"\n# Changed comment.\n", b"\x00"])
def test_changed_workflow_bytes_are_refused(suffix):
    with pytest.raises(ValueError, match="indexed orchestrator bytes differ"):
        validator.validate_schedule(WORKFLOW_PATH.read_bytes() + suffix)


@pytest.mark.parametrize("indexed", ["reviewed", "changed", "missing"])
def test_entrypoint_reads_index_and_reports_refusal(monkeypatch, capsys, indexed):
    read_index = Mock(return_value=WORKFLOW_PATH.read_bytes())
    if indexed == "changed":
        read_index.return_value += b" "
    elif indexed == "missing":
        read_index.side_effect = subprocess.CalledProcessError(128, ["git", "show"])
    monkeypatch.setattr(subprocess, "check_output", read_index)

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")

    read_index.assert_called_once_with(
        ["git", "show", ":.github/workflows/pr-orchestrator.yml"], stderr=subprocess.PIPE
    )
    assert exit_info.value.code == (0 if indexed == "reviewed" else 1)
    captured = capsys.readouterr()
    assert captured.out == ""
    if indexed == "reviewed":
        assert captured.err == ""
    else:
        assert "Capsule review deferral requires supported indexed orchestration:" in captured.err
        assert "run local review without deferral." in captured.err
