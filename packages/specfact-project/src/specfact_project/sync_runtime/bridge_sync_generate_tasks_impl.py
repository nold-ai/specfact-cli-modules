"""Generate tasks.md from proposal (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import re
from typing import Any


GTFP_MARKER_PATTERN = re.compile(
    r"^-\s*\*\*(NEW|EXTEND|FIX|ADD|MODIFY|UPDATE|REMOVE|REFACTOR)\*\*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)

_SECTION_MAPPING = {
    "testing": 2,
    "documentation": 3,
    "security": 4,
    "security & quality": 4,
    "code quality": 5,
}

_SECTION_NAMES = {
    1: "Implementation",
    2: "Testing",
    3: "Documentation",
    4: "Security & Quality",
    5: "Code Quality",
}


def _gtfp_append_code_block_line(current: dict[str, Any], stripped: str) -> None:
    if not stripped or stripped.startswith("#"):
        return
    if stripped.startswith("specfact "):
        current["tasks"].append(f"Support `{stripped}` command")
    else:
        current["tasks"].append(stripped)


def _gtfp_append_plain_task_line(current: dict[str, Any], stripped: str) -> None:
    content = stripped[2:].strip() if stripped.startswith("- ") else stripped
    content = re.sub(r"^\d+\.\s*", "", content).strip()
    if content.lower() in {"**commands:**", "commands:", "commands"}:
        return
    if content:
        current["tasks"].append(content)


def gtfp_extract_section_tasks(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_code_block = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        marker_match = GTFP_MARKER_PATTERN.match(stripped)
        if marker_match:
            if current:
                sections.append(current)
            current = {"title": marker_match.group(2).strip(), "tasks": []}
            in_code_block = False
            continue
        if current is None:
            continue
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            _gtfp_append_code_block_line(current, stripped)
            continue
        if not stripped:
            continue
        _gtfp_append_plain_task_line(current, stripped)
    if current:
        sections.append(current)
    return sections


def _ac_switch_main_section(
    new_section_num: int,
    state: dict[str, Any],
    lines: list[str],
) -> None:
    state["section_num"] = new_section_num
    state["subsection_num"] = 1
    state["task_num"] = 1
    state["current_section_name"] = _SECTION_NAMES.get(new_section_num, "Implementation")
    if not state["first_subsection"]:
        lines.append("")
    lines.append(f"## {new_section_num}. {state['current_section_name']}")
    lines.append("")
    state["first_subsection"] = True


def _ac_on_subsection_line(stripped: str, state: dict[str, Any], lines: list[str]) -> None:
    subsection_title = stripped[5:].strip() if stripped.startswith("- ###") else stripped[3:].strip()
    subsection_title_clean = re.sub(r"\(.*?\)", "", subsection_title).strip()
    subsection_title_clean = re.sub(r"^#+\s*", "", subsection_title_clean).strip()
    subsection_title_clean = re.sub(r"^\d+\.\s*", "", subsection_title_clean).strip()
    subsection_lower = subsection_title_clean.lower()
    new_section_num = _SECTION_MAPPING.get(subsection_lower)
    if new_section_num and new_section_num != state["section_num"]:
        _ac_switch_main_section(new_section_num, state, lines)
    if state["current_subsection"] is not None and not state["first_subsection"]:
        lines.append("")
        state["subsection_num"] += 1
        state["task_num"] = 1
    state["current_subsection"] = subsection_title_clean
    lines.append(f"### {state['section_num']}.{state['subsection_num']} {state['current_subsection']}")
    lines.append("")
    state["task_num"] = 1
    state["first_subsection"] = False


def _ac_on_task_line(stripped: str, state: dict[str, Any], lines: list[str]) -> bool:
    task_text = re.sub(r"^[-*]\s*\[[ x]\]\s*", "", stripped).strip()
    if not task_text:
        return False
    if state["current_subsection"] is None:
        state["current_subsection"] = "Tasks"
        lines.append(f"### {state['section_num']}.{state['subsection_num']} {state['current_subsection']}")
        lines.append("")
        state["task_num"] = 1
        state["first_subsection"] = False
    lines.append(f"- [ ] {state['section_num']}.{state['subsection_num']}.{state['task_num']} {task_text}")
    state["task_num"] += 1
    return True


def gtfp_process_acceptance_criteria(criteria_content: str, lines: list[str]) -> bool:
    state: dict[str, Any] = {
        "section_num": 1,
        "subsection_num": 1,
        "task_num": 1,
        "current_subsection": None,
        "first_subsection": True,
        "current_section_name": "Implementation",
    }
    lines.append("## 1. Implementation")
    lines.append("")
    tasks_found = False
    for line in criteria_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ###") or (stripped.startswith("###") and not stripped.startswith("####")):
            _ac_on_subsection_line(stripped, state, lines)
        elif stripped.startswith(("- [ ]", "- [x]", "[ ]", "[x]")):
            tasks_found = _ac_on_task_line(stripped, state, lines) or tasks_found
    return tasks_found


def gtfp_collect_checkbox_tasks(description: str) -> list[str]:
    out: list[str] = []
    for line in description.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("- [ ]", "- [x]", "[ ]", "[x]")):
            task_text = re.sub(r"^[-*]\s*\[[ x]\]\s*", "", stripped).strip()
            if task_text:
                out.append(task_text)
    return out


def gtfp_append_simple_checkbox_section(lines: list[str], task_items: list[str]) -> None:
    lines.append("## 1. Implementation")
    lines.append("")
    for idx, task in enumerate(task_items, start=1):
        lines.append(f"- [ ] 1.{idx} {task}")
    lines.append("")


def gtfp_build_from_marker_sections(lines: list[str], sections: list[dict[str, Any]]) -> None:
    lines.append("## 1. Implementation")
    lines.append("")
    subsection_num = 1
    for section in sections:
        section_title = section.get("title", "").strip()
        if not section_title:
            continue
        section_title_clean = re.sub(r"\([^)]*\)", "", section_title).strip()
        if not section_title_clean:
            continue
        lines.append(f"### 1.{subsection_num} {section_title_clean}")
        lines.append("")
        task_num = 1
        tasks = section.get("tasks") or [f"Implement {section_title_clean.lower()}"]
        for task in tasks:
            task_text = str(task).strip()
            if not task_text:
                continue
            lines.append(f"- [ ] 1.{subsection_num}.{task_num} {task_text}")
            task_num += 1
        lines.append("")
        subsection_num += 1


def gtfp_placeholder_tasks(lines: list[str]) -> None:
    lines.append("## 1. Implementation")
    lines.append("")
    lines.append("- [ ] 1.1 Implement changes as described in proposal")
    lines.append("")
    lines.append("## 2. Testing")
    lines.append("")
    lines.append("- [ ] 2.1 Add unit tests")
    lines.append("- [ ] 2.2 Add integration tests")
    lines.append("")
    lines.append("## 3. Code Quality")
    lines.append("")
    lines.append("- [ ] 3.1 Run linting: `hatch run format`")
    lines.append("- [ ] 3.2 Run type checking: `hatch run type-check`")


def _gtfp_try_acceptance_criteria(description: str, lines: list[str]) -> bool:
    acceptance_match = re.search(
        r"(?i)(?:-\s*)?##\s*Acceptance\s+Criteria\s*\n(.*?)(?=\n\s*(?:-\s*)?##|\Z)",
        description,
        re.DOTALL,
    )
    if not acceptance_match:
        return False
    return gtfp_process_acceptance_criteria(acceptance_match.group(1), lines)


def _gtfp_try_checkbox_scan(description: str, lines: list[str]) -> bool:
    if "- [ ]" not in description and "- [x]" not in description and "[ ]" not in description:
        return False
    task_items = gtfp_collect_checkbox_tasks(description)
    if not task_items:
        return False
    gtfp_append_simple_checkbox_section(lines, task_items)
    return True


def _gtfp_try_what_changes_markers(bridge: Any, description: str, lines: list[str]) -> bool:
    formatted_description = description
    if description and not GTFP_MARKER_PATTERN.search(description):
        formatted_description = bridge._format_what_changes_section(bridge._extract_what_changes_content(description))
    if not formatted_description or not GTFP_MARKER_PATTERN.search(formatted_description):
        return False
    sections = gtfp_extract_section_tasks(formatted_description)
    if not sections:
        return False
    gtfp_build_from_marker_sections(lines, sections)
    return True


def run_generate_tasks_from_proposal(bridge: Any, proposal: Any) -> str:
    lines = ["# Tasks: " + bridge._format_proposal_title(proposal.title), ""]
    description = proposal.description or ""
    tasks_found = _gtfp_try_acceptance_criteria(description, lines)
    if not tasks_found:
        tasks_found = _gtfp_try_checkbox_scan(description, lines)
    if not tasks_found:
        tasks_found = _gtfp_try_what_changes_markers(bridge, description, lines)
    if not tasks_found:
        gtfp_placeholder_tasks(lines)
    return "\n".join(lines)
