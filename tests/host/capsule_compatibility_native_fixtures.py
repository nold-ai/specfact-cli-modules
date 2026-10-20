"""Genuine runtime factories with explicit synthetic installation and acquisition seams."""

from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

import certifi
import specfact_cli.cli as core_cli
from specfact_cli.cli import app
from specfact_cli.registry import CommandRegistry, module_installer

from specfact_code_review.run import runner, runtime_builder, scope
from specfact_code_review.run.runner import _cleanup_capsule_runtime
from specfact_code_review.run.runtime_artifacts import load_runtime
from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts
from specfact_code_review.run.runtime_domains import member_dependency_graphs
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError, document_digest
from specfact_code_review.run.scope import cleanup_scope_resolution


ENVIRONMENT = "linux-x86_64-cp312"
CANARY = "PRIVATE_COMPATIBILITY_CANARY"
FIXED_CATEGORIES = {
    "crosshair-tool": "contracts_entry",
    "z3-solver": "contracts_pinned_transitive",
    "pylint": "pylint_entry",
    "astroid": "pylint_pinned_transitive",
}
REFERENCE_HASH = "395c7eb2d3f4a4dd471840c2c8672a0ec218c4b47fb84c400b875170d4dd7aaa"


def reference_versions():
    """Read actual package reference rows; these are never historical target facts."""
    resource = Path(runtime_builder.__file__).parents[1] / "resources/contracts/pr-range-v1-toolchain-lock.json"
    lock = json.loads(resource.read_text())
    selected = next(row for row in lock["environments"] if row["environment_id"] == ENVIRONMENT)
    return {row["normalized_name"]: row["version"] for row in selected["components"]}


def write_distribution(root, name, version, requirements=()):
    """Create real metadata and RECORD-backed modules for native Distribution reads."""
    module = name.replace("-", "_")
    metadata = root / f"{module}-{version}.dist-info"
    metadata.mkdir(parents=True)
    fields = ["Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"]
    fields.extend(f"Requires-Dist: {requirement}" for requirement in requirements)
    (metadata / "METADATA").write_text("\n".join(fields) + "\n")
    (root / f"{module}.py").write_text('"""Inert synthetic distribution payload."""\n')
    (metadata / "RECORD").write_text(f"{module}.py,,\n{metadata.name}/METADATA,,\n")
    return {"metadata": {"name": name, "version": version, "requires_dist": list(requirements)}}


def native_inventory(analyzer_root, case="conflict"):
    """Construct all four native domains without reproducing their selection logic."""
    versions = reference_versions()
    requirements = {
        "crosshair-tool": [f"z3-solver>={versions['z3-solver']}"],
        "pylint": [f"astroid>={versions['astroid']}"],
        "basedpyright": [f"nodejs-wheel-binaries>={versions['nodejs-wheel-binaries']}"],
        "pytest-cov": [f"pytest>={versions['pytest']}"],
    }
    names = (*FIXED_CATEGORIES, "basedpyright", "nodejs-wheel-binaries", "pytest", "pytest-cov")
    installed = [write_distribution(analyzer_root, name, versions[name], requirements.get(name, ())) for name in names]
    inventory = {"installed": installed, "environment": {"python_version": "3.12", "sys_platform": "linux"}}
    if case != "clear":
        installed[1]["metadata"]["version"] = "0.0.0+private.compatibility.canary"
    return inventory


def synthetic_worker(root, category="contracts_pinned_transitive"):
    """Supply a genuine CapsuleRuntime whose acquisition authority is synthetic."""
    analyzer_root = root / "opt/specfact/analyzers"
    inventory = native_inventory(analyzer_root, "clear")
    selected = next(name for name, value in FIXED_CATEGORIES.items() if value == category)
    row = next(row for row in inventory["installed"] if row["metadata"]["name"] == selected)
    row["metadata"]["version"] = "0.0.0+private.compatibility.canary"
    certificates = analyzer_root / "certifi/cacert.pem"
    certificates.parent.mkdir()
    shutil.copyfile(certifi.where(), certificates)
    runtime = runner.CapsuleRuntime(
        root=root,
        identity=document_digest({"synthetic_worker": str(root)}),
        environment_id=ENVIRONMENT,
        interpreter="/opt/specfact/python/bin/python",
        bootstrap="/opt/specfact/worker.py",
        bubblewrap=None,
        cleanup_root=root,
    )
    return runtime, inventory


def append_event(root, event):
    with (root / "native-events.jsonl").open("a") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


def acquire_worker(*, environment_id):
    root = Path(os.environ["HOME"]).parent
    counter = root / "worker-count"
    index = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(index + 1))
    config = json.loads((root / "fixture-config.json").read_text())
    category = config["case"] if config["case"] in FIXED_CATEGORIES.values() else "contracts_pinned_transitive"
    runtime, inventory = synthetic_worker(root / "invocations" / f"worker-{index}", category)
    if environment_id != ENVIRONMENT:
        raise AssertionError("Synthetic acquisition received an unexpected native selection")
    (root / f"inventory-{index}.json").write_text(json.dumps(inventory))
    append_event(root, {"event": "acquire", "index": index, "authority": "synthetic_acquisition"})
    return runtime, ""


def acquisition_build(plan, runtime, staging, *, build_log):
    """Replace only external build launch; prepare_runtime still seals and reloads."""
    root = Path(os.environ["HOME"]).parent
    index = int(runtime.root.name.removeprefix("worker-"))
    config = json.loads((root / "fixture-config.json").read_text())
    if config.get("fail_head") and index == 1:
        raise ValueError(CANARY + ":synthetic build failure")
    inventory = json.loads((root / f"inventory-{index}.json").read_text())
    artifact = staging / "artifact"
    artifact.mkdir()
    (artifact / "inventory.json").write_text(json.dumps(inventory))
    build_log.write(b"SYNTHETIC_BUILD_OUTPUT\n")
    (root / f"plan-{index}.json").write_text(json.dumps({"root": str(plan.root), "document": plan.document()}))
    append_event(root, {"event": "build", "index": index, "plan": plan.identity})
    return artifact


