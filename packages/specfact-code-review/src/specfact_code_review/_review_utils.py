"""Shared internal helpers for review runners."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding


@beartype
@require(lambda path_value: isinstance(path_value, str | Path))
@ensure(lambda result: isinstance(result, set))
def normalize_path_variants(path_value: str | Path) -> set[str]:
    """Return a normalized set of path spellings for source matching."""
    path = Path(path_value)
    variants = {
        os.path.normpath(str(path)),
        os.path.normpath(path.as_posix()),
    }
    try:
        resolved = path.resolve()
    except OSError:
        return variants
    variants.add(os.path.normpath(str(resolved)))
    variants.add(os.path.normpath(resolved.as_posix()))
    return variants


@beartype
@require(lambda tool: isinstance(tool, str) and bool(tool.strip()))
@require(lambda file_path: isinstance(file_path, Path))
@require(lambda message: isinstance(message, str) and bool(message.strip()))
@require(lambda severity: severity in {"error", "warning", "info"})
@ensure(lambda result: isinstance(result, ReviewFinding))
def tool_error(
    *,
    tool: str,
    file_path: Path,
    message: str,
    severity: Literal["error", "warning", "info"] = "error",
) -> ReviewFinding:
    return ReviewFinding(
        category="tool_error",
        severity=severity,
        tool=tool,
        rule="tool_error",
        file=str(file_path),
        line=1,
        message=message,
        fixable=False,
    )
