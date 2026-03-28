"""Conversion helpers between Spec-Kit features and OpenSpec changes."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require


@beartype
class SpecKitChangeProposalBridge:
    """Translate between Spec-Kit feature folders and OpenSpec change folders."""

    def __init__(self, scanner: Any) -> None:
        self._scanner = scanner

    @require(lambda feature_path: feature_path.exists(), "Feature path must exist")
    @require(lambda feature_path: feature_path.is_dir(), "Feature path must be a directory")
    @require(lambda change_name: len(change_name.strip()) > 0, "Change name must be non-empty")
    @ensure(lambda result: isinstance(result, Path), "Must return Path")
    @ensure(lambda result: result.exists(), "Change directory must exist")
    def convert_feature_to_change(self, feature_path: Path, change_name: str, output_dir: Path) -> Path:
        """Convert a Spec-Kit feature directory into an OpenSpec change."""
        spec_data, plan_data, tasks_data = self._load_feature_inputs(feature_path)
        capability = self._derive_capability_name(spec_data, change_name)
        change_dir = output_dir / change_name
        capability_dir = change_dir / "specs" / capability
        capability_dir.mkdir(parents=True, exist_ok=True)
        change_dir.mkdir(parents=True, exist_ok=True)

        (change_dir / "proposal.md").write_text(
            self._render_change_proposal(change_name, feature_path, capability, spec_data, plan_data),
            encoding="utf-8",
        )
        (change_dir / "design.md").write_text(
            self._render_change_design(change_name, spec_data, plan_data),
            encoding="utf-8",
        )
        (capability_dir / "spec.md").write_text(
            self._render_change_spec(capability, spec_data),
            encoding="utf-8",
        )
        (change_dir / "tasks.md").write_text(
            self._render_change_tasks(spec_data, tasks_data),
            encoding="utf-8",
        )
        return change_dir

    @require(lambda change_dir: change_dir.exists(), "Change directory must exist")
    @require(lambda change_dir: change_dir.is_dir(), "Change directory must be a directory")
    @ensure(lambda result: isinstance(result, Path), "Must return Path")
    @ensure(lambda result: result.exists(), "Feature directory must exist")
    def convert_change_to_feature(self, change_dir: Path, output_dir: Path) -> Path:
        """Convert an OpenSpec change folder into a Spec-Kit feature folder."""
        proposal, design, tasks, change_spec = self._load_change_inputs(change_dir)
        proposal_title = str(proposal["title"] or change_dir.name)
        proposal_rationale = str(proposal["rationale"] or "")
        feature_dir_name = str(proposal["feature_dir"] or f"001-{slugify(proposal_title)}")
        feature_dir = output_dir / feature_dir_name
        feature_dir.mkdir(parents=True, exist_ok=True)

        (feature_dir / "spec.md").write_text(
            self._render_speckit_spec(proposal_title, feature_dir_name, proposal_rationale, change_spec),
            encoding="utf-8",
        )
        (feature_dir / "plan.md").write_text(
            self._render_speckit_plan(proposal_title, design),
            encoding="utf-8",
        )
        (feature_dir / "tasks.md").write_text(
            self._render_speckit_tasks(tasks),
            encoding="utf-8",
        )
        return feature_dir

    @ensure(lambda result: isinstance(result, tuple), "Must return tuple")
    def _load_feature_inputs(
        self, feature_path: Path
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        """Load parsed Spec-Kit spec, plan, and tasks data."""
        spec_data = self._scanner.parse_spec_markdown(feature_path / "spec.md")
        if spec_data is None:
            msg = f"Spec-Kit feature is missing spec.md: {feature_path}"
            raise ValueError(msg)
        plan_data = self._read_optional_markdown(feature_path / "plan.md", self._scanner.parse_plan_markdown)
        tasks_data = self._read_optional_markdown(feature_path / "tasks.md", self._scanner.parse_tasks_markdown)
        return spec_data, plan_data, tasks_data

    @ensure(lambda result: isinstance(result, tuple), "Must return tuple")
    def _load_change_inputs(
        self, change_dir: Path
    ) -> tuple[dict[str, str | None], dict[str, list[str] | str], list[dict[str, Any]], dict[str, Any]]:
        """Load the OpenSpec artifacts needed for Spec-Kit export."""
        proposal_path = change_dir / "proposal.md"
        if not proposal_path.exists():
            msg = f"OpenSpec change is missing proposal.md: {change_dir}"
            raise ValueError(msg)

        spec_files = sorted((change_dir / "specs").glob("*/spec.md"))
        if not spec_files:
            msg = f"OpenSpec change is missing specs/*/spec.md: {change_dir}"
            raise ValueError(msg)

        proposal = self._parse_change_proposal(proposal_path)
        design = self._parse_change_design(change_dir / "design.md")
        tasks = self._parse_change_tasks(change_dir / "tasks.md")
        change_spec = self._parse_change_spec(spec_files[0])
        return proposal, design, tasks, change_spec

    @ensure(lambda result: result is None or isinstance(result, dict), "Must return optional dict")
    def _read_optional_markdown(self, path: Path, parser: Any) -> dict[str, Any] | None:
        """Read and annotate an optional Spec-Kit markdown artifact."""
        data = parser(path)
        if data is not None and path.exists():
            data["_raw_content"] = path.read_text(encoding="utf-8")
        return data

    @ensure(lambda result: isinstance(result, str) and len(result) > 0, "Capability must be non-empty")
    def _derive_capability_name(self, spec_data: dict[str, Any], change_name: str) -> str:
        """Derive a stable capability slug for the generated OpenSpec spec."""
        feature_title = str(spec_data.get("feature_title") or change_name)
        requirement_texts = [
            str(item.get("text", "")).strip()
            for item in spec_data.get("requirements", [])
            if isinstance(item, dict) and item.get("text")
        ]
        seed = requirement_texts[0] if requirement_texts else feature_title
        return slugify(seed)[:64] or slugify(change_name)

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_change_proposal(
        self,
        change_name: str,
        feature_path: Path,
        capability: str,
        spec_data: dict[str, Any],
        plan_data: dict[str, Any] | None,
    ) -> str:
        """Render the OpenSpec proposal.md file."""
        feature_title = str(spec_data.get("feature_title") or change_name)
        why_lines = self._proposal_why_lines(feature_title, spec_data, plan_data)
        requirement_lines = self._proposal_requirement_lines(feature_title, spec_data)
        lines = [
            f"# Change: {feature_title}",
            "",
            "## Why",
            "",
            *why_lines,
            "",
            "## What Changes",
            "",
            *requirement_lines,
            "",
            "## Capabilities",
            "",
            "### New Capabilities",
            "",
            f"- `{capability}`: Imported from Spec-Kit feature `{feature_path.name}`.",
            "",
            "## Impact",
            "",
            f"- Source feature: `{feature_path}`",
            "- Generated artifacts: `proposal.md`, `design.md`, `specs/`, `tasks.md`",
            "",
            "## Source Tracking",
            "",
            f"<!-- speckit_feature: {feature_path.name} -->",
            f"<!-- speckit_change_name: {change_name} -->",
        ]
        return "\n".join(lines) + "\n"

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _proposal_why_lines(
        self,
        feature_title: str,
        spec_data: dict[str, Any],
        plan_data: dict[str, Any] | None,
    ) -> list[str]:
        """Build the Why section lines for a generated proposal."""
        why_lines = [
            str(story.get("why_priority") or "").strip()
            for story in spec_data.get("stories", [])
            if isinstance(story, dict) and str(story.get("why_priority") or "").strip()
        ]
        if why_lines:
            return why_lines
        if plan_data and plan_data.get("summary"):
            return [str(plan_data["summary"]).strip()]
        return [f"Convert Spec-Kit feature '{feature_title}' into an OpenSpec change proposal."]

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _proposal_requirement_lines(self, feature_title: str, spec_data: dict[str, Any]) -> list[str]:
        """Build the What Changes bullet list for a generated proposal."""
        requirements = [
            f"- {item.get('text', '').strip()}"
            for item in spec_data.get("requirements", [])
            if isinstance(item, dict) and item.get("text")
        ]
        return requirements or [f"- Preserve the behavior described by {feature_title}."]

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_change_design(
        self, change_name: str, spec_data: dict[str, Any], plan_data: dict[str, Any] | None
    ) -> str:
        """Render the OpenSpec design.md file."""
        title = str(spec_data.get("feature_title") or change_name)
        if plan_data is None:
            return self._render_fallback_design(change_name, title)
        context_lines = self._plan_context_lines(plan_data)
        decision_lines = self._plan_decision_lines(plan_data)
        risk_lines = self._plan_risk_lines(plan_data)
        lines = [
            f"# Design: {change_name}",
            "",
            "## Summary",
            "",
            str(plan_data.get("summary") or f"Technical design for {title}."),
            "",
            "## Context",
            "",
            *context_lines,
            "",
            "## Decisions",
            "",
            *decision_lines,
            "",
            "## Risks / Trade-offs",
            "",
            *risk_lines,
            "",
        ]
        return "\n".join(lines)

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_fallback_design(self, change_name: str, title: str) -> str:
        """Render a minimal design when Spec-Kit plan.md is unavailable."""
        lines = [
            f"# Design: {change_name}",
            "",
            "## Summary",
            "",
            f"Technical design for {title}.",
            "",
            "## Context",
            "",
            "Spec-Kit `plan.md` was not present during conversion.",
            "",
            "## Decisions",
            "",
            "- Placeholder: add technical decisions once the implementation plan is available.",
            "",
            "## Risks / Trade-offs",
            "",
            "- Missing `plan.md` limited the technical context captured from Spec-Kit.",
            "",
        ]
        return "\n".join(lines)

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _plan_context_lines(self, plan_data: dict[str, Any]) -> list[str]:
        """Build the design context section from Spec-Kit plan data."""
        lines: list[str] = []
        if plan_data.get("language_version"):
            lines.append(f"- Language/Version: {plan_data['language_version']}")
        lines.extend(_dependency_lines(plan_data))
        lines.extend(f"- Stack: {item}" for item in plan_data.get("technology_stack", []))
        lines.extend(f"- Constraint: {item}" for item in plan_data.get("constraints", []))
        lines.extend(f"- Unknown: {item}" for item in plan_data.get("unknowns", []))
        return lines or self._fallback_plan_context(plan_data)

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _fallback_plan_context(self, plan_data: dict[str, Any]) -> list[str]:
        """Extract context lines from raw Technical Context markdown if needed."""
        raw_plan_content = str(plan_data.get("_raw_content") or "")
        match = re.search(
            r"^## Technical Context\n(.*?)(?=\n## |\Z)",
            raw_plan_content,
            re.MULTILINE | re.DOTALL,
        )
        if not match:
            return ["- No explicit technical context was captured from Spec-Kit plan.md."]
        return [f"- {line.strip()}" for line in match.group(1).splitlines() if line.strip()]

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _plan_decision_lines(self, plan_data: dict[str, Any]) -> list[str]:
        """Build the design decisions section from plan phases."""
        phases = [phase for phase in plan_data.get("phases", []) if isinstance(phase, dict)]
        if not phases:
            return ["- No explicit phases were captured from Spec-Kit plan.md."]
        lines: list[str] = []
        for phase in phases:
            phase_name = f"Phase {phase.get('number')}: {phase.get('name')}"
            phase_body = str(phase.get("content") or "").strip() or "No additional detail captured."
            lines.extend([f"### {phase_name}", "", phase_body, ""])
        if lines and lines[-1] == "":
            lines.pop()
        return lines

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _plan_risk_lines(self, plan_data: dict[str, Any]) -> list[str]:
        """Build the design risks section from constraints and unknowns."""
        risks = list(plan_data.get("constraints", [])) + list(plan_data.get("unknowns", []))
        return [f"- {risk}" for risk in risks] or ["- No significant risks were captured in Spec-Kit plan.md."]

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_change_spec(self, capability: str, spec_data: dict[str, Any]) -> str:
        """Render the generated OpenSpec spec file."""
        title = str(spec_data.get("feature_title") or capability)
        lines = [
            f"# Spec: {capability}",
            "",
            "## ADDED Requirements",
            "",
            f"### Requirement: {title}",
            "",
            "The system SHALL implement the imported Spec-Kit feature requirements and scenarios.",
            "",
            *self._spec_scenarios(spec_data),
        ]
        return "\n".join(lines) + "\n"

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _spec_scenarios(self, spec_data: dict[str, Any]) -> list[str]:
        """Build scenario blocks for the generated OpenSpec spec."""
        stories = [story for story in spec_data.get("stories", []) if isinstance(story, dict)]
        requirements = [item for item in spec_data.get("requirements", []) if isinstance(item, dict)]
        if stories:
            return _story_scenarios(stories)
        if requirements:
            return _requirement_scenarios(requirements)
        return [
            "#### Scenario: Imported feature placeholder",
            "",
            "- **GIVEN** the imported Spec-Kit feature is available",
            "- **WHEN** the change is applied",
            "- **THEN** the generated OpenSpec artifacts preserve the feature intent",
            "",
        ]

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_change_tasks(self, spec_data: dict[str, Any], tasks_data: dict[str, Any] | None) -> str:
        """Render the generated OpenSpec tasks file."""
        title = str(spec_data.get("feature_title") or "Imported feature")
        lines = [f"## 1. {title}", ""]
        phases = self._task_phases(tasks_data)
        if phases:
            lines.extend(_render_phase_task_lines(phases))
        else:
            lines.extend(["- [ ] 1.1 Implement the imported Spec-Kit scope", ""])
        return "\n".join(lines) + "\n"

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _task_phases(self, tasks_data: dict[str, Any] | None) -> list[dict[str, Any]]:
        """Normalize parsed task phases or reconstruct them from raw markdown."""
        phases = list((tasks_data or {}).get("phases", []))
        if self._phases_need_raw_fallback(phases):
            raw_content = str((tasks_data or {}).get("_raw_content") or "")
            return self._extract_phase_tasks_from_raw_markdown(raw_content)
        if phases:
            return phases
        task_items = [item for item in (tasks_data or {}).get("tasks", []) if isinstance(item, dict)]
        return [{"name": "Imported", "tasks": task_items}] if task_items else []

    @ensure(lambda result: isinstance(result, bool), "Must return bool")
    def _phases_need_raw_fallback(self, phases: list[dict[str, Any]]) -> bool:
        """Determine whether parsed phases need reconstruction from raw markdown."""
        if not phases:
            return False
        return all(not phase.get("tasks") for phase in phases if isinstance(phase, dict))

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _extract_phase_tasks_from_raw_markdown(self, tasks_markdown: str) -> list[dict[str, Any]]:
        """Fallback parser for Spec-Kit tasks.md when scanner task groups are empty."""
        phases: list[dict[str, Any]] = []
        phase_pattern = re.compile(r"^## Phase (\d+): (.+?)\n(.*?)(?=^## Phase |\Z)", re.MULTILINE | re.DOTALL)
        task_pattern = re.compile(
            r"^- \[([ x])\]\s+\[?T?\d+\]?\s*(?:\[P\])?\s*(?:\[US\d+\])?\s*(.+)$",
            re.MULTILINE,
        )
        for match in phase_pattern.finditer(tasks_markdown):
            phase_tasks = [
                {"checked": task_match.group(1) == "x", "description": task_match.group(2).strip()}
                for task_match in task_pattern.finditer(match.group(3))
            ]
            phases.append({"name": match.group(2).strip(), "tasks": phase_tasks})
        return phases

    @ensure(lambda result: isinstance(result, dict), "Must return dict")
    def _parse_change_proposal(self, proposal_path: Path) -> dict[str, str | None]:
        """Parse the minimal OpenSpec proposal fields required for Spec-Kit export."""
        content = proposal_path.read_text(encoding="utf-8")
        title_match = re.search(r"^# Change:\s*(.+)$", content, re.MULTILINE)
        why_match = re.search(r"^## Why\n(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
        feature_match = re.search(r"<!--\s*speckit_feature:\s*(.+?)\s*-->", content)
        return {
            "title": title_match.group(1).strip() if title_match else proposal_path.parent.name,
            "rationale": why_match.group(1).strip() if why_match else "",
            "feature_dir": feature_match.group(1).strip() if feature_match else None,
        }

    @ensure(lambda result: isinstance(result, dict), "Must return dict")
    def _parse_change_design(self, design_path: Path) -> dict[str, list[str] | str]:
        """Parse summary, context, decisions, and risks from design.md."""
        if not design_path.exists():
            return {"summary": "", "context": [], "decisions": [], "risks": []}
        content = design_path.read_text(encoding="utf-8")
        return {
            "summary": extract_markdown_section(content, "Summary"),
            "context": extract_bullet_like_lines(extract_markdown_section(content, "Context")),
            "decisions": extract_bullet_like_lines(extract_markdown_section(content, "Decisions")),
            "risks": extract_bullet_like_lines(extract_markdown_section(content, "Risks / Trade-offs")),
        }

    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _parse_change_tasks(self, tasks_path: Path) -> list[dict[str, Any]]:
        """Parse numbered OpenSpec tasks into grouped phases."""
        if not tasks_path.exists():
            return []
        content = tasks_path.read_text(encoding="utf-8")
        phase_matches = list(re.finditer(r"^###\s+(\d+)\.\s+(.+)$", content, re.MULTILINE))
        phases = [_phase_from_match(content, phase_matches, index, match) for index, match in enumerate(phase_matches)]
        return phases or [{"name": "Imported", "tasks": []}]

    @ensure(lambda result: isinstance(result, dict), "Must return dict")
    def _parse_change_spec(self, spec_path: Path) -> dict[str, Any]:
        """Parse generated OpenSpec scenarios for Spec-Kit export."""
        content = spec_path.read_text(encoding="utf-8")
        matches = list(re.finditer(r"^#### Scenario:\s*(.+)$", content, re.MULTILINE))
        scenarios = [_scenario_from_match(content, matches, index, match) for index, match in enumerate(matches)]
        return {"scenarios": scenarios}

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_speckit_spec(
        self, title: str, feature_dir_name: str, rationale: str, change_spec: dict[str, Any]
    ) -> str:
        """Render Spec-Kit spec.md from an OpenSpec change proposal."""
        lines = [
            "---",
            f"**Feature Branch**: `{feature_dir_name}`",
            f"**Created**: {datetime.now(UTC).strftime('%Y-%m-%d')}",
            "**Status**: Draft",
            "---",
            "",
            f"# Feature Specification: {title}",
            "",
            "## User Scenarios & Testing",
            "",
        ]
        for story_index, scenario in enumerate(change_spec.get("scenarios", []), start=1):
            lines.extend(_render_speckit_story(story_index, scenario, rationale))
        return "\n".join(lines) + "\n"

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_speckit_plan(self, title: str, design: dict[str, list[str] | str]) -> str:
        """Render Spec-Kit plan.md from OpenSpec design data."""
        context = design.get("context", [])
        risks = design.get("risks", [])
        decisions = design.get("decisions", [])
        context_lines = (
            [f"- {item}" for item in context]
            if isinstance(context, list) and context
            else ["- Imported from OpenSpec design context"]
        )
        risk_lines = [f"- {item}" for item in risks] if isinstance(risks, list) and risks else ["- None specified"]
        decision_lines = (
            [f"- {item}" for item in decisions]
            if isinstance(decisions, list) and decisions
            else ["- Imported from OpenSpec design decisions"]
        )
        lines = [
            f"# Implementation Plan: {title}",
            "",
            "## Summary",
            str(design.get("summary") or f"Implementation plan for {title}."),
            "",
            "## Technical Context",
            "",
            "**Language/Version**: Python 3.11+",
            "",
            "**Primary Dependencies:**",
            "",
            "- `typer` - CLI framework",
            "- `pydantic` - Data validation",
            "",
            "**Technology Stack:**",
            "",
            *context_lines,
            "",
            "**Constraints:**",
            "",
            *risk_lines,
            "",
            "**Unknowns:**",
            "",
            "- None at this time",
            "",
            "## Phase 0: Research",
            "",
            *decision_lines,
            "",
            "## Phase 1: Design",
            "",
            f"Design work for {title}.",
            "",
            "## Phase 2: Implementation",
            "",
            f"Implementation work for {title}.",
            "",
        ]
        return "\n".join(lines) + "\n"

    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _render_speckit_tasks(self, tasks: list[dict[str, Any]]) -> str:
        """Render Spec-Kit tasks.md from grouped OpenSpec tasks."""
        lines = ["# Tasks", ""]
        task_counter = 1
        for phase_index, phase in enumerate(tasks, start=1):
            lines.extend([f"## Phase {phase_index}: {phase.get('name', 'Imported')}", ""])
            for task in phase.get("tasks", []):
                checked = "x" if task.get("checked") else " "
                lines.append(f"- [{checked}] [T{task_counter:03d}] {task.get('description', '').strip()}")
                task_counter += 1
            lines.append("")
        if task_counter == 1:
            lines.extend(["## Phase 1: Imported", "", "- [ ] [T001] Review imported OpenSpec work", ""])
        return "\n".join(lines) + "\n"


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _dependency_lines(plan_data: dict[str, Any]) -> list[str]:
    """Convert parsed dependency metadata into design context bullet lines."""
    lines: list[str] = []
    for dep in plan_data.get("dependencies", []):
        if not isinstance(dep, dict):
            continue
        desc = f" - {dep.get('description')}" if dep.get("description") else ""
        lines.append(f"- Dependency: `{dep.get('name', '')}`{desc}")
    return lines


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _story_scenarios(stories: list[dict[str, Any]]) -> list[str]:
    """Convert Spec-Kit stories into OpenSpec scenario blocks."""
    lines: list[str] = []
    for story in stories:
        lines.extend(
            [
                f"#### Scenario: {story.get('title', 'Imported user story')}",
                "",
                f"<!-- speckit_priority: {story.get('priority', 'P3')} -->",
                f"<!-- speckit_invest: {story.get('invest', {})} -->",
                *(_acceptance_lines(story.get("acceptance") or [])),
                *(_scenario_group_lines(story.get("scenarios") or {})),
                "",
            ]
        )
    return lines


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _acceptance_lines(acceptances: list[Any]) -> list[str]:
    """Convert acceptance criteria into OpenSpec GIVEN/WHEN/THEN lines."""
    if acceptances:
        return [f"- **GIVEN** {acceptance}" for acceptance in acceptances]
    return [
        "- **GIVEN** the imported user story is in scope",
        "- **WHEN** the imported capability is exercised",
        "- **THEN** the behavior matches the original Spec-Kit acceptance intent",
    ]


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _scenario_group_lines(scenario_groups: dict[str, Any]) -> list[str]:
    """Convert grouped Spec-Kit scenarios into OpenSpec AND lines."""
    lines: list[str] = []
    for scenario_type in ("primary", "alternate", "exception", "recovery"):
        values = scenario_groups.get(scenario_type, []) if isinstance(scenario_groups, dict) else []
        for value in values:
            lines.append(f"- **AND** {scenario_type.title()} scenario: {value}")
    return lines


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _requirement_scenarios(requirements: list[dict[str, Any]]) -> list[str]:
    """Convert requirements into fallback OpenSpec scenario blocks."""
    lines: list[str] = []
    for requirement in requirements:
        lines.extend(
            [
                f"#### Scenario: {requirement.get('id', 'Imported requirement')}",
                "",
                f"- **GIVEN** {requirement.get('text', '').strip()}",
                "- **WHEN** the capability is implemented",
                "- **THEN** the imported requirement remains satisfied",
                "",
            ]
        )
    return lines


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _render_phase_task_lines(phases: list[dict[str, Any]]) -> list[str]:
    """Render OpenSpec task phases from normalized task data."""
    lines: list[str] = []
    for phase_index, phase in enumerate(phases, start=1):
        lines.extend([f"### {phase_index}. {phase.get('name', 'Phase')}", ""])
        tasks = phase.get("tasks", [])
        if not tasks:
            lines.append(f"- [ ] {phase_index}.1 Review {phase.get('name', 'phase')} work items")
        for task_index, task in enumerate(tasks, start=1):
            checked = "x" if task.get("checked") else " "
            lines.append(f"- [{checked}] {phase_index}.{task_index} {task.get('description', '').strip()}")
        lines.append("")
    return lines


@beartype
@ensure(lambda result: isinstance(result, dict), "Must return dict")
def _phase_from_match(
    content: str,
    phase_matches: list[re.Match[str]],
    index: int,
    match: re.Match[str],
) -> dict[str, Any]:
    """Build one grouped task phase from a markdown heading match."""
    start = match.end()
    end = phase_matches[index + 1].start() if index + 1 < len(phase_matches) else len(content)
    block = content[start:end]
    phase_tasks = [
        {"checked": task_match.group(1) == "x", "description": task_match.group(3).strip()}
        for task_match in re.finditer(r"^- \[([ x])\]\s+(\d+\.\d+)\s+(.+)$", block, re.MULTILINE)
    ]
    return {"name": match.group(2).strip(), "tasks": phase_tasks}


@beartype
@ensure(lambda result: isinstance(result, dict), "Must return dict")
def _scenario_from_match(
    content: str,
    matches: list[re.Match[str]],
    index: int,
    match: re.Match[str],
) -> dict[str, Any]:
    """Build one parsed scenario block from markdown."""
    start = match.end()
    end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
    block = content[start:end]
    bullets = [line[2:].strip() for line in block.splitlines() if line.strip().startswith("- ")]
    return {"title": match.group(1).strip(), "bullets": bullets}


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _render_speckit_story(story_index: int, scenario: dict[str, Any], rationale: str) -> list[str]:
    """Render a single Spec-Kit story block from parsed OpenSpec scenario data."""
    story_title = scenario.get("title", f"Story {story_index}")
    bullets = scenario.get("bullets", []) if isinstance(scenario, dict) else []
    lines = [
        f"### User Story {story_index} - {story_title} (Priority: P2)",
        f"Users can {str(story_title).lower()}",
        "",
        f"**Why this priority**: {rationale or 'Imported from OpenSpec change proposal.'}",
        "",
        "**Independent**: YES",
        "**Negotiable**: YES",
        "**Valuable**: YES",
        "**Estimable**: YES",
        "**Small**: YES",
        "**Testable**: YES",
        "",
        "**Acceptance Criteria:**",
        "",
    ]
    if bullets:
        lines.extend(f"{bullet_index}. {bullet}" for bullet_index, bullet in enumerate(bullets, start=1))
    else:
        lines.append(
            "1. **Given** the change proposal is approved, **When** work begins, **Then** the story is implemented"
        )
    lines.extend(["", "**Scenarios:**", "", "- **Primary Scenario**: Imported from OpenSpec scenario", ""])
    return lines


@beartype
@ensure(lambda result: isinstance(result, str), "Must return string")
def extract_markdown_section(content: str, heading: str) -> str:
    """Extract a markdown section body by heading text."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def extract_bullet_like_lines(section_text: str) -> list[str]:
    """Convert section text into compact bullet-like lines."""
    values: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip())
        elif stripped and not stripped.startswith("#"):
            values.append(stripped)
    return values


@beartype
@ensure(lambda result: isinstance(result, str), "Must return string")
def slugify(title: str) -> str:
    """Convert a title into a filesystem-safe slug."""
    name = re.sub(r"[^a-z0-9]+", "-", title.lower())
    name = re.sub(r"-+", "-", name)
    return name.strip("-")
