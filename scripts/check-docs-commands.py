#!/usr/bin/env python3
"""Validate bundle docs command examples, legacy resource paths, and core-doc links."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

import click
import yaml
from typer.main import get_command as typer_get_command


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
CORE_DOCS_HOST = "docs.specfact.io"
ALLOWED_CORE_DOCS_ROUTES = frozenset({"/", "/reference/documentation-url-contract/"})
CORE_COMMAND_PREFIXES = frozenset(
    {
        ("specfact",),
        ("specfact", "init"),
        ("specfact", "module"),
        ("specfact", "upgrade"),
    }
)
LEGACY_RESOURCE_PATH_SNIPPETS = (
    ".cursor/commands",
    ".claude/commands",
    ".claude/instructions",
    ".github/prompts",
    ".github/instructions",
    ".specfact/prompts",
    "src/specfact_cli/prompts",
    "src/specfact_cli/templates",
)
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "docs-review.yml"
MARKDOWN_CODE_RE = re.compile(r"`([^`\n]*specfact [^`\n]*)`")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HTML_HREF_RE = re.compile(r'href="([^"]+)"')


CommandPath = tuple[str, ...]


class CommandExample(NamedTuple):
    source: Path
    line_number: int
    text: str


class ValidationFinding(NamedTuple):
    category: str
    source: Path
    line_number: int
    message: str


MODULE_APP_MOUNTS = (
    ("specfact_backlog.backlog.commands", "app", ("specfact", "backlog")),
    ("specfact_backlog.policy_engine.commands", "app", ("specfact", "backlog", "policy")),
    ("specfact_codebase.code.commands", "app", ("specfact", "code")),
    ("specfact_code_review.review.commands", "app", ("specfact", "code")),
    ("specfact_govern.govern.commands", "app", ("specfact", "govern")),
    ("specfact_project.import_cmd.commands", "app", ("specfact", "import")),
    ("specfact_project.migrate.commands", "app", ("specfact", "migrate")),
    ("specfact_project.plan.commands", "app", ("specfact", "plan")),
    ("specfact_project.project.commands", "app", ("specfact", "project")),
    ("specfact_project.sync.commands", "app", ("specfact", "sync")),
    ("specfact_spec.spec.commands", "app", ("specfact", "spec")),
    ("specfact_spec.sdd.commands", "app", ("specfact", "spec")),
    ("specfact_spec.generate.commands", "app", ("specfact", "spec")),
)


def _script_name(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _ensure_package_paths() -> None:
    for src_path in sorted((REPO_ROOT / "packages").glob("*/src")):
        src = str(src_path)
        if src not in sys.path:
            sys.path.insert(0, src)


def _iter_validation_docs_paths() -> list[Path]:
    return sorted(path.resolve() for path in DOCS_ROOT.rglob("*.md"))


def _iter_bash_examples(text: str, source: Path) -> list[CommandExample]:
    examples: list[CommandExample] = []
    in_bash_block = False
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```bash"):
            in_bash_block = True
            continue
        if in_bash_block and stripped.startswith("```"):
            in_bash_block = False
            continue
        if in_bash_block and stripped.startswith("specfact "):
            examples.append(CommandExample(source=source, line_number=line_number, text=stripped))
    return examples


def _iter_inline_examples(text: str, source: Path) -> list[CommandExample]:
    examples: list[CommandExample] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        for match in MARKDOWN_CODE_RE.finditer(raw_line):
            examples.append(CommandExample(source=source, line_number=line_number, text=match.group(1).strip()))
    return examples


def _extract_command_examples(path: Path) -> list[CommandExample]:
    text = path.read_text(encoding="utf-8")
    seen: set[tuple[int, str]] = set()
    examples: list[CommandExample] = []
    for example in [*_iter_bash_examples(text, path), *_iter_inline_examples(text, path)]:
        key = (example.line_number, example.text)
        if key in seen:
            continue
        seen.add(key)
        examples.append(example)
    return examples


def _load_docs_texts(paths: list[Path]) -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in paths}


def _normalize_command_text(command_text: str) -> list[str]:
    normalized = command_text.strip().rstrip(":.,")
    return normalized.split()


def _collect_click_paths(group: click.Command, prefix: CommandPath) -> set[CommandPath]:
    paths: set[CommandPath] = set()
    if not isinstance(group, click.Group):
        return paths
    for name, command in group.commands.items():
        child_prefix = (*prefix, name)
        paths.add(child_prefix)
        if isinstance(command, click.Group):
            paths.update(_collect_click_paths(command, child_prefix))
    return paths


def _build_valid_command_paths() -> set[CommandPath]:
    _ensure_package_paths()
    paths: set[CommandPath] = set(CORE_COMMAND_PREFIXES)
    for module_name, attr_name, prefix in MODULE_APP_MOUNTS:
        module = importlib.import_module(module_name)
        app = getattr(module, attr_name)
        click_group = typer_get_command(app)
        paths.add(prefix)
        paths.update(_collect_click_paths(click_group, prefix))
    return paths


def _command_example_is_valid(command_text: str, valid_paths: set[CommandPath]) -> bool:
    tokens = _normalize_command_text(command_text)
    if not tokens or tokens[0] != "specfact":
        return True
    if len(tokens) == 1:
        return ("specfact",) in valid_paths
    if tokens[1].startswith("-"):
        return ("specfact",) in valid_paths
    prefixes = (tuple(tokens[:length]) for length in range(len(tokens), 0, -1))
    return any(prefix in valid_paths for prefix in prefixes if len(prefix) > 1)


def _validate_command_examples(text_by_path: dict[Path, str], valid_paths: set[CommandPath]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path, text in text_by_path.items():
        seen: set[tuple[int, str]] = set()
        for example in [*_iter_bash_examples(text, path), *_iter_inline_examples(text, path)]:
            key = (example.line_number, example.text)
            if key in seen:
                continue
            seen.add(key)
            if _command_example_is_valid(example.text, valid_paths):
                continue
            findings.append(
                ValidationFinding(
                    category="command",
                    source=example.source,
                    line_number=example.line_number,
                    message=f"Unknown command example: {example.text}",
                )
            )
    return findings


def _validate_legacy_resource_paths(text_by_path: dict[Path, str]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path, text in text_by_path.items():
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            for snippet in LEGACY_RESOURCE_PATH_SNIPPETS:
                if snippet not in raw_line:
                    continue
                findings.append(
                    ValidationFinding(
                        category="legacy-resource",
                        source=path,
                        line_number=line_number,
                        message=f"Legacy core-owned resource reference: {snippet}",
                    )
                )
    return findings


def _normalize_core_docs_route(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != CORE_DOCS_HOST:
        return None
    route = parsed.path or "/"
    if route != "/" and not route.endswith("/"):
        route += "/"
    return route


def _iter_core_docs_urls_from_text(text: str) -> list[str]:
    urls: list[str] = []
    for link in MARKDOWN_LINK_RE.findall(text):
        urls.append(link)
    for link in HTML_HREF_RE.findall(text):
        urls.append(link)
    return urls


def _validate_core_docs_links(text_by_path: dict[Path, str]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path, text in text_by_path.items():
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            for url in _iter_core_docs_urls_from_text(raw_line):
                route = _normalize_core_docs_route(url)
                if route is None or route in ALLOWED_CORE_DOCS_ROUTES:
                    continue
                findings.append(
                    ValidationFinding(
                        category="cross-site-link",
                        source=path,
                        line_number=line_number,
                        message=f"Unsupported docs.specfact.io route: {url}",
                    )
                )
    return findings


def _validate_core_docs_config(config_path: Path) -> list[ValidationFinding]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    findings: list[ValidationFinding] = []
    for key in ("docs_home_url", "core_cli_docs_url"):
        value = str(data.get(key, "")).strip()
        route = _normalize_core_docs_route(value)
        if route in ALLOWED_CORE_DOCS_ROUTES:
            continue
        findings.append(
            ValidationFinding(
                category="cross-site-link",
                source=config_path,
                line_number=1,
                message=f"{key} must target an allowed docs.specfact.io route: {value or '<missing>'}",
            )
        )
    return findings


def _format_findings(findings: list[ValidationFinding]) -> str:
    return "\n".join(
        f"{_script_name(finding.source)}:{finding.line_number}: [{finding.category}] {finding.message}"
        for finding in findings
    )


def _main() -> int:
    docs_paths = _iter_validation_docs_paths()
    text_by_path = _load_docs_texts(docs_paths)
    valid_paths = _build_valid_command_paths()
    findings = [
        *_validate_command_examples(text_by_path, valid_paths),
        *_validate_legacy_resource_paths(text_by_path),
        *_validate_core_docs_links(text_by_path),
        *_validate_core_docs_config(DOCS_ROOT / "_config.yml"),
    ]
    if findings:
        sys.stdout.write(_format_findings(findings) + "\n")
        return 1
    sys.stdout.write("Docs command validation passed with no findings.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
