"""Native dependency inventories fail precisely without invoking untrusted binaries."""

import struct
from pathlib import Path

import pytest

from specfact_code_review.run.runtime_models import ProjectRuntimeError
from specfact_code_review.run.runtime_native import elf_dependencies, inventory_native


def test_declared_missing_native_library_names_exact_requirement(tmp_path: Path) -> None:

    root = tmp_path / "runtime"
    root.mkdir()
    with pytest.raises(ValueError, match=r"project_native_library_missing:libspecfact_missing_473\.so\.1"):
        inventory_native(
            root, capsule_root=tmp_path / "capsule", declared=("libspecfact_missing_473.so.1",), system_roots=()
        )


def test_native_inventory_does_not_copy_unrequested_host_files(tmp_path: Path) -> None:

    root, system = tmp_path / "artifact", tmp_path / "system"
    root.mkdir()
    system.mkdir()
    (system / "unrelated-secret").write_text("must not copy")
    assert inventory_native(root, capsule_root=tmp_path / "capsule", declared=(), system_roots=(system,)) == []
    assert not list(root.rglob("unrelated-secret"))


def _elf(path: Path, needed: tuple[str, ...]) -> None:

    strings = b"\0" + b"".join(name.encode() + b"\0" for name in needed)
    offsets = []
    cursor = 1
    for name in needed:
        offsets.append(cursor)
        cursor += len(name) + 1
    dynamic = b"".join(struct.pack("<QQ", 1, offset) for offset in offsets) + struct.pack("<QQ", 0, 0)
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 18, 62)
    struct.pack_into("<Q", header, 40, 64)
    struct.pack_into("<HH", header, 58, 64, 3)
    sections = bytes(64)
    sections += struct.pack("<IIQQQQIIQQ", 0, 3, 0, 0, 256, len(strings), 0, 0, 1, 0)
    sections += struct.pack("<IIQQQQIIQQ", 0, 6, 0, 0, 256 + len(strings), len(dynamic), 1, 0, 8, 16)
    path.write_bytes(header + sections + strings + dynamic)


def test_project_native_libraries_use_their_own_loader_closure(tmp_path: Path) -> None:

    artifact, capsule, system = (tmp_path / name for name in ("artifact", "capsule", "system"))
    for root in (artifact, capsule, system):
        root.mkdir()
    _elf(system / "libodbc.so.2", ("libc.so.6",))
    _elf(system / "libc.so.6", ("ld-linux-x86-64.so.2",))
    _elf(system / "ld-linux-x86-64.so.2", ())
    _elf(capsule / "libc.so.6", ())
    original = (capsule / "libc.so.6").read_bytes()
    records = inventory_native(
        artifact, capsule_root=capsule, declared=("libodbc.so.2",), system_roots=(system,), target_loader=True
    )
    assert {Path(row["path"]).name for row in records} == {"libodbc.so.2", "libc.so.6", "ld-linux-x86-64.so.2"}
    assert (artifact / "native/ld-linux-x86-64.so.2").stat().st_mode & 0o111
    assert (capsule / "libc.so.6").read_bytes() == original


def test_owned_native_executables_include_their_shared_library_closure(tmp_path: Path) -> None:

    artifact, system = tmp_path / "artifact", tmp_path / "system"
    (artifact / "executables").mkdir(parents=True)
    system.mkdir()
    _elf(artifact / "executables/customer-tool", ("libcustomer.so.1",))
    _elf(system / "libcustomer.so.1", ())
    records = inventory_native(artifact, capsule_root=tmp_path / "capsule", declared=(), system_roots=(system,))
    assert (artifact / "native/libcustomer.so.1").is_file()
    assert any(row["path"] == "executables/customer-tool" for row in records)


def test_wrong_machine_elf_is_rejected_before_inventory(tmp_path: Path) -> None:
    payload = bytearray(64)
    payload[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", payload, 18, 183)
    struct.pack_into("<H", payload, 58, 64)
    binary = tmp_path / "foreign.so"
    binary.write_bytes(payload)
    with pytest.raises(ProjectRuntimeError, match="architecture_unsupported"):
        elf_dependencies(binary)
