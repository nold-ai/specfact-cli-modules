"""Keep Code Review bundle docs aligned with the Typer ``run`` command surface."""

from __future__ import annotations

from pathlib import Path

import click
from typer.main import get_command as typer_get_command

from specfact_code_review.review import commands as review_commands


MODULES_REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_DOC = MODULES_REPO_ROOT / "docs" / "bundles" / "code-review" / "run.md"


def _review_run_click_command() -> click.Command:
    review_group = typer_get_command(review_commands.review_app)
    run_cmd = review_group.commands.get("run")
    assert isinstance(run_cmd, click.Command)
    return run_cmd


def _public_option_flags(command: click.Command) -> set[str]:
    flags: set[str] = set()
    for param in command.params:
        if not isinstance(param, click.Option):
            continue
        for opt in param.opts:
            if opt.startswith("--"):
                flags.add(opt)
    return flags


def test_code_review_run_doc_mentions_public_ty_options() -> None:
    text = RUN_DOC.read_text(encoding="utf-8")
    flags = _public_option_flags(_review_run_click_command())
    for required in (
        "--bug-hunt",
        "--mode",
        "--focus",
        "--level",
        "--json",
        "--out",
        "--scope",
        "--path",
        "--include-tests",
        "--exclude-tests",
        "--fix",
        "--interactive",
        "--include-noise",
        "--suppress-noise",
        "--score-only",
        "--no-tests",
    ):
        assert required in flags, f"Typer surface missing {required}"
        assert required in text, f"docs/bundles/code-review/run.md must document {required}"


def test_code_review_run_doc_describes_invalid_flag_combinations() -> None:
    text = RUN_DOC.read_text(encoding="utf-8")
    assert "## Invalid combinations" in text
    assert "Positional" in text or "positional" in text
    assert "--scope" in text
    assert "--focus" in text
    assert "--include-tests" in text
    assert "--exclude-tests" in text
    assert "--out" in text and "--json" in text
