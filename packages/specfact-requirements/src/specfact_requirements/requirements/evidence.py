"""Reusable Requirements evidence evaluation and report persistence."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict, Unpack

import yaml
from beartype import beartype
from icontract import ensure
from specfact_cli.common.bundle_factory import create_empty_project_bundle
from specfact_cli.utils.bundle_loader import save_project_bundle

from specfact_requirements.requirements.lifecycle import (
    MATURITY_ORDER,
    SUPPORTED_REQUIRED_MATURITY,
    evaluate_mapping,
    lifecycle_status,
)
from specfact_requirements.requirements.runtime import (
    import_native_requirements_to_bundle,
    import_requirements_file_to_bundle,
    inspect_requirements_bundle_coverage,
    requirements_gate_finding_counts,
    validate_requirements_bundle,
)


SCHEMA_VERSION = "1"
EXECUTION_PROOF = "not-included"
EVIDENCE_SIDECAR_NAME = "requirements-evidence.yaml"


def _model_payload(value: Any) -> dict[str, Any]:
    return dict(value.model_dump(mode="json"))


def _diagnostic_payloads(diagnostics: Sequence[Any]) -> list[dict[str, Any]]:
    return [_model_payload(diagnostic) for diagnostic in diagnostics]


def _source_reasons(
    imported: int,
    diagnostics: Sequence[dict[str, Any]],
    validation: dict[str, Any] | None,
    coverage: dict[str, Any] | None,
    finding_counts: dict[str, int],
) -> list[str]:
    return [
        *_import_reasons(imported, diagnostics),
        *_validation_reasons(validation),
        *_coverage_reasons(coverage),
        *_error_gate_reasons(validation, finding_counts),
    ]


def _import_reasons(imported: int, diagnostics: Sequence[dict[str, Any]]) -> list[str]:
    reasons = [
        f"import-error:{diagnostic.get('code', 'unknown')}"
        for diagnostic in diagnostics
        if diagnostic.get("severity") == "error"
    ]
    if imported == 0:
        reasons.append("no-requirements-imported")
    return reasons


def _validation_reasons(validation: dict[str, Any] | None) -> list[str]:
    return ["validation-failed"] if validation is not None and validation.get("status") == "failed" else []


def _coverage_reasons(coverage: dict[str, Any] | None) -> list[str]:
    if coverage is None:
        return []
    total = int(coverage.get("total_requirements", 0))
    linked = int(coverage.get("with_test_links", 0))
    return [f"test-link-coverage-incomplete:{linked}/{total}"] if linked < total else []


def _error_gate_reasons(validation: dict[str, Any] | None, finding_counts: dict[str, int]) -> list[str]:
    violations = validation.get("violations", []) if validation is not None else []
    error_codes = {
        str(violation.get("code"))
        for violation in violations
        if isinstance(violation, dict) and violation.get("severity") == "error" and violation.get("code")
    }
    return [
        f"gate-finding:{name}={count}"
        for name, count in sorted(finding_counts.items())
        if count > 0 and name in error_codes
    ]


def _source_repository_root(source_path: Path) -> Path:
    for ancestor in source_path.parents:
        if ancestor.name == "openspec":
            return ancestor.parent
    raise ValueError("Requirements evidence source is not contained in an OpenSpec repository")


def _test_target_path(repo_root: Path, target: str) -> Path:
    return repo_root / target.split("::", maxsplit=1)[0]


def _is_repository_test_target(repo_root: Path, target: str) -> bool:
    if Path(target).is_absolute():
        return False
    try:
        resolved_root = repo_root.resolve()
        resolved_target = _test_target_path(repo_root, target).resolve()
    except OSError:
        return False
    return resolved_target.is_relative_to(resolved_root) and resolved_target.is_file()


def _read_sidecar_requirements(sidecar_path: Path) -> dict[str, Any] | None:
    try:
        payload = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        payload = {}
    return (
        payload["requirements"] if isinstance(payload, dict) and isinstance(payload.get("requirements"), dict) else None
    )


def _valid_test_targets(repo_root: Path, test_links: Any) -> tuple[list[str], list[str]]:
    if (
        not isinstance(test_links, list)
        or not test_links
        or not all(isinstance(target, str) and target for target in test_links)
    ):
        return [], ["invalid"]
    valid_links = [target for target in test_links if _is_repository_test_target(repo_root, target)]
    return valid_links, [
        f"evidence-sidecar-missing-test:{target}" for target in test_links if target not in valid_links
    ]


def _sidecar_entry(
    requirement_id: object, entry: object, repo_root: Path, imported_requirement_ids: set[str]
) -> tuple[str | None, list[str], list[str]]:
    if not isinstance(requirement_id, str) or not isinstance(entry, dict):
        return None, [], ["evidence-sidecar-invalid"]
    links, reasons = _valid_test_targets(repo_root, entry.get("test_links"))
    if reasons == ["invalid"]:
        return requirement_id, [], [f"evidence-sidecar-invalid-test-links:{requirement_id}"]
    if requirement_id not in imported_requirement_ids:
        reasons.insert(0, f"evidence-sidecar-unknown-requirement:{requirement_id}")
    return requirement_id, links, reasons


def _load_evidence_sidecar(
    source_path: Path, repo_root: Path, imported_requirement_ids: set[str]
) -> tuple[dict[str, list[str]], list[str]]:
    sidecar_path = source_path / EVIDENCE_SIDECAR_NAME
    if not sidecar_path.is_file():
        return {}, []
    requirements = _read_sidecar_requirements(sidecar_path)
    if requirements is None:
        return {}, ["evidence-sidecar-invalid"]
    links_by_requirement: dict[str, list[str]] = {}
    reasons: list[str] = []
    for requirement_id, entry in sorted(requirements.items(), key=lambda item: str(item[0])):
        key, links, entry_reasons = _sidecar_entry(requirement_id, entry, repo_root, imported_requirement_ids)
        reasons.extend(entry_reasons)
        if key is not None and links:
            links_by_requirement[key] = links
    return links_by_requirement, reasons


def _apply_evidence_sidecar(
    source_path: Path, imported_requirements: Sequence[Any], bundle_dir: Path, *, repository_root: Path | None = None
) -> list[str]:
    imported_ids = {str(requirement.requirement_id) for requirement in imported_requirements}
    links_by_requirement, reasons = _load_evidence_sidecar(
        source_path, repository_root or _source_repository_root(source_path), imported_ids
    )
    if reasons or not links_by_requirement:
        return reasons
    records: list[dict[str, Any]] = []
    for requirement in imported_requirements:
        record = _model_payload(requirement)
        test_links = links_by_requirement.get(str(requirement.requirement_id), [])
        if test_links:
            record["evidence_links"] = [
                *list(record.get("evidence_links", [])),
                *({"link_type": "test", "target": target} for target in test_links),
            ]
        records.append(record)
    overlay_path = bundle_dir / ".requirements-evidence-overlay.json"
    overlay_path.write_text(json.dumps({"requirements": records}), encoding="utf-8")
    try:
        import_requirements_file_to_bundle(overlay_path, bundle_dir)
    finally:
        overlay_path.unlink(missing_ok=True)
    return []


@contextmanager
def _source_path_for_import(source_path: Path) -> Generator[Path, None, None]:
    """Expose an archived change under its stable change id for core importers."""
    if source_path.parent.name != "archive":
        yield source_path
        return
    match = re.fullmatch(r"\d{4}-\d{2}-\d{2}-(.+)", source_path.name)
    if match is None:
        raise ValueError("OpenSpec archive source does not have a date-prefixed stable change id")
    with tempfile.TemporaryDirectory(prefix="specfact-requirements-archived-source-") as raw_root:
        import_root = Path(raw_root) / "openspec" / "changes" / match.group(1)
        import_root.parent.mkdir(parents=True)
        shutil.copytree(source_path, import_root)
        yield import_root


def _changed_change_roots(changed_paths: Sequence[str]) -> list[Path]:
    roots: set[Path] = set()
    for changed_path in changed_paths:
        parts = Path(changed_path).parts
        if len(parts) >= 3 and parts[:2] == ("openspec", "changes") and parts[2] != "archive":
            roots.add(Path(*parts[:3]))
    return sorted(roots)


def _git_changed_paths(repo_root: Path, arguments: list[str]) -> list[str]:
    result = subprocess.run(arguments, cwd=repo_root, check=True, capture_output=True, text=True)
    return result.stdout.splitlines()


def _discover_changed_openspec_sources(repo_root: Path, base_ref: str) -> list[Path]:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", base_ref) is None:
        raise ValueError("base ref must be a non-option Git ref using alphanumeric, '.', '_', '/', or '-' characters")
    roots = _changed_change_roots(
        _git_changed_paths(
            repo_root,
            ["git", "diff", "--name-only", "--diff-filter=ACMRD", f"{base_ref}...HEAD", "--", "openspec/changes"],
        )
    )
    return [repo_root / root for root in roots if (repo_root / root).is_dir()]


def _discover_staged_openspec_source_relatives(repo_root: Path) -> list[Path]:
    return _changed_change_roots(
        _git_changed_paths(
            repo_root, ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD", "--", "openspec/changes"]
        )
    )


def _safe_extract_git_archive(archive_contents: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive_contents), mode="r:") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Git index archive contains an unsafe member path")
        archive.extractall(destination, filter="data")


@contextmanager
def _materialize_git_index_snapshot(repo_root: Path) -> Generator[Path, None, None]:
    tree = _git_changed_paths(repo_root, ["git", "write-tree"])
    if len(tree) != 1 or not re.fullmatch(r"[0-9a-f]{40,64}", tree[0]):
        raise ValueError("Git index tree could not be materialized")
    archive = subprocess.run(
        ["git", "archive", "--format=tar", tree[0]], cwd=repo_root, check=True, capture_output=True
    ).stdout
    with tempfile.TemporaryDirectory(prefix="specfact-requirements-index-") as raw_snapshot:
        snapshot_root = Path(raw_snapshot)
        _safe_extract_git_archive(archive, snapshot_root)
        yield snapshot_root


def _skipped_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "skipped",
        "execution_proof": EXECUTION_PROOF,
        "sources": [],
        "summary": {"failed_sources": 0, "passed_sources": 0, "skipped_sources": 1, "total_sources": 0},
    }


def _read_optional_mapping(path: Path) -> dict[str, Any]:
    """Read one optional YAML mapping; callers turn unreadable input into a finding."""
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _read_review_evidence(path: Path | None) -> Mapping[str, Any] | None:
    """Return an optional provider-neutral review record without executing a provider."""
    return _read_optional_mapping(path) if path is not None else None


def _digest_mapping(value: Mapping[str, Any]) -> str:
    """Return the same canonical SHA-256 format used by lifecycle reports."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _normalized_source_plan(source: object) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Return a source identity and its fully preserved cases when valid."""
    if not isinstance(source, Mapping) or not isinstance(source.get("plan"), Mapping):
        return None
    plan = source["plan"]
    if not isinstance(plan.get("cases"), list) or not isinstance(plan.get("mapping_digest"), str):
        return None
    source_name = str(source.get("source", ""))
    cases = [{"source": source_name, **dict(case)} for case in plan["cases"] if isinstance(case, Mapping)]
    if len(cases) != len(plan["cases"]):
        return None
    return {"source": source_name, "mapping_digest": plan["mapping_digest"]}, cases


