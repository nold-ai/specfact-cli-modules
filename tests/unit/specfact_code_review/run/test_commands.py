from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run.findings import ReviewReport


runner = CliRunner()


def _report(*, score: int = 85) -> ReviewReport:
    return ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=score,
        findings=[],
        summary="Review command test report.",
    )


def test_run_command_json_output_uses_review_report(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **kwargs: _report(),
    )

    result = runner.invoke(app, ["review", "run", "--json", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    report = ReviewReport.model_validate_json(result.output)
    assert report.run_id == "review-run-001"


def test_run_command_score_only_prints_reward_delta(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **kwargs: _report(score=92),
    )

    result = runner.invoke(app, ["review", "run", "--score-only", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    assert result.output == "12\n"


def test_run_command_uses_git_diff_when_files_are_omitted(monkeypatch: Any) -> None:
    recorded: dict[str, list[Path]] = {}

    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda: [Path("tests/fixtures/review/clean_module.py")],
    )

    def fake_run_review(files: list[Path], **kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--json"])

    assert result.exit_code == 0
    assert recorded["files"] == [Path("tests/fixtures/review/clean_module.py")]


def test_run_command_fix_mode_applies_fixes_before_second_run(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_run_review(_files: list[Path], **kwargs: Any) -> ReviewReport:
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


def test_run_command_rejects_missing_files() -> None:
    result = runner.invoke(app, ["review", "run", "tests/fixtures/review/missing.py"])

    assert result.exit_code == 2
    assert "not found" in result.output.lower()
