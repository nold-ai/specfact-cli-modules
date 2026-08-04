#!/usr/bin/env python3
# ruff: noqa: N999
"""Validate generated module command overview paths against source Typer apps."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

import typer
from beartype import beartype
from icontract import ensure
from typer.testing import CliRunner


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_JSON = REPO_ROOT / "docs" / "reference" / "commands.generated.json"
APP_MOUNTS = (
    ("specfact_backlog.backlog.commands", "app", ("specfact", "backlog")),
    ("specfact_backlog.policy_engine.commands", "app", ("specfact", "backlog", "policy")),
    ("specfact_codebase.code.commands", "app", ("specfact", "code")),
    ("specfact_code_review.review.commands", "review_app", ("specfact", "code", "review")),
    ("specfact_govern.govern.commands", "app", ("specfact", "govern")),
    ("specfact_govern.enforce.commands", "app", ("specfact", "govern", "enforce")),
    ("specfact_project.project.commands", "app", ("specfact", "project")),
    ("specfact_requirements.requirements.commands", "app", ("specfact", "requirements")),
    ("specfact_spec.contract.commands", "app", ("specfact", "spec", "contract")),
    ("specfact_spec.spec.commands", "app", ("specfact", "spec")),
    ("specfact_spec.sdd.commands", "app", ("specfact", "spec", "sdd")),
    ("specfact_spec.generate.commands", "app", ("specfact", "spec", "generate")),
)
MISSING_MARKERS = (
    "missing",
    "requires an argument",
    "no such option",
    "no such command",
    "not a valid command",
)
MISSING_SUBCOMMAND_MARKERS = (
    "missing subcommand",
    "missing command",
)


def _paired_worktree_repo(source_marker: str, target_marker: str) -> Path | None:
    parts = REPO_ROOT.parts
    if source_marker not in parts:
        return None
    marker_index = parts.index(source_marker)
    base = Path(*parts[:marker_index])
    suffix = Path(*parts[marker_index + 1 :])
    return base / target_marker / suffix


def _ensure_package_paths() -> None:
    configured_core_repo = os.environ.get("SPECFACT_CLI_REPO", "").strip()
    core_repo_candidates: list[Path | None] = [
        Path(configured_core_repo).expanduser() if configured_core_repo else None,
        REPO_ROOT.parent / "specfact-cli",
        _paired_worktree_repo("specfact-cli-modules-worktrees", "specfact-cli-worktrees"),
    ]
    for candidate in core_repo_candidates:
        if candidate is None:
            continue
        src_path = candidate / "src"
        if src_path.is_dir():
            src = str(src_path.resolve())
            if src not in sys.path:
                sys.path.insert(0, src)
            break
    for src_path in sorted((REPO_ROOT / "packages").glob("*/src")):
        src = str(src_path)
        if src not in sys.path:
            sys.path.insert(0, src)


def _load_apps() -> dict[tuple[str, ...], object]:
    _ensure_package_paths()
    apps: dict[tuple[str, ...], object] = {}
    for module_path, attr_name, prefix in APP_MOUNTS:
        module = importlib.import_module(module_path)
        apps[prefix] = getattr(module, attr_name)
    return apps


def _load_records() -> list[dict[str, Any]]:
    raw = json.loads(COMMANDS_JSON.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{COMMANDS_JSON} must contain a JSON list")
    return [entry for entry in raw if isinstance(entry, dict)]


def _command_parts(record: dict[str, Any]) -> list[str]:
    command = record.get("command")
    return command.split() if isinstance(command, str) else []


def _select_app(apps: dict[tuple[str, ...], object], command_parts: list[str]) -> tuple[object, list[str]] | None:
    best_prefix: tuple[str, ...] | None = None
    for prefix in apps:
        if tuple(command_parts[: len(prefix)]) != prefix:
            continue
        if best_prefix is None or len(prefix) > len(best_prefix):
            best_prefix = prefix
    return None if best_prefix is None else (apps[best_prefix], command_parts[len(best_prefix) :])


def _invoke(
    runner: CliRunner,
    apps: dict[tuple[str, ...], object],
    command_parts: list[str],
    suffix: list[str],
) -> tuple[int, str]:
    selected = _select_app(apps, command_parts)
    if selected is None:
        return 2, f"No source app registered for generated command: {' '.join(command_parts)}"
    app, args = selected
    result = runner.invoke(cast(typer.Typer, app), [*args, *suffix])
    stdout = getattr(result, "stdout", "") or ""
    try:
        stderr = getattr(result, "stderr", "") or ""
    except ValueError:
        stderr = ""
    return result.exit_code, f"{stdout}{stderr}"


def _is_group(record: dict[str, Any]) -> bool:
    subcommands = record.get("subcommands")
    return isinstance(subcommands, list) and len(subcommands) > 0


def _has_required_argument(record: dict[str, Any]) -> bool:
    arguments = record.get("arguments")
    if not isinstance(arguments, list):
        return False
    return any(isinstance(argument, dict) and argument.get("required") for argument in arguments)


def _usage_lines(output: str) -> list[str]:
    usage_lines: list[str] = []
    capture_usage = False
    for line in output.splitlines():
        if "Usage:" in line:
            capture_usage = True
        if not capture_usage:
            continue
        if not line.strip():
            break
        usage_lines.append(line.lower())
    return usage_lines


def _check_help(runner: CliRunner, apps: dict[tuple[str, ...], object], record: dict[str, Any]) -> list[str]:
    command_parts = _command_parts(record)
    exit_code, output = _invoke(runner, apps, command_parts, ["--help"])
    if exit_code != 0:
        return [f"{record.get('command')}: --help exited {exit_code}\n{output}"]
    if "usage:" not in output.lower():
        return [f"{record.get('command')}: --help did not render usage\n{output}"]
    selected = _select_app(apps, command_parts)
    selected_args = selected[1] if selected is not None else []
    if not _is_group(record) and selected_args:
        command_parts = _command_parts(record)
        usage_lines = _usage_lines(output)
        if command_parts and command_parts[-1].lower() not in " ".join(usage_lines):
            return [f"{record.get('command')}: --help rendered parent usage instead of leaf usage\n{output}"]
    return []


def _check_group_missing_subcommand(
    runner: CliRunner,
    apps: dict[tuple[str, ...], object],
    record: dict[str, Any],
) -> list[str]:
    if not _is_group(record) or record.get("bare_invocation") == "executes":
        return []
    command_parts = _command_parts(record)
    exit_code, output = _invoke(runner, apps, command_parts, [])
    normalized = output.lower()
    failures: list[str] = []
    if exit_code == 0:
        failures.append(f"{record.get('command')}: bare group unexpectedly exited 0")
    if "usage:" not in normalized:
        failures.append(f"{record.get('command')}: bare group did not render usage")
    if not any(marker in normalized for marker in MISSING_SUBCOMMAND_MARKERS):
        failures.append(f"{record.get('command')}: bare group did not explain the missing subcommand")
    if normalized.count("usage:") != 1:
        failures.append(f"{record.get('command')}: expected exactly one usage block, saw {normalized.count('usage:')}")
    if failures:
        failures.append(output)
    return failures


def _check_missing_required_argument(
    runner: CliRunner,
    apps: dict[tuple[str, ...], object],
    record: dict[str, Any],
) -> list[str]:
    if _is_group(record) or not _has_required_argument(record):
        return []
    command_parts = _command_parts(record)
    exit_code, output = _invoke(runner, apps, command_parts, [])
    normalized = output.lower()
    failures: list[str] = []
    if exit_code == 0:
        failures.append(f"{record.get('command')}: missing required argument unexpectedly exited 0")
    if "usage:" not in normalized:
        failures.append(f"{record.get('command')}: missing required argument did not render usage")
    if not any(marker in normalized for marker in MISSING_MARKERS):
        failures.append(f"{record.get('command')}: missing required argument did not explain the failure")
    if normalized.count("usage:") != 1:
        failures.append(f"{record.get('command')}: expected exactly one usage block, saw {normalized.count('usage:')}")
    if failures:
        failures.append(output)
    return failures


@beartype
@ensure(lambda result: result in {0, 1})
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Validate only the first N generated commands")
    args = parser.parse_args(argv)

    apps = _load_apps()
    records = sorted(_load_records(), key=lambda record: len(str(record.get("command", "")).split()), reverse=True)
    if args.limit > 0:
        records = records[: args.limit]

    runner = CliRunner()
    failures: list[str] = []
    for record in records:
        failures.extend(_check_help(runner, apps, record))
        failures.extend(_check_group_missing_subcommand(runner, apps, record))
        failures.extend(_check_missing_required_argument(runner, apps, record))

    if failures:
        sys.stdout.write("Generated module command contract validation failed:\n")
        sys.stdout.write("\n\n".join(failures))
        sys.stdout.write("\n")
        return 1
    sys.stdout.write(f"check-command-contract: OK ({len(records)} generated module command path(s) validated)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
