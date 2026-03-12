"""Radon runner for governed code-review findings."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require

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


def _allowed_paths(files: list[Path]) -> set[str]:
    allowed: set[str] = set()
    for file_path in files:
        allowed.update(_normalize_path_variants(file_path))
    return allowed


def _tool_error(file_path: Path, message: str) -> list[ReviewFinding]:
    return [
        ReviewFinding(
            category="tool_error",
            severity="error",
            tool="radon",
            rule="tool_error",
            file=str(file_path),
            line=1,
            message=message,
            fixable=False,
        )
    ]


def _iter_blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            raise ValueError("radon block must be an object")
        flattened.append(block)
        closures = block.get("closures", [])
        if closures:
            if not isinstance(closures, list):
                raise ValueError("radon closures must be a list")
            flattened.extend(_iter_blocks(closures))
    return flattened


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_radon(files: list[Path]) -> list[ReviewFinding]:
    """Run Radon for the provided files and map complexity findings into ReviewFinding records."""
    if not files:
        return []

    try:
        result = subprocess.run(
            ["radon", "cc", "-j", *(str(file_path) for file_path in files)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise ValueError("radon output must be an object")
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return _tool_error(files[0], f"Unable to parse Radon output: {exc}")

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    try:
        for filename, blocks in payload.items():
            if not isinstance(filename, str):
                raise ValueError("radon filename must be a string")
            if _normalize_path_variants(filename).isdisjoint(allowed_paths):
                continue
            if not isinstance(blocks, list):
                raise ValueError("radon file payload must be a list")
            for block in _iter_blocks(blocks):
                complexity = block["complexity"]
                line = block["lineno"]
                name = block["name"]
                if not isinstance(complexity, int):
                    raise ValueError("radon complexity must be an integer")
                if complexity <= 12:
                    continue
                if not isinstance(line, int):
                    raise ValueError("radon line must be an integer")
                if not isinstance(name, str):
                    raise ValueError("radon name must be a string")
                severity = "warning" if complexity <= 15 else "error"
                findings.append(
                    ReviewFinding(
                        category="clean_code",
                        severity=severity,
                        tool="radon",
                        rule=f"CC{complexity}",
                        file=filename,
                        line=line,
                        message=f"Cyclomatic complexity for {name} is {complexity}.",
                        fixable=False,
                    )
                )
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(files[0], f"Unable to parse Radon finding payload: {exc}")

    return findings
