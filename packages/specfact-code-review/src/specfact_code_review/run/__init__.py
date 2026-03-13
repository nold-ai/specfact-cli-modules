"""Runtime helpers for code review."""

from typing import Any

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.scorer import ReviewScore, score_review


def run_review(*args: Any, **kwargs: Any) -> ReviewReport:
    """Lazily import the orchestrator to avoid package import cycles."""
    from specfact_code_review.run.runner import run_review as _run_review

    return _run_review(*args, **kwargs)


def run_tdd_gate(*args: Any, **kwargs: Any) -> list[ReviewFinding]:
    """Lazily import the TDD gate to avoid package import cycles."""
    from specfact_code_review.run.runner import run_tdd_gate as _run_tdd_gate

    return _run_tdd_gate(*args, **kwargs)


__all__ = ["ReviewFinding", "ReviewReport", "ReviewScore", "run_review", "run_tdd_gate", "score_review"]
