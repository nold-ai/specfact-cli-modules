from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from specfact_code_review.tools.semgrep_runner import (
    _run_semgrep_command,
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
AI_BLOAT_BAD_FIXTURE_RULES = {
    "bad_manual_loop_comprehension.py": "ai-bloat.manual-loop-comprehension",
    "bad_identity_try_except.py": "ai-bloat.identity-try-except",
    "bad_none_then_none.py": "ai-bloat.none-then-none",
    "bad_single_call_wrapper.py": "ai-bloat.single-call-wrapper",
}
GOOD_FIXTURES = [
    "good_get_modify.py",
    "good_nested_access.py",
    "good_cross_layer.py",
    "good_module_network.py",
    "good_print_in_src.py",
]
AI_BLOAT_GOOD_FIXTURES = [
    "good_manual_loop_comprehension.py",
    "good_passthrough_lambda.py",
    "good_identity_try_except.py",
    "good_none_then_none.py",
    "good_single_call_wrapper.py",
]


def test_run_semgrep_command_creates_runtime_dirs(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    target = tmp_path / "target.py"
    config = tmp_path / "clean_code.yaml"
    target.write_text("print('x')\n", encoding="utf-8")
    config.write_text("rules: []\n", encoding="utf-8")
    captured_env: dict[str, str] = {}

    def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del command
        env = kwargs["env"]
        assert isinstance(env, dict)
        captured_env.update({str(key): str(value) for key, value in env.items()})
        assert Path(captured_env["XDG_CONFIG_HOME"]).is_dir()
        assert Path(captured_env["XDG_CACHE_HOME"]).is_dir()
        assert Path(captured_env["SEMGREP_SETTINGS_FILE"]).parent.is_dir()
        return completed_process("semgrep", stdout='{"results": []}', returncode=0)

    monkeypatch.setattr(subprocess, "run", _run)

    _run_semgrep_command([target], bundle_root=None, config_file=config)

    assert captured_env["XDG_CONFIG_HOME"].endswith(".config")


@pytest.fixture(autouse=True)
def _stub_semgrep_on_path(monkeypatch: MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    real_which = shutil.which

    def _which(name: str) -> str | None:
        if name == "semgrep":
            return "/fake/semgrep"
        return real_which(name)

    monkeypatch.setattr("specfact_code_review.tools.tool_availability.shutil.which", _which)


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


def test_run_semgrep_maps_ai_bloat_rules_to_info_findings(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "ai-bloat.single-call-wrapper",
                "path": str(file_path),
                "start": {"line": 5},
                "extra": {"message": "Single-call wrapper adds no behavior.", "severity": "WARNING"},
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
    assert findings[0].category == "ai_bloat"
    assert findings[0].severity == "info"
    assert findings[0].rule == "ai-bloat.single-call-wrapper"


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
    run_mock = Mock()
    monkeypatch.setattr("specfact_code_review.tools.tool_availability.shutil.which", lambda _name: None)
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "semgrep"
    assert findings[0].severity == "warning"
    run_mock.assert_not_called()


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
    monkeypatch.setattr("specfact_code_review.tools.tool_availability.shutil.which", lambda _name: None)

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


@pytest.mark.parametrize(("fixture_name", "expected_rule"), list(AI_BLOAT_BAD_FIXTURE_RULES.items()))
def test_each_ai_bloat_bad_fixture_triggers_expected_rule(fixture_name: str, expected_rule: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert expected_rule in {finding.rule for finding in findings}
    assert all(finding.severity == "info" for finding in findings if finding.rule == expected_rule)


def test_ai_bloat_passthrough_lambda_rule_triggers_for_generated_fixture(tmp_path: Path) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    target = tmp_path / "bad_passthrough_lambda.py"
    target.write_text(
        """
def canonicalize(value: str) -> str:
    return value.strip()


callbacks = [lambda value: canonicalize(value)]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_semgrep([target])

    assert "ai-bloat.passthrough-lambda" in {finding.rule for finding in findings}
    assert all(finding.severity == "info" for finding in findings if finding.rule == "ai-bloat.passthrough-lambda")


@pytest.mark.parametrize("fixture_name", AI_BLOAT_GOOD_FIXTURES)
def test_each_ai_bloat_good_fixture_triggers_no_ai_bloat_findings(fixture_name: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert not any(finding.category == "ai_bloat" for finding in findings)