def _normalized_plan_inputs(sources: list[object]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    """Collect deterministic source identities and case records for one plan."""
    normalized = [_normalized_source_plan(source) for source in sources]
    if any(source is None for source in normalized):
        return None
    source_plans = [source[0] for source in normalized if source is not None]
    cases = [case for source in normalized if source is not None for case in source[1]]
    if not source_plans or not cases:
        return None
    return source_plans, cases


def _normalized_plan_report(report: Mapping[str, Any]) -> dict[str, Any] | None:
    """Build one deterministic plan artifact from passing lifecycle source reports."""
    if report.get("gate_decision") != "pass" or not isinstance(report.get("sources"), list):
        return None
    inputs = _normalized_plan_inputs(
        sorted(report["sources"], key=lambda item: str(item.get("source")) if isinstance(item, Mapping) else "")
    )
    if inputs is None:
        return None
    source_plans, cases = inputs
    identity = {"sources": source_plans, "cases": cases}
    mapping_digest = _digest_mapping({"sources": source_plans})
    plan = {
        "mapping_digest": mapping_digest,
        "cases": cases,
        "plan_digest": _digest_mapping({"mapping_digest": mapping_digest, "cases": cases}),
    }
    return {
        "schema_version": "2",
        "verdict": report["verdict"],
        "gate_decision": report["gate_decision"],
        "required_maturity": report["required_maturity"],
        "observed_maturity": report["observed_maturity"],
        "mapping_digest": mapping_digest,
        "plan": plan,
        "sources": source_plans,
        "plan_identity_digest": _digest_mapping(identity),
    }


def _lifecycle_report(
    source_paths: Sequence[Path],
    *,
    required_maturity: str,
    review_evidence: Mapping[str, Any] | None,
    source_labels: Mapping[Path, Path] | None = None,
) -> dict[str, Any]:
    """Evaluate sidecar mappings without claiming test execution."""
    if not source_paths:
        report = _skipped_report()
        report.update(
            {
                "schema_version": "2",
                "gate_decision": "pass",
                "required_maturity": required_maturity,
                "observed_maturity": "no-impact",
                "delivery_status": "no-impact",
                "implementation_evidence": "not-applicable",
            }
        )
        return report
    labels = source_labels or {}
    sources: list[dict[str, Any]] = []
    for source_path in source_paths:
        lifecycle = evaluate_mapping(
            _read_optional_mapping(source_path / EVIDENCE_SIDECAR_NAME),
            required_maturity=required_maturity,
            review_evidence=review_evidence,
        )
        sources.append({"source": labels.get(source_path, source_path).as_posix(), **lifecycle})
    failed_sources = sum(source["gate_decision"] == "fail" for source in sources)
    observed = min(
        (source["observed_maturity"] for source in sources),
        key=lambda maturity: MATURITY_ORDER.get(maturity, -1),
    )
    delivery_status, implementation_evidence = lifecycle_status(observed)
    return {
        "schema_version": "2",
        "verdict": "failed" if failed_sources else "passed",
        "gate_decision": "fail" if failed_sources else "pass",
        "required_maturity": required_maturity,
        "observed_maturity": observed,
        "delivery_status": delivery_status,
        "implementation_evidence": implementation_evidence,
        "sources": sources,
        "summary": {
            "failed_sources": failed_sources,
            "passed_sources": len(sources) - failed_sources,
            "skipped_sources": 0,
            "total_sources": len(sources),
        },
    }


def _evaluate_imported_source(
    source_path: Path,
    import_source: Path,
    import_result: Any,
    bundle_dir: Path,
) -> tuple[list[dict[str, Any]], int, dict[str, Any] | None, dict[str, Any] | None, dict[str, int], list[str]]:
    diagnostics = _diagnostic_payloads(import_result.diagnostics)
    imported = len(import_result.requirements)
    if any(diagnostic.get("severity") == "error" for diagnostic in diagnostics) or imported == 0:
        return diagnostics, imported, None, None, {}, []
    sidecar_reasons = _apply_evidence_sidecar(
        import_source,
        import_result.requirements,
        bundle_dir,
        repository_root=_source_repository_root(source_path),
    )
    if sidecar_reasons:
        return diagnostics, imported, None, None, {}, sidecar_reasons
    validation = _model_payload(validate_requirements_bundle(bundle_dir, profile="enterprise"))
    coverage = _model_payload(inspect_requirements_bundle_coverage(bundle_dir))
    finding_counts = dict(requirements_gate_finding_counts(bundle_dir, profile="enterprise"))
    return diagnostics, imported, validation, coverage, finding_counts, []


def _source_report(source_path: Path, bundle_dir: Path, source_label: Path) -> dict[str, Any]:
    save_project_bundle(create_empty_project_bundle(bundle_dir.name), bundle_dir, atomic=False)
    with _source_path_for_import(source_path) as import_source:
        import_result = import_native_requirements_to_bundle("openspec", import_source, bundle_dir)
        diagnostics, imported, validation, coverage, finding_counts, sidecar_reasons = _evaluate_imported_source(
            source_path, import_source, import_result, bundle_dir
        )
    reasons = [*sidecar_reasons, *_source_reasons(imported, diagnostics, validation, coverage, finding_counts)]
    return {
        "source": source_label.as_posix(),
        "verdict": "failed" if reasons else "passed",
        "reasons": reasons,
        "import": {"diagnostics": diagnostics, "imported": imported},
        "validation": validation,
        "coverage": coverage,
        "gate_finding_counts": finding_counts,
    }


def _evaluate_sources(
    source_paths: Sequence[Path], *, bundle_parent: Path, source_labels: Mapping[Path, Path] | None = None
) -> dict[str, Any]:
    if not source_paths:
        return _skipped_report()
    labels = source_labels or {}
    source_reports = [
        _source_report(
            source_path, bundle_parent / f"requirements-evidence-{index}", labels.get(source_path, source_path)
        )
        for index, source_path in enumerate(source_paths, start=1)
    ]
    failed_sources = sum(source["verdict"] == "failed" for source in source_reports)
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "failed" if failed_sources else "passed",
        "execution_proof": EXECUTION_PROOF,
        "sources": source_reports,
        "summary": {
            "failed_sources": failed_sources,
            "passed_sources": len(source_reports) - failed_sources,
            "skipped_sources": 0,
            "total_sources": len(source_reports),
        },
    }


