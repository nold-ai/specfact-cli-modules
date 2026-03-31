"""Ruff runner for governed code-review findings."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import normalize_path_variants, tool_error
from specfact_code_review.run.findings import ReviewFinding


def _allowed_paths(files: list[Path]) -> set[str]:
    allowed: set[str] = set()
    for file_path in files:
        allowed.update(normalize_path_variants(file_path))
    return allowed


def _category_for_rule(rule: str) -> Literal["security", "clean_code", "style"] | None:
    if rule.startswith("S"):
        return "security"
    if rule.startswith("C9"):
        return "clean_code"
    if rule.startswith(("E", "F", "I", "W")):
        return "style"
    return None


def _finding_from_item(item: object, *, allowed_paths: set[str]) -> ReviewFinding | None:
    if not isinstance(item, dict):
        raise ValueError("ruff finding must be an object")

    filename = item["filename"]
    if not isinstance(filename, str):
        raise ValueError("ruff filename must be a string")
    if normalize_path_variants(filename).isdisjoint(allowed_paths):
        return None

    location = item["location"]
    if not isinstance(location, dict):
        raise ValueError("ruff location must be an object")
    rule = item.get("code") or item.get("rule")
    if not isinstance(rule, str):
        raise ValueError("ruff rule must be a string")
    category = _category_for_rule(rule)
    if category is None:
        return None
    line = location["row"]
    if not isinstance(line, int):
        raise ValueError("ruff line must be an integer")
    message = item["message"]
    if not isinstance(message, str):
        raise ValueError("ruff message must be a string")

    return ReviewFinding(
        category=category,
        severity="warning",
        tool="ruff",
        rule=rule,
        file=filename,
        line=line,
        message=message,
        fixable=bool(item.get("fix")),
    )


def _payload_from_output(stdout: str) -> list[object]:
    payload = json.loads(stdout)
    if not isinstance(payload, list):
        raise ValueError("ruff output must be a list")
    return payload


def _findings_from_payload(payload: list[object], *, allowed_paths: set[str]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for item in payload:
        finding = _finding_from_item(item, allowed_paths=allowed_paths)
        if finding is not None:
            findings.append(finding)
    return findings


def _result_is_review_findings(result: list[ReviewFinding]) -> bool:
    return all(isinstance(finding, ReviewFinding) for finding in result)


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(_result_is_review_findings, "result must contain ReviewFinding instances")
def run_ruff(files: list[Path]) -> list[ReviewFinding]:
    """Run Ruff for the provided files and map findings into ReviewFinding records."""
    if not files:
        return []

    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format", "json", *[str(file_path) for file_path in files]],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        payload = _payload_from_output(result.stdout)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return [tool_error(tool="ruff", file_path=files[0], message=f"Unable to parse Ruff output: {exc}")]

    allowed_paths = _allowed_paths(files)
    try:
        return _findings_from_payload(payload, allowed_paths=allowed_paths)
    except (KeyError, TypeError, ValueError) as exc:
        return [
            tool_error(
                tool="ruff",
                file_path=files[0],
                message=f"Unable to parse Ruff finding payload: {exc}",
            )
        ]
