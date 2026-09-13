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


_PYTHON_LINTER_SUFFIXES = frozenset({".py", ".pyi"})


@beartype
@require(lambda files: isinstance(files, list))
@require(lambda files: all(isinstance(p, Path) for p in files))
@ensure(lambda result: isinstance(result, list))
def python_source_paths_for_tools(files: list[Path]) -> list[Path]:
    """Python source and type stub paths linters/typecheckers should analyze."""
    return [path for path in files if path.suffix in _PYTHON_LINTER_SUFFIXES]


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


_CAPSULE_TOOL_MODULES = {
    "radon": "radon",
    "pylint": "pylint",
    "basedpyright": "basedpyright",
    "crosshair": "crosshair",
    "semgrep": "semgrep.console_scripts.pysemgrep",
}


@beartype
@require(lambda command: bool(command) and all(isinstance(item, str) for item in command))
@ensure(lambda result: isinstance(result, list) and bool(result))
def analyzer_command(command: list[str]) -> list[str]:
    """Preserve isolated Python child imports and private Ruff cache in a capsule."""
    if Path(__file__).parent != Path("/opt/specfact/builtin/specfact_code_review"):
        return command
    if command[0] == "ruff":
        return [*command, "--cache-dir", "/opt/specfact/tmp/cache/ruff"]
    module = _CAPSULE_TOOL_MODULES.get(command[0])
    if module is None:
        return command
    return [
        "/opt/specfact/python/bin/python",
        "-I",
        "-S",
        "/opt/specfact/bootstrap/sealed_bootstrap.py",
        module,
        *command[1:],
    ]
