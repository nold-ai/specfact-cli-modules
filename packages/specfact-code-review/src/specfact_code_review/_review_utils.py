"""Shared internal helpers for review runners."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from specfact_code_review.run.findings import ReviewFinding


def _normalize_path_variants(path_value: str | Path) -> set[str]:
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


def _tool_error(
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
