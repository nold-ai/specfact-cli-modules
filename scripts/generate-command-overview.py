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
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import click
import yaml
from beartype import beartype
from icontract import ensure
from typer.core import TyperArgument, TyperOption
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
RUNTIME_VALIDATED_GROUPS = frozenset(
    {
        "specfact code import",
        "specfact code repro",
    }
)

OPTION_PARAMETER_TYPES = (click.Option, TyperOption)
ARGUMENT_PARAMETER_TYPES = (click.Argument, TyperArgument)
OFFICIAL_METADATA_FIELDS = (
    ("tier", "tier"),
    ("publisher", "publisher"),
    ("bundle_dependencies", "bundle_dependencies"),
    ("description", "description"),
    ("core_compatibility", "core_compatibility"),
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


def _is_official_nold_module(data: Mapping[str, object]) -> bool:
    publisher = data.get("publisher")
    return data.get("tier") == "official" and isinstance(publisher, Mapping) and publisher.get("name") == "nold-ai"


def _official_manifest_inventory() -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for manifest_path in sorted((REPO_ROOT / "packages").glob("*/module-package.yaml")):
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not _is_official_nold_module(data):
            continue
        package_id = data.get("name")
        grouped_root = data.get("bundle_group_command")
        if not isinstance(package_id, str) or not isinstance(grouped_root, str) or not grouped_root:
            raise ValueError(f"Invalid official module manifest: {manifest_path}")
        if package_id in inventory:
            raise ValueError(f"Duplicate official module manifest: {package_id}")
        inventory[package_id] = data
    if not inventory:
        raise ValueError(f"No official module manifests found under {REPO_ROOT / 'packages'}")
    return inventory


def _official_registry_inventory() -> dict[str, dict[str, object]]:
    registry_path = REPO_ROOT / "registry" / "index.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("modules"), list):
        raise ValueError(f"Invalid marketplace registry: {registry_path}")
    inventory: dict[str, dict[str, object]] = {}
    for entry in registry["modules"]:
        if not isinstance(entry, dict) or not _is_official_nold_module(entry):
            continue
        package_id = entry.get("id")
        if not isinstance(package_id, str):
            raise ValueError(f"Invalid official registry entry: {registry_path}")
        if package_id in inventory:
            raise ValueError(f"Duplicate official registry entry: {package_id} ({registry_path})")
        inventory[package_id] = entry
    return inventory


def _validate_matching_official_inventory_keys(manifests: Mapping[str, object], registry: Mapping[str, object]) -> None:
    if set(manifests) != set(registry):
        raise ValueError(
            "Official manifests and marketplace registry disagree: "
            f"manifests={sorted(manifests)}, registry={sorted(registry)}"
        )


def _official_metadata_drift(
    manifests: Mapping[str, Mapping[str, object]], registry: Mapping[str, Mapping[str, object]]
) -> list[str]:
    return [
        f"{package_id}: manifest.{manifest_field} != registry.{registry_field}"
        for package_id, manifest in sorted(manifests.items())
        for manifest_field, registry_field in OFFICIAL_METADATA_FIELDS
        if manifest.get(manifest_field) != registry[package_id].get(registry_field)
    ]


def _mount_inventory_findings(manifests: Mapping[str, Mapping[str, object]]) -> list[str]:
    mount_roots: dict[str, set[str]] = {}
    for _, _, prefix, package_id in MODULE_APP_MOUNTS:
        if len(prefix) < 2 or prefix[0] != "specfact":
            raise ValueError(f"Invalid command mount for {package_id}: {prefix}")
        mount_roots.setdefault(package_id, set()).add(prefix[1])
    missing = sorted(set(manifests) - set(mount_roots))
    unexpected = sorted(set(mount_roots) - set(manifests))
    mismatched_roots = [
        f"{package_id} (expected {root}, mounts {sorted(mount_roots[package_id])})"
        for package_id, manifest in sorted(manifests.items())
        if isinstance((root := manifest.get("bundle_group_command")), str)
        and package_id in mount_roots
        and root not in mount_roots[package_id]
    ]
    return [
        *([f"missing command mounts for {missing}"] if missing else []),
        *([f"command mounts without official manifests for {unexpected}"] if unexpected else []),
        *([f"grouped root mismatch for {mismatched_roots}"] if mismatched_roots else []),
    ]


@beartype
@ensure(lambda result: result is None)
def validate_official_mount_inventory() -> None:
    """Reject official package records that cannot appear in generated output."""
    manifests = _official_manifest_inventory()
    registry = _official_registry_inventory()
    _validate_matching_official_inventory_keys(manifests, registry)
    metadata_drift = _official_metadata_drift(manifests, registry)
    if metadata_drift:
        raise ValueError("Official manifest and registry metadata drift: " + "; ".join(metadata_drift))
    findings = _mount_inventory_findings(manifests)
    if findings:
        raise ValueError("Official module command inventory is inconsistent: " + "; ".join(findings))


def _command_options(command: click.Command) -> list[str]:
    options: set[str] = set()
    for param in command.params:
        if isinstance(param, OPTION_PARAMETER_TYPES):
            secondary_opts = param.secondary_opts
            options.update(opt for opt in [*param.opts, *secondary_opts] if opt.startswith("--"))
    return sorted(options)


def _argument_display_name(param: click.Argument | TyperArgument) -> str:
    return param.metavar or param.human_readable_name.upper()


def _command_arguments(command: click.Command) -> list[dict[str, Any]]:
    arguments: list[dict[str, Any]] = []
    for param in command.params:
        if isinstance(param, ARGUMENT_PARAMETER_TYPES):
            arguments.append(
                {
                    "name": _argument_display_name(param),
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


def _bare_invocation(command: click.Command, path: tuple[str, ...]) -> str:
    if " ".join(path) in RUNTIME_VALIDATED_GROUPS:
        return "executes"
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
        if isinstance(param, ARGUMENT_PARAMETER_TYPES):
            return True
        if isinstance(param, OPTION_PARAMETER_TYPES):
            opts = set(param.opts) | set(param.secondary_opts)
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
        "bare_invocation": _bare_invocation(command, path),
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
    validate_official_mount_inventory()
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
