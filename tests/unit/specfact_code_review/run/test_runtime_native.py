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


def _segmented_elf() -> bytearray:
    """Build an ELF64 shared object with both section and program metadata."""
    strings = b"\0libcustomer.so.1\0"
    payload = bytearray(704)
    payload[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", payload, 16, 3, 62, 1)
    struct.pack_into("<QQQ", payload, 24, 0, 64, 512)
    struct.pack_into("<HHHHHH", payload, 52, 64, 56, 2, 64, 3, 0)
    struct.pack_into("<IIQQQQQQ", payload, 64, 1, 4, 0, 0x400000, 0x400000, 512, 512, 4096)
    struct.pack_into("<IIQQQQQQ", payload, 120, 2, 4, 256, 0x400100, 0x400100, 64, 64, 8)
    payload[176 : 176 + len(strings)] = strings
    for index, entry in enumerate(((1, 1), (5, 0x4000B0), (10, len(strings)), (0, 0))):
        struct.pack_into("<QQ", payload, 256 + index * 16, *entry)
    struct.pack_into("<IIQQQQIIQQ", payload, 576, 0, 3, 2, 0x4000B0, 176, len(strings), 0, 0, 1, 0)
    struct.pack_into("<IIQQQQIIQQ", payload, 640, 0, 6, 2, 0x400100, 256, 64, 1, 0, 8, 16)
    return payload


def _remove_section_table(payload: bytearray, entry_size: int = 0) -> bytearray:
    struct.pack_into("<Q", payload, 40, 0)
    struct.pack_into("<HH", payload, 58, entry_size, 0)
    return payload[:512]


@pytest.mark.parametrize("entry_size", [0, 64])
def test_dependency_inventory_survives_removed_elf_section_table(tmp_path: Path, entry_size: int) -> None:
    artifact, system = tmp_path / "artifact", tmp_path / "system"
    artifact.mkdir()
    system.mkdir()
    binary = artifact / "extension.so"
    payload = _segmented_elf()
    binary.write_bytes(payload)
    assert elf_dependencies(binary) == ("libcustomer.so.1",)
    binary.write_bytes(_remove_section_table(payload, entry_size))
    assert elf_dependencies(binary) == ("libcustomer.so.1",)
    _elf(system / "libcustomer.so.1", ())
    records = inventory_native(artifact, capsule_root=tmp_path / "capsule", declared=(), system_roots=(system,))
    assert (artifact / "native/libcustomer.so.1").read_bytes() == (system / "libcustomer.so.1").read_bytes()
    assert next(row for row in records if row["path"] == "extension.so")["needed"] == ("libcustomer.so.1",)


@pytest.mark.parametrize(
    ("offset", "encoding", "value"),
    [
        (32, "Q", 500),  # Program-header table extends beyond file.
        (54, "H", 55),  # Wrong program-header entry size.
        (152, "Q", 1024),  # Dynamic segment exceeds file bounds.
        (160, "Q", 32),  # Dynamic segment file size exceeds memory size.
        (96, "Q", 176),  # String table is only in the load segment's memory tail.
        (80, "Q", 2**64 - 1),  # Virtual address range overflows ELF64 addresses.
        (280, "Q", 0x400200),  # String table starts beyond file-backed load bytes.
        (296, "Q", 1024),  # String table extends beyond load segment.
        (264, "Q", 100),  # Dependency offset exceeds string table.
        (304, "Q", 1),  # No DT_NULL termination.
        (272, "Q", 10),  # Missing DT_STRTAB, duplicate DT_STRSZ.
        (193, "B", 65),  # Dependency lacks a bounded NUL terminator.
        (177, "B", 255),  # Dependency is not ASCII.
    ],
)
def test_sectionless_elf_rejects_invalid_dynamic_entries(
    tmp_path: Path, offset: int, encoding: str, value: int
) -> None:
    payload = _remove_section_table(_segmented_elf())
    struct.pack_into("<" + encoding, payload, offset, value)
    binary = tmp_path / "invalid.so"
    binary.write_bytes(payload)
    with pytest.raises(ProjectRuntimeError, match="project_native_elf_invalid"):
        elf_dependencies(binary)


def test_sectionless_static_elf_has_no_dependencies(tmp_path: Path) -> None:
    payload = _remove_section_table(_segmented_elf())
    struct.pack_into("<H", payload, 56, 1)
    binary = tmp_path / "static"
    binary.write_bytes(payload)
    assert not elf_dependencies(binary)


def test_sectionless_elf_stops_at_dynamic_terminator(tmp_path: Path) -> None:
    payload = _remove_section_table(_segmented_elf())
    struct.pack_into("<QQ", payload, 320, 1, 2**64 - 1)
    struct.pack_into("<QQ", payload, 152, 80, 80)
    binary = tmp_path / "extension.so"
    binary.write_bytes(payload)
    assert elf_dependencies(binary) == ("libcustomer.so.1",)
