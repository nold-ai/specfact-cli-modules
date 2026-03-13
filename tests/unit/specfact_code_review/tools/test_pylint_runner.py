from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

from pytest import MonkeyPatch

from specfact_code_review.tools.pylint_runner import run_pylint
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


def test_run_pylint_maps_bare_except_to_architecture(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "message-id": "W0702",
            "path": str(file_path),
            "line": 7,
            "message": "No exception type(s) specified",
        }
    ]
    run_mock = Mock(return_value=completed_process("pylint", stdout=json.dumps(payload), returncode=16))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "architecture"
    assert findings[0].severity == "warning"
    assert findings[0].rule == "W0702"
    assert_tool_run(run_mock, ["pylint", "--output-format", "json", str(file_path)])


def test_run_pylint_maps_broad_except_to_architecture(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "message-id": "W0703",
            "path": str(file_path),
            "line": 11,
            "message": "Catching too general exception Exception",
        }
    ]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "architecture"
    assert findings[0].rule == "W0703"


def test_run_pylint_filters_findings_to_requested_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    other_path = tmp_path / "other.py"
    payload = [
        {
            "message-id": "W0702",
            "path": str(file_path),
            "line": 7,
            "message": "No exception type(s) specified",
        },
        {
            "message-id": "W0703",
            "path": str(other_path),
            "line": 9,
            "message": "Catching too general exception Exception",
        },
    ]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].file == str(file_path)
    assert findings[0].rule == "W0702"


def test_run_pylint_returns_tool_error_on_parse_error(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("pylint", stdout="not-json", returncode=32)),
    )

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "pylint"
