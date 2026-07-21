"""Runtime helpers for requirements context commands."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any, cast, get_args

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
_REQUIREMENTS_PUBLIC_MODULE = "specfact_cli.requirements"
_NATIVE_IMPORT_HELPERS = {
    "openspec": "import_openspec_change",
    "speckit": "import_speckit_feature",
}


class RequirementsCoreUnavailableError(RuntimeError):
    """Raised when the paired core requirements helpers are unavailable."""


def _load_requirements_module(module_name: str, purpose: str) -> Any:
    try:
        return import_module(module_name)
    except ImportError as exc:
        msg = (
            f"specfact-requirements requires the paired specfact-cli {purpose} "
            "from core change #350 (specfact-cli >=0.52.0)"
        )
        raise RequirementsCoreUnavailableError(msg) from exc


def _records_are_supported(result: Sequence[Mapping[str, Any]]) -> bool:
    return all(isinstance(record, Mapping) for record in result)


def _result_has_expected_keys(result: dict[str, Any]) -> bool:
    return "requirements" in result


def _has_attributes(result: Any, *attributes: str) -> bool:
    return all(hasattr(result, attribute) for attribute in attributes)


def _diagnostic_is_error(diagnostic: Any) -> bool:
    return str(getattr(diagnostic, "severity", "")) == "error"


@beartype
@require(
    lambda import_result: all(hasattr(import_result, attribute) for attribute in ("requirements", "diagnostics")),
    "import_result must expose requirements and diagnostics",
)
@ensure(lambda result: isinstance(result, bool))
def import_result_has_errors(import_result: Any) -> bool:
    """Return whether a core import result contains an error diagnostic."""
    return any(_diagnostic_is_error(diagnostic) for diagnostic in import_result.diagnostics)


def _core_import_helper(helper_name: str) -> Any:
    core_requirements = _load_requirements_module(_REQUIREMENTS_PUBLIC_MODULE, "native requirement import helpers")
    helper = getattr(core_requirements, helper_name, None)
    if callable(helper):
        return helper
    msg = f"specfact-requirements requires specfact-cli >=0.52.0; missing core helper '{helper_name}' from change #350"
    raise RequirementsCoreUnavailableError(msg)


def _openspec_project_root(change_dir: Path) -> Path | None:
    """Return the repository root for a conventionally located OpenSpec change."""
    changes_dir = change_dir.parent
    openspec_dir = changes_dir.parent
    if changes_dir.name == "changes" and openspec_dir.name == "openspec":
        return openspec_dir.parent
    return None


def _profile_aliases(profiles: frozenset[str]) -> frozenset[str]:
    aliases = set(profiles)
    aliases.update(profile.replace("_", "-") for profile in profiles)
    aliases.update(profile.replace("-", "_") for profile in profiles)
    return frozenset(aliases)


def _known_requirement_context_profiles() -> frozenset[str]:
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    known_profiles = getattr(context_helpers, "KNOWN_REQUIREMENT_CONTEXT_PROFILES", None)
    if known_profiles is None:
        profile_type = context_helpers.RequirementContextValidationProfile
        known_profiles = get_args(profile_type)
    return _profile_aliases(frozenset(str(profile) for profile in known_profiles))


@beartype
@require(lambda profile: bool(profile.strip()), "profile must be non-empty")
@ensure(lambda result: bool(result.strip()))
def normalize_requirement_context_profile(profile: str) -> str:
    """Return the core validator spelling for documented profile aliases."""
    return profile.replace("-", "_")


@beartype
@require(lambda profile: bool(profile.strip()), "profile must be non-empty")
@ensure(lambda result: isinstance(result, bool))
def is_requirement_context_profile_supported(profile: str) -> bool:
    """Return whether the paired core validator exposes this profile."""
    normalized = normalize_requirement_context_profile(profile)
    return normalized in {
        normalize_requirement_context_profile(candidate) for candidate in _known_requirement_context_profiles()
    }


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
    temporary_sidecar = sidecar.with_name(f".{sidecar.name}.tmp")
    try:
        temporary_sidecar.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        temporary_sidecar.replace(sidecar)
    finally:
        if temporary_sidecar.exists():
            temporary_sidecar.unlink()


def _persist_imported_requirements(bundle_dir: Path, imported: Sequence[Any]) -> None:
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    bundle = _load_bundle_with_requirements(bundle_dir)
    merged = merge_requirement_inputs(context_helpers.load_requirements_from_bundle(bundle), imported)
    context_helpers.attach_requirements_to_bundle(bundle, merged)
    save_project_bundle(bundle, bundle_dir, atomic=True)
    _write_requirements_sidecar(bundle_dir, merged)


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
    _persist_imported_requirements(bundle_dir, result.requirements)
    return result


@beartype
@require(lambda source_kind: source_kind in _NATIVE_IMPORT_HELPERS, "source_kind must be openspec or speckit")
@require(lambda source_dir: source_dir.is_dir(), "source_dir must exist")
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@ensure(lambda result: _has_attributes(result, "requirements", "diagnostics"))
def import_native_requirements_to_bundle(source_kind: str, source_dir: Path, bundle_dir: Path) -> Any:
    """Delegate a native source import to core and persist only valid records."""
    import_helper = _core_import_helper(_NATIVE_IMPORT_HELPERS[source_kind])
    project_root = _openspec_project_root(source_dir) if source_kind == "openspec" else None
    result = import_helper(source_dir, project_root=project_root) if project_root else import_helper(source_dir)
    if not import_result_has_errors(result):
        _persist_imported_requirements(bundle_dir, result.requirements)
    return result


def _sole_source(candidates: list[Path], expected_layout: str) -> Path:
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(f"No import source found; expected {expected_layout}.")
    names = ", ".join(candidate.name for candidate in candidates)
    raise ValueError(f"Multiple import sources found ({names}); pass an explicit path instead of {expected_layout}.")


@beartype
@require(lambda project_root: project_root.is_dir(), "project_root must exist")
@ensure(lambda result: result.is_dir())
def auto_detect_openspec_change(project_root: Path) -> Path:
    """Return the single conventional OpenSpec change source below a project root."""
    changes_dir = project_root / "openspec" / "changes"
    candidates = (
        [path for path in sorted(changes_dir.iterdir()) if path.is_dir() and path.name != "archive"]
        if changes_dir.is_dir()
        else []
    )
    return _sole_source(candidates, "openspec/changes/")


@beartype
@require(lambda project_root: project_root.is_dir(), "project_root must exist")
@ensure(lambda result: result.is_dir())
def auto_detect_speckit_feature(project_root: Path) -> Path:
    """Return the single conventional Spec Kit feature source below a project root."""
    specs_dir = project_root / "specs"
    candidates = (
        [path for path in sorted(specs_dir.iterdir()) if path.is_dir() and (path / "spec.md").is_file()]
        if specs_dir.is_dir()
        else []
    )
    return _sole_source(candidates, "specs/<feature>/")


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@require(
    lambda profile: profile is None or is_requirement_context_profile_supported(profile),
    "profile must be a known requirement context profile when provided",
)
@ensure(lambda result: isinstance(result, ValidationReport))
def validate_requirements_bundle(bundle_dir: Path, *, profile: str | None = None) -> ValidationReport:
    """Validate requirement context evidence usefulness for a bundle."""
    bundle = _load_bundle_with_requirements(bundle_dir)
    context_helpers = _load_requirements_module(_REQUIREMENTS_CONTEXT_MODULE, "requirements context helpers")
    normalized_profile = normalize_requirement_context_profile(profile) if profile is not None else None
    return context_helpers.validate_requirement_context(bundle, profile=normalized_profile, project_root=Path.cwd())


@beartype
@require(lambda bundle_dir: bundle_dir.is_dir(), "bundle_dir must exist")
@require(
    lambda profile: profile is None or is_requirement_context_profile_supported(profile),
    "profile must be a known requirement context profile when provided",
)
@ensure(lambda result: all(isinstance(code, str) and isinstance(count, int) for code, count in result.items()))
def requirements_gate_finding_counts(bundle_dir: Path, *, profile: str | None = None) -> dict[str, int]:
    """Count core validation findings without reimplementing their gate logic."""
    report = validate_requirements_bundle(bundle_dir, profile=profile)
    counts: dict[str, int] = {}
    for violation in report.violations:
        code = violation.get("code")
        if isinstance(code, str):
            counts[code] = counts.get(code, 0) + 1
    return counts


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
        payload["gate_finding_counts"] = requirements_gate_finding_counts(bundle_dir)
    return payload
