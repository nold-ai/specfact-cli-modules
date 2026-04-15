"""Smoke tests for lazy `specfact_code_review.run` exports."""

from __future__ import annotations

import specfact_code_review.run as run_pkg


def test_run_package_exports_run_review() -> None:
    assert callable(run_pkg.run_review)


def test_all_exports_are_defined() -> None:
    for name in run_pkg.__all__:
        assert hasattr(run_pkg, name)
