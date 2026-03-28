"""Format and extract What Changes sections (cyclomatic complexity reduction)."""

from __future__ import annotations

import re
from typing import Any


_NEW_KW = ["new", "add", "introduce", "create", "implement", "support"]
_EXTEND_KW = ["extend", "enhance", "improve", "expand", "additional"]
_MODIFY_KW = ["modify", "update", "change", "refactor", "fix", "correct"]
_END_SECTION_KEYWORDS = [
    "acceptance criteria",
    "dependencies",
    "related issues",
    "related prs",
    "related issues/prs",
    "additional context",
    "testing",
    "documentation",
    "security",
    "quality",
    "non-functional",
    "three-phase",
    "known limitations",
    "security model",
]


def _fwc_early_return(description: str) -> str | None:
    if not description or not description.strip():
        return "No description provided."
    if re.search(
        r"^-\s*\*\*(NEW|EXTEND|FIX|ADD|MODIFY|UPDATE|REMOVE|REFACTOR)\*\*:",
        description,
        re.MULTILINE | re.IGNORECASE,
    ):
        return description.strip()
    return None


def _fwc_change_type_from_title_keywords(section_lower: str) -> str:
    if any(keyword in section_lower for keyword in _NEW_KW):
        return "NEW"
    if any(keyword in section_lower for keyword in _EXTEND_KW):
        return "EXTEND"
    if any(keyword in section_lower for keyword in _MODIFY_KW):
        return "MODIFY"
    return "MODIFY"


def _fwc_subsection_change_type(section_lower: str, section_title: str, lookahead: str) -> str:
    change_type = _fwc_change_type_from_title_keywords(section_lower)
    if "new" in section_lower or section_title.startswith("New "):
        change_type = "NEW"
    if (
        any(k in lookahead for k in ["new command", "new feature", "add ", "introduce", "create"])
        and "extend" not in lookahead
        and "modify" not in lookahead
    ):
        change_type = "NEW"
    return change_type


def _fwc_is_subsection_boundary(next_stripped: str) -> bool:
    return (
        next_stripped.startswith("- ###")
        or (next_stripped.startswith("###") and not next_stripped.startswith("####"))
        or (next_stripped.startswith("##") and not next_stripped.startswith("###"))
    )


def _fwc_collect_subsection_content(lines: list[str], i: int) -> tuple[list[str], int]:
    subsection_content: list[str] = []
    while i < len(lines):
        next_line = lines[i]
        next_stripped = next_line.strip()
        if _fwc_is_subsection_boundary(next_stripped):
            break
        if not subsection_content and not next_stripped:
            i += 1
            continue
        if next_stripped:
            content = next_stripped[2:].strip() if next_stripped.startswith("- ") else next_stripped
            if content:
                if content.startswith(("```", "**", "*")):
                    subsection_content.append(f"  {content}")
                else:
                    subsection_content.append(f"  - {content}")
        else:
            subsection_content.append("")
        i += 1
    return subsection_content, i


def _fwc_format_subsection_block(lines: list[str], i: int, formatted_lines: list[str]) -> int:
    line = lines[i]
    stripped = line.strip()
    section_title = stripped[5:].strip() if stripped.startswith("- ###") else stripped[3:].strip()
    section_lower = section_title.lower()
    lookahead = "\n".join(lines[i + 1 : min(i + 5, len(lines))]).lower()
    change_type = _fwc_subsection_change_type(section_lower, section_title, lookahead)
    formatted_lines.append(f"- **{change_type}**: {section_title}")
    i += 1
    subsection_content, i = _fwc_collect_subsection_content(lines, i)
    if subsection_content:
        formatted_lines.extend(subsection_content)
        formatted_lines.append("")
    return i


