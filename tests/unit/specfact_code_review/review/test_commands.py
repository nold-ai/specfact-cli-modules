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
    expected_snippets = (
        "remove AI bloat",
        "safe_mechanical",
        "design_judgment",
        "--scope range --base-ref <full-base-ref> --head-ref <full-head-ref>",
        "--pr-context-file <event-derived-absolute-path>",
        "--enforcement full",
        "range_preview",
        "protected consumer",
        "Findings without guidance_kind are unguided advisories",
        "Sort findings by guidance_kind before editing",
        "exact patch preview",
        "default to keep or skip",
        "specfact code review run --scope changed --enforcement shadow --focus simplify",
        "cleanup_forecast",
        "remediation_packet",
        "not proof of AI authorship",
    )
    assert all(snippet in result.output for snippet in expected_snippets)


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


def test_review_run_warns_when_enforcement_defaults_to_changed(monkeypatch: Any) -> None:
    def _fake_run_command(_files: list[Path], **_kwargs: object) -> tuple[int, str | None]:
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(app, ["review", "run"])

    assert result.exit_code == 0
    assert "Code review enforcement default is 'changed'" in result.output
    assert "--enforcement full" in result.output


def test_review_run_explicit_changed_enforcement_does_not_warn(monkeypatch: Any) -> None:
    def _fake_run_command(_files: list[Path], **_kwargs: object) -> tuple[int, str | None]:
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(app, ["review", "run", "--enforcement", "changed"])

    assert result.exit_code == 0
    assert "Code review enforcement default is 'changed'" not in result.output


def test_review_run_range_defaults_to_full_enforcement(monkeypatch: Any) -> None:
    recorded: dict[str, object] = {}

    def _fake_run_command(_files: list[Path], **kwargs: object) -> tuple[int, str | None]:
        recorded.update(kwargs)
        return 0, None

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fake_run_command)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "range",
            "--base-ref",
            "1" * 40,
            "--head-ref",
            "2" * 40,
            "--pr-context-file",
            "/tmp/pr-context.json",
        ],
    )

    assert result.exit_code == 0
    assert recorded["review_mode"] == "full"


def test_review_run_rejects_legacy_mode_with_explicit_enforcement(monkeypatch: Any) -> None:
    def _fail_run_command(_files: list[Path], **_kwargs: object) -> tuple[int, str | None]:
        raise AssertionError("run_command should not be called with ambiguous enforcement flags")

    monkeypatch.setattr("specfact_code_review.review.commands.run_command", _fail_run_command)

    result = runner.invoke(app, ["review", "run", "--mode", "shadow", "--enforcement", "changed"])

    assert result.exit_code != 0
    assert "Use only one of --mode or --enforcement" in _plain_output(result.output)


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