@beartype
@ensure(lambda result: isinstance(result, dict))
def evaluate_requirements_evidence(
    repo_root: Path,
    *,
    base_ref: str | None = None,
    staged: bool = False,
    required_maturity: str | None = None,
    review_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate changed native requirements without running their verification."""
    if (base_ref is None) != staged:
        raise ValueError("choose exactly one of --base-ref or --staged")
    if required_maturity is not None and required_maturity not in SUPPORTED_REQUIRED_MATURITY:
        raise ValueError("required maturity must be planned, accepted, test-authored, red, or verified")
    if base_ref is not None:
        sources = _discover_changed_openspec_sources(repo_root, base_ref)
        if required_maturity is not None:
            return _lifecycle_report(sources, required_maturity=required_maturity, review_evidence=review_evidence)
        with tempfile.TemporaryDirectory(prefix="specfact-requirements-evidence-") as bundle_parent:
            return _evaluate_sources(sources, bundle_parent=Path(bundle_parent))
    relative_sources = _discover_staged_openspec_source_relatives(repo_root)
    with _materialize_git_index_snapshot(repo_root) as snapshot_root:
        snapshot_sources = [snapshot_root / source for source in relative_sources if (snapshot_root / source).is_dir()]
        labels = {
            snapshot_root / source: repo_root / source
            for source in relative_sources
            if (snapshot_root / source).is_dir()
        }
        if required_maturity is not None:
            return _lifecycle_report(
                snapshot_sources,
                required_maturity=required_maturity,
                review_evidence=review_evidence,
                source_labels=labels,
            )
        with tempfile.TemporaryDirectory(prefix="specfact-requirements-evidence-") as bundle_parent:
            return _evaluate_sources(snapshot_sources, bundle_parent=Path(bundle_parent), source_labels=labels)


def _gate_failure_report(error: Exception) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "failed",
        "execution_proof": EXECUTION_PROOF,
        "sources": [
            {
                "source": "<gate>",
                "verdict": "failed",
                "reasons": [f"gate-exception:{type(error).__name__}"],
                "import": {"diagnostics": [], "imported": 0},
                "validation": None,
                "coverage": None,
                "gate_finding_counts": {},
            }
        ],
        "summary": {"failed_sources": 1, "passed_sources": 0, "skipped_sources": 0, "total_sources": 1},
    }


def _write_evidence_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_summary(report: dict[str, Any], output_path: Path) -> None:
    summary = report["summary"]
    source_summary = (
        f"{summary['total_sources']} total; {summary['passed_sources']} passed; "
        f"{summary['failed_sources']} failed; {summary['skipped_sources']} skipped"
    )
    lifecycle_report = "gate_decision" in report
    lines = [
        "## Requirements evidence",
        "",
        f"- Verdict: **{report['verdict']}**",
        f"- Sources: {source_summary}",
    ]
    if lifecycle_report:
        lines.extend(
            [
                f"- Gate decision: **{report['gate_decision']}**",
                f"- Required maturity: `{report['required_maturity']}`",
                f"- Observed maturity: `{report['observed_maturity']}`",
                f"- Implementation evidence: `{report['implementation_evidence']}`",
            ]
        )
    else:
        lines.append(
            "- Test-execution proof: not included (this gate validates requirement-source and linkage evidence)."
        )
    lines.extend(
        f"- `{source['source']}`: {', '.join(source.get('reasons', source.get('findings', [])))}"
        for source in report["sources"]
        if source.get("reasons", source.get("findings", []))
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _evidence_destinations_alias(output_path: Path, summary_path: Path) -> bool:
    """Return whether report destinations resolve or refer to the same file."""
    if output_path.resolve() == summary_path.resolve():
        return True
    try:
        return output_path.exists() and summary_path.exists() and output_path.samefile(summary_path)
    except OSError:
        return False


@dataclass(frozen=True)
class RequirementsEvidenceRequest:
    """Explicit destinations and selection inputs for one evidence report."""

    repo_root: Path
    output_path: Path
    summary_path: Path | None = None
    base_ref: str | None = None
    staged: bool = False
    required_maturity: str | None = None
    review_evidence_path: Path | None = None
    plan_output_path: Path | None = None


class _LegacyEvidenceOptions(TypedDict, total=False):
    """Typed keyword compatibility surface for legacy Python callers."""

    summary_path: Path | None
    base_ref: str | None
    staged: bool
    required_maturity: str | None
    review_evidence_path: Path | None
    plan_output_path: Path | None


def _legacy_request(
    repo_root: Path, output_path: Path, positional: tuple[Any, ...], options: Mapping[str, Any]
) -> RequirementsEvidenceRequest:
    if len(positional) > 1:
        raise TypeError("write_requirements_evidence accepts at most one positional summary path")
    supported = {"summary_path", "base_ref", "staged", "required_maturity", "review_evidence_path", "plan_output_path"}
    unexpected = sorted(set(options).difference(supported))
    if unexpected:
        raise TypeError(f"unexpected write_requirements_evidence option: {unexpected[0]}")
    summary_path = positional[0] if positional else options.get("summary_path")
    return RequirementsEvidenceRequest(
        repo_root=repo_root,
        output_path=output_path,
        summary_path=summary_path,
        base_ref=options.get("base_ref"),
        staged=bool(options.get("staged", False)),
        required_maturity=options.get("required_maturity"),
        review_evidence_path=options.get("review_evidence_path"),
        plan_output_path=options.get("plan_output_path"),
    )


def _write_requirements_evidence(request: RequirementsEvidenceRequest) -> int:
    if request.summary_path is not None and _evidence_destinations_alias(request.output_path, request.summary_path):
        raise ValueError("output and summary paths must resolve to different destinations")
    try:
        report = evaluate_requirements_evidence(
            request.repo_root,
            base_ref=request.base_ref,
            staged=request.staged,
            required_maturity=request.required_maturity,
            review_evidence=_read_review_evidence(request.review_evidence_path),
        )
    except Exception as error:  # pylint: disable=broad-exception-caught
        report = _gate_failure_report(error)
    _write_evidence_report(report, request.output_path)
    if request.plan_output_path is not None and request.required_maturity is not None:
        normalized_plan = _normalized_plan_report(report)
        if normalized_plan is not None:
            _write_evidence_report(normalized_plan, request.plan_output_path)
    if request.summary_path is not None:
        _write_markdown_summary(report, request.summary_path)
    return 1 if report["verdict"] == "failed" else 0


@beartype
@ensure(lambda result: result in {0, 1})
def write_requirements_evidence(
    repo_root: Path, output_path: Path, *positional: Path, **options: Unpack[_LegacyEvidenceOptions]
) -> int:
    """Write evidence while preserving the v1 Python call convention."""
    return _write_requirements_evidence(_legacy_request(repo_root, output_path, positional, options))
