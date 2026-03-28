"""
Pure helpers for Spec-Kit markdown sections generated from SpecFact plan models.

Extracted from SpecKitConverter to keep per-function cyclomatic complexity low.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from specfact_cli.models.plan import Feature, PlanBundle, Story


GWT_PATTERN = r"Given\s+(.+?),\s*When\s+(.+?),\s*Then\s+(.+?)(?:$|,)"


def build_feature_branch(feature_num: int, feature_dir_name: str) -> str:
    return f"{feature_num:03d}-{feature_dir_name}"


def spec_header_lines(feature_branch: str, title: str, created: str | None = None) -> list[str]:
    created = created or datetime.now().strftime("%Y-%m-%d")
    return [
        "---",
        f"**Feature Branch**: `{feature_branch}`",
        f"**Created**: {created}",
        "**Status**: Draft",
        "---",
        "",
        f"# Feature Specification: {title}",
        "",
    ]


def story_priority_from_tags(tags: list[str] | None) -> str:
    priority = "P3"
    if tags:
        for tag in tags:
            if tag.startswith("P") and tag[1:].isdigit():
                priority = tag
                break
    return priority


def priority_rationale_from_story(story: Story, feature: Feature) -> str:
    priority_rationale = "Core functionality"
    if story.tags:
        for tag in story.tags:
            if tag.startswith(("priority:", "rationale:")):
                priority_rationale = tag.split(":", 1)[1].strip()
                break
    if (not priority_rationale or priority_rationale == "Core functionality") and feature.outcomes:
        priority_rationale = feature.outcomes[0] if len(feature.outcomes[0]) < 100 else "Core functionality"
    return priority_rationale


def invsest_lines() -> list[str]:
    return [
        "**Independent**: YES",
        "**Negotiable**: YES",
        "**Valuable**: YES",
        "**Estimable**: YES",
        "**Small**: YES",
        "**Testable**: YES",
        "",
    ]


def _categorize_gwt(acc_lower: str, scenario_text: str, buckets: _ScenarioBuckets) -> None:
    if any(keyword in acc_lower for keyword in ["error", "exception", "fail", "invalid", "reject"]):
        buckets.exception.append(scenario_text)
    elif any(keyword in acc_lower for keyword in ["recover", "retry", "fallback", "retry"]):
        buckets.recovery.append(scenario_text)
    elif any(keyword in acc_lower for keyword in ["alternate", "alternative", "different", "optional"]):
        buckets.alternate.append(scenario_text)
    else:
        buckets.primary.append(scenario_text)


def _categorize_simple_synthetic(acc_lower: str, scenario_text: str, buckets: _ScenarioBuckets) -> None:
    if any(keyword in acc_lower for keyword in ["error", "exception", "fail", "invalid", "reject", "handle error"]):
        buckets.exception.append(scenario_text)
    elif any(keyword in acc_lower for keyword in ["recover", "retry", "fallback"]):
        buckets.recovery.append(scenario_text)
    elif any(keyword in acc_lower for keyword in ["alternate", "alternative", "different", "optional"]):
        buckets.alternate.append(scenario_text)
    else:
        buckets.primary.append(scenario_text)


def _categorize_plain(acc_lower: str, acc: str, buckets: _ScenarioBuckets) -> None:
    if any(keyword in acc_lower for keyword in ["error", "exception", "fail", "invalid"]):
        buckets.exception.append(acc)
    elif any(keyword in acc_lower for keyword in ["recover", "retry", "fallback"]):
        buckets.recovery.append(acc)
    elif any(keyword in acc_lower for keyword in ["alternate", "alternative", "different"]):
        buckets.alternate.append(acc)
    else:
        buckets.primary.append(acc)


class _ScenarioBuckets:
    __slots__ = ("alternate", "exception", "primary", "recovery")

    def __init__(self) -> None:
        self.primary: list[str] = []
        self.alternate: list[str] = []
        self.exception: list[str] = []
        self.recovery: list[str] = []


def _parse_gwt_parts(acc: str) -> tuple[str, str, str] | None:
    if "Given" not in acc or "When" not in acc or "Then" not in acc:
        return None
    match = re.search(GWT_PATTERN, acc, re.IGNORECASE | re.DOTALL)
    if match:
        given = match.group(1).strip()
        when = match.group(2).strip()
        then = match.group(3).strip()
    else:
        parts = acc.split(", ")
        given = parts[0].replace("Given ", "").strip() if len(parts) > 0 else ""
        when = parts[1].replace("When ", "").strip() if len(parts) > 1 else ""
        then = parts[2].replace("Then ", "").strip() if len(parts) > 2 else ""
    return given, when, then


def _append_gwt_acceptance(
    acc: str,
    acc_idx: int,
    lines: list[str],
    buckets: _ScenarioBuckets,
) -> None:
    parsed = _parse_gwt_parts(acc)
    if parsed is None:
        return
    given, when, then = parsed
    lines.append(f"{acc_idx}. **Given** {given}, **When** {when}, **Then** {then}")
    scenario_text = f"{given}, {when}, {then}"
    acc_lower = acc.lower()
    _categorize_gwt(acc_lower, scenario_text, buckets)


def _build_synthetic_from_simple(acc: str, acc_lower: str) -> tuple[str, str, str] | None:
    if not ("must" in acc_lower or "should" in acc_lower or "will" in acc_lower):
        return None
    if "verify" in acc_lower or "validate" in acc_lower:
        action = (
            acc.replace("Must verify", "")
            .replace("Must validate", "")
            .replace("Should verify", "")
            .replace("Should validate", "")
            .strip()
        )
        given = "user performs action"
        when = f"system {action}"
        then = f"{action} succeeds"
        return given, when, then
    if "handle" in acc_lower or "display" in acc_lower:
        action = (
            acc.replace("Must handle", "")
            .replace("Must display", "")
            .replace("Should handle", "")
            .replace("Should display", "")
            .strip()
        )
        given = "error condition occurs"
        when = "system processes error"
        then = f"system {action}"
        return given, when, then
    given = "user interacts with system"
    when = "action is performed"
    then = acc.replace("Must", "").replace("Should", "").replace("Will", "").strip()
    return given, when, then


def _append_simple_or_plain_acceptance(
    acc: str,
    acc_idx: int,
    lines: list[str],
    buckets: _ScenarioBuckets,
) -> None:
    acc_lower = acc.lower()
    synthetic = _build_synthetic_from_simple(acc, acc_lower)
    if synthetic is not None:
        given, when, then = synthetic
        lines.append(f"{acc_idx}. **Given** {given}, **When** {when}, **Then** {then}")
        scenario_text = f"{given}, {when}, {then}"
        _categorize_simple_synthetic(acc_lower, scenario_text, buckets)
        return
    lines.append(f"{acc_idx}. {acc}")
    _categorize_plain(acc_lower, acc, buckets)


def _append_primary_scenario_lines(lines: list[str], primary: list[str]) -> None:
    if primary:
        for scenario in primary:
            lines.append(f"- **Primary Scenario**: {scenario}")
    else:
        lines.append("- **Primary Scenario**: Standard user flow")


def _append_alternate_scenario_lines(lines: list[str], alternate: list[str]) -> None:
    if alternate:
        for scenario in alternate:
            lines.append(f"- **Alternate Scenario**: {scenario}")
    else:
        lines.append("- **Alternate Scenario**: Alternative user flow")


def _append_exception_scenario_lines(lines: list[str], exception: list[str]) -> None:
    if exception:
        for scenario in exception:
            lines.append(f"- **Exception Scenario**: {scenario}")
    else:
        lines.append("- **Exception Scenario**: Error handling")


def _append_recovery_scenario_lines(lines: list[str], recovery: list[str]) -> None:
    if recovery:
        for scenario in recovery:
            lines.append(f"- **Recovery Scenario**: {scenario}")
    else:
        lines.append("- **Recovery Scenario**: Recovery from errors")


def _append_scenarios_section(lines: list[str], buckets: _ScenarioBuckets) -> None:
    if not (buckets.primary or buckets.alternate or buckets.exception or buckets.recovery):
        return
    lines.append("**Scenarios:**")
    lines.append("")
    _append_primary_scenario_lines(lines, buckets.primary)
    _append_alternate_scenario_lines(lines, buckets.alternate)
    _append_exception_scenario_lines(lines, buckets.exception)
    _append_recovery_scenario_lines(lines, buckets.recovery)
    lines.append("")


def _user_stories_section(feature: Feature) -> list[str]:
    lines: list[str] = []
    if not feature.stories:
        return lines
    lines.append("## User Scenarios & Testing")
    lines.append("")

    for idx, story in enumerate(feature.stories, start=1):
        priority = story_priority_from_tags(story.tags)
        lines.append(f"### User Story {idx} - {story.title} (Priority: {priority})")
        lines.append(f"Users can {story.title}")
        lines.append("")
        rationale = priority_rationale_from_story(story, feature)
        lines.append(f"**Why this priority**: {rationale}")
        lines.append("")
        lines.extend(invsest_lines())
        lines.append("**Acceptance Criteria:**")
        lines.append("")

        buckets = _ScenarioBuckets()
        for acc_idx, acc in enumerate(story.acceptance, start=1):
            if "Given" in acc and "When" in acc and "Then" in acc:
                _append_gwt_acceptance(acc, acc_idx, lines, buckets)
            else:
                _append_simple_or_plain_acceptance(acc, acc_idx, lines, buckets)

        lines.append("")
        _append_scenarios_section(lines, buckets)
        lines.append("")

    return lines


def generate_spec_markdown(feature: Feature, feature_num: int, feature_dir_name: str) -> str:
    feature_branch = build_feature_branch(feature_num, feature_dir_name)
    lines = spec_header_lines(feature_branch, feature.title)
    lines.extend(_user_stories_section(feature))

    if feature.outcomes:
        lines.append("## Functional Requirements")
        lines.append("")
        for idx, outcome in enumerate(feature.outcomes, start=1):
            lines.append(f"**FR-{idx:03d}**: System MUST {outcome}")
        lines.append("")

    if feature.acceptance:
        lines.append("## Success Criteria")
        lines.append("")
        for idx, acc in enumerate(feature.acceptance, start=1):
            lines.append(f"**SC-{idx:03d}**: {acc}")
        lines.append("")

    if feature.constraints:
        lines.append("### Edge Cases")
        lines.append("")
        for constraint in feature.constraints:
            lines.append(f"- {constraint}")
        lines.append("")

    return "\n".join(lines)


def _default_stack() -> list[str]:
    return ["Python 3.11+", "Typer for CLI", "Pydantic for data validation"]


def _idea_constraint_hits(constraint: str, constraint_lower: str, stack: list[str], seen: set[str]) -> None:
    if "python" in constraint_lower and constraint not in seen:
        stack.append(constraint)
        seen.add(constraint)

    for fw in ["fastapi", "django", "flask", "typer", "tornado", "bottle"]:
        if fw in constraint_lower and constraint not in seen:
            stack.append(constraint)
            seen.add(constraint)
            break

    for db in ["postgres", "postgresql", "mysql", "sqlite", "redis", "mongodb", "cassandra"]:
        if db in constraint_lower and constraint not in seen:
            stack.append(constraint)
            seen.add(constraint)
            break


def _feature_constraint_hits(constraint: str, constraint_lower: str, stack: list[str], seen: set[str]) -> None:
    if constraint in seen:
        return

    for fw in ["fastapi", "django", "flask", "typer", "tornado", "bottle"]:
        if fw in constraint_lower:
            stack.append(constraint)
            seen.add(constraint)
            break

    for db in ["postgres", "postgresql", "mysql", "sqlite", "redis", "mongodb", "cassandra"]:
        if db in constraint_lower:
            stack.append(constraint)
            seen.add(constraint)
            break

    for test in ["pytest", "unittest", "nose", "tox"]:
        if test in constraint_lower:
            stack.append(constraint)
            seen.add(constraint)
            break

    for deploy in ["docker", "kubernetes", "aws", "gcp", "azure"]:
        if deploy in constraint_lower:
            stack.append(constraint)
            seen.add(constraint)
            break


def extract_technology_stack(feature: Feature, plan_bundle: PlanBundle) -> list[str]:
    stack: list[str] = []
    seen: set[str] = set()

    if plan_bundle.idea and plan_bundle.idea.constraints:
        for constraint in plan_bundle.idea.constraints:
            constraint_lower = constraint.lower()
            _idea_constraint_hits(constraint, constraint_lower, stack, seen)

    if feature.constraints:
        for constraint in feature.constraints:
            constraint_lower = constraint.lower()
            _feature_constraint_hits(constraint, constraint_lower, stack, seen)

    if not stack:
        stack = _default_stack()

    return stack


def _language_version_from_stack(technology_stack: list[str]) -> str:
    return next((s for s in technology_stack if "Python" in s), "Python 3.11+")


_FW_MARKERS = ("typer", "fastapi", "django", "flask", "pydantic", "sqlalchemy")


def _is_framework_dependency_line(s: str) -> bool:
    s_lower = s.lower()
    return any(fw in s_lower for fw in _FW_MARKERS)


def _format_dependency_line(dep: str) -> str:
    dep_lower = dep.lower()
    if "fastapi" in dep_lower:
        return "- `fastapi` - Web framework"
    if "django" in dep_lower:
        return "- `django` - Web framework"
    if "flask" in dep_lower:
        return "- `flask` - Web framework"
    if "typer" in dep_lower:
        return "- `typer` - CLI framework"
    if "pydantic" in dep_lower:
        return "- `pydantic` - Data validation"
    if "sqlalchemy" in dep_lower:
        return "- `sqlalchemy` - ORM"
    return f"- {dep}"


def _primary_dependencies_lines(technology_stack: list[str]) -> list[str]:
    lines: list[str] = [
        "**Primary Dependencies:**",
        "",
    ]
    dependencies = [s for s in technology_stack if _is_framework_dependency_line(s)]
    if dependencies:
        for dep in dependencies[:5]:
            lines.append(_format_dependency_line(dep))
    else:
        lines.append("- `typer` - CLI framework")
        lines.append("- `pydantic` - Data validation")
    lines.append("")
    return lines


def _technology_stack_lines(technology_stack: list[str]) -> list[str]:
    lines = [
        "**Technology Stack:**",
        "",
    ]
    for stack_item in technology_stack:
        lines.append(f"- {stack_item}")
    lines.append("")
    return lines


def _constraints_lines(feature: Feature) -> list[str]:
    lines = [
        "**Constraints:**",
        "",
    ]
    if feature.constraints:
        for constraint in feature.constraints:
            lines.append(f"- {constraint}")
    else:
        lines.append("- None specified")
    lines.append("")
    return lines


def _unknowns_lines() -> list[str]:
    return [
        "**Unknowns:**",
        "",
        "- None at this time",
        "",
    ]


def _fallback_constitution_lines(contracts_defined: bool) -> list[str]:
    lines = [
        "## Constitution Check",
        "",
        "**Article VII (Simplicity)**:",
        "- [ ] Evidence extraction pending",
        "",
        "**Article VIII (Anti-Abstraction)**:",
        "- [ ] Evidence extraction pending",
        "",
        "**Article IX (Integration-First)**:",
    ]
    if contracts_defined:
        lines.append("- [x] Contracts defined?")
        lines.append("- [ ] Contract tests written?")
    else:
        lines.append("- [ ] Contracts defined?")
        lines.append("- [ ] Contract tests written?")
    lines.extend(
        [
            "",
            "**Status**: PENDING",
            "",
        ]
    )
    return lines


def _contract_param_line(param: dict[str, Any]) -> str:
    param_type = param.get("type", "Any")
    required = "required" if param.get("required", True) else "optional"
    default = f" (default: {param.get('default')})" if param.get("default") is not None else ""
    return f"- `{param['name']}`: {param_type} ({required}){default}"


def _append_contract_block(lines: list[str], contracts: dict[str, Any]) -> None:
    if contracts.get("parameters"):
        lines.append("**Parameters:**")
        for param in contracts["parameters"]:
            lines.append(_contract_param_line(param))
        lines.append("")

    if contracts.get("return_type"):
        return_type = contracts["return_type"].get("type", "Any")
        lines.append(f"**Return Type**: `{return_type}`")
        lines.append("")

    if contracts.get("preconditions"):
        lines.append("**Preconditions:**")
        for precondition in contracts["preconditions"]:
            lines.append(f"- {precondition}")
        lines.append("")

    if contracts.get("postconditions"):
        lines.append("**Postconditions:**")
        for postcondition in contracts["postconditions"]:
            lines.append(f"- {postcondition}")
        lines.append("")

    if contracts.get("error_contracts"):
        lines.append("**Error Contracts:**")
        for error_contract in contracts["error_contracts"]:
            exc_type = error_contract.get("exception_type", "Exception")
            condition = error_contract.get("condition", "Error condition")
            lines.append(f"- `{exc_type}`: {condition}")
        lines.append("")


def _contract_definitions_section(feature: Feature) -> list[str]:
    lines: list[str] = []
    for story in feature.stories:
        if not story.contracts:
            continue
        lines.append(f"#### {story.title}")
        lines.append("")
        _append_contract_block(lines, story.contracts)
    lines.append("")
    return lines


def _phases_tail(feature_title: str) -> list[str]:
    return [
        "## Phase 0: Research",
        "",
        f"Research and technical decisions for {feature_title}.",
        "",
        "## Phase 1: Design",
        "",
        f"Design phase for {feature_title}.",
        "",
        "## Phase 2: Implementation",
        "",
        f"Implementation phase for {feature_title}.",
        "",
        "## Phase -1: Pre-Implementation Gates",
        "",
        "Pre-implementation gate checks:",
        "- [ ] Constitution check passed",
        "- [ ] Contracts defined",
        "- [ ] Technical context validated",
        "",
    ]


def generate_plan_markdown(
    feature: Feature,
    plan_bundle: PlanBundle,
    constitution_section: str | None,
    contracts_defined: bool,
) -> str:
    lines = [f"# Implementation Plan: {feature.title}", ""]
    lines.append("## Summary")
    lines.append(f"Implementation plan for {feature.title}.")
    lines.append("")

    lines.append("## Technical Context")
    lines.append("")

    technology_stack = extract_technology_stack(feature, plan_bundle)
    language_version = _language_version_from_stack(technology_stack)

    lines.append(f"**Language/Version**: {language_version}")
    lines.append("")

    lines.extend(_primary_dependencies_lines(technology_stack))
    lines.extend(_technology_stack_lines(technology_stack))
    lines.extend(_constraints_lines(feature))
    lines.extend(_unknowns_lines())

    if constitution_section is not None:
        lines.append(constitution_section)
    else:
        lines.extend(_fallback_constitution_lines(contracts_defined))

    if contracts_defined:
        lines.append("### Contract Definitions")
        lines.append("")
        lines.extend(_contract_definitions_section(feature))

    lines.extend(_phases_tail(feature.title))
    return "\n".join(lines)


def _is_setup_task(task_lower: str) -> bool:
    return any(keyword in task_lower for keyword in ["setup", "install", "configure", "create project", "initialize"])


def _is_foundational_task(task_lower: str) -> bool:
    return any(keyword in task_lower for keyword in ["implement", "create model", "set up database", "middleware"])


def collect_task_buckets(
    stories: list[Story],
    extract_story_number: Callable[[str], int],
) -> tuple[list[tuple[int, str, int]], list[tuple[int, str, int]], dict[int, list[tuple[int, str]]], int]:
    setup_tasks: list[tuple[int, str, int]] = []
    foundational_tasks: list[tuple[int, str, int]] = []
    story_tasks: dict[int, list[tuple[int, str]]] = {}
    task_counter = 1

    for story in stories:
        story_num = extract_story_number(story.key)

        if story.tasks:
            for task_desc in story.tasks:
                task_lower = task_desc.lower()
                if _is_setup_task(task_lower):
                    setup_tasks.append((task_counter, task_desc, story_num))
                    task_counter += 1
                elif _is_foundational_task(task_lower):
                    foundational_tasks.append((task_counter, task_desc, story_num))
                    task_counter += 1
                else:
                    story_tasks.setdefault(story_num, []).append((task_counter, task_desc))
                    task_counter += 1
        else:
            foundational_tasks.append((task_counter, f"Implement {story.title}", story_num))
            task_counter += 1

    return setup_tasks, foundational_tasks, story_tasks, task_counter


def _append_setup_and_foundational(
    lines: list[str],
    setup_tasks: list[tuple[int, str, int]],
    foundational_tasks: list[tuple[int, str, int]],
) -> None:
    if setup_tasks:
        lines.append("## Phase 1: Setup")
        lines.append("")
        for task_num, task_desc, story_num in setup_tasks:
            lines.append(f"- [ ] [T{task_num:03d}] [P] [US{story_num}] {task_desc}")
        lines.append("")

    if foundational_tasks:
        lines.append("## Phase 2: Foundational")
        lines.append("")
        for task_num, task_desc, story_num in foundational_tasks:
            lines.append(f"- [ ] [T{task_num:03d}] [P] [US{story_num}] {task_desc}")
        lines.append("")


def _append_story_phases(
    lines: list[str],
    stories: list[Story],
    story_tasks: dict[int, list[tuple[int, str]]],
    extract_story_number: Callable[[str], int],
) -> None:
    for story_idx, story in enumerate(stories, start=1):
        story_num = extract_story_number(story.key)
        phase_num = story_idx + 2
        story_task_list = story_tasks.get(story_num, [])

        if not story_task_list:
            continue

        priority = story_priority_from_tags(story.tags)
        lines.append(f"## Phase {phase_num}: User Story {story_idx} (Priority: {priority})")
        lines.append("")
        for task_num, task_desc in story_task_list:
            lines.append(f"- [ ] [T{task_num:03d}] [US{story_idx}] {task_desc}")
        lines.append("")


def generate_tasks_markdown(
    feature: Feature,
    extract_story_number: Callable[[str], int],
) -> str:
    lines = ["# Tasks", ""]

    setup_tasks, foundational_tasks, story_tasks, _ = collect_task_buckets(
        feature.stories,
        extract_story_number,
    )

    _append_setup_and_foundational(lines, setup_tasks, foundational_tasks)
    _append_story_phases(lines, feature.stories, story_tasks, extract_story_number)

    if not feature.stories:
        lines.append("## Phase 1: Setup")
        lines.append("")
        lines.append(f"- [ ] [T001] Implement {feature.title}")
        lines.append("")

    return "\n".join(lines)
