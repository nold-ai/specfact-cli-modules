"""House-rules skill template and update algorithm."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.ledger.client import LedgerRun


MAX_SKILL_LINES = 35
SKILL_PATH = Path("skills/specfact-code-review/SKILL.md")
MIRROR_PATH = Path(".cursor/rules/house_rules.mdc")
TITLE_PREFIX = "# House Rules - AI Coding Context"
MODULE_LABEL = "nold-ai/specfact-code-review"
TOP_VIOLATIONS_HEADER = "## TOP VIOLATIONS (auto-updated by specfact code review rules update)"
TOP_VIOLATIONS_MARKER = "<!-- auto-managed: do not edit manually -->"
DEFAULT_DO_RULES = (
    "- Keep functions under 120 LOC and cyclomatic complexity <= 12",
    "- Add @require/@ensure (icontract) + @beartype to all new public APIs",
    "- Run hatch run contract-test-contracts before any commit",
    "- Guard all chained attribute access: a.b.c needs null-check or early return",
    "- Return typed values from all public methods",
    "- Write the test file BEFORE the feature file (TDD-first)",
    "- Use get_logger(__name__) from common.logger_setup, never print()",
)
DEFAULT_DONT_RULES = (
    "- Don't mix read + write in the same method; split responsibilities",
    "- Don't use bare except: or except Exception: pass",
    "- Don't add # noqa / # type: ignore without inline justification",
    "- Don't call repository.* and http_client.* in the same function",
    "- Don't import at module level if it triggers network calls",
    "- Don't hardcode secrets; use env vars via pydantic.BaseSettings",
    "- Don't create functions > 120 lines",
)


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
        "description: House rules for AI coding sessions derived from review findings",
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
def update_house_rules(
    skill_path: Path,
    runs: Sequence[LedgerRun],
    *,
    updated_on: date | None = None,
    mirror_path: Path | None = None,
) -> str:
    """Update the skill file from recent ledger runs and return the new content."""
    content = skill_path.read_text(encoding="utf-8")
    updated = _render_updated_skill(content, runs=runs, updated_on=updated_on)
    skill_path.write_text(updated, encoding="utf-8")
    if mirror_path is not None:
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        mirror_path.write_text(updated, encoding="utf-8")
    return updated


@beartype
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

    recent_runs = sorted(runs, key=lambda run: run.created_at)[-20:]
    recent_ten_runs = recent_runs[-10:]
    rule_counts = _count_rules(recent_runs)
    recent_ten_counts = _count_rules(recent_ten_runs)

    existing_rules = _parse_existing_rules(current_lines[marker_index + 1 :])
    candidate_counts: dict[str, int] = {rule: count for rule, count in rule_counts.items() if count >= 3}
    for rule in existing_rules:
        if recent_ten_counts.get(rule, 0) > 0:
            candidate_counts.setdefault(rule, rule_counts.get(rule, 0))

    ranked_rules = sorted(candidate_counts.items(), key=lambda item: (-item[1], item[0]))
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
    "MAX_SKILL_LINES",
    "MIRROR_PATH",
    "SKILL_PATH",
    "default_skill_content",
    "update_house_rules",
]
