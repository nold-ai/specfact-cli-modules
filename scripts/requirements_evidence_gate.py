"""Produce auditable Requirements evidence for changed OpenSpec sources."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml
from specfact_cli.common.bundle_factory import create_empty_project_bundle
from specfact_cli.utils.bundle_loader import save_project_bundle


SCHEMA_VERSION = "1"
EXECUTION_PROOF = "not-included"
EVIDENCE_SIDECAR_NAME = "requirements-evidence.yaml"
_requirements_runtime = import_module("specfact_requirements.requirements.runtime")
import_native_requirements_to_bundle = _requirements_runtime.import_native_requirements_to_bundle
import_requirements_file_to_bundle = _requirements_runtime.import_requirements_file_to_bundle
inspect_requirements_bundle_coverage = _requirements_runtime.inspect_requirements_bundle_coverage
requirements_gate_finding_counts = _requirements_runtime.requirements_gate_finding_counts
validate_requirements_bundle = _requirements_runtime.validate_requirements_bundle


def _model_payload(value: Any) -> dict[str, Any]:
    """Return a JSON-compatible mapping from a Pydantic-style report."""
    payload = value.model_dump(mode="json")
    return dict(payload)


def _diagnostic_payloads(diagnostics: Sequence[Any]) -> list[dict[str, Any]]:
    """Serialize importer diagnostics for the evidence report."""
    return [_model_payload(diagnostic) for diagnostic in diagnostics]


def _import_reasons(imported: int, diagnostics: Sequence[dict[str, Any]]) -> list[str]:
    """Return deterministic reasons for import-stage failures."""
    errors = [
        f"import-error:{diagnostic.get('code', 'unknown')}"
        for diagnostic in diagnostics
        if diagnostic.get("severity") == "error"
    ]
    return [*errors, *(["no-requirements-imported"] if imported == 0 else [])]


def _validation_reasons(validation: dict[str, Any] | None) -> list[str]:
    """Return the failure marker for a failed validation report."""
    return ["validation-failed"] if validation is not None and validation.get("status") == "failed" else []


def _coverage_reasons(coverage: dict[str, Any] | None) -> list[str]:
    """Return the failure marker for incomplete test-link coverage."""
    if coverage is None:
        return []
    total = int(coverage.get("total_requirements", 0))
    with_test_links = int(coverage.get("with_test_links", 0))
    return [f"test-link-coverage-incomplete:{with_test_links}/{total}"] if with_test_links < total else []


def _error_gate_reasons(validation: dict[str, Any] | None, finding_counts: dict[str, int]) -> list[str]:
    """Return only gate counts corresponding to error-level violations."""
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


def _source_reasons(
    imported: int,
    diagnostics: Sequence[dict[str, Any]],
    validation: dict[str, Any] | None,
    coverage: dict[str, Any] | None,
    finding_counts: dict[str, int],
) -> list[str]:
    """Return stable reasons that explain a source's failed verdict."""
    return [
        *_import_reasons(imported, diagnostics),
        *_validation_reasons(validation),
        *_coverage_reasons(coverage),
        *_error_gate_reasons(validation, finding_counts),
    ]


