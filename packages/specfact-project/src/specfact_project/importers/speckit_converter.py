"""
Spec-Kit to SpecFact converter.

This module converts Spec-Kit markdown artifacts (spec.md, plan.md, tasks.md, constitution.md)
to SpecFact format (plans, protocols).
"""

# pylint: disable=too-many-lines,import-outside-toplevel,line-too-long,broad-exception-caught,too-many-nested-blocks,too-many-arguments,too-many-locals,reimported,redefined-outer-name,logging-fstring-interpolation,unused-argument,protected-access,too-many-positional-arguments,consider-using-in,unused-import,redefined-argument-from-local,using-constant-test,too-many-boolean-expressions,too-many-return-statements,use-implicit-booleaness-not-comparison,too-many-branches,too-many-statements

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require
from pydantic import BaseModel
from specfact_cli import runtime
from specfact_cli.models.plan import Feature, Idea, PlanBundle, Product, Release, Story
from specfact_cli.models.protocol import Protocol
from specfact_cli.utils.structure import SpecFactStructure

from specfact_project.analyzers.constitution_evidence_extractor import ConstitutionEvidenceExtractor
from specfact_project.generators.plan_generator import PlanGenerator
from specfact_project.generators.protocol_generator import ProtocolGenerator
from specfact_project.generators.workflow_generator import WorkflowGenerator
from specfact_project.importers import speckit_markdown_sections as speckit_md
from specfact_project.importers.speckit_change_proposal_bridge import SpecKitChangeProposalBridge
from specfact_project.importers.speckit_scanner import SpecKitScanner
from specfact_project.migrations.plan_migrator import get_current_schema_version


