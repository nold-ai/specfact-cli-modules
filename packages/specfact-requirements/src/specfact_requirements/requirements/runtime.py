"""Runtime helpers for requirements context commands."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import yaml
from beartype import beartype
from icontract import ensure, require
from specfact_cli.models.project import ProjectBundle
from specfact_cli.models.validation import ValidationReport
from specfact_cli.utils.bundle_loader import load_project_bundle, save_project_bundle


_LEGACY_REQUIREMENTS_INPUTS_FILE = "requirements.inputs.yaml"
_REQUIREMENTS_INPUTS_FILE = "inputs.yaml"
_REQUIREMENTS_INPUTS_DIR = "requirements"
_REQUIREMENTS_MODELS_MODULE = "specfact_cli.models.requirements"
_REQUIREMENTS_CONTEXT_MODULE = "specfact_cli.requirements.context"
KNOWN_REQUIREMENT_CONTEXT_PROFILES: frozenset[str] = frozenset(
    {
        "api-first-team",
        "solo",
        "solo-developer",
        "startup",
        "team",
        "enterprise",
        "enterprise-full-stack",
        "strict",
        "solo_developer",
        "api_first_team",
        "enterprise_full_stack",
    }
)


class RequirementsCoreUnavailableError(RuntimeError):
    """Raised when the paired core requirements helpers are unavailable."""


def _load_requirements_module(module_name: str, purpose: str) -> Any:
    try:
        return import_module(module_name)
    except ImportError as exc:
        msg = (
            f"specfact-requirements requires the paired specfact-cli {purpose} "
            "from core change requirements-02-module-commands"
        )
        raise RequirementsCoreUnavailableError(msg) from exc


def _records_are_supported(result: Sequence[Mapping[str, Any]]) -> bool:
    return all(isinstance(record, Mapping) for record in result)


def _result_has_expected_keys(result: dict[str, Any]) -> bool:
    return "requirements" in result


def _has_attributes(result: Any, *attributes: str) -> bool:
    return all(hasattr(result, attribute) for attribute in attributes)


def _profile_is_supported(profile: str) -> bool:
    return profile in KNOWN_REQUIREMENT_CONTEXT_PROFILES


@beartype
@require(lambda profile: bool(profile.strip()), "profile must be non-empty")
@ensure(lambda result: bool(result.strip()))
def normalize_requirement_context_profile(profile: str) -> str:
    """Return the core validator spelling for documented profile aliases."""
    return profile.replace("-", "_")


def _requirements_sidecar_path(bundle_dir: Path) -> Path:
    return bundle_dir / "reports" / _REQUIREMENTS_INPUTS_DIR / _REQUIREMENTS_INPUTS_FILE


def _legacy_requirements_sidecar_path(bundle_dir: Path) -> Path:
    return bundle_dir / _LEGACY_REQUIREMENTS_INPUTS_FILE


def _existing_requirements_sidecar_path(bundle_dir: Path) -> Path | None:
    for candidate in (_requirements_sidecar_path(bundle_dir), _legacy_requirements_sidecar_path(bundle_dir)):
        if candidate.exists():
            return candidate
    return None


def _load_bundle_with_requirements(bundle_dir: Path) -> ProjectBundle:
    bundle = load_project_bundle(bundle_dir)
    sidecar = _existing_requirements_sidecar_path(bundle_dir)
    if sidecar is None:
        return bundle
    payload = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{sidecar} must contain a requirements.inputs mapping payload"
        raise ValueError(msg)
    model_helpers = _load_requirements_module(_REQUIREMENTS_MODELS_MODULE, "requirements models")
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    records = model_helpers.load_requirements_input_extension(cast(dict[str, Any], payload))
    context_helpers.attach_requirements_to_bundle(bundle, records)
    return bundle


def _write_requirements_sidecar(bundle_dir: Path, records: Sequence[Any]) -> None:
    model_helpers = _load_requirements_module(_REQUIREMENTS_MODELS_MODULE, "requirements models")
    payload = model_helpers.requirements_input_extension_payload(list(records))
    sidecar = _requirements_sidecar_path(bundle_dir)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@beartype
@require(lambda source_file: source_file.is_file(), "source_file must exist")
@ensure(_records_are_supported, "all loaded records must be RequirementInput or mapping values")
def load_requirement_records(source_file: Path) -> list[Mapping[str, Any]]:
    """Load requirement records from a JSON or YAML source file."""
    loaded = yaml.safe_load(source_file.read_text(encoding="utf-8"))
    if loaded is None:
        return []
    if isinstance(loaded, list):
        return cast(list[Mapping[str, Any]], loaded)
    if isinstance(loaded, dict):
        maybe_records = loaded.get("requirements")
        if isinstance(maybe_records, list):
            return cast(list[Mapping[str, Any]], maybe_records)
        return [cast(Mapping[str, Any], loaded)]
    msg = "requirements source must be a mapping, a list, or a mapping with a requirements list"
    raise ValueError(msg)


@beartype
@require(lambda existing: all(hasattr(record, "requirement_id") for record in existing))
@require(lambda imported: all(hasattr(record, "requirement_id") for record in imported))
@ensure(lambda result: all(hasattr(record, "requirement_id") for record in result))
def merge_requirement_inputs(
    existing: Sequence[Any],
    imported: Sequence[Any],
) -> list[Any]:
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
@ensure(lambda result: _has_attributes(result, "requirements", "diagnostics"))
def import_requirements_file_to_bundle(source_file: Path, bundle_dir: Path) -> Any:
    """Normalize requirement records from a file and attach valid records to a ProjectBundle."""
    records = load_requirement_records(source_file)
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    result = context_helpers.normalize_requirement_records(records, source_locator=source_file.as_posix())
    bundle = _load_bundle_with_requirements(bundle_dir)
    merged = merge_requirement_inputs(context_helpers.load_requirements_from_bundle(bundle), result.requirements)
    context_helpers.attach_requirements_to_bundle(bundle, merged)
    save_project_bundle(bundle, bundle_dir, atomic=True)
    _write_requirements_sidecar(bundle_dir, merged)
    return result


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@require(_profile_is_supported, "profile must be a known requirement context profile")
@ensure(lambda result: isinstance(result, ValidationReport))
def validate_requirements_bundle(bundle_dir: Path, *, profile: str = "startup") -> ValidationReport:
    """Validate requirement context evidence usefulness for a bundle."""
    bundle = _load_bundle_with_requirements(bundle_dir)
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    return context_helpers.validate_requirement_context(bundle, profile=normalize_requirement_context_profile(profile))


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@ensure(lambda result: _has_attributes(result, "total_requirements", "with_test_links"))
def inspect_requirements_bundle_coverage(bundle_dir: Path) -> Any:
    """Inspect coverage for normalized requirement inputs attached to a bundle."""
    bundle = _load_bundle_with_requirements(bundle_dir)
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    return context_helpers.inspect_requirement_context_coverage(context_helpers.load_requirements_from_bundle(bundle))


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@ensure(_result_has_expected_keys)
def list_requirements_with_coverage(bundle_dir: Path, *, show_coverage: bool = False) -> dict[str, Any]:
    """Return serializable requirement rows and optional coverage summary."""
    bundle = _load_bundle_with_requirements(bundle_dir)
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    requirements = context_helpers.load_requirements_from_bundle(bundle)
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
        payload["coverage"] = context_helpers.inspect_requirement_context_coverage(requirements).model_dump(mode="json")
    return payload
