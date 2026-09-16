"""Replay default Semgrep in the official sealed capsule; never grant review authority."""

from __future__ import annotations

# This diagnostic deliberately reuses controller snapshot/verification APIs without
# changing production hooks, signed workers, or their acceptance decisions.
# pylint: disable=protected-access
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from icontract import ensure, require

from specfact_code_review.run import runner
from specfact_code_review.run.runtime_builder import copy_project
from specfact_code_review.run.sandbox import (
    SnapshotInvocationContext,
    build_launch_plan,
    execute_launch_plan,
    preflight_reserved_imports,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@ensure(lambda result: bool(result) and all(path.is_file() and not path.is_symlink() for path in result))
def signed_configs(capsule: Path) -> list[Path]:
    """Use the authenticated builtin defaults, never rules from reviewed source."""
    root = capsule / "opt/specfact/builtin/specfact_code_review"
    clean = root / ".semgrep/clean_code.yaml"
    if not clean.is_file() or clean.is_symlink():
        raise ValueError("signed default rule pack missing")
    ai = root / "resources/semgrep-rules/ai-bloat.yaml"
    return [clean, *([ai] if ai.is_file() and not ai.is_symlink() else [])]


@ensure(lambda result: isinstance(result, bool))
def needs_replay(evidence: Path) -> bool:
    """Limit replay to the already-recorded incomplete Semgrep member."""
    report = evidence / "code-review.json"
    if not report.is_file():
        return False
    value = json.loads(report.read_text())
    return any(
        item.get("id") == "semgrep-clean" and item.get("evidence_outcome") == "UNKNOWN"
        for item in value.get("analyzer_evidence", [])
    )


@require(
    lambda source, files: source.is_dir() and all(path.is_file() and path.is_relative_to(source) for path in files)
)
def capture_replay(runtime: runner.CapsuleRuntime, source: Path, files: list[Path], evidence: Path) -> None:
    """Retain a separate offline replay's decoded output and explicit authority limit."""
    evidence.mkdir(parents=True, exist_ok=True)
    configs = signed_configs(runtime.root)
    arguments = (
        "semgrep.console_scripts.pysemgrep",
        "--disable-version-check",
        "--quiet",
        "--disable-nosem",
        "--metrics=off",
        *(part for path in configs for part in ("--config", "/" + path.relative_to(runtime.root).as_posix())),
        "--json",
        *("/opt/specfact/snapshot/" + path.relative_to(source).as_posix() for path in files),
    )
    with tempfile.TemporaryDirectory(prefix="specfact-semgrep-diagnostic-") as temporary:
        request, output, scratch, control = runner._prepare_capsule_process_roots(Path(temporary))
        context = SnapshotInvocationContext(
            member="semgrep-clean",
            snapshot_root=source,
            config_roots=(request,),
            output_root=output,
            temporary_root=scratch,
            control_root=control,
            capsule_root=runtime.root,
            interpreter=runtime.interpreter,
            bootstrap=runtime.bootstrap,
            project_runtime_root=None,
            network="none",
            environment_id=runtime.environment_id,
            import_domain="portable",
        )
        preflight = preflight_reserved_imports(context)
        if preflight.status != "PASS":
            raise ValueError(preflight.reason)
        execution = execute_launch_plan(
            build_launch_plan(context), runtime.bubblewrap, extra_argv=arguments, timeout=90
        )
        (evidence / "semgrep.stdout").write_bytes(execution.stdout.encode("utf-8"))
        (evidence / "semgrep.stderr").write_bytes(execution.stderr.encode("utf-8"))
        receipt = {
            "schema": "sealed-semgrep-diagnostic-v1",
            "authority": "diagnostic-only",
            "acceptance": False,
            "capsule_identity": runtime.identity,
            "environment_id": runtime.environment_id,
            "context_digest": context.digest,
            "argv": list(arguments),
            "isolation_status": execution.status,
            "returncode": execution.returncode,
            "reason": execution.reason,
            "startup_difference": (
                "Direct official Semgrep uses the launcher's fresh HOME/XDG directories instead of the "
                "adapter's nested fresh semgrep-home; metrics are disabled explicitly. "
                "This is a replay, not recovered original stdout."
            ),
            "configuration_sha256": {path.relative_to(runtime.root).as_posix(): _digest(path) for path in configs},
            "source_sha256": {path.relative_to(source).as_posix(): _digest(path) for path in files},
            "stdout_sha256": _digest(evidence / "semgrep.stdout"),
            "stderr_sha256": _digest(evidence / "semgrep.stderr"),
        }
        (evidence / "semgrep-diagnostic.json").write_text(json.dumps(receipt, indent=2) + "\n")


@ensure(lambda result: result == 0)
def main() -> int:
    """Capture the actual staged Python inputs through existing snapshot and isolation APIs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    repository, evidence = args.checkout.resolve(), args.evidence.resolve()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        raise ValueError("diagnostic requires a credential-free developer child")
    if not needs_replay(evidence):
        return 0
    os.chdir(repository)
    names = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], timeout=30)
    files = [Path(os.fsdecode(name)) for name in names.split(b"\0") if name.endswith((b".py", b".pyi"))]
    if not files:
        raise ValueError("no staged Python diagnostic inputs")
    runtime, reason = runner._prepare_capsule_runtime()
    if runtime is None:
        raise ValueError(reason)
    try:
        with tempfile.TemporaryDirectory(prefix="specfact-diagnostic-index-") as temporary:
            root = Path(temporary)
            (root / "index").mkdir()
            snapshot = runner._cached_analysis_snapshot(files, root / "index")
            if snapshot is None:
                raise ValueError("cached_snapshot_materialization_unavailable")
            source = root / "source"
            copy_project(snapshot.root, source, include_vcs=False)
            inputs = [source / path.relative_to(snapshot.root) for path in snapshot.files]
            capture_replay(runtime, source, inputs, evidence)
    finally:
        runner._cleanup_capsule_runtime(runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
