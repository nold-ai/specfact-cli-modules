"""Tests for the requirements runtime module."""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import NoReturn

import pytest
from specfact_cli.common.bundle_factory import create_empty_project_bundle
from specfact_cli.requirements import importers as core_requirements_importers
from specfact_cli.utils.bundle_loader import save_project_bundle

from specfact_requirements.requirements import runtime as requirements_runtime
from specfact_requirements.requirements.runtime import (
    RequirementsCoreUnavailableError,
    auto_detect_openspec_change,
    import_native_requirements_to_bundle,
    import_requirements_file_to_bundle,
    list_requirements_with_coverage,
    requirements_gate_finding_counts,
    validate_requirements_bundle,
)


def _requirement_record(requirement_id: str = "REQ-165", *, with_evidence: bool = False) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": "1",
        "requirement_id": requirement_id,
        "title": "Requirement context is imported as validation evidence",
        "sources": [
            {
                "source_type": "issue",
                "locator": "https://github.com/nold-ai/specfact-cli-modules/issues/165",
                "title": "Requirements Input Runtime Commands Follow-Up",
            }
        ],
    }
    if with_evidence:
        record["evidence_links"] = [{"link_type": "test", "target": "tests/unit/specfact_requirements"}]
    return record


def _bundle_dir(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle = create_empty_project_bundle("bundle")
    save_project_bundle(bundle, bundle_dir, atomic=False)
    return bundle_dir


def _openspec_change(project_root: Path) -> Path:
    change_dir = project_root / "openspec" / "changes" / "widget-evidence"
    spec_path = change_dir / "specs" / "widgets" / "spec.md"
    spec_path.parent.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("# Change: Widget evidence\n", encoding="utf-8")
    (change_dir / "tasks.md").write_text("# Tasks: Widget evidence\n", encoding="utf-8")
    spec_path.write_text(
        """## ADDED Requirements

### Requirement: Widget rendering

The system SHALL render a widget.

#### Scenario: Render a valid widget

- **GIVEN** a valid widget request
- **WHEN** rendering runs
- **THEN** the widget is returned
""",
        encoding="utf-8",
    )
    return change_dir


def _speckit_feature(project_root: Path) -> Path:
    feature_dir = project_root / "specs" / "001-widget-rendering"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        """# Feature Specification: Widget rendering

## User Scenarios & Testing

### User Story 1 - Render widgets (Priority: P1)

As a user, I want widgets rendered so that I can see them.

**Acceptance Scenarios**:

1. **Given** a valid widget request, **When** rendering runs, **Then** the widget is returned

## Requirements

- **FR-001**: System MUST render a widget
""",
        encoding="utf-8",
    )
    return feature_dir


def _block_runtime_import(module_name: str) -> Callable[[str], ModuleType]:
    def blocked_import(name: str) -> ModuleType:
        if name == module_name:
            raise ImportError(f"blocked import: {name}")
        return import_module(name)

    return blocked_import


def _unavailable_native_validator(*_args: object, **_kwargs: object) -> NoReturn:
    raise FileNotFoundError


def test_import_requirements_file_to_bundle_preserves_valid_records_and_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "requirements.json"
    source.write_text(
        json.dumps(
            {
                "requirements": [
                    _requirement_record(),
                    {"requirement_id": "REQ-BROKEN", "schema_version": "1", "title": "Missing source refs"},
                ]
            }
        ),
        encoding="utf-8",
    )
    bundle_dir = _bundle_dir(tmp_path)

    result = import_requirements_file_to_bundle(source, bundle_dir)

    assert [record.requirement_id for record in result.requirements] == ["REQ-165"]
    assert [diagnostic.requirement_id for diagnostic in result.diagnostics] == ["REQ-BROKEN"]
    listing = list_requirements_with_coverage(bundle_dir)
    assert [record["requirement_id"] for record in listing["requirements"]] == ["REQ-165"]


@pytest.mark.parametrize("profile", ["enterprise", "enterprise-full-stack"])
def test_validate_requirements_bundle_uses_profile_aware_core_validation(tmp_path: Path, profile: str) -> None:
    source = tmp_path / "requirements.json"
    source.write_text(json.dumps([_requirement_record()]), encoding="utf-8")
    bundle_dir = _bundle_dir(tmp_path)
    import_requirements_file_to_bundle(source, bundle_dir)

    report = validate_requirements_bundle(bundle_dir, profile=profile)

    assert report.status == "failed"
    assert report.violations[0]["location"] == "requirements.inputs[REQ-165].evidence_links"


def test_imported_requirements_survive_later_atomic_bundle_save(tmp_path: Path) -> None:
    source = tmp_path / "requirements.json"
    source.write_text(json.dumps([_requirement_record("REQ-PRESERVE", with_evidence=True)]), encoding="utf-8")
    bundle_dir = _bundle_dir(tmp_path)
    import_requirements_file_to_bundle(source, bundle_dir)

    assert (bundle_dir / "reports" / "requirements" / "inputs.yaml").is_file()
    assert not (bundle_dir / "requirements.inputs.yaml").exists()

    bundle = create_empty_project_bundle("bundle")
    save_project_bundle(bundle, bundle_dir, atomic=True)

    listing = list_requirements_with_coverage(bundle_dir)

    assert [record["requirement_id"] for record in listing["requirements"]] == ["REQ-PRESERVE"]


