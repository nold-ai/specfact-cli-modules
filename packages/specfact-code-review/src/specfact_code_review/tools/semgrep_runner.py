"""Semgrep runner for governed code-review findings."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding


SEMGREP_RULE_CATEGORY = {
    "get-modify-same-method": "clean_code",
    "unguarded-nested-access": "clean_code",
    "cross-layer-call": "architecture",
    "module-level-network": "architecture",
    "print-in-src": "architecture",
}


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
            tool="semgrep",
            rule="tool_error",
            file=str(file_path),
            line=1,
            message=message,
            fixable=False,
        )
    ]


def _normalize_rule_id(rule: str) -> str:
    for suffix in SEMGREP_RULE_CATEGORY:
        if rule == suffix or rule.endswith(f".{suffix}"):
            return suffix
    return rule


def _resolve_config_path() -> Path:
    package_root = Path(__file__).resolve().parents[3]
    config_path = package_root / ".semgrep" / "clean_code.yaml"
    if config_path.exists():
        return config_path
    raise FileNotFoundError(f"Semgrep config not found at {config_path}")


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_semgrep(files: list[Path]) -> list[ReviewFinding]:
    """Run Semgrep for the provided files and map findings into ReviewFinding records."""
    if not files:
        return []

    try:
        with tempfile.TemporaryDirectory(prefix="semgrep-home-") as temp_home:
            semgrep_home = Path(temp_home)
            semgrep_log_dir = semgrep_home / ".semgrep"
            semgrep_log_dir.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["HOME"] = str(semgrep_home)
            env["XDG_CONFIG_HOME"] = str(semgrep_home / ".config")
            env["XDG_CACHE_HOME"] = str(semgrep_home / ".cache")
            env["SEMGREP_SETTINGS_FILE"] = str(semgrep_log_dir / "settings.yml")
            env.setdefault("SEMGREP_SEND_METRICS", "off")
            result = subprocess.run(
                [
                    "semgrep",
                    "--config",
                    str(_resolve_config_path()),
                    "--json",
                    *(str(file_path) for file_path in files),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
                env=env,
            )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise ValueError("semgrep output must be an object")
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("semgrep results must be a list")
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return _tool_error(files[0], f"Unable to parse Semgrep output: {exc}")

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    try:
        for item in raw_results:
            if not isinstance(item, dict):
                raise ValueError("semgrep finding must be an object")
            filename = item["path"]
            if not isinstance(filename, str):
                raise ValueError("semgrep filename must be a string")
            if _normalize_path_variants(filename).isdisjoint(allowed_paths):
                continue

            raw_rule = item["check_id"]
            if not isinstance(raw_rule, str):
                raise ValueError("semgrep rule must be a string")
            rule = _normalize_rule_id(raw_rule)
            category = SEMGREP_RULE_CATEGORY.get(rule)
            if category is None:
                continue

            start = item["start"]
            if not isinstance(start, dict):
                raise ValueError("semgrep start location must be an object")
            line = start["line"]
            if not isinstance(line, int):
                raise ValueError("semgrep line must be an integer")

            extra = item["extra"]
            if not isinstance(extra, dict):
                raise ValueError("semgrep extra payload must be an object")
            message = extra["message"]
            if not isinstance(message, str):
                raise ValueError("semgrep message must be a string")

            findings.append(
                ReviewFinding(
                    category=category,
                    severity="warning",
                    tool="semgrep",
                    rule=rule,
                    file=filename,
                    line=line,
                    message=message,
                    fixable=False,
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(files[0], f"Unable to parse Semgrep finding payload: {exc}")

    return findings
