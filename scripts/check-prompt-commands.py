#!/usr/bin/env python3
"""Validate shipped bundle prompt command references against mounted CLI contracts."""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

import click
from typer.main import get_command as typer_get_command


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_ROOT = REPO_ROOT / "packages"
INLINE_COMMAND_RE = re.compile(r"`(/?specfact(?:[\s.][^`\n]*)?)`")
OPTION_RE = re.compile(r"(?<![\w-])--[A-Za-z][A-Za-z0-9-]*")
COMMAND_STARTS = ("specfact ", "/specfact ", "specfact.", "/specfact.")
IGNORED_OPTIONS = frozenset({"--help"})
SKIP_OPTION_VALIDATION = frozenset({"[OPTIONS]", "[options]", "[ARGS]"})
REQUIRED_GUIDANCE_SNIPPETS = (
    "operating guidance",
    "not the source of truth",
    "CLI help is authoritative",
    "--help",
    "ask the user",
)
# Keep this explicit until bundle command metadata exposes prompt-validator mounts.
MODULE_APP_MOUNTS = (
    ("specfact_backlog.backlog.commands", "app", ("specfact", "backlog")),
    ("specfact_backlog.policy_engine.commands", "app", ("specfact", "backlog", "policy")),
    ("specfact_codebase.code.commands", "app", ("specfact", "code")),
    ("specfact_code_review.review.commands", "app", ("specfact", "code")),
    ("specfact_govern.govern.commands", "app", ("specfact", "govern")),
    ("specfact_govern.enforce.commands", "app", ("specfact", "govern", "enforce")),
    ("specfact_project.import_cmd.commands", "app", ("specfact", "import")),
    ("specfact_project.migrate.commands", "app", ("specfact", "migrate")),
    ("specfact_project.plan.commands", "app", ("specfact", "plan")),
    ("specfact_project.project.commands", "app", ("specfact", "project")),
    ("specfact_project.sync.commands", "app", ("specfact", "sync")),
    ("specfact_spec.contract.commands", "app", ("specfact", "spec", "contract")),
    ("specfact_spec.spec.commands", "app", ("specfact", "spec")),
    ("specfact_spec.sdd.commands", "app", ("specfact", "spec")),
    ("specfact_spec.generate.commands", "app", ("specfact", "spec", "generate")),
)
CORE_COMMAND_PATHS = frozenset(
    {
        ("specfact",),
        ("specfact", "init"),
        ("specfact", "module"),
        ("specfact", "upgrade"),
    }
)


class PromptCommandExample(NamedTuple):
    source: Path
    line_number: int
    text: str


class ValidationFinding(NamedTuple):
    category: str
    source: Path
    line_number: int
    message: str


class CommandIndex(NamedTuple):
    command_paths: set[tuple[str, ...]]
    options_by_path: dict[tuple[str, ...], set[str]]


def _script_name(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _ensure_package_paths() -> None:
    for src_path in sorted((REPO_ROOT / "packages").glob("*/src")):
        src = str(src_path)
        if src not in sys.path:
            sys.path.insert(0, src)


def _iter_prompt_paths(root: Path = PROMPT_ROOT) -> list[Path]:
    paths: list[Path] = []
    for package_root in sorted(root.glob("*/resources/prompts")):
        paths.extend(path.resolve() for path in sorted(package_root.rglob("*.md")) if path.is_file())
    return paths


def _load_texts(paths: Iterable[Path]) -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in paths}


def _command_options(command: click.Command) -> set[str]:
    options: set[str] = set()
    for param in command.params:
        if isinstance(param, click.Option):
            options.update(opt for opt in param.opts if opt.startswith("--"))
            options.update(opt for opt in param.secondary_opts if opt.startswith("--"))
    return options


