from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

from pytest import MonkeyPatch

from specfact_code_review.tools.radon_runner import run_radon
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


def test_run_radon_maps_complexity_thresholds_and_filters_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    other_path = tmp_path / "other.py"
    payload = {
        str(file_path): [
            {"type": "function", "name": "warn_me", "complexity": 13, "lineno": 7},
            {"type": "function", "name": "fail_me", "complexity": 16, "lineno": 19},
            {"type": "function", "name": "ok_me", "complexity": 10, "lineno": 27},
        ],
        str(other_path): [
            {"type": "function", "name": "skip_me", "complexity": 20, "lineno": 3},
        ],
    }
    run_mock = Mock(return_value=completed_process("radon", stdout=json.dumps(payload)))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_radon([file_path])

    assert len(findings) == 2
    assert findings[0].file == str(file_path)
    assert findings[0].severity == "warning"
    assert findings[0].category == "clean_code"
    assert findings[1].severity == "error"
    assert {finding.rule for finding in findings} == {"CC13", "CC16"}
    assert_tool_run(run_mock, ["radon", "cc", "-j", str(file_path)])


def test_run_radon_returns_no_findings_for_complexity_twelve_or_below(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        str(file_path): [
            {"type": "function", "name": "ok_me", "complexity": 12, "lineno": 11},
        ]
    }
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("radon", stdout=json.dumps(payload))))

    findings = run_radon([file_path])

    assert findings == []


def test_run_radon_returns_tool_error_on_parse_error(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("radon", stdout="not-json", returncode=2))
    )

    findings = run_radon([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "radon"
