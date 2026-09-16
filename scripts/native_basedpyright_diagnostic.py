"""Replay an incomplete basedpyright member in its verified offline target worker."""

from __future__ import annotations

# This diagnostic reuses verified controller APIs without modifying signed workers.
# pylint: disable=protected-access
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from icontract import ensure, require

from specfact_code_review.run import runner
from specfact_code_review.run.portable_snapshot import discover_snapshot
from specfact_code_review.run.runtime_builder import copy_project, prepare_runtime
from specfact_code_review.run.runtime_interpreter import project_worker
from specfact_code_review.run.runtime_models import document_digest
from specfact_code_review.run.sandbox import (
    SnapshotInvocationContext,
    build_launch_plan,
    execute_launch_plan,
    preflight_reserved_imports,
)


_CONTROLLER = """import json, subprocess, sys
sys.path[:0] = ['/opt/specfact/analyzers', '/opt/specfact/builtin']
from specfact_code_review.run.target_launch import target_command
result = subprocess.run(target_command('basedpyright', json.loads(sys.argv[1])), check=False, timeout=30)
raise SystemExit(result.returncode)
"""
_FIELDS = ("project_identity", "identity", "environment_id", "capsule_identity")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@ensure(lambda result: result is None or set(result) == set(_FIELDS))
def failed_review_context(evidence: Path) -> dict[str, str] | None:
    """Require the original member failure and successful runtime attachment."""
    report = json.loads((evidence / "code-review.json").read_text())
    members = [item for item in report.get("analyzer_evidence", []) if item.get("id") == "basedpyright"]
    if len(members) != 1 or members[0].get("evidence_outcome") != "UNKNOWN":
        return None
    runtime = report.get("scope_evidence", {}).get("project_runtime", {})
    if runtime.get("status") != "PASS":
        raise ValueError("original review runtime is incomplete")
    values = {**runtime, "capsule_identity": members[0].get("capsule_identity")}
    if any(not isinstance(values.get(field), str) or not values[field] for field in _FIELDS):
        raise ValueError("original review runtime identities are incomplete")
    return {field: values[field] for field in _FIELDS}


@ensure(lambda expected, actual: all(expected.get(field) == actual.get(field) for field in _FIELDS))
def validate_identities(expected: dict[str, str], actual: dict[str, str]) -> None:
    """Never substitute a pre-hook or approximate runtime for the reviewed one."""
    if any(expected.get(field) != actual.get(field) for field in _FIELDS):
        raise ValueError("review runtime identity mismatch; replay refused")


@require(lambda source, files: source.is_dir() and all(path.is_relative_to(source) for path in files))
def capture_replay(runtime, prepared, source: Path, files: list[Path], evidence: Path) -> None:
    """Keep the signed nested worker and native configuration discovery unchanged."""
    arguments = [
        "--outputjson",
        "--pythonpath",
        "/opt/specfact/project-runtime/bin/python",
        *("/opt/specfact/snapshot/" + path.relative_to(source).as_posix() for path in files),
    ]
    with tempfile.TemporaryDirectory(prefix="specfact-basedpyright-diagnostic-") as temporary:
        request, output, scratch, control = runner._prepare_capsule_process_roots(Path(temporary))
        context = SnapshotInvocationContext(
            member="basedpyright",
            snapshot_root=source,
            config_roots=(request,),
            output_root=output,
            temporary_root=scratch,
            control_root=control,
            capsule_root=runtime.root,
            interpreter=runtime.interpreter,
            bootstrap=runtime.bootstrap,
            project_runtime_root=prepared.root,
            network="none",
            environment_id=runtime.environment_id,
            import_domain="portable",
        )
        preflight = preflight_reserved_imports(context)
        if preflight.status != "PASS":
            raise ValueError(preflight.reason)
        plan = replace(
            build_launch_plan(context),
            argv=(runtime.interpreter, "-I", "-S", "-c", _CONTROLLER, json.dumps(arguments)),
        )
        execution = execute_launch_plan(plan, runtime.bubblewrap, extra_argv=(), timeout=45)
        (evidence / "basedpyright.stdout").write_text(execution.stdout, encoding="utf-8")
        (evidence / "basedpyright.stderr").write_text(execution.stderr, encoding="utf-8")
        receipt = {
            "schema": "sealed-basedpyright-diagnostic-v1",
            "authority": "diagnostic-only",
            "acceptance": False,
            "review_context": _runtime_identities(runtime, prepared),
            "context_digest": context.digest,
            "argv": arguments,
            "controller_sha256": hashlib.sha256(_CONTROLLER.encode()).hexdigest(),
            "isolation_status": execution.status,
            "returncode": execution.returncode,
            "reason": execution.reason,
            "startup_difference": (
                "A separate trusted controller calls the unchanged signed nested target worker directly. "
                "This is replay output, not recovered original stdout; adapter JSON parsing is omitted."
            ),
            "source_sha256": {path.relative_to(source).as_posix(): _digest(path) for path in files},
            "stdout_sha256": _digest(evidence / "basedpyright.stdout"),
            "stderr_sha256": _digest(evidence / "basedpyright.stderr"),
        }
        (evidence / "basedpyright-diagnostic.json").write_text(json.dumps(receipt, indent=2) + "\n")