def _collect_click_index(command: click.Command, prefix: tuple[str, ...], index: CommandIndex) -> None:
    index.command_paths.add(prefix)
    index.options_by_path.setdefault(prefix, set()).update(_command_options(command))
    if not isinstance(command, click.Group):
        return
    for name, child in command.commands.items():
        _collect_click_index(child, (*prefix, name), index)


def _build_command_index() -> CommandIndex:
    _ensure_package_paths()
    index = CommandIndex(
        command_paths=set(CORE_COMMAND_PATHS), options_by_path={path: set() for path in CORE_COMMAND_PATHS}
    )
    for module_name, attr_name, prefix in MODULE_APP_MOUNTS:
        try:
            module = importlib.import_module(module_name)
            app = getattr(module, attr_name)
            click_command = typer_get_command(app)
        except Exception as exc:
            msg = f"Failed to load CLI mount {module_name}:{attr_name} at {' '.join(prefix)}: {exc}"
            raise RuntimeError(msg) from exc
        _collect_click_index(click_command, prefix, index)
    return index


def _strip_comment(line: str) -> str:
    if line.lstrip().startswith("#"):
        return ""
    return re.sub(r"\s+#.*$", "", line).strip()


def _starts_with_command(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(COMMAND_STARTS)


def _normalize_prompt_command(raw: str) -> str:
    command = raw.strip().rstrip(":,")
    if command.startswith("/"):
        command = command[1:]
    return " ".join(command.split())


def _iter_fenced_command_examples(text: str, source: Path) -> list[PromptCommandExample]:
    examples: list[PromptCommandExample] = []
    in_shell_block = False
    pending = ""
    pending_line = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            fence_parts = stripped.removeprefix("```").split(maxsplit=1)
            fence_language = fence_parts[0].lower() if fence_parts else ""
            if in_shell_block:
                in_shell_block = False
                pending = ""
                pending_line = 0
            else:
                in_shell_block = fence_language in {"bash", "sh", "shell", "zsh", "console"}
            continue
        if not in_shell_block:
            continue
        line = _strip_comment(stripped)
        if not line:
            continue
        continued = line.rstrip("\\").strip()
        if pending:
            pending = f"{pending} {continued}"
        elif _starts_with_command(line):
            pending = continued
            pending_line = line_number
        else:
            continue
        if line.endswith("\\"):
            continue
        examples.append(PromptCommandExample(source, pending_line, _normalize_prompt_command(pending)))
        pending = ""
        pending_line = 0
    return examples


def _iter_inline_command_examples(text: str, source: Path) -> list[PromptCommandExample]:
    examples: list[PromptCommandExample] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        for match in INLINE_COMMAND_RE.finditer(raw_line):
            command = _normalize_prompt_command(match.group(1))
            if command.startswith("specfact"):
                examples.append(PromptCommandExample(source, line_number, command))
    return examples


def _extract_prompt_command_examples_from_text(text: str, source: Path) -> list[PromptCommandExample]:
    seen: set[tuple[int, str]] = set()
    examples: list[PromptCommandExample] = []
    inline_examples = _iter_inline_command_examples(text, source)
    cli_inline_examples = [example for example in inline_examples if "." not in example.text.split(maxsplit=1)[0]]
    slash_inline_examples = [example for example in inline_examples if "." in example.text.split(maxsplit=1)[0]]
    for example in [*_iter_fenced_command_examples(text, source), *cli_inline_examples, *slash_inline_examples]:
        key = (example.line_number, example.text)
        if key in seen:
            continue
        seen.add(key)
        examples.append(example)
    return examples


def _command_tokens(command_text: str) -> list[str]:
    tokens = command_text.split()
    if not tokens:
        return []
    # Tokens containing dots are IDE slash-command shortcuts, not CLI command paths.
    if "." in tokens[0]:
        return []
    return tokens


def _resolve_command_path(command_text: str, command_paths: set[tuple[str, ...]]) -> tuple[str, ...] | None:
    tokens = _command_tokens(command_text)
    if not tokens or tokens[0] != "specfact":
        return None
    command_words: list[str] = []
    for token in tokens:
        if token.startswith(("-", "[", "<")):
            break
        command_words.append(token)
    for length in range(len(command_words), 0, -1):
        candidate = tuple(command_words[:length])
        if candidate in command_paths:
            if len(candidate) == 1 and len(candidate) < len(command_words):
                return None
            return candidate
    return None


def _unknown_command_finding(example: PromptCommandExample) -> ValidationFinding:
    return ValidationFinding(
        category="command",
        source=example.source,
        line_number=example.line_number,
        message=f"Unknown prompt command example: {example.text}",
    )


def _options_for_path(path: tuple[str, ...], index: CommandIndex) -> set[str]:
    options: set[str] = set(IGNORED_OPTIONS)
    for length in range(1, len(path) + 1):
        options.update(index.options_by_path.get(tuple(path[:length]), set()))
    return options


def _unknown_option_findings(
    example: PromptCommandExample, path: tuple[str, ...], index: CommandIndex
) -> list[ValidationFinding]:
    if any(marker in example.text for marker in SKIP_OPTION_VALIDATION):
        return []
    allowed_options = _options_for_path(path, index)
    findings: list[ValidationFinding] = []
    for option in sorted(set(OPTION_RE.findall(example.text))):
        if option in allowed_options:
            continue
        findings.append(
            ValidationFinding(
                category="option",
                source=example.source,
                line_number=example.line_number,
                message=f"Unknown option for {' '.join(path)}: {option} in {example.text}",
            )
        )
    return findings


def _validate_prompt_command_examples(
    text_by_path: dict[Path, str], command_index: CommandIndex
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path, text in text_by_path.items():
        for example in _extract_prompt_command_examples_from_text(text, path):
            if not _command_tokens(example.text):
                continue
            resolved_path = _resolve_command_path(example.text, command_index.command_paths)
            if resolved_path is None:
                findings.append(_unknown_command_finding(example))
                continue
            findings.extend(_unknown_option_findings(example, resolved_path, command_index))
    return findings


def _has_executable_prompt_command(text: str, source: Path) -> bool:
    return any(_command_tokens(example.text) for example in _extract_prompt_command_examples_from_text(text, source))


def _has_cli_reality_check(text: str) -> bool:
    normalized = " ".join(text.split()).lower()
    return all(snippet.lower() in normalized for snippet in REQUIRED_GUIDANCE_SNIPPETS)


def _validate_cli_reality_check_guidance(text_by_path: dict[Path, str]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path, text in text_by_path.items():
        if not _has_executable_prompt_command(text, path):
            continue
        if _has_cli_reality_check(text):
            continue
        findings.append(
            ValidationFinding(
                category="guidance",
                source=path,
                line_number=1,
                message="Missing CLI reality-check/self-healing guidance for executable prompt commands",
            )
        )
    return findings


def _format_findings(findings: list[ValidationFinding]) -> str:
    return "\n".join(
        f"{_script_name(finding.source)}:{finding.line_number}: [{finding.category}] {finding.message}"
        for finding in findings
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate bundle prompt command references.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Prompt files to validate. Defaults to packages/*/resources/prompts/**/*.md.",
    )
    return parser.parse_args(argv)


def _selected_paths(args: argparse.Namespace) -> list[Path]:
    if not args.paths:
        return _iter_prompt_paths()
    return [path.resolve() for path in args.paths if path.suffix == ".md" and path.is_file()]


def _main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    paths = _selected_paths(args)
    text_by_path = _load_texts(paths)
    command_index = _build_command_index()
    findings = [
        *_validate_prompt_command_examples(text_by_path, command_index),
        *_validate_cli_reality_check_guidance(text_by_path),
    ]
    if findings:
        sys.stderr.write(_format_findings(findings) + "\n")
        return 1
    sys.stdout.write("Prompt command validation passed with no findings.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
