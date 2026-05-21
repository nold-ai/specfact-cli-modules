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

    assert result.exit_code == 0
    assert "simplify" in result.output


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
