"""Attach a validated local runtime to review without changing v1 PR authority."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from icontract import require

from specfact_code_review.run.portable_worker import DEPENDENT_MEMBERS, preparation_failure_snapshot, select_test_paths
from specfact_code_review.run.runtime_artifacts import load_runtime
from specfact_code_review.run.runtime_builder import copy_project, prepare_runtime
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_interpreter import project_worker
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError, document_digest
from specfact_code_review.run.runtime_sources import verify_inputs
from specfact_code_review.run.runtime_vcs import vcs_context


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
                "requirements.in",
                "pylock.toml",
                "setup.py",
                "setup.cfg",
                "uv.lock",
                "poetry.lock",
            )
        )
    )


@require(lambda root: root.is_dir())
def discover_snapshot(root: Path, *, config_path: Path | None, source_snapshot: Any = None) -> ProjectPlan:
    """Attach selected VCS metadata without changing the immutable source tree."""
    plan = discover_project(root, config_path=config_path)
    repository = getattr(source_snapshot, "repository", None)
    if repository is None:
        return plan
    commit = source_snapshot.commit
    if commit.startswith(("index:", "index-")):
        commit = "HEAD"
    return replace(plan, vcs_repository=repository, vcs=vcs_context(repository, commit))


@dataclass(frozen=True)
class ProjectSnapshotRequest:
    """Source and selection context for one independently bound review side."""

    snapshot_root: Path
    files: list[Path]
    options: Any
    assurance_kind: str
    source_snapshot: Any = None


@require(lambda request: request.snapshot_root.is_dir())
def run_project_snapshot(runtime: Any, request: ProjectSnapshotRequest) -> tuple[Any, dict[str, Any]]:
    """Bind every review side to its selected signed Python worker."""
    snapshot_root, files, options = request.snapshot_root, request.files, request.options
    source_snapshot = request.source_snapshot
    try:
        plan = discover_snapshot(snapshot_root, config_path=options.project_config, source_snapshot=source_snapshot)
        with project_worker(runtime, plan) as selected:
            return _run_project_snapshot(selected, request, plan)
    except (OSError, ValueError) as exc:
        return _failed_project_snapshot(
            runtime, snapshot_root=snapshot_root, files=files, options=options, reason=str(exc)
        )


def _failed_project_snapshot(
    runtime: Any, *, snapshot_root: Path, files: list[Path], options: Any, reason: str
) -> tuple[Any, dict[str, Any]]:
    from specfact_code_review.run.runner import CapsuleSnapshotSettings, _run_capsule_snapshot

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
        "remedy": (
            "Inspect project configuration with specfact code review runtime inspect --json, then run runtime prepare."
        ),
    }


def _run_in_private_source(runtime: Any, request: ProjectSnapshotRequest, settings: Any) -> Any:
    """Keep excluded host files out of every portable analyzer's source mount."""
    from specfact_code_review.run.runner import _run_capsule_snapshot

    with tempfile.TemporaryDirectory(prefix="specfact-project-source-") as directory:
        source = Path(directory) / "source"
        copy_project(request.snapshot_root, source)
        files = [
            source / Path(os.path.abspath(request.snapshot_root / path)).relative_to(request.snapshot_root)
            for path in request.files
        ]
        return _run_capsule_snapshot(
            runtime, snapshot_root=source, files=files, options=request.options, settings=settings
        )


@require(lambda request: request.snapshot_root.is_dir())
def _run_project_snapshot(
    runtime: Any, request: ProjectSnapshotRequest, plan: ProjectPlan
) -> tuple[Any, dict[str, Any]]:
    """Prepare once, execute applicable members, and retain independent evidence."""
    from specfact_code_review.run.runner import CapsuleSnapshotSettings

    snapshot_root, files, options = request.snapshot_root, request.files, request.options
    assurance_kind = request.assurance_kind
    try:
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
        return _failed_project_snapshot(
            runtime, snapshot_root=snapshot_root, files=files, options=options, reason=str(exc)
        )
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
    snapshot = _run_in_private_source(
        bound,
        request,
        CapsuleSnapshotSettings(
            project_runtime_root=prepared.root,
            member_argv=arguments,
            portable_runtime=True,
            unavailable_members=unavailable,
        ),
    )
    try:
        verify_inputs(plan)
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
            ProjectSnapshotRequest(
                snapshot_root=snapshot.root,
                source_snapshot=snapshot,
                files=files,
                options=side_options,
                assurance_kind="index" if scope_evidence.get("assurance_kind") == "index" else "range_preview",
            ),
        )
        results.append(result)
        bindings[side] = binding
    combined, findings = _classify_range_findings(resolution, results[0], results[1])
    evidence = {**scope_evidence, "project_runtime": bindings, "protected_pr_eligible": False}
    if evidence.get("assurance_kind") in {"range_candidate", "pr_range"}:
        evidence["assurance_kind"] = "range_preview"
    return _capsule_report(combined, findings, options=options, scope_evidence=evidence)
