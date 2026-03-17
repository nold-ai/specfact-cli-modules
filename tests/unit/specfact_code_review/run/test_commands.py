from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run import commands as run_commands
from specfact_code_review.run.findings import ReviewFinding, ReviewReport


runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_FILE = REPO_ROOT / "tests/fixtures/review/clean_module.py"


def _report(*, score: int = 85) -> ReviewReport:
    return ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=score,
        findings=[],
        summary="Review command test report.",
    )


def _write_repo_file(repo_root: Path, relative_path: str, *, content: str = "VALUE = 1\n") -> Path:
    file_path = repo_root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return Path(relative_path)


def test_run_command_json_output_uses_review_report(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )
    out = tmp_path / "review-report.json"

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--json",
            "--out",
            str(out),
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code == 0
    assert result.output.strip() == str(out)
    report = ReviewReport.model_validate_json(out.read_text(encoding="utf-8"))
    assert report.run_id == "review-run-001"


def test_run_command_default_json_output_path_uses_review_report(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )
    monkeypatch.chdir(tmp_path)

    exit_code, output = run_commands.run_command(
        [FIXTURE_FILE],
        json_output=True,
    )

    assert exit_code == 0
    assert output == "review-report.json"
    report = ReviewReport.model_validate_json((tmp_path / "review-report.json").read_text(encoding="utf-8"))
    assert report.run_id == "review-run-001"


def test_run_command_score_only_prints_reward_delta(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(score=92),
    )

    result = runner.invoke(app, ["review", "run", "--score-only", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    assert result.output == "12\n"


def test_run_command_uses_git_diff_when_files_are_omitted(monkeypatch: Any, tmp_path: Path) -> None:
    recorded: dict[str, list[Path]] = {}
    out = tmp_path / "review-report.json"

    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [Path("tests/fixtures/review/clean_module.py")],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--json", "--out", str(out)])

    assert result.exit_code == 0
    assert recorded["files"] == [Path("tests/fixtures/review/clean_module.py")]
    assert out.exists()


def test_run_command_supports_full_scope_and_path_filters(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    _write_repo_file(tmp_path, "packages/specfact-backlog/src/specfact_backlog/commands.py")
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [package_file, Path("packages/specfact-backlog/src/specfact_backlog/commands.py")],
        raising=False,
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "full",
            "--path",
            "packages/specfact-code-review",
            "--json",
            "--out",
            "review-report.json",
        ],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_supports_changed_scope_with_repeatable_path_filters(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    test_file = _write_repo_file(
        tmp_path,
        "tests/unit/specfact_code_review/run/test_commands.py",
        content="def test_scope_paths() -> None:\n    assert True\n",
    )
    _write_repo_file(tmp_path, "packages/specfact-backlog/src/specfact_backlog/commands.py")
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [
            package_file,
            test_file,
            Path("packages/specfact-backlog/src/specfact_backlog/commands.py"),
        ],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "changed",
            "--path",
            "packages/specfact-code-review",
            "--path",
            "tests/unit/specfact_code_review",
            "--json",
            "--out",
            "review-report.json",
        ],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file, test_file]


def test_run_command_rejects_out_without_json(tmp_path: Path) -> None:
    out = tmp_path / "review-report.json"
    result = runner.invoke(app, ["review", "run", "--out", str(out), "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 2
    assert "Use " in result.output
    assert "out" in result.output
    assert "json" in result.output


def test_run_help_does_not_render_nested_command_suffix() -> None:
    result = runner.invoke(app, ["review", "run", "--help"])

    assert result.exit_code == 0
    assert "COMMAND [ARGS]" not in result.output


def test_run_command_rejects_json_and_score_only_together() -> None:
    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--json",
            "--score-only",
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code == 2
    assert "Use either " in result.output
    assert "json" in result.output
    assert "score" in result.output
    assert "not both" in result.output


def test_run_command_rejects_scope_mixed_with_positional_files() -> None:
    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "tests/fixtures/review/clean_module.py",
            "--scope",
            "full",
        ],
    )

    assert result.exit_code == 2
    assert "choose positional files or auto-scope controls" in result.output.lower()


def test_run_command_rejects_path_mixed_with_positional_files() -> None:
    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "tests/fixtures/review/clean_module.py",
            "--path",
            "tests/fixtures/review",
        ],
    )

    assert result.exit_code == 2
    assert "choose positional files or auto-scope controls" in result.output.lower()


