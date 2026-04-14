#!/usr/bin/env python3
"""Validate docs/agent-rules/*.md frontmatter applies_when against canonical task signals."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from beartype import beartype
from icontract import ensure


CANONICAL_TASK_SIGNALS: frozenset[str] = frozenset(
    {
        "session-bootstrap",
        "implementation",
        "openspec-change-selection",
        "branch-management",
        "github-public-work",
        "change-readiness",
        "finalization",
        "release",
        "documentation-update",
        "repository-orientation",
        "command-lookup",
        "detailed-reference",
        "verification",
    }
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)


@beartype
def _parse_frontmatter(text: str) -> dict[str, object] | str:
    """Return a frontmatter mapping, or a human-readable error message when parsing fails."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return "missing or invalid opening YAML frontmatter block (expected --- at file start)"
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return f"YAML parse error in frontmatter: {exc}"
    if not isinstance(loaded, dict):
        return "frontmatter must parse to a mapping (YAML dict), not a list or scalar"
    return loaded


@beartype
def _iter_signal_errors(rules_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(rules_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path.name}: failed to read file: {exc}")
            continue
        parsed = _parse_frontmatter(text)
        if isinstance(parsed, str):
            errors.append(f"{path.name}: {parsed}")
            continue
        data = parsed
        raw = data.get("applies_when")
        if raw is None:
            continue
        if isinstance(raw, str):
            signals = [raw]
        elif isinstance(raw, list):
            invalid = [item for item in raw if item is not None and not isinstance(item, str)]
            if invalid:
                bad_types = sorted({type(item).__name__ for item in invalid})
                errors.append(f"{path.name}: applies_when list entries must be str or null; got types: {bad_types}")
                continue
            signals = [item for item in raw if isinstance(item, str)]
        else:
            errors.append(f"{path.name}: applies_when must be a list or string")
            continue
        errors.extend(_validate_signals(path.name, signals))
    return errors


@beartype
def _validate_signals(path_name: str, signals: list[str]) -> list[str]:
    errors: list[str] = []
    for signal in signals:
        if signal not in CANONICAL_TASK_SIGNALS:
            errors.append(
                f"{path_name}: unknown applies_when value {signal!r} "
                f"(not in canonical set; update INDEX.md or fix frontmatter)"
            )
    return errors


@beartype
def _report_errors(errors: list[str]) -> int:
    if not errors:
        return 0
    sys.stderr.write(
        "validate_agent_rule_applies_when: agent rule doc validation failed "
        "(frontmatter and applies_when; see docs/agent-rules/INDEX.md — Task signal definitions):\n"
    )
    for line in errors:
        sys.stderr.write(f"  {line}\n")
    return 1


@beartype
@ensure(lambda result: result >= 0, "exit code must be non-negative")
def main() -> int:
    root = Path(__file__).resolve().parents[1]
    rules_dir = root / "docs" / "agent-rules"
    if not rules_dir.is_dir():
        sys.stderr.write("validate_agent_rule_applies_when: docs/agent-rules not found\n")
        return 2

    return _report_errors(_iter_signal_errors(rules_dir))


if __name__ == "__main__":
    sys.exit(main())
