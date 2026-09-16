"""Declared native capabilities remain controller-owned and identity-bound."""

import json
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import runtime_builder, runtime_tools
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


def test_repository_declares_native_tools_without_executing_commands(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="sample"\nversion="1"\n[tool.specfact.code-review]\nnative_tools=["git", "uname", "sed"]\n'
    )
    plan = discover_project(tmp_path)
    assert plan.native_tools == ("git", "sed", "uname")
    assert plan.document()["native_tools"] == ("git", "sed", "uname")


def test_explicit_native_tools_override_repository_declaration(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.specfact.code-review]\nnative_tools=["git"]\n')
    config = tmp_path / "review.toml"
    config.write_text('native_tools=["uname"]\n')
    assert discover_project(tmp_path, config_path=config).native_tools == ("uname",)


@pytest.mark.parametrize("declaration", ['["curl"]', '["/usr/bin/git"]', '"git"'])
def test_unknown_native_capabilities_are_not_path_guesses(tmp_path: Path, declaration: str) -> None:
    (tmp_path / "pyproject.toml").write_text(f"[tool.specfact.code-review]\nnative_tools={declaration}\n")
    with pytest.raises(ProjectRuntimeError, match=r"native_tools|native_tool_unsupported"):
        discover_project(tmp_path)


def _native_fixture(tmp_path: Path, monkeypatch):
    """Use ELF fixtures without executing native code on the host."""
    system = tmp_path / "system"
    system.mkdir()
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 18, 62)
    for name in ("uname", "sed", "git", *runtime_tools.GIT_HELPER_NAMES, "ld-linux-x86-64.so.2"):
        (system / name).write_bytes(header)
    monkeypatch.setattr(runtime_tools, "PROGRAM_ROOT", system)
    monkeypatch.setattr(runtime_tools, "GIT_HELPER_ROOTS", (system,))
    monkeypatch.setattr(runtime_tools, "SYSTEM_LIBRARY_ROOTS", (system,))
    return runtime_tools, system


def test_capture_binds_launchers_executables_and_loader(tmp_path: Path, monkeypatch) -> None:
    tools, system = _native_fixture(tmp_path, monkeypatch)
    capture = tools.capture_native_tools(("uname",))
    assert set(capture.files) == {
        "bin/uname",
        "native-tools/executables/uname",
        "native-tools/native/ld-linux-x86-64.so.2",
    }
    assert all(row["sha256"].startswith("sha256:") for row in capture.inventory.values())
    original = capture.identity
    (system / "ld-linux-x86-64.so.2").write_bytes((system / "ld-linux-x86-64.so.2").read_bytes() + b"changed")
    assert tools.capture_native_tools(("uname",)).identity != original
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    tools.install_native_tools(capture, artifact)
    assert (artifact / "native-tools/native/ld-linux-x86-64.so.2").read_bytes() == capture.files[
        "native-tools/native/ld-linux-x86-64.so.2"
    ]
    assert b"/usr/bin" not in (artifact / "bin/uname").read_bytes()


@pytest.mark.parametrize("collision", ["bin/uname", "bin", "native-tools/forged"])
def test_builder_tool_collisions_fail_before_any_install(tmp_path: Path, monkeypatch, collision: str) -> None:
    tools, _ = _native_fixture(tmp_path, monkeypatch)
    capture = tools.capture_native_tools(("uname",))
    artifact = tmp_path / "artifact"
    target = artifact / collision
    target.parent.mkdir(parents=True)
    target.write_text("builder controlled")
    with pytest.raises(ProjectRuntimeError, match="native_tool_collision"):
        tools.install_native_tools(capture, artifact)
    assert target.read_text() == "builder controlled"
    assert not (artifact / "native-tools/executables/uname").exists()


def test_missing_git_helper_is_actionable_not_an_ambient_fallback(tmp_path: Path, monkeypatch) -> None:
    tools, system = _native_fixture(tmp_path, monkeypatch)
    (system / "git-remote-http").unlink()
    with pytest.raises(ProjectRuntimeError, match="native_tool_missing:git-remote-http"):
        tools.capture_native_tools(("git",))


def test_empty_capture_reads_no_native_programs(tmp_path: Path, monkeypatch) -> None:
    tools, _ = _native_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(tools, "PROGRAM_ROOT", tmp_path / "absent")
    capture = tools.capture_native_tools(())
    assert not capture.files
    assert not capture.inventory


def _elf_needing(path: Path, needed: str) -> None:
    """Give one synthetic ELF a real DT_NEEDED string-table entry."""
    strings = b"\0" + needed.encode() + b"\0"
    dynamic = struct.pack("<QQQQ", 1, 1, 0, 0)
    header = bytearray(path.read_bytes()[:64])
    struct.pack_into("<Q", header, 40, 64)
    struct.pack_into("<HH", header, 58, 64, 3)
    sections = bytes(64)
    sections += struct.pack("<IIQQQQIIQQ", 0, 3, 0, 0, 256, len(strings), 0, 0, 1, 0)
    sections += struct.pack("<IIQQQQIIQQ", 0, 6, 0, 0, 256 + len(strings), len(dynamic), 1, 0, 8, 16)
    path.write_bytes(header + sections + strings + dynamic)


def _sealed_shell(tmp_path: Path) -> Path:
    capsule = tmp_path / "capsule"
    (capsule / "bin").mkdir(parents=True)
    (capsule / "bin/sh").write_bytes(b"sealed shell fixture")
    (capsule / "bin/sh").chmod(0o755)
    return capsule