def test_run_command_fix_mode_applies_fixes_before_second_run(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_run_review(_files: list[Path], **_kwargs: Any) -> ReviewReport:
        calls.append("run_review")
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)
    monkeypatch.setattr(
        "specfact_code_review.run.commands._apply_fixes",
        lambda files: calls.append("apply_fixes"),
    )

    result = runner.invoke(app, ["review", "run", "--fix", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    assert calls == ["run_review", "apply_fixes", "run_review"]


def test_run_command_default_output_renders_findings(monkeypatch: Any) -> None:
    report = ReviewReport(
        run_id="review-run-002",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=70,
        findings=[
            ReviewFinding(
                category="style",
                severity="warning",
                tool="ruff",
                rule="F401",
                file="tests/fixtures/review/clean_module.py",
                line=1,
                message="Unused import.",
                fixable=True,
            )
        ],
        summary="Rendered output report.",
    )
    monkeypatch.setattr("specfact_code_review.run.commands.run_review", lambda files, **_kwargs: report)

    result = runner.invoke(app, ["review", "run", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    assert "Code Review: style" in result.output
    assert "Rendered output report." in result.output


def test_run_command_fails_when_scope_and_paths_match_no_files(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [package_file],
        raising=False,
    )

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "full",
            "--path",
            "packages/specfact-backlog",
        ],
    )

    assert result.exit_code == 2
    assert "no reviewable files" in result.output.lower()
    assert "scope" in result.output.lower()
    assert "full" in result.output.lower()


def test_changed_files_from_git_diff_filters_python_files(monkeypatch: Any, tmp_path: Path) -> None:
    python_file = tmp_path / "example.py"
    python_file.write_text("VALUE = 1\n", encoding="utf-8")
    text_file = tmp_path / "README.md"
    text_file.write_text("hi\n", encoding="utf-8")

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if command[:3] == ["git", "diff", "HEAD"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{python_file}\n{text_file}\nmissing.py\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    changed_files_from_git_diff = vars(run_commands)["_changed_files_from_git_diff"]

    assert changed_files_from_git_diff(include_tests=False) == [python_file]


def test_changed_files_from_git_diff_excludes_test_files_by_default(monkeypatch: Any, tmp_path: Path) -> None:
    source_file = tmp_path / "example.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    test_file = tmp_path / "tests/unit/test_example.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if command[:3] == ["git", "diff", "HEAD"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{source_file}\n{test_file}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    changed_files_from_git_diff = vars(run_commands)["_changed_files_from_git_diff"]

    assert changed_files_from_git_diff(include_tests=False) == [source_file]
    assert changed_files_from_git_diff(include_tests=True) == [source_file, test_file]


def test_changed_files_from_git_diff_includes_untracked_python_files(monkeypatch: Any, tmp_path: Path) -> None:
    tracked_file = tmp_path / "tracked.py"
    tracked_file.write_text("VALUE = 1\n", encoding="utf-8")
    untracked_file = tmp_path / "new_file.py"
    untracked_file.write_text("VALUE = 2\n", encoding="utf-8")

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if command[:3] == ["git", "diff", "HEAD"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{tracked_file}\n",
                stderr="",
            )
        if command[:4] == ["git", "ls-files", "--others", "--exclude-standard"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{untracked_file}\n",
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    changed_files_from_git_diff = vars(run_commands)["_changed_files_from_git_diff"]

    assert changed_files_from_git_diff(include_tests=False) == [tracked_file, untracked_file]


def test_apply_fixes_raises_when_format_command_fails(monkeypatch: Any) -> None:
    calls = {"count": 0}

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls["count"] += 1
        if calls["count"] == 1:
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args[0], returncode=2, stdout="", stderr="format failed")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    apply_fixes = vars(run_commands)["_apply_fixes"]

    with pytest.raises(RuntimeError, match="format failed"):
        apply_fixes([Path("tests/fixtures/review/clean_module.py")])


def test_run_command_rejects_missing_files() -> None:
    result = runner.invoke(app, ["review", "run", "tests/fixtures/review/missing.py"])

    assert result.exit_code == 2
    assert "not found" in result.output.lower()