def _summary(source_reports: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Count source verdicts for the aggregate evidence report."""
    failed_sources = sum(source["verdict"] == "failed" for source in source_reports)
    passed_sources = sum(source["verdict"] == "passed" for source in source_reports)
    return {
        "failed_sources": failed_sources,
        "passed_sources": passed_sources,
        "skipped_sources": 0,
        "total_sources": len(source_reports),
    }


def _source_repository_root(source_path: Path) -> Path:
    """Return the repository root for a conventional OpenSpec change directory."""
    return source_path.parents[2]


def _test_target_path(repo_root: Path, target: str) -> Path:
    """Return the repository path component of a pytest-style test target."""
    return repo_root / target.split("::", maxsplit=1)[0]


def _is_repository_test_target(repo_root: Path, target: str) -> bool:
    """Return whether a relative test target resolves to a file inside ``repo_root``."""
    if Path(target).is_absolute():
        return False
    try:
        resolved_root = repo_root.resolve()
        resolved_target = _test_target_path(repo_root, target).resolve()
    except OSError:
        return False
    return resolved_target.is_relative_to(resolved_root) and resolved_target.is_file()


def _read_sidecar_requirements(sidecar_path: Path) -> dict[str, Any] | None:
    """Read the optional sidecar's requirement-to-test mapping."""
    try:
        payload = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        payload = {}
    return (
        payload["requirements"] if isinstance(payload, dict) and isinstance(payload.get("requirements"), dict) else None
    )


def _valid_test_targets(repo_root: Path, test_links: Any) -> tuple[list[str], list[str]]:
    """Separate repository-contained test targets from deterministic failures."""
    if (
        not isinstance(test_links, list)
        or not test_links
        or not all(isinstance(target, str) and target for target in test_links)
    ):
        return [], ["invalid"]
    valid_links = [target for target in test_links if _is_repository_test_target(repo_root, target)]
    missing_targets = [target for target in test_links if target not in valid_links]
    return valid_links, [f"evidence-sidecar-missing-test:{target}" for target in missing_targets]


def _sidecar_entry(
    requirement_id: object,
    entry: object,
    repo_root: Path,
    imported_requirement_ids: set[str],
) -> tuple[str | None, list[str], list[str]]:
    """Validate one sidecar requirement mapping and return its usable links."""
    if not isinstance(requirement_id, str) or not isinstance(entry, dict):
        return None, [], ["evidence-sidecar-invalid"]
    links, reasons = _valid_test_targets(repo_root, entry.get("test_links"))
    if reasons == ["invalid"]:
        return requirement_id, [], [f"evidence-sidecar-invalid-test-links:{requirement_id}"]
    if requirement_id not in imported_requirement_ids:
        reasons.insert(0, f"evidence-sidecar-unknown-requirement:{requirement_id}")
    return requirement_id, links, reasons


def _load_evidence_sidecar(
    source_path: Path,
    repo_root: Path,
    imported_requirement_ids: set[str],
) -> tuple[dict[str, list[str]], list[str]]:
    """Load valid requirement-to-test links from an optional source sidecar."""
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


def _apply_evidence_sidecar(source_path: Path, imported_requirements: Sequence[Any], bundle_dir: Path) -> list[str]:
    """Overlay declared test links into the disposable bundle only."""
    imported_requirement_ids = {str(requirement.requirement_id) for requirement in imported_requirements}
    links_by_requirement, reasons = _load_evidence_sidecar(
        source_path,
        _source_repository_root(source_path),
        imported_requirement_ids,
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


def _discover_changed_openspec_sources(repo_root: Path, base_ref: str) -> list[Path]:
    """Return existing active change directories that differ from ``base_ref``."""
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", base_ref) is None:
        msg = "base ref must be a non-option Git ref using alphanumeric, '.', '_', '/', or '-' characters"
        raise ValueError(msg)
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMRD",
            f"{base_ref}...HEAD",
            "--",
            "openspec/changes",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    change_roots: set[Path] = set()
    for changed_path in result.stdout.splitlines():
        parts = Path(changed_path).parts
        if len(parts) < 3 or parts[:2] != ("openspec", "changes") or parts[2] == "archive":
            continue
        candidate = repo_root / "openspec" / "changes" / parts[2]
        if candidate.is_dir():
            change_roots.add(candidate)
    return sorted(change_roots)


def _evaluate_sources(source_paths: Sequence[Path], *, bundle_parent: Path) -> dict[str, Any]:
    """Evaluate source validity and traceability using the Requirements runtime."""
    if not source_paths:
        return {
            "schema_version": SCHEMA_VERSION,
            "verdict": "skipped",
            "execution_proof": EXECUTION_PROOF,
            "sources": [],
            "summary": {"failed_sources": 0, "passed_sources": 0, "skipped_sources": 1, "total_sources": 0},
        }

    source_reports: list[dict[str, Any]] = []
    for index, source_path in enumerate(source_paths, start=1):
        bundle_dir = bundle_parent / f"requirements-evidence-{index}"
        save_project_bundle(create_empty_project_bundle(bundle_dir.name), bundle_dir, atomic=False)
        import_result = import_native_requirements_to_bundle("openspec", source_path, bundle_dir)
        diagnostics = _diagnostic_payloads(import_result.diagnostics)
        imported = len(import_result.requirements)
        validation: dict[str, Any] | None = None
        coverage: dict[str, Any] | None = None
        finding_counts: dict[str, int] = {}
        sidecar_reasons: list[str] = []
        if not any(diagnostic.get("severity") == "error" for diagnostic in diagnostics) and imported > 0:
            sidecar_reasons = _apply_evidence_sidecar(source_path, import_result.requirements, bundle_dir)
            if not sidecar_reasons:
                validation = _model_payload(validate_requirements_bundle(bundle_dir, profile="enterprise"))
                coverage = _model_payload(inspect_requirements_bundle_coverage(bundle_dir))
                finding_counts = dict(requirements_gate_finding_counts(bundle_dir, profile="enterprise"))
        reasons = [*sidecar_reasons, *_source_reasons(imported, diagnostics, validation, coverage, finding_counts)]
        source_reports.append(
            {
                "source": source_path.as_posix(),
                "verdict": "failed" if reasons else "passed",
                "reasons": reasons,
                "import": {"diagnostics": diagnostics, "imported": imported},
                "validation": validation,
                "coverage": coverage,
                "gate_finding_counts": finding_counts,
            }
        )

    summary = _summary(source_reports)
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": "failed" if summary["failed_sources"] else "passed",
        "execution_proof": EXECUTION_PROOF,
        "sources": source_reports,
        "summary": summary,
    }


def _write_evidence_report(report: dict[str, Any], output_path: Path) -> None:
    """Write the JSON report before the caller evaluates its exit status."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_summary(report: dict[str, Any], output_path: Path) -> None:
    """Write a concise CI summary without overstating the proof level."""
    summary = report["summary"]
    lines = [
        "## Requirements evidence",
        "",
        f"- Verdict: **{report['verdict']}**",
        f"- Sources: {summary['total_sources']} total; {summary['passed_sources']} passed; "
        f"{summary['failed_sources']} failed; {summary['skipped_sources']} skipped",
        "- Test-execution proof: not included (this gate validates requirement-source and linkage evidence).",
    ]
    for source in report["sources"]:
        if source["reasons"]:
            lines.append(f"- `{source['source']}`: {', '.join(source['reasons'])}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _gate_failure_report(error: Exception) -> dict[str, Any]:
    """Return schema-compatible failure evidence when evaluation cannot complete."""
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


def _run_evidence_gate(repo_root: Path, base_ref: str, output_path: Path, summary_path: Path | None = None) -> int:
    """Discover, evaluate, and persist evidence; return a CI-compatible status."""
    try:
        source_paths = _discover_changed_openspec_sources(repo_root, base_ref)
        with tempfile.TemporaryDirectory(prefix="specfact-requirements-evidence-") as raw_bundle_parent:
            report = _evaluate_sources(source_paths, bundle_parent=Path(raw_bundle_parent))
    except Exception as error:  # pylint: disable=broad-exception-caught
        # This CI boundary intentionally turns every ordinary evaluation error into retained evidence.
        report = _gate_failure_report(error)
    _write_evidence_report(report, output_path)
    if summary_path is not None:
        _write_markdown_summary(report, summary_path)
    return 1 if report["verdict"] == "failed" else 0


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for CI and local dogfooding runs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True, help="Git ref used as the branch-diff base.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root to inspect.")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON evidence artifact.")
    parser.add_argument("--summary", type=Path, help="Optional destination for a GitHub Actions Markdown summary.")
    return parser.parse_args()


def _main() -> int:
    """Execute the requirements evidence gate."""
    arguments = _parse_args()
    return _run_evidence_gate(arguments.repo_root.resolve(), arguments.base_ref, arguments.output, arguments.summary)


if __name__ == "__main__":
    raise SystemExit(_main())