def _runtime_identities(runtime, prepared) -> dict[str, str]:
    return {
        "project_identity": prepared.descriptor["project_identity"],
        "identity": prepared.identity,
        "environment_id": runtime.environment_id,
        "capsule_identity": document_digest({"capsule": runtime.identity, "project_runtime": prepared.identity}),
    }


@require(lambda repository, evidence: repository.is_dir() and evidence.is_dir())
def replay(repository: Path, evidence: Path, expected: dict[str, str]) -> None:
    """Recapture the actual index and reuse only a fully verified matching cache."""
    names = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], cwd=repository, timeout=30
    )
    files = [repository / os.fsdecode(name) for name in names.split(b"\0") if name.endswith((b".py", b".pyi"))]
    if not files:
        raise ValueError("no staged Python diagnostic inputs")
    runtime, reason = runner._prepare_capsule_runtime(environment_id=expected["environment_id"])
    if runtime is None:
        raise ValueError(reason)
    try:
        with tempfile.TemporaryDirectory(prefix="specfact-basedpyright-index-") as temporary:
            root = Path(temporary)
            (root / "index").mkdir(mode=0o700)
            snapshot = runner._cached_analysis_snapshot(files, root / "index")
            if snapshot is None:
                raise ValueError("cached_snapshot_materialization_unavailable")
            plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
            with project_worker(runtime, plan) as selected:
                prepared = prepare_runtime(plan, runtime=selected, offline=True)
                actual = _runtime_identities(selected, prepared)
                validate_identities(expected, actual)
                source = root / "source"
                copy_project(snapshot.root, source, include_vcs=False)
                inputs = [source / path.relative_to(snapshot.root) for path in snapshot.files]
                capture_replay(selected, prepared, source, inputs, evidence)
    finally:
        runner._cleanup_capsule_runtime(runtime)


@ensure(lambda result: result in {0, 1})
def main() -> int:
    """Retain an explicit incomplete diagnostic instead of inventing matching context."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    repository, evidence = args.checkout.resolve(), args.evidence.resolve()
    try:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise ValueError("diagnostic requires a credential-free developer child")
        os.chdir(repository)
        if expected := failed_review_context(evidence):
            replay(repository, evidence, expected)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        (evidence / "basedpyright-diagnostic.json").write_text(
            json.dumps(
                {
                    "schema": "sealed-basedpyright-diagnostic-v1",
                    "authority": "diagnostic-only",
                    "acceptance": False,
                    "isolation_status": "UNKNOWN",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
                indent=2,
            )
            + "\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
