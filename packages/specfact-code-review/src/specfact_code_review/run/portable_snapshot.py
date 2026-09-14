"""Attach a validated local runtime to review without changing v1 PR authority."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from icontract import require

from specfact_code_review.run.portable_worker import DEPENDENT_MEMBERS, preparation_failure_snapshot, select_test_paths
from specfact_code_review.run.runtime_artifacts import load_runtime
from specfact_code_review.run.runtime_builder import prepare_runtime
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError, document_digest


@require(lambda root: root.is_dir())
def project_runtime_requested(root: Path, options: Any) -> bool:
    """Recognize declared project environments while preserving stdlib-only fixtures."""
    return bool(
        options.project_config
        or options.project_runtime
        or any(
            (root / name).exists()
            for name in (
                "pyproject.toml",
                "hatch.toml",
                "requirements.txt",
                "setup.py",
                "setup.cfg",
                "uv.lock",
                "poetry.lock",
            )
        )
    )


@require(lambda snapshot_root: snapshot_root.is_dir())
def run_project_snapshot(
    runtime: Any,
    *,
    snapshot_root: Path,
    files: list[Path],
    options: Any,
    assurance_kind: str,
) -> tuple[Any, dict[str, Any]]:
    """Prepare once, execute applicable members, and retain independent evidence."""
    from specfact_code_review.run.runner import CapsuleSnapshotSettings, _run_capsule_snapshot

    try:
        plan = discover_project(snapshot_root, config_path=options.project_config)
        prepared = (
            load_runtime(
                options.project_runtime,
                plan=plan,
                environment_id=runtime.environment_id,
                worker_identity=runtime.identity,
            )
            if options.project_runtime
            else prepare_runtime(plan, runtime=runtime)
        )
    except (OSError, ValueError) as exc:
        reason = str(exc)
        unavailable = preparation_failure_snapshot(reason)
        snapshot = _run_capsule_snapshot(
            runtime,
            snapshot_root=snapshot_root,
            files=files,
            options=options,
            settings=CapsuleSnapshotSettings(portable_runtime=True, unavailable_members=unavailable),
        )
        return snapshot, {
            "status": "UNKNOWN",
            "diagnostic": reason,
            "remedy": "Inspect project configuration with specfact code review runtime inspect --json, then run runtime prepare.",
        }
    evidence = {
        "status": "PASS",
        "schema": "project-runtime-layer-v2",
        "identity": prepared.identity,
        "project_identity": plan.identity,
        "environment_id": runtime.environment_id,
        "authority": "local_build",
        "protected_pr_eligible": False,
        "source_roots": list(plan.source_roots),
    }
    arguments: dict[str, tuple[str, ...]] = {
        "basedpyright": ("--pythonpath", "/opt/specfact/project-runtime/bin/python"),
    }
    conflicts = prepared.descriptor.get("inventory", {}).get("analyzer_conflicts", {})
    unavailable = {
        member: {"execution_state": "error", "evidence_outcome": "UNKNOWN", "diagnostic": reason}
        for member, reason in conflicts.items()
    }
    if not options.no_tests:
        try:
            selectors = select_test_paths(plan, files, full=assurance_kind == "full")
            arguments["targeted-pytest-coverage"] = ("portable-pytest-v2", json.dumps({"selectors": selectors}))
        except ProjectRuntimeError as exc:
            unavailable["targeted-pytest-coverage"] = {
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "diagnostic": str(exc),
            }
    bound = replace(
        runtime, identity=document_digest({"capsule": runtime.identity, "project_runtime": prepared.identity})
    )
    snapshot = _run_capsule_snapshot(
        bound,
        snapshot_root=snapshot_root,
        files=files,
        options=options,
        settings=CapsuleSnapshotSettings(
            project_runtime_root=prepared.root,
            member_argv=arguments,
            portable_runtime=True,
            unavailable_members=unavailable,
        ),
    )
    try:
        load_runtime(
            prepared.descriptor_path, plan=plan, environment_id=runtime.environment_id, worker_identity=runtime.identity
        )
    except ProjectRuntimeError as exc:
        for member in DEPENDENT_MEMBERS:
            snapshot.evidence[member].update(execution_state="error", evidence_outcome="UNKNOWN", diagnostic=str(exc))
        evidence.update(status="UNKNOWN", diagnostic=str(exc))
    return snapshot, evidence


@require(lambda scope_evidence: scope_evidence.get("assurance_kind") != "pr_range")
def run_project_scope_pair(resolution: Any, *, runtime: Any, options: Any, scope_evidence: dict[str, Any]) -> Any:
    """Resolve each immutable side separately; local provenance cannot authorize a PR."""
    from specfact_code_review.run.runner import _capsule_report, _classify_range_findings, _snapshot_python_files

    snapshots = (resolution.base_snapshot, resolution.head_snapshot)
    results = []
    bindings = {}
    for side, snapshot in zip(("base", "head"), snapshots, strict=True):
        side_options = replace(options, project_runtime=None) if side == "base" else options
        files = _snapshot_python_files(snapshot, resolution)
        if not files:
            files = [snapshot.root / path for path in sorted(snapshot.contents) if Path(path).suffix in {".py", ".pyi"}]
        result, binding = run_project_snapshot(
            runtime,
            snapshot_root=snapshot.root,
            files=files,
            options=side_options,
            assurance_kind="index" if scope_evidence.get("assurance_kind") == "index" else "range_preview",
        )
        results.append(result)
        bindings[side] = binding
    combined, findings = _classify_range_findings(resolution, results[0], results[1])
    evidence = {**scope_evidence, "project_runtime": bindings, "protected_pr_eligible": False}
    if evidence.get("assurance_kind") in {"range_candidate", "pr_range"}:
        evidence["assurance_kind"] = "range_preview"
    return _capsule_report(combined, findings, options=options, scope_evidence=evidence)