def test_requirements_runtime_raises_clear_error_when_core_context_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "requirements.json"
    source.write_text(json.dumps([_requirement_record()]), encoding="utf-8")
    bundle_dir = _bundle_dir(tmp_path)
    monkeypatch.setattr(
        requirements_runtime,
        "import_module",
        _block_runtime_import("specfact_cli.requirements.context"),
    )

    with pytest.raises(RequirementsCoreUnavailableError, match="requirements context helpers"):
        import_requirements_file_to_bundle(source, bundle_dir)

    with pytest.raises(RequirementsCoreUnavailableError, match="requirements context helpers"):
        validate_requirements_bundle(bundle_dir)


def test_requirements_runtime_raises_clear_error_when_core_models_are_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle_dir = _bundle_dir(tmp_path)
    sidecar = bundle_dir / "reports" / "requirements" / "inputs.yaml"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("requirements: []\n", encoding="utf-8")
    monkeypatch.setattr(
        requirements_runtime,
        "import_module",
        _block_runtime_import("specfact_cli.models.requirements"),
    )

    with pytest.raises(RequirementsCoreUnavailableError, match="requirements models"):
        list_requirements_with_coverage(bundle_dir)


def test_list_requirements_with_coverage_is_machine_readable(tmp_path: Path) -> None:
    source = tmp_path / "requirements.json"
    source.write_text(json.dumps([_requirement_record("REQ-COVERED", with_evidence=True)]), encoding="utf-8")
    bundle_dir = _bundle_dir(tmp_path)
    import_requirements_file_to_bundle(source, bundle_dir)

    listing = list_requirements_with_coverage(bundle_dir, show_coverage=True)

    assert listing["requirements"][0]["requirement_id"] == "REQ-COVERED"
    assert listing["requirements"][0]["title"] == "Requirement context is imported as validation evidence"
    assert listing["coverage"]["total_requirements"] == 1
    assert listing["coverage"]["with_test_links"] == 1


def test_import_openspec_change_persists_core_records_without_mutating_source(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    change_dir = _openspec_change(project_root)
    before = {path.relative_to(change_dir): path.read_bytes() for path in change_dir.rglob("*") if path.is_file()}
    bundle_dir = _bundle_dir(project_root)

    result = import_native_requirements_to_bundle("openspec", change_dir, bundle_dir)

    assert [record.requirement_id for record in result.requirements] == [
        "openspec:widget-evidence:widgets:widget-rendering"
    ]
    assert result.diagnostics == []
    assert list_requirements_with_coverage(bundle_dir)["requirements"][0]["requirement_id"] == (
        "openspec:widget-evidence:widgets:widget-rendering"
    )
    repeated_result = import_native_requirements_to_bundle("openspec", change_dir, bundle_dir)
    assert [record.requirement_id for record in repeated_result.requirements] == [
        "openspec:widget-evidence:widgets:widget-rendering"
    ]
    assert [record["requirement_id"] for record in list_requirements_with_coverage(bundle_dir)["requirements"]] == [
        "openspec:widget-evidence:widgets:widget-rendering"
    ]
    after = {path.relative_to(change_dir): path.read_bytes() for path in change_dir.rglob("*") if path.is_file()}
    assert after == before


def test_import_speckit_feature_persists_core_records(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    feature_dir = _speckit_feature(project_root)
    bundle_dir = _bundle_dir(project_root)

    result = import_native_requirements_to_bundle("speckit", feature_dir, bundle_dir)

    assert [record.requirement_id for record in result.requirements] == ["speckit:001-widget-rendering:render-a-widget"]
    assert result.diagnostics == []


def test_auto_detect_openspec_change_ignores_archive_directory(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    change_dir = _openspec_change(project_root)
    (project_root / "openspec" / "changes" / "archive" / "2026-07-14-widget-evidence").mkdir(parents=True)

    detected = auto_detect_openspec_change(project_root)

    assert detected == change_dir


def test_import_rejected_by_core_does_not_persist_partial_sidecar(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    change_dir = _openspec_change(project_root)
    (project_root / "openspec" / "config.yaml").write_text("schema: company-custom\n", encoding="utf-8")
    bundle_dir = _bundle_dir(project_root)

    result = import_native_requirements_to_bundle("openspec", change_dir, bundle_dir)

    assert result.requirements == []
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["unsupported-source-schema"]
    assert not (bundle_dir / "reports" / "requirements" / "inputs.yaml").exists()


def test_import_openspec_uses_source_repository_native_validation_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "source-project"
    change_dir = _openspec_change(project_root)
    config_dir = project_root / ".specfact"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "validation:\n  openspec:\n    require_native_validation: true\n",
        encoding="utf-8",
    )
    bundle_dir = _bundle_dir(tmp_path / "bundle-project")
    linked_change_dir = tmp_path / "linked-widget-evidence"
    linked_change_dir.symlink_to(change_dir, target_is_directory=True)
    monkeypatch.setattr(core_requirements_importers.subprocess, "run", _unavailable_native_validator)

    result = import_native_requirements_to_bundle("openspec", linked_change_dir, bundle_dir)

    assert result.requirements == []
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["upstream-validator-unavailable"]
    assert not (bundle_dir / "reports" / "requirements" / "inputs.yaml").exists()


def test_profile_resolution_and_gate_counts_delegate_to_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = tmp_path / "project"
    change_dir = _openspec_change(project_root)
    bundle_dir = _bundle_dir(project_root)
    import_native_requirements_to_bundle("openspec", change_dir, bundle_dir)
    config_dir = project_root / ".specfact"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("profile: enterprise\n", encoding="utf-8")
    monkeypatch.chdir(project_root)

    configured_report = validate_requirements_bundle(bundle_dir)
    explicit_report = validate_requirements_bundle(bundle_dir, profile="solo")
    gate_counts = requirements_gate_finding_counts(bundle_dir)

    assert configured_report.status == "failed"
    assert explicit_report.status == "warnings"
    assert gate_counts["scenario-unverified"] == 1
