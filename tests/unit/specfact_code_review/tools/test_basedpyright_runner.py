from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

from pytest import MonkeyPatch

from specfact_code_review.tools.basedpyright_runner import run_basedpyright
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


def test_run_basedpyright_returns_empty_for_no_files() -> None:
    assert run_basedpyright([]) == []


def test_basedpyright_extends_and_baseline_files_are_governed_but_disabled(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    (tmp_path / "pyproject.toml").write_text("[tool.basedpyright]\nextends='base.json'\n", encoding="utf-8")
    (tmp_path / "base.json").write_text('{"baselineFile":"baseline.json"}', encoding="utf-8")
    (tmp_path / "baseline.json").write_text("{}", encoding="utf-8")

    policy = scope.resolve_basedpyright_policy(tmp_path, expected_version="1.39.10")
    projection = scope.project_basedpyright_policy(policy, snapshot_root=tmp_path, eligible_inputs=("src/app.py",))

    assert set(policy.reference_paths) == {"pyproject.toml", "base.json", "baseline.json"}
    assert projection.status == "PASS"
    assert "baselineFile" not in projection.values
    assert "--baselinefile" not in projection.argv


def test_basedpyright_no_config_uses_generated_default(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    policy = scope.resolve_basedpyright_policy(tmp_path, expected_version="1.39.10")

    assert policy.identity == "basedpyright-default-v1"
    assert policy.identity_kind == "builtin_mode"


def test_basedpyright_project_rebases_relative_paths_per_snapshot(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    policy = scope.BasedPyrightPolicy(include=("src",), exclude=(), ignore=())
    left = scope.project_basedpyright_policy(policy, snapshot_root=tmp_path / "base", eligible_inputs=("src/app.py",))
    right = scope.project_basedpyright_policy(policy, snapshot_root=tmp_path / "head", eligible_inputs=("src/app.py",))

    assert left.values["include"] == [str(tmp_path / "base/src/app.py")]
    assert right.values["include"] == [str(tmp_path / "head/src/app.py")]
    assert left.logical_policy_digest == right.logical_policy_digest


def test_basedpyright_project_rejects_unbound_paths(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    policy = scope.BasedPyrightPolicy(include=("../escape",), exclude=(), ignore=())

    result = scope.project_basedpyright_policy(policy, snapshot_root=tmp_path, eligible_inputs=("src/app.py",))

    assert result.status == "UNKNOWN"


def test_run_basedpyright_skips_yaml_manifests(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    manifest = tmp_path / "module-package.yaml"
    manifest.write_text("name: example\nversion: 1\n", encoding="utf-8")
    run_mock = Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)

    assert run_basedpyright([manifest]) == []

    run_mock.assert_not_called()


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


def test_run_basedpyright_returns_tool_error_for_invalid_diagnostic_payload(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    file_path = tmp_path / "target.py"
    payload = {"generalDiagnostics": [{"file": str(file_path)}]}
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("basedpyright", stdout=json.dumps(payload)))
    )

    findings = run_basedpyright([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "basedpyright"
