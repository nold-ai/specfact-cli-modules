from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

from pytest import MonkeyPatch

from specfact_code_review.tools.basedpyright_runner import run_basedpyright
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


def test_run_basedpyright_maps_error_diagnostic_to_type_safety(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "generalDiagnostics": [
            {
                "file": str(file_path),
                "range": {"start": {"line": 3, "character": 0}},
                "severity": "error",
                "message": 'Argument of type "int" cannot be assigned to parameter of type "str"',
            }
        ]
    }
    run_mock = Mock(return_value=completed_process("basedpyright", stdout=json.dumps(payload), returncode=1))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_basedpyright([file_path])

    assert len(findings) == 1
    assert findings[0].category == "type_safety"
    assert findings[0].severity == "error"
    assert findings[0].tool == "basedpyright"
    assert findings[0].file == str(file_path)
    assert findings[0].line == 4
    assert_tool_run(run_mock, ["basedpyright", "--outputjson", "--project", ".", str(file_path)])


def test_run_basedpyright_maps_warning_severity(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "generalDiagnostics": [
            {
                "file": str(file_path),
                "range": {"start": {"line": 6, "character": 0}},
                "severity": "warning",
                "message": "Code is unreachable",
            }
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("basedpyright", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_basedpyright([file_path])

    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].rule == "basedpyright"


def test_run_basedpyright_filters_findings_to_requested_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    other_path = tmp_path / "other.py"
    payload = {
        "generalDiagnostics": [
            {
                "file": str(file_path),
                "range": {"start": {"line": 1, "character": 0}},
                "severity": "error",
                "message": "Type mismatch",
            },
            {
                "file": str(other_path),
                "range": {"start": {"line": 2, "character": 0}},
                "severity": "error",
                "message": "Skip me",
            },
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("basedpyright", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_basedpyright([file_path])

    assert len(findings) == 1
    assert findings[0].file == str(file_path)
    assert findings[0].message == "Type mismatch"


def test_run_basedpyright_returns_tool_error_when_unavailable(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    run_mock = Mock(side_effect=FileNotFoundError("basedpyright not found"))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_basedpyright([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "basedpyright"
