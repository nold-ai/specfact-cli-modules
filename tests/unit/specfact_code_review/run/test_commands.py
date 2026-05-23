from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pytest
from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run import commands as run_commands
from specfact_code_review.run.findings import ReviewFinding, ReviewReport


runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_FILE = REPO_ROOT / "tests/fixtures/review/clean_module.py"
SafeMechanicalAction = Literal["remove", "inline", "collapse"]
SAFE_MECHANICAL_ACTIONS: dict[str, SafeMechanicalAction] = {
    "ai-bloat.dead-branch": "remove",
    "ai-bloat.pass-through-try-except": "remove",
    "ai-bloat.redundant-intermediate": "inline",
    "ai-bloat.verbose-bool-return": "collapse",
}


def _report(*, score: int = 85) -> ReviewReport:
    return ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=score,
        findings=[],
        summary="Review command test report.",
    )


def _safe_mechanical_finding(file_path: Path, *, line: int, rule: str) -> ReviewFinding:
    return ReviewFinding(
        category="ai_bloat",
        severity="info",
        tool="ast",
        rule=rule,
        file=str(file_path),
        line=line,
        message="Safe mechanical simplification.",
        fixable=True,
        confidence="high",
        rewrite_hint="Apply the local rewrite.",
        canonical_pattern="safe-mechanical",
        estimated_deletion_lines=1,
        guidance_kind="safe_mechanical",
        recommended_action=SAFE_MECHANICAL_ACTIONS[rule],
        clean_code_principle="kiss",
        rationale="The rewrite is local and behavior-preserving.",
        safety_checks=["pattern shape is exact"],
        action_status="recommended",
    )


def _safe_mechanical_report(file_path: Path, *, line: int, rule: str) -> ReviewReport:
    return ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=85,
        findings=[_safe_mechanical_finding(file_path, line=line, rule=rule)],
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
    assert result.output == "92\n"


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


def test_run_command_passes_simplify_focus_after_scope_resolution(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    recorded: dict[str, object] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [package_file],
    )

    def fake_run_review(files: list[Path], **kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        recorded["focus"] = kwargs.get("focus")
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
            "--focus",
            "simplify",
            "--json",
            "--out",
            "review-report.json",
        ],
    )

    assert result.exit_code == 0
    assert recorded == {"files": [package_file], "focus": "simplify"}


def test_run_command_normalizes_simplify_focus_on_direct_request(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    recorded: dict[str, object] = {}

    def fake_run_review(files: list[Path], **kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        recorded["focus"] = kwargs.get("focus")
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    exit_code, output = run_commands.run_command(
        run_commands.ReviewRunRequest(
            files=[package_file],
            json_output=True,
            out=Path("review-report.json"),
            focus_facets=("simplify",),
            review_focus=None,
        )
    )

    assert exit_code == 0
    assert output == "review-report.json"
    assert recorded == {"files": [package_file], "focus": "simplify"}


def test_apply_simplification_fixes_inlines_redundant_intermediate(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    )

    assert applied == 1
    assert target.read_text(encoding="utf-8") == "def total(values: list[int]) -> int:\n    return sum(values)\n"


def test_apply_simplification_fixes_skips_non_safe_guidance(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = "def total(values: list[int]) -> int:\n    result = []\n    return result\n"
    target.write_text(source, encoding="utf-8")
    report = _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    report.findings[0].guidance_kind = "needs_tests"

    applied = run_commands._apply_simplification_fixes(report)

    assert applied == 0
    assert target.read_text(encoding="utf-8") == source


def test_apply_simplification_fixes_collapses_verbose_bool_return(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def allowed(role: str) -> bool:\n    if role == 'admin':\n        return True\n    return False\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.verbose-bool-return")
    )

    assert applied == 1
    assert target.read_text(encoding="utf-8") == "def allowed(role: str) -> bool:\n    return role == 'admin'\n"


def test_apply_simplification_fixes_removes_dead_branch(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    if value > 10:\n"
        "        return 'still large'\n"
        "    return 'small'\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=4, rule="ai-bloat.dead-branch")
    )

    assert applied == 1
    assert target.read_text(encoding="utf-8") == (
        "def classify(value: int) -> str:\n    if value > 10:\n        return 'large'\n    return 'small'\n"
    )


def test_apply_simplification_fixes_keeps_dead_branch_with_else(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = (
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    if value > 10:\n"
        "        return 'still large'\n"
        "    else:\n"
        "        return 'fallback'\n"
        "    return 'small'\n"
    )
    target.write_text(source, encoding="utf-8")

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=4, rule="ai-bloat.dead-branch")
    )

    assert applied == 0
    assert target.read_text(encoding="utf-8") == source


def test_apply_simplification_fixes_removes_pass_through_try_except(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def parse(raw: str) -> object:\n"
        "    try:\n"
        "        return parse_json(raw)\n"
        "    except Exception:\n"
        "        raise\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.pass-through-try-except")
    )

    assert applied == 1
    assert target.read_text(encoding="utf-8") == "def parse(raw: str) -> object:\n    return parse_json(raw)\n"


def test_apply_simplification_fixes_uses_bottom_up_line_order(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def total(values: list[int]) -> int:\n"
        "    result = sum(values)\n"
        "    return result\n"
        "\n"
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    if value > 10:\n"
        "        return 'still large'\n"
        "    return 'small'\n",
        encoding="utf-8",
    )
    report = ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=85,
        findings=[
            _safe_mechanical_finding(target, line=2, rule="ai-bloat.redundant-intermediate"),
            _safe_mechanical_finding(target, line=8, rule="ai-bloat.dead-branch"),
        ],
        summary="Review command test report.",
    )

    applied = run_commands._apply_simplification_fixes(report)

    assert applied == 2
    assert target.read_text(encoding="utf-8") == (
        "def total(values: list[int]) -> int:\n"
        "    return sum(values)\n"
        "\n"
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    return 'small'\n"
    )


