"""Tests for the requirements runtime module."""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from types import ModuleType

import pytest
from specfact_cli.common.bundle_factory import create_empty_project_bundle
from specfact_cli.utils.bundle_loader import save_project_bundle

from specfact_requirements.requirements import runtime as requirements_runtime
from specfact_requirements.requirements.runtime import (
    RequirementsCoreUnavailableError,
    import_requirements_file_to_bundle,
    list_requirements_with_coverage,
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


def _block_runtime_import(module_name: str) -> Callable[[str], ModuleType]:
    def blocked_import(name: str) -> ModuleType:
        if name == module_name:
            raise ImportError(f"blocked import: {name}")
        return import_module(name)

    return blocked_import


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