def _fwc_format_bullet_line(stripped: str, line: str, formatted_lines: list[str]) -> None:
    if any(marker in stripped for marker in ["**NEW**", "**EXTEND**", "**MODIFY**", "**FIX**"]):
        formatted_lines.append(line)
        return
    line_lower = stripped.lower()
    prefix = stripped[2:].strip() if stripped.startswith("- ") else stripped
    if any(keyword in line_lower for keyword in _NEW_KW):
        formatted_lines.append(f"- **NEW**: {prefix}")
    elif any(keyword in line_lower for keyword in _EXTEND_KW):
        formatted_lines.append(f"- **EXTEND**: {prefix}")
    elif any(keyword in line_lower for keyword in _MODIFY_KW):
        formatted_lines.append(f"- **MODIFY**: {prefix}")
    else:
        formatted_lines.append(line)


def _fwc_format_plain_line(stripped: str, formatted_lines: list[str]) -> None:
    line_lower = stripped.lower()
    if re.search(r"\bnew\s+(command|feature|capability|functionality|system|module|component)", line_lower) or any(
        keyword in line_lower for keyword in _NEW_KW
    ):
        formatted_lines.append(f"- **NEW**: {stripped}")
    elif any(keyword in line_lower for keyword in _EXTEND_KW):
        formatted_lines.append(f"- **EXTEND**: {stripped}")
    elif any(keyword in line_lower for keyword in _MODIFY_KW):
        formatted_lines.append(f"- **MODIFY**: {stripped}")
    else:
        formatted_lines.append(f"- {stripped}")


def _fwc_ensure_markers(result: str) -> str:
    if "**NEW**" in result or "**EXTEND**" in result or "**MODIFY**" in result:
        return result
    lines_list = result.split("\n")
    for idx, line in enumerate(lines_list):
        if line.strip() and not line.strip().startswith("#"):
            line_lower = line.lower()
            rest = line.strip().lstrip("- ")
            if any(keyword in line_lower for keyword in ["new", "add", "introduce", "create"]):
                lines_list[idx] = f"- **NEW**: {rest}"
            elif any(keyword in line_lower for keyword in ["extend", "enhance", "improve"]):
                lines_list[idx] = f"- **EXTEND**: {rest}"
            else:
                lines_list[idx] = f"- **MODIFY**: {rest}"
            break
    return "\n".join(lines_list)


def run_format_what_changes_section(bridge: Any, description: str) -> str:
    _ = bridge
    early = _fwc_early_return(description)
    if early is not None:
        return early
    lines = description.split("\n")
    formatted_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("- ###") or (stripped.startswith("###") and not stripped.startswith("####")):
            i = _fwc_format_subsection_block(lines, i, formatted_lines)
            continue
        if stripped.startswith(("- [ ]", "- [x]", "-")):
            _fwc_format_bullet_line(stripped, line, formatted_lines)
        elif stripped:
            _fwc_format_plain_line(stripped, formatted_lines)
        else:
            formatted_lines.append("")
        i += 1
    return _fwc_ensure_markers("\n".join(formatted_lines))


def _ewcc_section_title_lower(stripped: str) -> str:
    return re.sub(r"^-\s*#+\s*|^#+\s*", "", stripped).strip().lower()


def _ewcc_should_stop_at_section(stripped: str, section_title: str) -> bool:
    return any(keyword in section_title for keyword in _END_SECTION_KEYWORDS) or (
        stripped.startswith(("##", "- ##"))
        and not stripped.startswith(("###", "- ###"))
        and section_title not in ["what changes", "why"]
    )


def run_extract_what_changes_content(bridge: Any, description: str) -> str:
    _ = bridge
    if not description or not description.strip():
        return "No description provided."
    lines = description.split("\n")
    what_changes_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##") or (stripped.startswith("-") and "##" in stripped):
            section_title = _ewcc_section_title_lower(stripped)
            if _ewcc_should_stop_at_section(stripped, section_title):
                break
        what_changes_lines.append(line)
    result = "\n".join(what_changes_lines).strip()
    if not result or len(result) < 20:
        return description
    return result
