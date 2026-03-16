"""House-rules skill template, IDE sync, and update algorithm."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date
from enum import StrEnum
from importlib.resources import files
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.ledger.client import LedgerRun


_BUNDLED_SKILL_PATH = ("resources", "skills", "specfact-code-review", "SKILL.md")


MAX_SKILL_LINES = 35
SKILL_PATH = Path("skills/specfact-code-review/SKILL.md")

CURSOR_RULES_PATH = Path(".cursor/rules/house_rules.mdc")
TITLE_PREFIX = "# House Rules - AI Coding Context"
MODULE_LABEL = "nold-ai/specfact-code-review"
TOP_VIOLATIONS_HEADER = "## TOP VIOLATIONS (auto-updated by specfact code review rules update)"
TOP_VIOLATIONS_MARKER = "<!-- auto-managed: do not edit manually -->"
DEFAULT_DESCRIPTION = "House rules for AI coding sessions derived from review findings"
DEFAULT_DO_RULES = (
    "- Ask whether tests should be included before repo-wide review; "
    "default to excluding tests unless test changes are the target",
    "- Keep functions under 120 LOC and cyclomatic complexity <= 12",
    "- Add @require/@ensure (icontract) + @beartype to all new public APIs",
    "- Run hatch run contract-test-contracts before any commit",
    "- Guard all chained attribute access: a.b.c needs null-check or early return",
    "- Return typed values from all public methods",
    "- Write the test file BEFORE the feature file (TDD-first)",
    "- Use get_logger(__name__) from common.logger_setup, never print()",
)
DEFAULT_DONT_RULES = (
    "- Don't enable known noisy findings unless you explicitly want strict/full review output",
    "- Don't mix read + write in the same method; split responsibilities",
    "- Don't use bare except: or except Exception: pass",
    "- Don't add # noqa / # type: ignore without inline justification",
    "- Don't call repository.* and http_client.* in the same function",
    "- Don't import at module level if it triggers network calls",
    "- Don't hardcode secrets; use env vars via pydantic.BaseSettings",
    "- Don't create functions > 120 lines",
)


class SupportedIde(StrEnum):
    """IDE targets with canonical install locations for this skill."""

    CLAUDE = "claude"
    CODEX = "codex"
    CURSOR = "cursor"
    VIBE = "vibe"


IDE_SKILL_PATHS: dict[SupportedIde, Path] = {
    SupportedIde.CLAUDE: Path(".claude/skills/specfact-code-review/SKILL.md"),
    SupportedIde.CODEX: Path(".codex/skills/specfact-code-review/SKILL.md"),
    SupportedIde.VIBE: Path(".vibe/skills/specfact-code-review/SKILL.md"),
}


@beartype
@ensure(lambda result: result is None or isinstance(result, str))
def load_bundled_skill_content() -> str | None:
    """Load the bundled SKILL.md from package resources, or None if not found."""
    try:
        pkg = files("specfact_code_review")
        for part in _BUNDLED_SKILL_PATH:
            pkg = pkg / part
        return pkg.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, AttributeError):
        return None


@beartype
@require(lambda cwd: cwd.exists(), "cwd must exist")
@ensure(lambda result: isinstance(result, list))
def sync_skill_to_ide(
    content: str,
    cwd: Path,
    *,
    ide: SupportedIde | None = None,
) -> list[Path]:
    """Write the selected IDE target, or refresh already-installed canonical IDE targets."""
    written: list[Path] = []
    for path in _resolve_sync_targets(cwd, ide=ide):
        full = cwd / path
        full.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_cursor_rule(content) if path == CURSOR_RULES_PATH else content
        full.write_text(rendered, encoding="utf-8")
        written.append(full)
    return written


@beartype
@require(lambda content: bool(content.strip()), "content must not be empty")
@ensure(lambda result: bool(result.strip()))
def render_cursor_rule(content: str) -> str:
    """Render SKILL.md content as a Cursor auto-attached rule."""
    body = content
    description = DEFAULT_DESCRIPTION
    if content.startswith("---\n"):
        _, _, remainder = content.partition("\n---\n")
        if remainder:
            body = remainder.lstrip("\n")
            match = re.search(r"^description:\s*(?P<description>.+)$", content, flags=re.MULTILINE)
            if match:
                description = match.group("description").strip()
    lines = [
        "---",
        f"description: {description}",
        "alwaysApply: true",
        "---",
        "",
        body.rstrip("\n"),
    ]
    return "\n".join(lines) + "\n"


@beartype
@ensure(
    lambda result: len(result.splitlines()) <= MAX_SKILL_LINES,
    f"house-rules skill must stay within {MAX_SKILL_LINES} lines",
)
def default_skill_content(*, updated_on: date | None = None) -> str:
    """Return the default house-rules skill content."""
    stamp = (updated_on or date.today()).isoformat()
    lines = [
        "---",
        "name: specfact-code-review",
        f"description: {DEFAULT_DESCRIPTION}",
        "allowed-tools: []",
        "---",
        "",
        f"{TITLE_PREFIX} (v1)",
        "",
        f"Updated: {stamp} | Module: {MODULE_LABEL}",
        "",
        "## DO",
        *DEFAULT_DO_RULES,
        "",
        "## DON'T",
        *DEFAULT_DONT_RULES,
        "",
        TOP_VIOLATIONS_HEADER,
        TOP_VIOLATIONS_MARKER,
    ]
    return "\n".join(lines) + "\n"


@beartype
@require(lambda skill_path: skill_path.exists(), "skill_path must exist before update")
@require(lambda skill_path: skill_path.is_file(), "skill_path must point to a file")
def update_house_rules(
    skill_path: Path,
    runs: Sequence[LedgerRun],
    *,
    updated_on: date | None = None,
) -> str:
    """Update the skill file from recent ledger runs and return the new content."""
    content = skill_path.read_text(encoding="utf-8")
    updated = _render_updated_skill(content, runs=runs, updated_on=updated_on)
    skill_path.write_text(updated, encoding="utf-8")
    return updated


def _resolve_sync_targets(cwd: Path, *, ide: SupportedIde | None) -> list[Path]:
    if ide is not None:
        return [_target_path_for_ide(ide)]

    targets: list[Path] = []
    if (cwd / CURSOR_RULES_PATH).exists():
        targets.append(CURSOR_RULES_PATH)
    for path in IDE_SKILL_PATHS.values():
        if (cwd / path).exists():
            targets.append(path)
    return targets


def _target_path_for_ide(ide: SupportedIde) -> Path:
    if ide is SupportedIde.CURSOR:
        return CURSOR_RULES_PATH
    return IDE_SKILL_PATHS[ide]


def _ranked_rule_counts(runs: Sequence[LedgerRun], existing_rules: Sequence[str]) -> list[tuple[str, int]]:
    recent_runs = sorted(runs, key=lambda run: run.created_at)[-20:]
    recent_ten_counts = _count_rules(recent_runs[-10:])
    rule_counts = _count_rules(recent_runs)
    candidate_counts: dict[str, int] = {rule: count for rule, count in rule_counts.items() if count >= 3}
    for rule in existing_rules:
        if recent_ten_counts.get(rule, 0) > 0:
            candidate_counts.setdefault(rule, rule_counts.get(rule, 0))
    return sorted(candidate_counts.items(), key=lambda item: (-item[1], item[0]))


@beartype
@require(lambda content: TOP_VIOLATIONS_HEADER in content, "content must contain the TOP VIOLATIONS section")
@require(lambda content: TOP_VIOLATIONS_MARKER in content, "content must contain the auto-managed marker")
@ensure(
    lambda result: len(result.splitlines()) <= MAX_SKILL_LINES,
    f"house-rules skill must stay within {MAX_SKILL_LINES} lines",
)
def _render_updated_skill(content: str, *, runs: Sequence[LedgerRun], updated_on: date | None = None) -> str:
    lines = content.rstrip("\n").splitlines()
    title_index = _find_index(lines, lambda line: line.startswith(TITLE_PREFIX))
    updated_index = _find_index(lines, lambda line: line.startswith("Updated: "))
    top_header_index = _find_index(lines, lambda line: line == TOP_VIOLATIONS_HEADER)
    marker_index = top_header_index + 1

    if marker_index >= len(lines) or lines[marker_index] != TOP_VIOLATIONS_MARKER:
        msg = "Skill file is missing the auto-managed TOP VIOLATIONS marker."
        raise ValueError(msg)

    next_version = _next_version(lines[title_index])
    stamp = (updated_on or date.today()).isoformat()
    current_lines = list(lines)
    current_lines[title_index] = f"{TITLE_PREFIX} (v{next_version})"
    current_lines[updated_index] = f"Updated: {stamp} | Module: {MODULE_LABEL}"
    existing_rules = _parse_existing_rules(current_lines[marker_index + 1 :])
    ranked_rules = _ranked_rule_counts(runs, existing_rules)
    preserved_lines = current_lines[: marker_index + 1]
    rendered_lines = _render_with_budget(preserved_lines, ranked_rules)
    return "\n".join(rendered_lines) + "\n"


def _find_index(lines: list[str], predicate: Callable[[str], bool]) -> int:
    for index, line in enumerate(lines):
        if predicate(line):
            return index
    msg = "Skill file is missing a required section."
    raise ValueError(msg)


def _next_version(title_line: str) -> int:
    match = re.search(r"\(v(?P<version>\d+)\)", title_line)
    current = int(match.group("version")) if match else 1
    return current + 1


def _count_rules(runs: Sequence[LedgerRun]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for run in runs:
        for finding in run.findings_json:
            rule = finding.get("rule")
            if isinstance(rule, str) and rule.strip():
                counts[rule] += 1
    return counts


def _parse_existing_rules(lines: Sequence[str]) -> list[str]:
    rules: list[str] = []
    for line in lines:
        if not line.startswith("- "):
            continue
        rule = line[2:].split(" ", maxsplit=1)[0]
        if rule:
            rules.append(rule)
    return rules


def _render_with_budget(prefix_lines: list[str], ranked_rules: list[tuple[str, int]]) -> list[str]:
    kept_rules = list(ranked_rules)
    rendered = _materialize_lines(prefix_lines, kept_rules)
    while len(rendered) > MAX_SKILL_LINES and kept_rules:
        kept_rules.pop()
        rendered = _materialize_lines(prefix_lines, kept_rules)
    return rendered


def _materialize_lines(prefix_lines: list[str], ranked_rules: Sequence[tuple[str, int]]) -> list[str]:
    rule_lines = [f"- {rule} ({count} hits in last 20 runs)" for rule, count in ranked_rules]
    return [*prefix_lines, *rule_lines]


__all__ = [
    "CURSOR_RULES_PATH",
    "IDE_SKILL_PATHS",
    "MAX_SKILL_LINES",
    "SKILL_PATH",
    "SupportedIde",
    "default_skill_content",
    "load_bundled_skill_content",
    "render_cursor_rule",
    "sync_skill_to_ide",
    "update_house_rules",
]
