"""Composition writes retain directory anchors across hostile path substitutions."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest

from specfact_code_review.run import toolchain


def _payload(root: Path) -> toolchain.InstalledPayload:
    source = root / "specfact_code_review/resources/policy.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"sealed policy")
    source.chmod(0o644)
    identity = toolchain.InstalledModuleIdentity("", "", "", "", "", "", str(root))
    entry = toolchain.PayloadEntry(
        "specfact_code_review/resources/policy.json",
        "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest(),
        0o644,
        toolchain._payload_source_bytes(root, source.relative_to(root))[2],
    )
    return toolchain.InstalledPayload("PASS", identity=identity, manifest=(entry,))


@pytest.mark.parametrize("stage", ["payload", "bootstrap", "mount"])
def test_composition_parent_swap_cannot_write_outside_capsule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """Swap a checked destination immediately before its actual write syscall."""
    payload = _payload(tmp_path / "installed")
    root = tmp_path / "capsule"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = {
        "payload": root / "opt/specfact/builtin/.specfact_code_review.copying/resources/policy.json",
        "bootstrap": root / "opt/specfact/bootstrap/.sealed_bootstrap.py.copying",
        "mount": root / "opt/specfact/snapshot",
    }[stage]
    swapped = False
    original_open, original_mkdir, original_write = os.open, os.mkdir, Path.write_bytes

    def swap(name: str | Path) -> None:
        nonlocal swapped
        if not swapped and Path(name).name == target.name:
            target.parent.rename(target.parent.with_name(target.parent.name + ".retained"))
            target.parent.symlink_to(outside, target_is_directory=True)
            swapped = True

    def open_file(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if flags & os.O_CREAT:
            swap(path)
        return original_open(path, flags, *args, **kwargs)

    def mkdir(path: Any, *args: Any, **kwargs: Any) -> None:
        if stage == "mount":
            swap(path)
        original_mkdir(path, *args, **kwargs)

    def write(path: Path, data: bytes) -> int:
        swap(path)
        return original_write(path, data)

    monkeypatch.setattr(os, "open", open_file)
    monkeypatch.setattr(os, "mkdir", mkdir)
    monkeypatch.setattr(Path, "write_bytes", write)
    result = toolchain.compose_post_base_capsule(
        payload,
        capsule_root=root,
        immutable_base_root_digest="sha256:" + "5" * 64,
        analyzer_installed_set_digest="sha256:" + "6" * 64,
        native_launcher_digest="sha256:" + "7" * 64,
        project_runtime_identity="not-applicable",
    )
    assert swapped
    assert not tuple(outside.iterdir()), "composition followed the substituted parent into an outside directory"
    assert result.status == "UNKNOWN"
