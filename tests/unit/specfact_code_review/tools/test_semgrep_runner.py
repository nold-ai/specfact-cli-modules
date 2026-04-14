from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from specfact_code_review.tools.semgrep_runner import (
    _snip_stderr_tail,
    find_semgrep_config,
    run_semgrep,
    run_semgrep_bugs,
)
from tests.unit.specfact_code_review.tools.helpers import completed_process


FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "semgrep"
BAD_FIXTURE_RULES = {
    "bad_get_modify.py": "get-modify-same-method",
    "bad_nested_access.py": "unguarded-nested-access",
    "bad_cross_layer.py": "cross-layer-call",
    "bad_module_network.py": "module-level-network",
    "bad_print_in_src.py": "print-in-src",
}
GOOD_FIXTURES = [
    "good_get_modify.py",
    "good_nested_access.py",
    "good_cross_layer.py",
    "good_module_network.py",
    "good_print_in_src.py",
]


def test_run_semgrep_maps_findings_to_review_finding(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "get-modify-same-method",
                "path": str(file_path),
                "start": {"line": 4},
                "extra": {"message": "Method mixes read and write responsibilities."},
            }
        ]
    }
    run_mock = Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].tool == "semgrep"
    assert findings[0].category == "clean_code"
    assert findings[0].rule == "get-modify-same-method"
    assert findings[0].line == 4
    assert findings[0].fixable is False
    run_mock.assert_called_once()


def test_run_semgrep_maps_naming_rule_to_naming_category(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "banned-generic-public-names",
                "path": str(file_path),
                "start": {"line": 2},
                "extra": {"message": "Public API name is too generic."},
            }
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "naming"
    assert findings[0].rule == "banned-generic-public-names"


def test_run_semgrep_filters_findings_to_requested_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    other_path = tmp_path / "other.py"
    payload = {
        "results": [
            {
                "check_id": "cross-layer-call",
                "path": str(file_path),
                "start": {"line": 7},
                "extra": {"message": "Cross-layer calls should be separated."},
            },
            {
                "check_id": "print-in-src",
                "path": str(other_path),
                "start": {"line": 9},
                "extra": {"message": "Avoid print in source files."},
            },
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].file == str(file_path)
    assert findings[0].rule == "cross-layer-call"


def test_run_semgrep_returns_tool_error_when_semgrep_is_unavailable(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    run_mock = Mock(side_effect=FileNotFoundError("semgrep not found"))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "semgrep"
    assert findings[0].severity == "error"


def test_run_semgrep_returns_empty_list_for_clean_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps({"results": []}))),
    )

    findings = run_semgrep([file_path])

    assert not findings


def test_run_semgrep_returns_tool_error_when_results_key_is_missing(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps({"version": "1.0"}))),
    )

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "semgrep"


def test_run_semgrep_ignores_unsupported_rules(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "unsupported-rule",
                "path": str(file_path),
                "start": {"line": 3},
                "extra": {"message": "Ignored rule."},
            }
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep([file_path])

    assert not findings


def test_find_semgrep_config_with_explicit_bundle_root(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    (root / ".semgrep").mkdir(parents=True)
    (root / ".semgrep" / "clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    assert find_semgrep_config(bundle_root=root) == root / ".semgrep" / "clean_code.yaml"


def test_snip_stderr_tail_keeps_last_chars() -> None:
    """Long stderr should retain the suffix (most recent diagnostics), not the prefix."""
    long = "UNIQUE_HEAD_MARKER" + ("A" * 5000) + "END_OF_ERROR"
    out = _snip_stderr_tail(long)
    assert "END_OF_ERROR" in out
    assert out.startswith("…")
    assert "UNIQUE_HEAD_MARKER" not in out


def test_find_semgrep_config_stops_at_git_directory(tmp_path: Path) -> None:
    """Do not resolve a config outside the repo (e.g. stray ~/.semgrep)."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    nested = repo / "nested" / "pkg" / "tools"
    nested.mkdir(parents=True)
    (repo / "nested" / ".semgrep").mkdir(parents=True)
    (repo / "nested" / ".semgrep" / "clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    fake_here = nested / "runner.py"
    fake_here.write_text("#", encoding="utf-8")
    assert find_semgrep_config(module_file=fake_here) == repo / "nested" / ".semgrep" / "clean_code.yaml"


def test_run_semgrep_bugs_returns_empty_when_semgrep_cli_missing(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Bug pass must not emit a second skip finding; run_semgrep already reports missing semgrep."""
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep" / "bugs.yaml").write_text("rules: []\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    assert run_semgrep_bugs([target], bundle_root=bundle) == []


def test_run_semgrep_retries_after_transient_parse_failure(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "unguarded-nested-access",
                "path": str(file_path),
                "start": {"line": 2},
                "extra": {"message": "Nested attribute access can fail."},
            }
        ]
    }
    run_mock = Mock(
        side_effect=[
            completed_process("semgrep", stdout="", returncode=2),
            completed_process("semgrep", stdout=json.dumps(payload), returncode=1),
        ]
    )
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].rule == "unguarded-nested-access"
    assert run_mock.call_count == 2


@pytest.mark.parametrize(("fixture_name", "expected_rule"), list(BAD_FIXTURE_RULES.items()))
def test_each_bad_fixture_triggers_expected_rule(fixture_name: str, expected_rule: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert findings
    assert expected_rule in {finding.rule for finding in findings}


@pytest.mark.parametrize("fixture_name", GOOD_FIXTURES)
def test_each_good_fixture_triggers_no_findings(fixture_name: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert not findings
