"""C14 red tests for the analyzer process isolation boundary."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sandbox_api() -> Any:
    from specfact_code_review.run import sandbox

    return sandbox


def _context(tmp_path: Path, sandbox_api: Any, *, member: str = "ruff") -> Any:
    roots = {
        "snapshot": tmp_path / "snapshot",
        "policy": tmp_path / "policy",
        "output": tmp_path / "output",
        "temporary": tmp_path / "temporary",
        "capsule": tmp_path / "capsule",
    }
    for root in roots.values():
        root.mkdir()
    return sandbox_api.SnapshotInvocationContext(
        member=member,
        snapshot_root=roots["snapshot"],
        config_roots=(roots["policy"],),
        output_root=roots["output"],
        temporary_root=roots["temporary"],
        capsule_root=roots["capsule"],
        interpreter="/opt/specfact/python/bin/python",
        bootstrap="/opt/specfact/bootstrap/runner.py",
        project_runtime_root=None,
        network="none",
        control_root=tmp_path / "control",
    )


def test_snapshot_sandbox_capability_and_root_policy(sandbox_api: Any, tmp_path: Path) -> None:
    plan = sandbox_api.build_launch_plan(_context(tmp_path, sandbox_api))

    assert plan.root_mode == "empty-bwrap-root"
    assert plan.network == "none"
    assert plan.capabilities == ()
    assert plan.writable_roots == ("/opt/specfact/output", "/opt/specfact/tmp")


def test_import_capable_analyzer_cannot_tamper_with_other_evidence_roots(sandbox_api: Any, tmp_path: Path) -> None:
    context = _context(tmp_path, sandbox_api, member="targeted-pytest-coverage")
    plan = sandbox_api.build_launch_plan(context)

    assert plan.mount_for("snapshot").read_only is True
    assert plan.mount_for("policy").read_only is True
    assert plan.mount_for("output").read_only is False
    assert all(mount.destination != "/opt/specfact/base-output" for mount in plan.mounts)


def test_analyzer_subprocesses_use_snapshot_invocation_context(sandbox_api: Any, tmp_path: Path) -> None:
    context = _context(tmp_path, sandbox_api)
    plan = sandbox_api.build_launch_plan(context)

    assert plan.context_digest == context.digest
    assert plan.cwd == "/opt/specfact/snapshot"
    assert plan.argv[:4] == ("/opt/specfact/python/bin/python", "-I", "-S", "/opt/specfact/bootstrap/runner.py")


def test_radon_uses_a_mounted_empty_control_working_directory(sandbox_api: Any, tmp_path: Path) -> None:
    context = _context(tmp_path, sandbox_api, member="radon")
    context.control_root.mkdir()
    plan = sandbox_api.build_launch_plan(context)

    assert plan.cwd == "/opt/specfact/control"
    control = next(mount for mount in plan.mounts if mount.destination == plan.cwd)
    assert control.role == "control"
    assert control.read_only is True
    assert control.source.is_dir()
    assert not control.source.is_symlink()
    assert not tuple(control.source.iterdir())


@pytest.mark.parametrize("kind", ["non-empty", "symlink"])
def test_radon_rejects_untrusted_control_root(sandbox_api: Any, tmp_path: Path, kind: str) -> None:
    context = _context(tmp_path, sandbox_api, member="radon")
    if kind == "non-empty":
        context.control_root.mkdir()
        (context.control_root / "candidate.txt").write_text("untrusted", encoding="utf-8")
    else:
        target = tmp_path / "control-target"
        target.mkdir()
        context.control_root.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="empty real directory"):
        sandbox_api.build_launch_plan(context)


def test_snapshot_context_mounts_every_sealed_analyzer_config_root(sandbox_api: Any, tmp_path: Path) -> None:
    context = _context(tmp_path, sandbox_api)
    second = tmp_path / "coverage-policy"
    second.mkdir()
    context = context.with_config_roots((*context.config_roots, second))

    plan = sandbox_api.build_launch_plan(context)

    mounted_sources = {mount.source for mount in plan.mounts if mount.role == "config"}
    assert mounted_sources == set(context.config_roots)
    assert all(mount.read_only for mount in plan.mounts if mount.role == "config")


def test_snapshot_sitecustomize_cannot_run_during_analyzer_startup(sandbox_api: Any, tmp_path: Path) -> None:
    context = _context(tmp_path, sandbox_api)
    (context.snapshot_root / "sitecustomize.py").write_text("raise RuntimeError('owned')\n", encoding="utf-8")

    plan = sandbox_api.build_launch_plan(context)

    assert "-I" in plan.argv
    assert "-S" in plan.argv
    assert context.snapshot_root not in plan.startup_sys_path


@pytest.mark.parametrize("reserved", ["specfact_code_review.py", "pytest.py", "sitecustomize.py"])
def test_snapshot_cannot_shadow_capsule_reserved_imports(sandbox_api: Any, tmp_path: Path, reserved: str) -> None:
    context = _context(tmp_path, sandbox_api, member="targeted-pytest-coverage")
    (context.snapshot_root / reserved).write_text("VALUE = 'candidate'\n", encoding="utf-8")

    result = sandbox_api.preflight_reserved_imports(context)

    assert result.status == "UNKNOWN"
    assert result.reason == "reserved_import_collision"


def test_runtime_capsule_boots_in_empty_bwrap_root_without_host_mounts(sandbox_api: Any, tmp_path: Path) -> None:
    plan = sandbox_api.build_launch_plan(_context(tmp_path, sandbox_api))

    assert plan.root_source == "verified-capsule-root"
    assert not any(str(mount.source).startswith(("/usr", "/lib", "/System")) for mount in plan.mounts)
    assert not plan.host_runtime_mounts


def test_sandbox_executor_launches_verified_bubblewrap_from_same_open_descriptor(
    sandbox_api: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context(tmp_path, sandbox_api)
    bubblewrap = context.capsule_root / "opt/specfact/bin/bwrap-static"
    bubblewrap.parent.mkdir(parents=True)
    payload = b"signed static bubblewrap"
    bubblewrap.write_bytes(payload)
    bubblewrap.chmod(0o755)
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "{}", "")

    monkeypatch.setattr(sandbox_api.subprocess, "run", run)
    identity = sandbox_api.BubblewrapIdentity(
        path="/opt/specfact/bin/bwrap-static",
        format="ELF",
        architecture="x86_64",
        linkage="static",
        interpreter=(),
        needed=(),
        sha256="sha256:" + hashlib.sha256(payload).hexdigest(),
        descriptor_digest="sha256:" + "b" * 64,
    )

    result = sandbox_api.execute_launch_plan(
        sandbox_api.build_launch_plan(context),
        identity,
        extra_argv=("specfact_code_review.run.runner", "/opt/specfact/config/0/request.json"),
    )

    command, kwargs = calls[0]
    assert result.status == "PASS"
    assert command[0].startswith("/proc/self/fd/")
    assert kwargs["pass_fds"]
    assert kwargs["env"] == {}
    assert "--unshare-all" in command
    assert "--unshare-net" not in command
    assert "--cap-drop" in command


def test_bwrap_launcher_is_static_elf_without_interp_or_needed(sandbox_api: Any) -> None:
    identity = sandbox_api.BubblewrapIdentity(
        path="/opt/specfact/bin/bwrap-static",
        format="ELF",
        architecture="x86_64",
        linkage="static",
        interpreter=(),
        needed=(),
        sha256="sha256:" + "a" * 64,
        descriptor_digest="sha256:" + "b" * 64,
    )

    assert sandbox_api.validate_bubblewrap(identity).status == "PASS"


@pytest.mark.parametrize("field", ["linkage", "interpreter", "needed"])
def test_bwrap_launch_rejects_dynamic_or_host_loader_dependency(sandbox_api: Any, field: str) -> None:
    values = {
        "path": "/opt/specfact/bin/bwrap-static",
        "format": "ELF",
        "architecture": "x86_64",
        "linkage": "static",
        "interpreter": (),
        "needed": (),
        "sha256": "sha256:" + "a" * 64,
        "descriptor_digest": "sha256:" + "b" * 64,
    }
    values[field] = "dynamic" if field == "linkage" else ("/lib64/ld-linux.so",)

    assert sandbox_api.validate_bubblewrap(sandbox_api.BubblewrapIdentity(**values)).status == "UNKNOWN"


def test_bwrap_pre_namespace_maps_only_static_payload_and_kernel_objects(sandbox_api: Any) -> None:
    mapped = sandbox_api.validate_pre_namespace_objects(
        (
            {"kind": "static_executable", "path": "/opt/specfact/bin/bwrap-static"},
            {"kind": "kernel_object", "path": "/proc/self/ns/user"},
        )
    )

    assert mapped.status == "PASS"
    assert mapped.host_loader_objects == ()


def test_runtime_observation_declares_non_adversarial_candidate_assumption(sandbox_api: Any, tmp_path: Path) -> None:
    context = _context(tmp_path, sandbox_api, member="targeted-pytest-coverage")

    statement = sandbox_api.runtime_observation_scope(context)

    assert statement.adversarial_candidate_resistance is False
    assert "candidate Python" in statement.limitation
    assert statement.status_on_policy_uncertainty == "UNKNOWN"
