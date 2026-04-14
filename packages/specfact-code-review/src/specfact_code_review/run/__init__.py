"""Runtime helpers for code review."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Literal

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.scorer import ReviewScore, score_review


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, ReviewReport))
def run_review(
    files: list[Path],
    *,
    no_tests: bool = False,
    include_noise: bool = False,
    progress_callback: Callable[[str], None] | None = None,
    bug_hunt: bool = False,
    review_level: Literal["error", "warning"] | None = None,
    review_mode: Literal["shadow", "enforce"] = "enforce",
) -> ReviewReport:
    """Lazily import the orchestrator to avoid package import cycles."""
    run_review_impl = import_module("specfact_code_review.run.runner").run_review
    return run_review_impl(
        files,
        no_tests=no_tests,
        include_noise=include_noise,
        progress_callback=progress_callback,
        bug_hunt=bug_hunt,
        review_level=review_level,
        review_mode=review_mode,
    )


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list))
@ensure(lambda result: all(isinstance(finding, ReviewFinding) for finding in result))
def run_tdd_gate(files: list[Path]) -> list[ReviewFinding]:
    """Lazily import the TDD gate to avoid package import cycles."""
    run_tdd_gate_impl = import_module("specfact_code_review.run.runner").run_tdd_gate
    return run_tdd_gate_impl(files)


__all__ = ["ReviewFinding", "ReviewReport", "ReviewScore", "run_review", "run_tdd_gate", "score_review"]