def fixture_report(root):
    """Build CLI-output fixtures from genuine sealed descriptors, never fake models."""
    descriptors = sorted((root / "home/.cache/specfact/code-review/project-runtimes-v2").glob("*/project-runtime.json"))
    events = [json.loads(line) for line in (root / "native-events.jsonl").read_text().splitlines()]
    plans = [event["plan"] for event in events if event["event"] == "build"]
    documents = {json.loads(path.read_text())["project_identity"]: json.loads(path.read_text()) for path in descriptors}
    bindings = {}
    members = {}
    for side, identity in zip(("base", "head"), plans, strict=True):
        descriptor = documents[identity]
        bindings[side] = {
            "status": "PASS",
            "schema": descriptor["schema"],
            "identity": descriptor["identity"],
            "project_identity": identity,
            "environment_id": descriptor["environment_id"],
            "authority": "local_build",
            "protected_pr_eligible": False,
            "source_roots": descriptor["project"]["source_roots"],
        }
        for member, diagnostic in descriptor["inventory"]["analyzer_conflicts"].items():
            members.setdefault(member, {})[side] = {
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "diagnostic": diagnostic,
            }
    return {
        "findings": [],
        "analyzer_evidence": [{"id": member, **sides} for member, sides in members.items()],
        "scope_evidence": {"project_runtime": bindings},
        "assurance_status": "UNKNOWN",
        "overall_verdict": "FAIL",
    }


def synthetic_cli(*, args):
    root = Path(os.environ["HOME"]).parent
    report = fixture_report(root)
    (root / "review.private.json").write_text(json.dumps(report))
    print(CANARY + ":private CLI output")
    config = json.loads((root / "fixture-config.json").read_text())
    append_event(root, {"event": "review", "args": args, "authority": "synthetic_cli_output"})
    raise SystemExit(config["review_exit"])


def cleanup_worker(runtime):
    root = Path(os.environ["HOME"]).parent
    record_prepared_runtime(root, runtime)
    _cleanup_capsule_runtime(runtime)
    append_event(root, {"event": "worker_cleanup", "removed": not runtime.root.exists()})


def cleanup_scope(resolution):
    paths = [snapshot.root for snapshot in (resolution.base_snapshot, resolution.head_snapshot) if snapshot]
    cleanup_scope_resolution(resolution)
    append_event(
        Path(os.environ["HOME"]).parent, {"event": "scope_cleanup", "removed": all(not path.exists() for path in paths)}
    )


def synthetic_verification(package, metadata, **kwargs):
    root = Path(os.environ["HOME"]).parent
    config = json.loads((root / "fixture-config.json").read_text())
    if config.get("case") == "verifier_error":
        raise ValueError(CANARY)
    append_event(
        root,
        {
            "event": "verify",
            "authority": "synthetic_installation",
            "name": metadata.name,
            "options": kwargs,
            "package": str(package),
        },
    )
    return config.get("case") != "verifier_false"


def install_synthetic_boundaries():
    """Install only declared external seams in a fresh isolated fixture process."""
    CommandRegistry.get_module_typer = staticmethod(lambda _name: app)
    module_installer.verify_module_artifact = synthetic_verification
    for name, replacement in {
        "_capsule_environment_id": lambda: ENVIRONMENT,
        "_prepare_capsule_runtime": acquire_worker,
        "_cleanup_capsule_runtime": cleanup_worker,
    }.items():
        setattr(runner, name, replacement)
    scope.cleanup_scope_resolution = cleanup_scope
    patch.object(runtime_builder, "_build", acquisition_build).start()
    core_cli.app = synthetic_cli


def native_trial(inventory, analyzer_root):
    """Run both native owners over a copy; callers assert exact outcomes and immutability."""
    trial = copy.deepcopy(inventory)
    for row in trial["installed"]:
        name = row["metadata"]["name"]
        if name in FIXED_CATEGORIES:
            row["metadata"]["version"] = reference_versions()[name]
    return analyzer_dependency_conflicts(trial, analyzer_root), member_dependency_graphs(trial, analyzer_root)


def record_prepared_runtime(root, runtime):
    index = int(runtime.root.name.removeprefix("worker-"))
    plan_path = root / f"plan-{index}.json"
    if not plan_path.exists():
        return
    value = json.loads(plan_path.read_text())
    plan = ProjectPlan(root=Path(value["root"]), **value["document"])
    for path in (root / "home/.cache/specfact/code-review/project-runtimes-v2").glob("*/project-runtime.json"):
        if json.loads(path.read_text())["project_identity"] != plan.identity:
            continue
        try:
            prepared = load_runtime(
                path, plan=plan, environment_id=runtime.environment_id, worker_identity=runtime.identity
            )
        except ProjectRuntimeError as error:
            append_event(root, {"event": "native_verification_rejected", "index": index, "reason": str(error)})
            continue
        append_event(
            root,
            {
                "event": "verified_prepared",
                "index": index,
                "identity": prepared.identity,
                "descriptor_path": str(prepared.descriptor_path),
                "root": str(prepared.root),
                "class": type(prepared).__module__ + "." + type(prepared).__name__,
                "native_conflicts": prepared.descriptor["inventory"]["analyzer_conflicts"],
                "member_domains": sorted(prepared.descriptor["inventory"]["member_graphs"]),
                "plan_identity": plan.identity,
                "worker_identity": runtime.identity,
            },
        )
