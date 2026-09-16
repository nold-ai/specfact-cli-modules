"""Portable runtime artifacts reject stale, corrupt and escaping content."""

import json
from pathlib import Path

import pytest

from specfact_code_review.run.runtime_artifacts import load_runtime, seal_runtime
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError, document_digest


def test_local_descriptor_roundtrip_and_corruption(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    artifact = tmp_path / "artifact"
    (artifact / "site-packages").mkdir(parents=True)
    payload = artifact / "site-packages" / "consumer.py"
    payload.write_text("VALUE = 1\n", encoding="utf-8")
    plan = discover_project(source)
    prepared = seal_runtime(
        artifact, plan=plan, environment_id="linux-x86_64-cp312", worker_identity="sha256:" + "a" * 64
    )
    observed = load_runtime(
        prepared.descriptor_path, plan=plan, environment_id="linux-x86_64-cp312", worker_identity="sha256:" + "a" * 64
    )
    assert observed.identity == prepared.identity
    assert observed.descriptor["provenance"]["authority"] == "local_build"
    payload.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ProjectRuntimeError, match="payload"):
        load_runtime(
            prepared.descriptor_path,
            plan=plan,
            environment_id="linux-x86_64-cp312",
            worker_identity="sha256:" + "a" * 64,
        )


def test_runtime_rejects_wrong_abi_and_inputs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "requirements.txt").write_text("requests<3\n", encoding="utf-8")
    artifact = tmp_path / "artifact"
    (artifact / "site-packages").mkdir(parents=True)
    plan = discover_project(source)
    prepared = seal_runtime(
        artifact, plan=plan, environment_id="linux-x86_64-cp312", worker_identity="sha256:" + "a" * 64
    )
    with pytest.raises(ProjectRuntimeError, match="environment"):
        load_runtime(
            prepared.descriptor_path,
            plan=plan,
            environment_id="linux-x86_64-cp311",
            worker_identity="sha256:" + "a" * 64,
        )
    (source / "requirements.txt").write_text("requests<4\n", encoding="utf-8")
    with pytest.raises(ProjectRuntimeError, match="inputs"):
        load_runtime(
            prepared.descriptor_path,
            plan=discover_project(source),
            environment_id="linux-x86_64-cp312",
            worker_identity="sha256:" + "a" * 64,
        )


def test_runtime_rejects_links_and_descriptor_tampering(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    artifact = tmp_path / "artifact"
    (artifact / "site-packages").mkdir(parents=True)
    (artifact / "site-packages" / "bad").symlink_to("/etc/passwd")
    with pytest.raises(ProjectRuntimeError, match="symlink"):
        seal_runtime(
            artifact,
            plan=discover_project(source),
            environment_id="linux-x86_64-cp312",
            worker_identity="sha256:" + "a" * 64,
        )
    (artifact / "site-packages" / "bad").unlink()
    prepared = seal_runtime(
        artifact,
        plan=discover_project(source),
        environment_id="linux-x86_64-cp312",
        worker_identity="sha256:" + "a" * 64,
    )
    data = json.loads(prepared.descriptor_path.read_text(encoding="utf-8"))
    data["provenance"]["authority"] = "protected_pr"
    prepared.descriptor_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProjectRuntimeError, match="descriptor"):
        load_runtime(
            prepared.descriptor_path,
            plan=discover_project(source),
            environment_id="linux-x86_64-cp312",
            worker_identity="sha256:" + "a" * 64,
        )


def test_descriptor_rejects_a_different_analyzer_worker(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    plan = discover_project(source)
    prepared = seal_runtime(
        artifact, plan=plan, environment_id="linux-x86_64-cp312", worker_identity="sha256:" + "a" * 64
    )
    with pytest.raises(ProjectRuntimeError, match="worker_identity_mismatch"):
        load_runtime(
            prepared.descriptor_path,
            plan=plan,
            environment_id="linux-x86_64-cp312",
            worker_identity="sha256:" + "b" * 64,
        )


@pytest.mark.parametrize(
    "inventory",
    [[], {"analyzer_conflicts": []}, {"member_graphs": []}, {"pytest_arguments": 7}, {"pytest_arguments": [False]}],
)
def test_descriptor_rejects_malformed_inventory(tmp_path: Path, inventory) -> None:

    source, artifact = tmp_path / "source", tmp_path / "artifact"
    source.mkdir()
    artifact.mkdir()
    plan = discover_project(source)
    prepared = seal_runtime(artifact, plan=plan, environment_id="linux-x86_64-cp312", worker_identity="worker")
    data = prepared.descriptor
    data["inventory"] = inventory
    data["identity"] = document_digest({key: value for key, value in data.items() if key != "identity"})
    prepared.descriptor_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProjectRuntimeError, match="inventory_invalid"):
        load_runtime(prepared.descriptor_path, plan=plan, environment_id="linux-x86_64-cp312", worker_identity="worker")
