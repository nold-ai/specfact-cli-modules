"""Runtime helpers for requirements context commands."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import yaml
from beartype import beartype
from icontract import ensure, require
from specfact_cli.models.project import ProjectBundle
from specfact_cli.models.requirements import (
    RequirementInput,
    load_requirements_input_extension,
    requirements_input_extension_payload,
)
from specfact_cli.models.validation import ValidationReport
from specfact_cli.requirements.context import (
    KNOWN_REQUIREMENT_CONTEXT_PROFILES,
    RequirementContextCoverageSummary,
    RequirementContextImportResult,
    RequirementContextValidationProfile,
    attach_requirements_to_bundle,
    inspect_requirement_context_coverage,
    load_requirements_from_bundle,
    normalize_requirement_records,
    validate_requirement_context,
)
from specfact_cli.utils.bundle_loader import load_project_bundle, save_project_bundle


_REQUIREMENTS_INPUTS_FILE = "requirements.inputs.yaml"


def _records_are_supported(result: Sequence[RequirementInput | Mapping[str, Any]]) -> bool:
    return all(isinstance(record, RequirementInput | Mapping) for record in result)


def _result_has_expected_keys(result: dict[str, Any]) -> bool:
    return "requirements" in result


def _profile_is_supported(profile: str) -> bool:
    return profile in KNOWN_REQUIREMENT_CONTEXT_PROFILES


def _requirements_sidecar_path(bundle_dir: Path) -> Path:
    return bundle_dir / _REQUIREMENTS_INPUTS_FILE


def _load_bundle_with_requirements(bundle_dir: Path) -> ProjectBundle:
    bundle = load_project_bundle(bundle_dir)
    sidecar = _requirements_sidecar_path(bundle_dir)
    if not sidecar.exists():
        return bundle
    payload = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{sidecar} must contain a requirements.inputs mapping payload"
        raise ValueError(msg)
    records = load_requirements_input_extension(cast(dict[str, Any], payload))
    attach_requirements_to_bundle(bundle, records)
    return bundle


def _write_requirements_sidecar(bundle_dir: Path, records: Sequence[RequirementInput]) -> None:
    payload = requirements_input_extension_payload(list(records))
    _requirements_sidecar_path(bundle_dir).write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@beartype
@require(lambda source_file: source_file.is_file(), "source_file must exist")
@ensure(_records_are_supported, "all loaded records must be RequirementInput or mapping values")
def load_requirement_records(source_file: Path) -> list[RequirementInput | Mapping[str, Any]]:
    """Load requirement records from a JSON or YAML source file."""
    loaded = yaml.safe_load(source_file.read_text(encoding="utf-8"))
    if loaded is None:
        return []
    if isinstance(loaded, list):
        return cast(list[RequirementInput | Mapping[str, Any]], loaded)
    if isinstance(loaded, dict):
        maybe_records = loaded.get("requirements")
        if isinstance(maybe_records, list):
            return cast(list[RequirementInput | Mapping[str, Any]], maybe_records)
        return [cast(Mapping[str, Any], loaded)]
    msg = "requirements source must be a mapping, a list, or a mapping with a requirements list"
    raise ValueError(msg)


@beartype
@require(lambda existing: all(isinstance(record, RequirementInput) for record in existing))
@require(lambda imported: all(isinstance(record, RequirementInput) for record in imported))
@ensure(lambda result: all(isinstance(record, RequirementInput) for record in result))
def merge_requirement_inputs(
    existing: Sequence[RequirementInput],
    imported: Sequence[RequirementInput],
) -> list[RequirementInput]:
    """Merge imported requirements by stable ID while preserving existing order."""
    by_id = {record.requirement_id: record for record in existing}
    order = [record.requirement_id for record in existing]
    for record in imported:
        if record.requirement_id not in by_id:
            order.append(record.requirement_id)
        by_id[record.requirement_id] = record
    return [by_id[requirement_id] for requirement_id in order]


@beartype
@require(lambda source_file: source_file.is_file(), "source_file must exist")
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@ensure(lambda result: isinstance(result, RequirementContextImportResult))
def import_requirements_file_to_bundle(source_file: Path, bundle_dir: Path) -> RequirementContextImportResult:
    """Normalize requirement records from a file and attach valid records to a ProjectBundle."""
    records = load_requirement_records(source_file)
    result = normalize_requirement_records(records, source_locator=source_file.as_posix())
    bundle = _load_bundle_with_requirements(bundle_dir)
    merged = merge_requirement_inputs(load_requirements_from_bundle(bundle), result.requirements)
    attach_requirements_to_bundle(bundle, merged)
    save_project_bundle(bundle, bundle_dir, atomic=True)
    _write_requirements_sidecar(bundle_dir, merged)
    return result


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@require(_profile_is_supported, "profile must be a known requirement context profile")
@ensure(lambda result: isinstance(result, ValidationReport))
def validate_requirements_bundle(
    bundle_dir: Path, *, profile: RequirementContextValidationProfile = "startup"
) -> ValidationReport:
    """Validate requirement context evidence usefulness for a bundle."""
    bundle = _load_bundle_with_requirements(bundle_dir)
    return validate_requirement_context(bundle, profile=profile)


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@ensure(lambda result: isinstance(result, RequirementContextCoverageSummary))
def inspect_requirements_bundle_coverage(bundle_dir: Path) -> RequirementContextCoverageSummary:
    """Inspect coverage for normalized requirement inputs attached to a bundle."""
    bundle = _load_bundle_with_requirements(bundle_dir)
    return inspect_requirement_context_coverage(load_requirements_from_bundle(bundle))


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@ensure(_result_has_expected_keys)
def list_requirements_with_coverage(bundle_dir: Path, *, show_coverage: bool = False) -> dict[str, Any]:
    """Return serializable requirement rows and optional coverage summary."""
    bundle = _load_bundle_with_requirements(bundle_dir)
    requirements = load_requirements_from_bundle(bundle)
    payload: dict[str, Any] = {
        "requirements": [
            {
                "requirement_id": requirement.requirement_id,
                "title": requirement.title,
                "source_count": len(requirement.sources),
                "evidence_link_count": len(requirement.evidence_links),
            }
            for requirement in requirements
        ]
    }
    if show_coverage:
        payload["coverage"] = inspect_requirement_context_coverage(requirements).model_dump(mode="json")
    return payload
