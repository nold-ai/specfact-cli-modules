"""Native dependency inventories fail precisely without invoking untrusted binaries."""

from pathlib import Path

import pytest


def test_declared_missing_native_library_names_exact_requirement(tmp_path: Path) -> None:
    from specfact_code_review.run.runtime_native import inventory_native

    root = tmp_path / "runtime"
    root.mkdir()
    with pytest.raises(ValueError, match=r"project_native_library_missing:libspecfact_missing_473\.so\.1"):
        inventory_native(
            root, capsule_root=tmp_path / "capsule", declared=("libspecfact_missing_473.so.1",), system_roots=()
        )


def test_native_inventory_does_not_copy_unrequested_host_files(tmp_path: Path) -> None:
    from specfact_code_review.run.runtime_native import inventory_native

    root, system = tmp_path / "artifact", tmp_path / "system"
    root.mkdir()
    system.mkdir()
    (system / "unrelated-secret").write_text("must not copy")
    assert inventory_native(root, capsule_root=tmp_path / "capsule", declared=(), system_roots=(system,)) == []
    assert not list(root.rglob("unrelated-secret"))