def test_git_helper_transitive_libraries_are_captured(tmp_path: Path, monkeypatch) -> None:
    tools, system = _native_fixture(tmp_path, monkeypatch)
    (system / "libhelper.so.1").write_bytes((system / "git").read_bytes())
    (system / "libtransitive.so.1").write_bytes((system / "git").read_bytes())
    _elf_needing(system / "git-remote-http", "libhelper.so.1")
    _elf_needing(system / "libhelper.so.1", "libtransitive.so.1")
    capture = tools.capture_native_tools(("git",), capsule_root=_sealed_shell(tmp_path))
    assert "native-tools/native/libhelper.so.1" in capture.files
    assert "native-tools/native/libtransitive.so.1" in capture.files
    assert "@capsule/bin/sh" in capture.inventory
    original = capture.identity
    (system / "libtransitive.so.1").write_bytes((system / "git").read_bytes() + b"changed")
    assert tools.capture_native_tools(("git",), capsule_root=tmp_path / "capsule").identity != original
    (system / "libtransitive.so.1").unlink()
    with pytest.raises(ProjectRuntimeError, match=r"native_library_missing:libtransitive\.so\.1"):
        tools.capture_native_tools(("git",), capsule_root=tmp_path / "capsule")


def test_native_capture_identity_participates_in_offline_cache_lookup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_builder, "capture_public_trust", lambda _root: b"synthetic public trust")
    _, system = _native_fixture(tmp_path, monkeypatch)
    plan = ProjectPlan(tmp_path, manager="pip", native_tools=("uname",))
    runtime = SimpleNamespace(environment_id="linux-x86_64-cp312", identity="sha256:" + "a" * 64)
    monkeypatch.setattr(runtime_builder, "git_identity", dict)
    identities = []
    original_digest = runtime_builder.document_digest

    def record(values):
        identities.append(values)
        return original_digest(values)

    monkeypatch.setattr(runtime_builder, "document_digest", record)
    for _ in range(2):
        with pytest.raises(ProjectRuntimeError, match="offline_cache_miss"):
            runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache", offline=True)
        (system / "ld-linux-x86-64.so.2").write_bytes((system / "uname").read_bytes() + b"changed")
    assert identities[0]["native_tools"] != identities[1]["native_tools"]
    assert "runtime_tools.py" in identities[0]["builder"]


def test_builder_cannot_replace_captured_tool_bytes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_builder, "capture_public_trust", lambda _root: b"synthetic public trust")
    _, system = _native_fixture(tmp_path, monkeypatch)
    plan = ProjectPlan(tmp_path, manager="pip", native_tools=("uname",))
    runtime = SimpleNamespace(
        root=tmp_path / "capsule", environment_id="linux-x86_64-cp312", identity="sha256:" + "a" * 64
    )
    original = (system / "uname").read_bytes()
    monkeypatch.setattr(runtime_builder, "git_identity", dict)
    monkeypatch.setattr(runtime_builder, "verify_inputs", lambda _plan: None)
    monkeypatch.setattr(runtime_builder, "analyzer_dependency_conflicts", lambda *_args: {})
    monkeypatch.setattr(runtime_builder, "member_dependency_graphs", lambda *_args: {})

    def build(_plan, _runtime, staging, **_kwargs):
        artifact = staging / "artifact"
        artifact.mkdir()
        (artifact / "inventory.json").write_text(json.dumps({}))
        (system / "uname").write_bytes(original + b"changed after capture")
        return artifact

    def project_libraries(artifact, **_kwargs):
        assert not (artifact / "native-tools").exists()
        return []

    monkeypatch.setattr(runtime_builder, "_build", build)
    monkeypatch.setattr(runtime_builder, "inventory_native", project_libraries)
    prepared = runtime_builder.prepare_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache")
    assert (prepared.root / "native-tools/executables/uname").read_bytes() == original
    assert prepared.descriptor["inventory"]["native_tools"]["native-tools/executables/uname"][
        "sha256"
    ] == runtime_builder.content_digest(original)


@pytest.mark.parametrize("tool", ["uname", "sed"])
def test_non_elf_tools_fail_with_exact_capability(tmp_path: Path, monkeypatch, tool: str) -> None:
    tools, system = _native_fixture(tmp_path, monkeypatch)
    (system / tool).write_text("not an ELF binary")
    with pytest.raises(ProjectRuntimeError, match=f"native_tool_not_elf:{tool}"):
        tools.capture_native_tools((tool,))


def test_git_requires_sealed_shell_not_host_shell(tmp_path: Path, monkeypatch) -> None:
    tools, _ = _native_fixture(tmp_path, monkeypatch)
    capsule = tmp_path / "capsule"
    (capsule / "bin").mkdir(parents=True)
    (capsule / "bin/sh").symlink_to("/bin/sh")
    with pytest.raises(ProjectRuntimeError, match="native_tool_shell_missing"):
        tools.capture_native_tools(("git",), capsule_root=capsule)


def test_declared_git_captures_local_transport_services(tmp_path: Path, monkeypatch) -> None:
    tools, _ = _native_fixture(tmp_path, monkeypatch)
    capture = tools.capture_native_tools(("git",), capsule_root=_sealed_shell(tmp_path))
    for name in ("git-upload-pack", "git-receive-pack", "git-upload-archive"):
        assert f"native-tools/git-core/{name}" in capture.files
        assert f"native-tools/executables/git-core/{name}" in capture.files
