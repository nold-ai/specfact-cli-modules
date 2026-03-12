"""Ruff runner for governed code-review findings."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

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


def _category_for_rule(rule: str) -> str:
    if rule.startswith("S"):
        return "security"
    if rule.startswith("C9"):
        return "clean_code"
    if rule.startswith(("E", "F", "I", "W")):
        return "style"
    return "style"


def _tool_error(file_path: Path, message: str) -> list[ReviewFinding]:
    return [
        ReviewFinding(
            category="tool_error",
            severity="error",
            tool="ruff",
            rule="tool_error",
            file=str(file_path),
            line=1,
            message=message,
            fixable=False,
        )
    ]


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_ruff(files: list[Path]) -> list[ReviewFinding]:
    """Run Ruff for the provided files and map findings into ReviewFinding records."""
    if not files:
        return []

    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format", "json", *(str(file_path) for file_path in files)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, list):
            raise ValueError("ruff output must be a list")
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return _tool_error(files[0], f"Unable to parse Ruff output: {exc}")

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    try:
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("ruff finding must be an object")
            filename = item["filename"]
            if not isinstance(filename, str):
                raise ValueError("ruff filename must be a string")
            if _normalize_path_variants(filename).isdisjoint(allowed_paths):
                continue
            location = item["location"]
            if not isinstance(location, dict):
                raise ValueError("ruff location must be an object")
            rule = item.get("code") or item.get("rule")
            if not isinstance(rule, str):
                raise ValueError("ruff rule must be a string")
            line = location["row"]
            if not isinstance(line, int):
                raise ValueError("ruff line must be an integer")
            message = item["message"]
            if not isinstance(message, str):
                raise ValueError("ruff message must be a string")
            findings.append(
                ReviewFinding(
                    category=_category_for_rule(rule),
                    severity="warning",
                    tool="ruff",
                    rule=rule,
                    file=filename,
                    line=line,
                    message=message,
                    fixable=bool(item.get("fix")),
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(files[0], f"Unable to parse Ruff finding payload: {exc}")

    return findings
