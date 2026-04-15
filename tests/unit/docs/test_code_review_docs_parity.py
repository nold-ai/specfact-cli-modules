"""Keep Code Review bundle docs aligned with the Typer ``run`` command surface."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
import typer
from typer.main import get_command as typer_get_command

from specfact_code_review.review import commands as review_commands
from specfact_code_review.review.commands import _resolve_review_run_flags
from specfact_code_review.run.commands import (
    ConflictingScopeError,
    InvalidOptionCombinationError,
    MissingOutForJsonError,
    ReviewRunRequest,
    _raise_if_targeting_styles_conflict,
    _validate_review_request,
)


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
    assert flags, "expected at least one public --option on the review run command"
    for flag in sorted(flags):
        assert flag in text, f"docs/bundles/code-review/run.md must document {flag}"


def _resolver_messages_for_docs_parity() -> list[str]:
    messages: list[str] = []
    with pytest.raises(typer.BadParameter) as exc:
        _resolve_review_run_flags(
            files=[],
            include_tests=True,
            exclude_tests=True,
            focus=None,
            include_noise=False,
            suppress_noise=False,
            interactive=False,
        )
    messages.append(str(exc.value))

    with pytest.raises(typer.BadParameter) as exc:
        _resolve_review_run_flags(
            files=[],
            include_tests=True,
            exclude_tests=None,
            focus=["source"],
            include_noise=False,
            suppress_noise=False,
            interactive=False,
        )
    messages.append(str(exc.value))
    return messages


def test_code_review_run_doc_describes_invalid_flag_combinations() -> None:
    text = RUN_DOC.read_text(encoding="utf-8")
    assert "## Invalid combinations" in text

    for msg in _resolver_messages_for_docs_parity():
        assert msg in text, f"run.md must document Typer resolver text: {msg!r}"

    with pytest.raises(InvalidOptionCombinationError) as exc:
        _validate_review_request(ReviewRunRequest(files=[], json_output=True, score_only=True))
    assert str(exc.value) in text

    with pytest.raises(MissingOutForJsonError) as exc:
        _validate_review_request(ReviewRunRequest(files=[], json_output=False, out=Path("review-out.json")))
    assert str(exc.value) in text

    for kwargs in (
        {"scope": "changed", "path_filters": []},
        {"scope": None, "path_filters": [Path("packages/specfact-code-review")]},
    ):
        with pytest.raises(ConflictingScopeError) as exc:
            _raise_if_targeting_styles_conflict(
                [Path("packages/specfact-code-review/src/x.py")],
                **kwargs,
            )
        assert str(exc.value) in text