class SpecKitConverter:
    """
    Converter from Spec-Kit format to SpecFact format.

    Converts markdown artifacts (spec.md, plan.md, tasks.md, constitution.md) → plan bundles.
    """

    @beartype
    def __init__(self, repo_path: Path, mapping_file: Path | None = None) -> None:
        """
        Initialize Spec-Kit converter.

        Args:
            repo_path: Path to Spec-Kit repository
            mapping_file: Optional custom mapping file (default: built-in)
        """
        self.repo_path = Path(repo_path)
        self.scanner = SpecKitScanner(repo_path)
        self.protocol_generator = ProtocolGenerator()
        self.plan_generator = PlanGenerator()
        self.workflow_generator = WorkflowGenerator()
        self.constitution_extractor = ConstitutionEvidenceExtractor(repo_path)
        self.mapping_file = mapping_file

    @beartype
    @ensure(lambda result: isinstance(result, Protocol), "Must return Protocol")
    @ensure(lambda result: len(result.states) >= 2, "Must have at least INIT and COMPLETE states")
    def convert_protocol(self, output_path: Path | None = None) -> Protocol:
        """
        Convert Spec-Kit features to SpecFact protocol.

        Creates a minimal protocol from feature states.
        Since Spec-Kit markdown artifacts don't explicitly define FSM protocols,
        this generates a simple protocol based on feature workflow.

        Args:
            output_path: Optional path to write protocol.yaml (default: .specfact/protocols/workflow.protocol.yaml)

        Returns:
            Generated Protocol model
        """
        # For markdown-based Spec-Kit, create a minimal protocol
        # States based on feature workflow: INIT -> FEATURE_1 -> ... -> COMPLETE
        features = self.scanner.discover_features()

        if not features:
            # Default minimal protocol if no features found
            states = ["INIT", "COMPLETE"]
        else:
            states = ["INIT"]
            for feature in features:
                feature_key = feature.get("feature_key", "UNKNOWN")
                states.append(feature_key)
            states.append("COMPLETE")

        protocol = Protocol(
            states=states,
            start="INIT",
            transitions=[],
            guards={},
        )

        # Write to file if output path provided
        if output_path:
            SpecFactStructure.ensure_structure(output_path.parent)
            # Only suppress FileExistsError if file already exists (idempotent)
            if output_path.exists():
                return protocol
            self.protocol_generator.generate(protocol, output_path)
        else:
            # Use default path - construct .specfact/protocols/workflow.protocol.yaml
            output_path = self.repo_path / ".specfact" / "protocols" / "workflow.protocol.yaml"
            SpecFactStructure.ensure_structure(self.repo_path)
            # Only suppress FileExistsError if file already exists (idempotent)
            if output_path.exists():
                return protocol
            self.protocol_generator.generate(protocol, output_path)

        return protocol

    def _write_converted_plan_bundle(self, plan_bundle: PlanBundle, output_path: Path | None) -> None:
        """Persist plan bundle to *output_path* or the default plan location."""
        if output_path:
            if output_path.is_dir():
                resolved = output_path / SpecFactStructure.ensure_plan_filename(output_path.name)
            else:
                resolved = output_path.with_name(SpecFactStructure.ensure_plan_filename(output_path.name))
            SpecFactStructure.ensure_structure(resolved.parent)
            self.plan_generator.generate(plan_bundle, resolved)
            return
        default_path = SpecFactStructure.get_default_plan_path(
            base_path=self.repo_path, preferred_format=runtime.get_output_format()
        )
        if default_path.parent.name == "projects":
            return
        resolved = default_path
        if resolved.exists() and resolved.is_dir():
            plan_filename = SpecFactStructure.ensure_plan_filename(resolved.name)
            resolved = resolved / plan_filename
        elif not resolved.exists():
            resolved = resolved.with_name(SpecFactStructure.ensure_plan_filename(resolved.name))
        SpecFactStructure.ensure_structure(resolved.parent)
        self.plan_generator.generate(plan_bundle, resolved)

    @beartype
    @ensure(lambda result: isinstance(result, PlanBundle), "Must return PlanBundle")
    @ensure(
        lambda result: result.version == get_current_schema_version(),
        "Must have current schema version",
    )
    def convert_plan(self, output_path: Path | None = None) -> PlanBundle:
        """
        Convert Spec-Kit markdown artifacts to SpecFact plan bundle.

        Args:
            output_path: Optional path to write plan bundle (default: .specfact/plans/main.bundle.<format>)

        Returns:
            Generated PlanBundle model
        """
        # Discover features from markdown artifacts
        discovered_features = self.scanner.discover_features()

        # Extract features from markdown data (empty list if no features found)
        features = self._extract_features_from_markdown(discovered_features) if discovered_features else []

        # Parse constitution for constraints (only if needed for idea creation)
        structure = self.scanner.scan_structure()
        memory_dir = Path(structure.get("specify_memory_dir", "")) if structure.get("specify_memory_dir") else None
        constraints: list[str] = []
        if memory_dir and Path(memory_dir).exists():
            memory_data = self.scanner.parse_memory_files(Path(memory_dir))
            constraints = memory_data.get("constraints", [])

        # Create idea from repository
        repo_name = self.repo_path.name or "Imported Project"
        idea = Idea(
            title=self._humanize_name(repo_name),
            narrative=f"Imported from Spec-Kit project: {repo_name}",
            target_users=[],
            value_hypothesis="",
            constraints=constraints,
            metrics=None,
        )

        # Create product with themes (extract from feature titles)
        themes = self._extract_themes_from_features(features)
        product = Product(
            themes=themes,
            releases=[
                Release(
                    name="v0.1",
                    objectives=["Migrate from Spec-Kit"],
                    scope=[f.key for f in features],
                    risks=[],
                )
            ],
        )

        # Create plan bundle with current schema version
        plan_bundle = PlanBundle(
            version=get_current_schema_version(),
            idea=idea,
            business=None,
            product=product,
            features=features,
            metadata=None,
            clarifications=None,
        )

        self._write_converted_plan_bundle(plan_bundle, output_path)

        return plan_bundle

    @staticmethod
    def _strings_from_dict_or_str(items: list[Any], text_key: str) -> list[str]:
        out: list[str] = []
        for item in items:
            if isinstance(item, dict):
                out.append(item.get(text_key, ""))
            elif isinstance(item, str):
                out.append(item)
        return out

    @staticmethod
    def _feature_confidence(feature_title: str, stories: list[Story], outcomes: list[str]) -> float:
        confidence = 0.5
        if feature_title and feature_title != "Unknown Feature":
            confidence += 0.2
        if stories:
            confidence += 0.2
        if outcomes:
            confidence += 0.1
        return min(confidence, 1.0)

    def _feature_from_discovered_row(self, feature_data: dict[str, Any]) -> Feature:
        feature_key = feature_data.get("feature_key", "UNKNOWN")
        feature_title = feature_data.get("feature_title", "Unknown Feature")
        stories = self._extract_stories_from_spec(feature_data)
        outcomes = self._strings_from_dict_or_str(feature_data.get("requirements", []), "text")
        acceptance = self._strings_from_dict_or_str(feature_data.get("success_criteria", []), "text")
        confidence = self._feature_confidence(feature_title, stories, outcomes)
        return Feature(
            key=feature_key,
            title=feature_title,
            outcomes=outcomes if outcomes else [f"Provides {feature_title} functionality"],
            acceptance=acceptance if acceptance else [f"{feature_title} is functional"],
            constraints=feature_data.get("edge_cases", []),
            stories=stories,
            confidence=confidence,
            draft=False,
            source_tracking=None,
            contract=None,
            protocol=None,
        )

    @beartype
    @require(lambda discovered_features: isinstance(discovered_features, list), "Must be list")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    @ensure(lambda result: all(isinstance(f, Feature) for f in result), "All items must be Features")
    def _extract_features_from_markdown(self, discovered_features: list[dict[str, Any]]) -> list[Feature]:
        """Extract features from Spec-Kit markdown artifacts."""
        return [self._feature_from_discovered_row(fd) for fd in discovered_features]

    @staticmethod
    def _normalize_story_scenarios(raw: Any) -> dict[str, Any] | None:
        if raw and isinstance(raw, dict):
            filtered = {k: v for k, v in raw.items() if v and isinstance(v, list) and len(v) > 0}
            return filtered if filtered else None
        return None

    def _tasks_for_story(self, feature_data: dict[str, Any], story_key: str) -> list[str]:
        tasks_data = feature_data.get("tasks", {})
        if not tasks_data or "tasks" not in tasks_data:
            return []
        out: list[str] = []
        for task in tasks_data["tasks"]:
            if not isinstance(task, dict):
                continue
            story_ref = task.get("story_ref", "")
            if (story_ref and story_ref in story_key) or not story_ref:
                out.append(task.get("description", ""))
        return out

    def _story_from_spec_row(self, feature_data: dict[str, Any], story_data: dict[str, Any]) -> Story:
        story_key = story_data.get("key", "UNKNOWN")
        story_title = story_data.get("title", "Unknown Story")
        priority = story_data.get("priority", "P3")
        priority_map = {"P1": 8, "P2": 5, "P3": 3, "P4": 1}
        story_points = priority_map.get(priority, 3)
        acceptance = story_data.get("acceptance", [])
        tasks = self._tasks_for_story(feature_data, story_key)
        scenarios = self._normalize_story_scenarios(story_data.get("scenarios"))
        return Story(
            key=story_key,
            title=story_title,
            acceptance=acceptance if acceptance else [f"{story_title} is implemented"],
            tags=[priority],
            story_points=story_points,
            value_points=story_points,
            tasks=tasks,
            confidence=0.8,
            draft=False,
            scenarios=scenarios,
            contracts=None,
        )

    @beartype
    @require(lambda feature_data: isinstance(feature_data, dict), "Must be dict")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    @ensure(lambda result: all(isinstance(s, Story) for s in result), "All items must be Stories")
    def _extract_stories_from_spec(self, feature_data: dict[str, Any]) -> list[Story]:
        """Extract user stories from Spec-Kit spec.md data."""
        spec_stories = feature_data.get("stories", [])
        return [self._story_from_spec_row(feature_data, sd) for sd in spec_stories if isinstance(sd, dict)]

    @beartype
    @require(lambda features: isinstance(features, list), "Must be list")
    @require(lambda features: all(isinstance(f, Feature) for f in features), "All items must be Features")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    @ensure(lambda result: all(isinstance(t, str) for t in result), "All items must be strings")
    @ensure(lambda result: len(result) > 0, "Must have at least one theme")
    def _extract_themes_from_features(self, features: list[Feature]) -> list[str]:
        """Extract themes from feature titles."""
        themes: set[str] = set()
        themes.add("Core")

        for feature in features:
            # Extract theme from feature title (first word or key pattern)
            title = feature.title
            if title:
                # Try to extract meaningful theme from title
                words = title.split()
                if words:
                    # Use first significant word as theme
                    theme = words[0]
                    if len(theme) > 2:
                        themes.add(theme)

        return sorted(themes)

    @beartype
    @ensure(lambda result: result.exists(), "Output path must exist")
    @ensure(lambda result: result.suffix == ".yml", "Must be YAML file")
    def generate_semgrep_rules(self, output_path: Path | None = None) -> Path:
        """
        Generate Semgrep async rules for the repository.

        Args:
            output_path: Optional path to write Semgrep rules (default: .semgrep/async-anti-patterns.yml)

        Returns:
            Path to generated Semgrep rules file
        """
        if output_path is None:
            # Use default path
            output_path = self.repo_path / ".semgrep" / "async-anti-patterns.yml"

        self.workflow_generator.generate_semgrep_rules(output_path)
        return output_path

    @beartype
    @require(lambda budget: budget > 0, "Budget must be positive")
    @require(lambda python_version: python_version.startswith("3."), "Python version must be 3.x")
    @ensure(lambda result: result.exists(), "Output path must exist")
    @ensure(lambda result: result.suffix == ".yml", "Must be YAML file")
    def generate_github_action(
        self,
        output_path: Path | None = None,
        repo_name: str | None = None,
        budget: int = 90,
        python_version: str = "3.12",
    ) -> Path:
        """
        Generate GitHub Action workflow for SpecFact validation.

        Args:
            output_path: Optional path to write workflow (default: .github/workflows/specfact-gate.yml)
            repo_name: Repository name for context
            budget: Time budget in seconds for validation (must be > 0)
            python_version: Python version for workflow (must be 3.x)

        Returns:
            Path to generated GitHub Action workflow file
        """
        if output_path is None:
            # Use default path
            output_path = self.repo_path / ".github" / "workflows" / "specfact-gate.yml"

        if repo_name is None:
            repo_name = self.repo_path.name or "specfact-project"

        self.workflow_generator.generate_github_action(output_path, repo_name, budget, python_version)
        return output_path

    @beartype
    @ensure(lambda result: isinstance(result, int), "Must return int (number of features converted)")
    @ensure(lambda result: result >= 0, "Result must be non-negative")
    def convert_to_speckit(
        self,
        plan_bundle: PlanBundle | BaseModel | dict[str, Any],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        """
        Convert SpecFact plan bundle to Spec-Kit markdown artifacts.

        Generates spec.md, plan.md, and tasks.md files for each feature in the plan bundle.

        Args:
            plan_bundle: SpecFact plan bundle to convert
            progress_callback: Optional callback function(current, total) to report progress

        Returns:
            Number of features converted
        """
        if isinstance(plan_bundle, PlanBundle):
            normalized_bundle = plan_bundle
        elif isinstance(plan_bundle, BaseModel):
            normalized_bundle = PlanBundle.model_validate(plan_bundle.model_dump(mode="python"))
        else:
            normalized_bundle = PlanBundle.model_validate(plan_bundle)

        features_converted = 0
        total_features = len(normalized_bundle.features)
        # Track used feature numbers to avoid duplicates
        used_feature_nums: set[int] = set()

        for idx, feature in enumerate(normalized_bundle.features, start=1):
            # Report progress if callback provided
            if progress_callback:
                progress_callback(idx, total_features)
            # Generate feature directory name from key (FEATURE-001 -> 001-feature-name)
            # Use number from key if available and not already used, otherwise use sequential index
            extracted_num = self._extract_feature_number(feature.key)
            if extracted_num == 0 or extracted_num in used_feature_nums:
                # No number found in key, or number already used - use sequential numbering
                # Find next available sequential number starting from idx
                feature_num = idx
                while feature_num in used_feature_nums:
                    feature_num += 1
            else:
                feature_num = extracted_num
            used_feature_nums.add(feature_num)
            feature_name = self._to_feature_dir_name(feature.title)

            # Create feature directory
            feature_dir = self.repo_path / "specs" / f"{feature_num:03d}-{feature_name}"
            feature_dir.mkdir(parents=True, exist_ok=True)

            # Generate spec.md (pass calculated feature_num to avoid recalculation)
            spec_content = self._generate_spec_markdown(feature, feature_num=feature_num)
            (feature_dir / "spec.md").write_text(spec_content, encoding="utf-8")

            # Generate plan.md
            plan_content = self._generate_plan_markdown(feature, normalized_bundle)
            (feature_dir / "plan.md").write_text(plan_content, encoding="utf-8")

            # Generate tasks.md
            tasks_content = self._generate_tasks_markdown(feature)
            (feature_dir / "tasks.md").write_text(tasks_content, encoding="utf-8")

            features_converted += 1

        return features_converted

    @beartype
    @require(lambda feature_path: feature_path.exists(), "Feature path must exist")
    @require(lambda feature_path: feature_path.is_dir(), "Feature path must be a directory")
    @require(lambda change_name: len(change_name.strip()) > 0, "Change name must be non-empty")
    @require(lambda output_dir: output_dir is not None, "Output directory must be provided")
    @ensure(lambda result: isinstance(result, Path), "Must return Path")
    @ensure(lambda result: result.exists(), "Change directory must exist")
    def convert_to_change_proposal(self, feature_path: Path, change_name: str, output_dir: Path) -> Path:
        """
        Convert a Spec-Kit feature directory into an OpenSpec change proposal.

        Args:
            feature_path: Path to Spec-Kit feature directory
            change_name: OpenSpec change identifier to create
            output_dir: Parent directory that contains OpenSpec changes

        Returns:
            Created change directory
        """
        bridge = SpecKitChangeProposalBridge(self.scanner)
        return bridge.convert_feature_to_change(Path(feature_path), change_name, Path(output_dir))

    @beartype
    @require(lambda change_dir: change_dir.exists(), "Change directory must exist")
    @require(lambda change_dir: change_dir.is_dir(), "Change directory must be a directory")
    @require(lambda output_dir: output_dir is not None, "Output directory must be provided")
    @ensure(lambda result: isinstance(result, Path), "Must return Path")
    @ensure(lambda result: result.exists(), "Feature directory must exist")
    def convert_to_speckit_feature(self, change_dir: Path, output_dir: Path) -> Path:
        """
        Convert an OpenSpec change proposal into a Spec-Kit feature directory.

        Args:
            change_dir: Path to OpenSpec change directory
            output_dir: Spec-Kit specs directory to write into

        Returns:
            Created feature directory
        """
        bridge = SpecKitChangeProposalBridge(self.scanner)
        return bridge.convert_change_to_feature(Path(change_dir), Path(output_dir))

    @beartype
    @require(lambda feature: isinstance(feature, Feature), "Must be Feature instance")
    @require(
        lambda feature_num: feature_num is None or feature_num > 0,
        "Feature number must be None or positive",
    )
    @ensure(lambda result: isinstance(result, str), "Must return string")
    @ensure(lambda result: len(result) > 0, "Result must be non-empty")
    def _generate_spec_markdown(self, feature: Feature, feature_num: int | None = None) -> str:
        """
        Generate Spec-Kit spec.md content from SpecFact feature.

        Args:
            feature: Feature to generate spec for
            feature_num: Optional pre-calculated feature number (avoids recalculation with fallback)
        """
        if feature_num is None:
            feature_num = self._extract_feature_number(feature.key)
            if feature_num == 0:
                feature_num = 1
        feature_name = self._to_feature_dir_name(feature.title)
        return speckit_md.generate_spec_markdown(feature, feature_num, feature_name)

    @beartype
    @require(
        lambda feature, plan_bundle: isinstance(feature, Feature) and isinstance(plan_bundle, PlanBundle),
        "Must be Feature and PlanBundle instances",
    )
    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _generate_plan_markdown(self, feature: Feature, plan_bundle: PlanBundle) -> str:
        """Generate Spec-Kit plan.md content from SpecFact feature."""
        contracts_defined = any(story.contracts for story in feature.stories if story.contracts)
        constitution_section: str | None
        try:
            constitution_evidence = self.constitution_extractor.extract_all_evidence(self.repo_path)
            constitution_section = self.constitution_extractor.generate_constitution_check_section(
                constitution_evidence
            )
        except Exception:
            constitution_section = None
        return speckit_md.generate_plan_markdown(feature, plan_bundle, constitution_section, contracts_defined)

    @beartype
    @require(lambda feature: isinstance(feature, Feature), "Must be Feature instance")
    @ensure(lambda result: isinstance(result, str), "Must return string")
    def _generate_tasks_markdown(self, feature: Feature) -> str:
        """Generate Spec-Kit tasks.md content from SpecFact feature."""
        return speckit_md.generate_tasks_markdown(feature, self._extract_story_number)

    @beartype
    @require(lambda feature: isinstance(feature, Feature), "Must be Feature instance")
    @require(lambda plan_bundle: isinstance(plan_bundle, PlanBundle), "Must be PlanBundle instance")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    @ensure(lambda result: len(result) > 0, "Must have at least one stack item")
    def _extract_technology_stack(self, feature: Feature, plan_bundle: PlanBundle) -> list[str]:
        """
        Extract technology stack from feature and plan bundle constraints.

        Args:
            feature: Feature to extract stack from
            plan_bundle: Plan bundle containing idea-level constraints

        Returns:
            List of technology stack items
        """
        return speckit_md.extract_technology_stack(feature, plan_bundle)

    @beartype
    @require(lambda feature_key: isinstance(feature_key, str), "Must be string")
    @ensure(lambda result: isinstance(result, int), "Must return int")
    def _extract_feature_number(self, feature_key: str) -> int:
        """Extract feature number from key (FEATURE-001 -> 1)."""

        match = re.search(r"(\d+)", feature_key)
        return int(match.group(1)) if match else 0

    @beartype
    @require(lambda story_key: isinstance(story_key, str), "Must be string")
    @ensure(lambda result: isinstance(result, int), "Must return int")
    def _extract_story_number(self, story_key: str) -> int:
        """Extract story number from key (STORY-001 -> 1)."""

        match = re.search(r"(\d+)", story_key)
        return int(match.group(1)) if match else 0

    @beartype
    @require(lambda title: isinstance(title, str), "Must be string")
    @ensure(lambda result: isinstance(result, str), "Must return string")
    @ensure(lambda result: len(result) > 0, "Result must be non-empty")
    def _to_feature_dir_name(self, title: str) -> str:
        """Convert feature title to directory name (User Authentication -> user-authentication)."""

        # Convert to lowercase, replace spaces and special chars with hyphens
        name = title.lower()
        name = re.sub(r"[^a-z0-9]+", "-", name)
        name = re.sub(r"-+", "-", name)  # Collapse multiple hyphens
        return name.strip("-")

    @beartype
    @require(lambda name: isinstance(name, str) and len(name) > 0, "Name must be non-empty string")
    @ensure(lambda result: isinstance(result, str), "Must return string")
    @ensure(lambda result: len(result) > 0, "Result must be non-empty")
    def _humanize_name(self, name: str) -> str:
        """Convert component name to human-readable title."""

        # Handle PascalCase
        name = re.sub(r"([A-Z])", r" \1", name).strip()
        # Handle snake_case
        name = name.replace("_", " ").replace("-", " ")
        return name.title()
