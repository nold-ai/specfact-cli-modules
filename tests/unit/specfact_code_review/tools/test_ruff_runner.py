from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast
from unittest.mock import Mock

from pytest import MonkeyPatch

from specfact_code_review.tools.ruff_runner import run_ruff
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


def test_ruff_snapshot_mode_disables_cache(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    projection = scope.project_ruff_policy(scope.RuffPolicy.default(version="0.15.12"), snapshot_root=tmp_path)

    assert "--no-cache" in projection.argv
    assert projection.cache_writes == ()


def test_ruff_task_tag_cannot_hide_e501(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    policy = scope.RuffPolicy.default(version="0.15.12", task_tags=("TODO",))
    projection = scope.project_ruff_policy(policy, snapshot_root=tmp_path)
    lint = cast(dict[str, object], projection.values["lint"])
    pycodestyle = cast(dict[str, object], lint["pycodestyle"])

    assert pycodestyle["ignore-overlong-task-comments"] is False
    assert projection.evidence["original_task_tags"] == ["TODO"]


def test_ruff_fix_only_cannot_hide_unfixable_finding(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    policy = scope.RuffPolicy.default(version="0.15.12", fix=True, fix_only=True)
    projection = scope.project_ruff_policy(policy, snapshot_root=tmp_path)

    assert projection.values["fix"] is False
    assert projection.values["fix-only"] is False


def test_run_ruff_maps_categories_and_fixable_flag(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "code": "S603",
            "filename": str(file_path),
            "location": {"row": 4, "column": 1},
            "message": "subprocess call uses shell=True",
            "fix": None,
        },
        {
            "code": "C901",
            "filename": str(file_path),
            "location": {"row": 10, "column": 1},
            "message": "function is too complex",
            "fix": None,
        },
        {
            "code": "E501",
            "filename": str(file_path),
            "location": {"row": 20, "column": 1},
            "message": "line too long",
            "fix": {"applicability": "safe"},
        },
        {
            "code": "F401",
            "filename": str(file_path),
            "location": {"row": 30, "column": 1},
            "message": "imported but unused",
            "fix": None,
        },
        {
            "code": "I001",
            "filename": str(file_path),
            "location": {"row": 40, "column": 1},
            "message": "import block is un-sorted",
            "fix": None,
        },
        {
            "code": "W291",
            "filename": str(file_path),
            "location": {"row": 50, "column": 1},
            "message": "trailing whitespace",
            "fix": None,
        },
    ]
    run_mock = Mock(return_value=completed_process("ruff", stdout=json.dumps(payload), returncode=1))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_ruff([file_path])

    assert [finding.rule for finding in findings] == ["S603", "C901", "E501", "F401", "I001", "W291"]
    assert findings[0].category == "security"
    assert findings[1].category == "clean_code"
    assert findings[2].category == "style"
    assert findings[2].fixable is True
    assert findings[3].category == "style"
    assert findings[4].category == "style"
    assert findings[5].category == "style"
    assert_tool_run(run_mock, ["ruff", "check", "--output-format", "json", str(file_path)])


def test_run_ruff_filters_findings_to_requested_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    other_path = tmp_path / "other.py"
    payload = [
        {
            "code": "E501",
            "filename": str(file_path),
            "location": {"row": 7, "column": 1},
            "message": "line too long",
            "fix": None,
        },
        {
            "code": "S603",
            "filename": str(other_path),
            "location": {"row": 9, "column": 1},
            "message": "subprocess call uses shell=True",
            "fix": None,
        },
    ]
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("ruff", stdout=json.dumps(payload), returncode=1))
    )

    findings = run_ruff([file_path])

    assert len(findings) == 1
    assert findings[0].file == str(file_path)
    assert findings[0].rule == "E501"


def test_run_ruff_skips_unsupported_rule_families(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = [
        {
            "code": "UP035",
            "filename": str(file_path),
            "location": {"row": 3, "column": 1},
            "message": "Import from collections.abc instead: Iterable",
            "fix": {"applicability": "safe"},
        },
        {
            "code": "B007",
            "filename": str(file_path),
            "location": {"row": 8, "column": 1},
            "message": "Loop control variable not used within loop body",
            "fix": None,
        },
        {
            "code": "E501",
            "filename": str(file_path),
            "location": {"row": 12, "column": 1},
            "message": "line too long",
            "fix": None,
        },
    ]
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("ruff", stdout=json.dumps(payload), returncode=1))
    )

    findings = run_ruff([file_path])

    assert len(findings) == 1
    assert findings[0].rule == "E501"
    assert findings[0].category == "style"


def test_run_ruff_returns_tool_error_on_parse_error(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("ruff", stdout="not-json", returncode=2))
    )

    findings = run_ruff([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "ruff"
    assert findings[0].severity == "error"


def test_run_ruff_returns_tool_error_on_operational_exit_with_parseable_payload(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("ruff", stdout="[]", stderr="invalid configuration", returncode=2)),
    )

    findings = run_ruff([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "ruff"
    assert "returncode=2" in findings[0].message
    assert "invalid configuration" in findings[0].message


def test_run_ruff_returns_tool_error_when_ruff_is_unavailable(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    run_mock = Mock(side_effect=FileNotFoundError("ruff not found"))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_ruff([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "ruff"
