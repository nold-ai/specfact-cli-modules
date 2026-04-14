"""Tests for scripts/pre_commit_code_review.py."""

# pyright: reportUnknownMemberType=false

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_script_module() -> Any:
    """Load scripts/pre_commit_code_review.py as a Python module."""
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "pre_commit_code_review.py"
    spec = importlib.util.spec_from_file_location("pre_commit_code_review", script_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load script module at {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLE_FAIL_REVIEW_REPORT: dict[str, object] = {
    "overall_verdict": "FAIL",
    "findings": [
        {"severity": "error", "rule": "e1"},
        {"severity": "warning", "rule": "w1"},
    ],
}


def test_specfact_review_paths_keeps_only_python_sources() -> None:
    module = _load_script_module()
    assert module._specfact_review_paths(
        [
            "tests/test_app.py",
            "openspec/changes/foo/tasks.md",
            "openspec/changes/foo/proposal.md",
            "registry/modules/specfact-code-review-0.47.0.tar.gz",
            "registry/index.json",
            "packages/specfact-code-review/module-package.yaml",
            "src/pkg/stub.pyi",
        ]
    ) == ["tests/test_app.py", "src/pkg/stub.pyi"]


def test_filter_review_gate_paths_excludes_module_package_manifest() -> None:
    """module-package.yaml is not Python; it must not trigger the code-review gate."""
    module = _load_script_module()

    assert module.filter_review_gate_paths(["packages/specfact-code-review/module-package.yaml"]) == []


def test_filter_review_gate_paths_keeps_contract_relevant_trees() -> None:
    """Review gate should include staged paths under tooling and contract trees."""
    module = _load_script_module()

    assert module.filter_review_gate_paths(
        [
            "src/app.py",
            "README.md",
            "tests/test_app.py",
            "openspec/changes/foo/tasks.md",
            "openspec/changes/foo/proposal.md",
            "openspec/changes/foo/TDD_EVIDENCE.md",
            "notes.txt",
        ]
    ) == [
        "tests/test_app.py",
        "openspec/changes/foo/tasks.md",
        "openspec/changes/foo/proposal.md",
    ]


def test_build_review_command_writes_json_report() -> None:
    """Pre-commit gate should write ReviewReport JSON for IDE/Copilot and use exit verdict."""
    module = _load_script_module()

    command = module.build_review_command(["tests/test_app.py", "packages/specfact-spec/src/x.py"])

    assert command[:5] == [sys.executable, "-m", "specfact_cli.cli", "code", "review"]
    assert "--json" in command
    assert "--out" in command
    assert module.REVIEW_JSON_OUT in command
    assert command[-2:] == ["tests/test_app.py", "packages/specfact-spec/src/x.py"]


def test_main_skips_when_no_relevant_files(capsys: pytest.CaptureFixture[str]) -> None:
    """Hook should not fail commits when no staged review-relevant paths are present."""
    module = _load_script_module()

    exit_code = module.main(["README.md", "docs/guide.md", "src/app.py"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "skipping code review gate" in out


def test_main_skips_specfact_when_only_openspec_markdown(capsys: pytest.CaptureFixture[str]) -> None:
    """OpenSpec Markdown is gate-relevant but must not be passed to SpecFact as Python paths."""
    module = _load_script_module()

    exit_code = module.main(["openspec/changes/foo/tasks.md", "openspec/changes/foo/proposal.md"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "skipping SpecFact code review" in out
    assert ".py/.pyi" in out


def test_main_warnings_only_does_not_block_despite_cli_fail_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pre-commit gate blocks on error findings only; warning-only FAIL verdict is advisory."""
    module = _load_script_module()
    repo_root = tmp_path
    payload: dict[str, object] = {
        "overall_verdict": "FAIL",
        "findings": [{"severity": "warning", "rule": "w1"}],
    }
    _write_sample_review_report(repo_root, payload)

    def _fake_root() -> Path:
        return repo_root

    def _fake_ensure() -> tuple[bool, str | None]:
        return True, None

    def _fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        _write_sample_review_report(repo_root, payload)
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(module, "_repo_root", _fake_root)
    monkeypatch.setattr(module, "ensure_runtime_available", _fake_ensure)
    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main(["tests/unit/test_app.py"])
    err = capsys.readouterr().err
    assert exit_code == 0
    assert "warnings=1" in err


def test_main_propagates_review_gate_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Blocking review verdicts must block the commit by returning non-zero."""
    module = _load_script_module()
    repo_root = tmp_path
    _write_sample_review_report(repo_root, SAMPLE_FAIL_REVIEW_REPORT)

    def _fake_root() -> Path:
        return repo_root

    def _fake_ensure() -> tuple[bool, str | None]:
        return True, None

    def _fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "--json" in cmd
        assert module.REVIEW_JSON_OUT in cmd
        assert _kwargs.get("cwd") == str(repo_root)
        assert _kwargs.get("timeout") == 300
        _write_sample_review_report(repo_root, SAMPLE_FAIL_REVIEW_REPORT)
        return subprocess.CompletedProcess(cmd, 1, stdout=".specfact/code-review.json\n", stderr="")

    monkeypatch.setattr(module, "_repo_root", _fake_root)
    monkeypatch.setattr(module, "ensure_runtime_available", _fake_ensure)
    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main(["tests/unit/test_app.py"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    err = captured.err
    assert "Code review summary: 2 finding(s)" in err
    assert "errors=1" in err
    assert "warnings=1" in err
    assert "overall_verdict='FAIL'" in err
    assert "Code review report file:" in err
    assert "absolute path:" in err
    assert "Copy-paste for Copilot or Cursor:" in err
    assert "Read `.specfact/code-review.json`" in err
    assert "@workspace Open `.specfact/code-review.json`" in err


def _write_sample_review_report(repo_root: Path, payload: dict[str, object]) -> None:
    spec_dir = repo_root / ".specfact"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "code-review.json").write_text(json.dumps(payload), encoding="utf-8")


def test_count_findings_by_severity_buckets_unknown() -> None:
    """Severities map to error/warning/advisory; others go to other."""
    module = _load_script_module()
    counts = module.count_findings_by_severity(
        [
            {"severity": "error"},
            {"severity": "WARN"},
            {"severity": "advisory"},
            {"severity": "info"},
            {"severity": "custom"},
            "not-a-dict",
        ]
    )
    assert counts == {"error": 1, "warning": 1, "advisory": 1, "info": 1, "other": 2}


def test_main_missing_report_still_returns_exit_code_and_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """If JSON is not on disk, stderr explains; exit code still comes from the review subprocess."""
    module = _load_script_module()

    def _fake_root() -> Path:
        return tmp_path

    def _fake_ensure() -> tuple[bool, str | None]:
        return True, None

    def _fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="")

    monkeypatch.setattr(module, "_repo_root", _fake_root)
    monkeypatch.setattr(module, "ensure_runtime_available", _fake_ensure)
    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main(["tests/unit/test_app.py"])

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "expected review report at" in err
    assert "not created" in err
    assert ".specfact/code-review.json" in err


def test_main_timeout_fails_hook(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Subprocess timeout must fail the hook with a clear message."""
    module = _load_script_module()
    repo_root = Path(__file__).resolve().parents[3]

    def _fake_ensure() -> tuple[bool, str | None]:
        return True, None

    def _fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert _kwargs.get("cwd") == str(repo_root)
        assert _kwargs.get("timeout") == 300
        raise subprocess.TimeoutExpired(cmd, 300)

    monkeypatch.setattr(module, "ensure_runtime_available", _fake_ensure)
    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module, "_repo_root", lambda: repo_root)

    exit_code = module.main(["tests/unit/test_app.py"])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "timed out after 300s" in err
    assert "tests/unit/test_app.py" in err


def test_main_prints_actionable_setup_guidance_when_runtime_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing review runtime should fail with actionable setup guidance."""
    module = _load_script_module()

    def _fake_ensure() -> tuple[bool, str | None]:
        return False, "Run `hatch run dev-deps` to install specfact-cli."

    monkeypatch.setattr(module, "ensure_runtime_available", _fake_ensure)

    exit_code = module.main(["tests/unit/test_app.py"])

    assert exit_code == 1
    assert "dev-deps" in capsys.readouterr().out
