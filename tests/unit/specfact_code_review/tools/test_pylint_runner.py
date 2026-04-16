from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

from pytest import MonkeyPatch

from specfact_code_review.tools.pylint_runner import run_pylint
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


def test_run_pylint_returns_empty_for_no_files() -> None:
    assert run_pylint([]) == []


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


def test_run_pylint_empty_stdout_is_tool_error(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(
            return_value=completed_process(
                "pylint",
                stdout="",
                stderr="config error: missing plugin",
                returncode=2,
            ),
        ),
    )

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "pylint"
    assert "stdout=''" in findings[0].message
    assert "config error" in findings[0].message
    assert "returncode=2" in findings[0].message


def test_run_pylint_whitespace_only_stdout_is_tool_error(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("pylint", stdout="  \n\t  ", stderr="", returncode=1)),
    )

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert "pylint produced no JSON on stdout" in findings[0].message


def test_run_pylint_empty_stdout_truncates_long_stderr(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    unique_tail = "UNIQUE_STDERR_TAIL_FOR_TRUNCATION_TEST"
    long_stderr = "e" * 4096 + unique_tail
    assert len(long_stderr) > 4096
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(
            return_value=completed_process(
                "pylint",
                stdout="",
                stderr=long_stderr,
                returncode=3,
            ),
        ),
    )

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "pylint"
    assert unique_tail not in findings[0].message
    assert "... (" in findings[0].message
    assert "chars total)" in findings[0].message
    assert f"... ({len(long_stderr)} chars total)" in findings[0].message


def test_run_pylint_coerces_line_zero_to_one(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "message-id": "C0301",
            "path": str(file_path),
            "line": 0,
            "message": "line too long",
        }
    ]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].line == 1


def test_run_pylint_coerces_empty_message_text(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "message-id": "C0301",
            "path": str(file_path),
            "line": 3,
            "message": "",
        }
    ]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].message == "(pylint provided no message text)"


def test_run_pylint_coerces_negative_line_to_one(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "message-id": "C0301",
            "path": str(file_path),
            "line": -5,
            "message": "line too long",
        }
    ]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].line == 1


def test_run_pylint_coerces_whitespace_only_message(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "message-id": "C0301",
            "path": str(file_path),
            "line": 3,
            "message": "   \t\n  ",
        }
    ]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].message == "(pylint provided no message text)"


def test_run_pylint_parses_json_with_surrounding_whitespace(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "message-id": "W0702",
            "path": str(file_path),
            "line": 7,
            "message": "No exception type(s) specified",
        }
    ]
    stdout = "\n  " + json.dumps(payload) + "  \n"
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=stdout, returncode=16)))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].rule == "W0702"


def test_run_pylint_returns_tool_error_for_invalid_payload_item(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [{"path": str(file_path), "line": 7, "message": "No exception type(s) specified"}]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "pylint"
