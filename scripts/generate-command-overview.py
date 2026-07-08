#!/usr/bin/env python3
# ruff: noqa: N999
"""Generate deterministic module command overview artifacts for humans and AI agents."""

from __future__ import annotations

import argparse
import difflib
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

import click
from beartype import beartype
from icontract import ensure
from typer.main import get_command


REPO_ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = REPO_ROOT / "docs" / "reference" / "commands.generated.json"
MARKDOWN_PATH = REPO_ROOT / "docs" / "reference" / "commands.generated.md"
LLMS_PATH = REPO_ROOT / "llms.txt"

MODULE_APP_MOUNTS = (
    ("specfact_backlog.backlog.commands", "app", ("specfact", "backlog"), "nold-ai/specfact-backlog"),
    ("specfact_codebase.code.commands", "app", ("specfact", "code"), "nold-ai/specfact-codebase"),
    ("specfact_code_review.review.commands", "app", ("specfact", "code", "review"), "nold-ai/specfact-code-review"),
    ("specfact_govern.govern.commands", "app", ("specfact", "govern"), "nold-ai/specfact-govern"),
    ("specfact_project.project.commands", "app", ("specfact", "project"), "nold-ai/specfact-project"),
    (
        "specfact_requirements.requirements.commands",
        "app",
        ("specfact", "requirements"),
        "nold-ai/specfact-requirements",
    ),
    ("specfact_spec.spec.commands", "app", ("specfact", "spec"), "nold-ai/specfact-spec"),
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


def _command_options(command: click.Command) -> list[str]:
    options: set[str] = set()
    for param in command.params:
        if hasattr(param, "opts"):
            secondary_opts = getattr(param, "secondary_opts", ())
            options.update(opt for opt in [*param.opts, *secondary_opts] if opt.startswith("--"))
    return sorted(options)


def _command_arguments(command: click.Command) -> list[dict[str, Any]]:
    arguments: list[dict[str, Any]] = []
    for param in command.params:
        if not hasattr(param, "opts") and hasattr(param, "human_readable_name"):
            arguments.append(
                {
                    "name": param.human_readable_name,
                    "required": bool(param.required),
                    "nargs": param.nargs,
                }
            )
    return arguments


def _command_children(command: click.Command) -> dict[str, click.Command]:
    if not (hasattr(command, "list_commands") and hasattr(command, "get_command")):
        return {}
    context_cls = getattr(command, "context_class", click.Context)
    with context_cls(command, info_name=command.name) as ctx:
        children: dict[str, click.Command] = {}
        for name in command.list_commands(ctx):
            if name == "__delegate__":
                continue
            child = command.get_command(ctx, name)
            if child is not None:
                children[name] = child
        return children


def _bare_invocation(command: click.Command) -> str:
    is_group = hasattr(command, "list_commands") and hasattr(command, "get_command")
    if is_group and bool(getattr(command, "invoke_without_command", False)) and _has_bare_business_parameters(command):
        return "executes"
    if is_group:
        return "requires-subcommand"
    return "executes"


def _has_bare_business_parameters(command: click.Command) -> bool:
    ignored_options = {
        "--help",
        "-h",
        "--help-advanced",
        "-ha",
        "--install-completion",
        "--show-completion",
    }
    for param in command.params:
        if not hasattr(param, "opts") and hasattr(param, "human_readable_name"):
            return True
        if hasattr(param, "opts"):
            opts = set(param.opts) | set(getattr(param, "secondary_opts", ()))
            if opts and opts.isdisjoint(ignored_options):
                return True
    return False


def _walk(command: click.Command, path: tuple[str, ...], source: str, module_id: str) -> list[dict[str, Any]]:
    children = _command_children(command)
    record = {
        "command": " ".join(path),
        "owner_repo": "nold-ai/specfact-cli-modules",
        "owner_package": module_id,
        "install_prerequisite": f"specfact module install {module_id}",
        "short_help": (command.short_help or "").strip(),
        "arguments": _command_arguments(command),
        "bare_invocation": _bare_invocation(command),
        "options": _command_options(command),
        "subcommands": sorted(children),
        "source": source,
        "hidden": bool(getattr(command, "hidden", False)),
        "deprecated": bool(getattr(command, "deprecated", False)),
    }
    records = [record]
    for name, child in sorted(children.items()):
        records.extend(_walk(child, (*path, name), source, module_id))
    return records


@beartype
@ensure(lambda result: all("command" in record for record in result))
def build_records() -> list[dict[str, Any]]:
    _ensure_package_paths()
    records: list[dict[str, Any]] = []
    for module_name, attr_name, prefix, module_id in MODULE_APP_MOUNTS:
        module = importlib.import_module(module_name)
        app = getattr(module, attr_name)
        click_command = cast(click.Command, get_command(app))
        records.extend(_walk(click_command, prefix, f"{module_name}:{attr_name}", module_id))
    return sorted(records, key=lambda record: record["command"])


def _render_markdown(records: list[dict[str, Any]]) -> str:
    lines = [
        "---",
        "layout: default",
        "title: Generated SpecFact Module Command Overview",
        "permalink: /reference/generated-module-command-overview/",
        "exempt: true",
        "exempt_reason: Generated command contract artifact.",
        "---",
        "",
        "# Generated SpecFact Module Command Overview",
        "",
        "This file is generated from the current module command trees. Do not edit by hand.",
        "",
        "| Command | Module | Install | Options | Subcommands | Context |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        arguments = ", ".join(
            f"{arg['name']}{' (required)' if arg.get('required') else ''}" for arg in record["arguments"]
        )
        options = ", ".join(record["options"]) or "-"
        subcommands = ", ".join(record["subcommands"]) or "-"
        help_text = str(record["short_help"]).replace("\n", " ")
        lines.append(
            f"| `{record['command']}` | {record['owner_package']} | `{record['install_prerequisite']}` | "
            f"{options}; args: {arguments or '-'} | {subcommands} | {help_text} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_llms(markdown: str) -> str:
    return "\n".join(
        [
            "# SpecFact Module Commands",
            "",
            (
                "Use this generated overview as the current module command contract "
                "before following older docs or prompts."
            ),
            "",
            markdown,
        ]
    )


def _desired_outputs() -> dict[Path, str]:
    records = build_records()
    markdown = _render_markdown(records)
    return {
        JSON_PATH: json.dumps(records, indent=2, sort_keys=True) + "\n",
        MARKDOWN_PATH: markdown,
        LLMS_PATH: _render_llms(markdown),
    }


def _check(outputs: dict[Path, str]) -> int:
    failures = []
    for path, expected in outputs.items():
        actual = path.read_text(encoding="utf-8") if path.exists() else ""
        if actual != expected:
            failures.append(path)
            sys.stdout.write(
                "\n".join(
                    difflib.unified_diff(
                        actual.splitlines(),
                        expected.splitlines(),
                        fromfile=str(path),
                        tofile=f"{path} (generated)",
                        lineterm="",
                    )
                )
                + "\n"
            )
    if failures:
        sys.stdout.write(
            "Module command overview artifacts are stale. Run: python scripts/generate-command-overview.py --write\n"
        )
        return 1
    return 0


@beartype
@ensure(lambda result: result in {0, 1})
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write generated artifacts")
    parser.add_argument("--check", action="store_true", help="Check generated artifacts are current")
    args = parser.parse_args(argv)
    outputs = _desired_outputs()
    if args.write:
        for path, text in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return 0
    return _check(outputs)


if __name__ == "__main__":
    raise SystemExit(main())