def test_apply_simplification_fixes_skips_when_source_no_longer_matches(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result + 1\n"
    target.write_text(source, encoding="utf-8")

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    )

    assert applied == 0
    assert target.read_text(encoding="utf-8") == source


def test_run_review_once_applies_simplification_fixes_before_rerun(monkeypatch: Any, tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n",
        encoding="utf-8",
    )
    reports = [
        _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate"),
        _report(),
    ]
    monkeypatch.setattr("specfact_code_review.run.commands.run_review", lambda files, **kwargs: reports.pop(0))
    monkeypatch.setattr("specfact_code_review.run.commands._apply_fixes", lambda files: None)

    report = run_commands._run_review_once(
        [target],
        run_commands._ReviewLoopFlags(
            no_tests=True,
            include_noise=False,
            fix=True,
            progress_callback=None,
            bug_hunt=False,
            review_mode="enforce",
            review_level=None,
            review_focus="simplify",
        ),
    )

    assert report.findings == []
    assert target.read_text(encoding="utf-8") == "def total(values: list[int]) -> int:\n    return sum(values)\n"


def test_run_command_rejects_unknown_keyword_override() -> None:
    with pytest.raises(run_commands.RunCommandError, match="Unexpected keyword arguments: unknown"):
        run_commands.run_command([], unknown=True)


def test_run_command_rejects_focus_with_no_matching_files(monkeypatch: Any, tmp_path: Path) -> None:
    docs_file = _write_repo_file(tmp_path, "docs/helpers/example.py")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(run_commands.NoReviewableFilesError, match="No reviewable Python files matched"):
        run_commands.run_command(
            run_commands.ReviewRunRequest(
                files=[docs_file],
                focus_facets=("source",),
            )
        )


def test_filter_files_by_focus_unions_source_tests_and_docs() -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/run/commands.py")
    test_file = Path("tests/unit/specfact_code_review/run/test_commands.py")
    docs_file = Path("docs/tools/example.py")
    text_file = Path("docs/readme.md")

    assert run_commands._filter_files_by_focus(
        [source_file, test_file, docs_file, text_file],
        ("source", "tests", "docs"),
    ) == [source_file, test_file, docs_file]


def test_run_command_ignores_dot_specfact_in_changed_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".specfact/modules/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [ignored_file, package_file],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--json", "--out", "review-report.json"])

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_hidden_directory_in_changed_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".cache/review-work/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [ignored_file, package_file],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--json", "--out", "review-report.json"])

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_dot_specfact_in_full_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".specfact/modules/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [ignored_file, package_file],
        raising=False,
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        ["review", "run", "--scope", "full", "--json", "--out", "review-report.json"],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_hidden_directory_in_full_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".cache/review-work/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [ignored_file, package_file],
        raising=False,
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        ["review", "run", "--scope", "full", "--json", "--out", "review-report.json"],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_dot_specfact_positional_file(monkeypatch: Any, tmp_path: Path) -> None:
    project_file = _write_repo_file(
        tmp_path,
        ".specfact/modules/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )

    result = runner.invoke(app, ["review", "run", str(project_file)])

    assert result.exit_code == 2
    assert "no python files to review" in result.output.lower()


def test_run_command_ignores_hidden_directory_positional_file(monkeypatch: Any, tmp_path: Path) -> None:
    project_file = _write_repo_file(
        tmp_path,
        ".cache/review-work/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )

    result = runner.invoke(app, ["review", "run", str(project_file)])

    assert result.exit_code == 2
    assert "no python files to review" in result.output.lower()


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
