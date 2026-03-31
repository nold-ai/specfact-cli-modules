from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from specfact_code_review.review.commands import app


runner = CliRunner()


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
