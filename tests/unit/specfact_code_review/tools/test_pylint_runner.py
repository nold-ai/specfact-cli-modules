from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

from pytest import MonkeyPatch, mark

from specfact_code_review.tools.pylint_runner import run_pylint
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


def test_run_pylint_returns_empty_for_no_files() -> None:
    assert not run_pylint([])


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
    assert findings[0].line == 7
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


@mark.parametrize(
    ("fields", "expected"),
    [
        ((0, "line too long"), (1, "line too long")),
        ((-5, "line too long"), (1, "line too long")),
        ((3, ""), (3, "(pylint provided no message text)")),
        ((3, "   \t\n  "), (3, "(pylint provided no message text)")),
    ],
)
def test_run_pylint_normalizes_report_fields(
    tmp_path: Path, monkeypatch: MonkeyPatch, fields: tuple[int, str], expected: tuple[int, str]
) -> None:
    file_path = tmp_path / "target.py"
    line, message = fields
    payload = [{"message-id": "C0301", "path": str(file_path), "line": line, "message": message}]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert (findings[0].line, findings[0].message) == expected


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
    assert findings[0].line == 7
    assert findings[0].message == "No exception type(s) specified"
    assert findings[0].category == "architecture"


def test_run_pylint_returns_tool_error_for_invalid_payload_item(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [{"path": str(file_path), "line": 7, "message": "No exception type(s) specified"}]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("pylint", stdout=json.dumps(payload))))

    findings = run_pylint([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "pylint"


def test_run_pylint_rejects_startup_failure_with_clean_json(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    diagnostic = "project_worker_startup_import_state_changed"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("pylint", stdout="[]", stderr=diagnostic, returncode=78)),
    )

    findings = run_pylint([tmp_path / "target.py"])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert diagnostic in findings[0].message
    assert "78" in findings[0].message
