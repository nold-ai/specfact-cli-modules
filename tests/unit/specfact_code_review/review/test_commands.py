from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from specfact_code_review.review.commands import InvalidOptionCombinationError, app


runner = CliRunner()
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain_output(text: str) -> str:
    return ANSI_RE.sub("", text)


def test_review_run_help_lists_simplify_focus() -> None:
    result = runner.invoke(app, ["review", "run", "--help"])
    output = _plain_output(result.output)

    assert result.exit_code == 0
    assert "simplify" in output
    assert "--instructions" in output


def test_review_run_instructions_prints_ai_workflow_without_running_review(monkeypatch: Any) -> None:
    def _fail_run_command(_files: list[Path], **_kwargs: object) -> tuple[int, str | None]:
        raise AssertionError("run_command should not be called for --instructions")

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fail_run_command)

    result = runner.invoke(app, ["review", "run", "--instructions"])

    assert result.exit_code == 0
    assert "remove AI bloat" in result.output
    assert "safe_mechanical" in result.output
    assert "design_judgment" in result.output
    assert "branch-delta Python files" in result.output
    assert "git diff --name-only <base-ref>...HEAD" in result.output
    assert "Findings without guidance_kind are unguided advisories" in result.output
    assert "Sort findings by guidance_kind before editing" in result.output
    assert "exact patch preview" in result.output
    assert "default to keep or skip" in result.output
    assert "specfact code review run --scope changed --enforcement shadow --focus simplify" in result.output
    assert "cleanup_forecast" in result.output
    assert "remediation_packet" in result.output
    assert "not proof of AI authorship" in result.output


def test_review_run_interactive_prompts_for_test_inclusion(monkeypatch: Any) -> None:
    recorded: dict[str, Any] = {}

    def _fake_run_command(files: list[Path], **kwargs: object) -> tuple[int, str | None]:
        recorded["files"] = files
        recorded["kwargs"] = kwargs
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(app, ["review", "run", "--interactive"], input="y\n")

    assert result.exit_code == 0
    assert "Include changed and untracked test files in this review?" in result.output
    assert recorded["files"] == []
    assert recorded["kwargs"]["include_tests"] is True


def test_review_run_non_interactive_defaults_to_excluding_tests(monkeypatch: Any) -> None:
    recorded: dict[str, Any] = {}

    def _fake_run_command(_files: list[Path], **kwargs: object) -> tuple[int, str | None]:
        recorded["kwargs"] = kwargs
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(app, ["review", "run"])

    assert result.exit_code == 0
    assert recorded["kwargs"]["include_tests"] is False


def test_review_run_focus_source_sets_include_tests_false(monkeypatch: Any) -> None:
    recorded: dict[str, Any] = {}

    def _fake_run_command(_files: list[Path], **kwargs: object) -> tuple[int, str | None]:
        recorded["kwargs"] = kwargs
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(
        app,
        ["review", "run", "--focus", "source", "tests/fixtures/review/clean_module.py"],
    )

    assert result.exit_code == 0
    assert recorded["kwargs"]["include_tests"] is False


def test_review_run_rejects_conflicting_test_flags() -> None:
    result = runner.invoke(app, ["review", "run", "--include-tests", "--exclude-tests"])

    assert result.exit_code != 0
    assert "Cannot use both --include-tests and --exclude-tests" in _plain_output(result.output)


def test_review_run_rejects_focus_with_test_flags() -> None:
    result = runner.invoke(app, ["review", "run", "--focus", "source", "--include-tests"])

    assert result.exit_code != 0


def test_review_run_rejects_unknown_focus() -> None:
    result = runner.invoke(app, ["review", "run", "--focus", "unknown"])

    assert result.exit_code != 0


def test_review_run_exclude_tests_sets_include_tests_false(monkeypatch: Any) -> None:
    recorded: dict[str, Any] = {}

    def _fake_run_command(_files: list[Path], **kwargs: object) -> tuple[int, str | None]:
        recorded["kwargs"] = kwargs
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(app, ["review", "run", "--exclude-tests"])

    assert result.exit_code == 0
    assert recorded["kwargs"]["include_tests"] is False


def test_review_run_prints_run_command_output(monkeypatch: Any) -> None:
    def _fake_run_command(_files: list[Path], **_kwargs: object) -> tuple[int, str | None]:
        return 0, "review output"

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(app, ["review", "run"])

    assert result.exit_code == 0
    assert "review output" in result.output


def test_review_run_surfaces_run_command_validation_errors(monkeypatch: Any) -> None:
    def _fake_run_command(_files: list[Path], **_kwargs: object) -> tuple[int, str | None]:
        raise InvalidOptionCombinationError("invalid review options")

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(app, ["review", "run"])

    assert result.exit_code != 0
    assert "invalid review options" in result.output


def test_review_run_explicit_files_do_not_prompt_and_keep_tests(monkeypatch: Any) -> None:
    recorded: dict[str, Any] = {}

    def _fake_run_command(files: list[Path], **kwargs: object) -> tuple[int, str | None]:
        recorded["files"] = files
        recorded["kwargs"] = kwargs
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(
        app,
        ["review", "run", "--interactive", "tests/unit/specfact_code_review/run/test_commands.py"],
    )

    assert result.exit_code == 0
    assert "Include changed and untracked test files" not in result.output
    assert recorded["files"] == [Path("tests/unit/specfact_code_review/run/test_commands.py")]
    assert recorded["kwargs"]["include_tests"] is True
