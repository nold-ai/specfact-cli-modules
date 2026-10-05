from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from specfact_code_review.run import native_project_manager


@pytest.fixture(autouse=True)
def _restore_fixture_permissions(tmp_path: Path) -> object:  # pyright: ignore[reportUnusedFunction]
    yield
    for root, directories, files in os.walk(tmp_path, topdown=False):
        for name in files:
            path = Path(root) / name
            if not path.is_symlink():
                path.chmod(0o600)
        for name in directories:
            path = Path(root) / name
            if not path.is_symlink():
                path.chmod(0o700)
    tmp_path.chmod(0o700)


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


def _wheel(
    root: Path,
    *,
    filename: str = "fixture_dep-2.0-py3-none-any.whl",
    entries: dict[str, bytes] | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / filename
    members = entries or {
        "fixture_dep/__init__.py": b"VALUE = 2\n",
        "fixture_dep-2.0.dist-info/METADATA": b"Name: fixture-dep\nVersion: 2.0\n",
        "fixture_dep-2.0.dist-info/RECORD": b"",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    path.chmod(0o600)
    return path


def _bundle(
    tmp_path: Path,
    *,
    manager: str = "pip",
    abi: str = "cp313",
    filename: str = "fixture_dep-2.0-py3-none-any.whl",
    entries: dict[str, bytes] | None = None,
    kind: str = "wheel",
) -> tuple[Path, Path, Path, Path, dict[str, Any]]:
    root = tmp_path / "bundle"
    wheelhouse = root / "wheelhouse"
    wheel = _wheel(wheelhouse, filename=filename, entries=entries)
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    tags = filename.removesuffix(".whl").rsplit("-", 3)[-3:]
    tag = "-".join(tags) if kind == "wheel" else ""
    artifact = {
        "build_hook_required": kind != "wheel",
        "filename": filename,
        "kind": kind,
        "mode": 0o600,
        "package": "fixture-dep",
        "sha256": digest,
        "size": wheel.stat().st_size,
        "tags": [tag] if tag else [],
        "url": f"https://files.pythonhosted.org/packages/aa/{filename}",
        "version": "2.0",
    }
    versions = {"pip": "26.2.1", "hatch": "1.18.0", "uv": "0.12.13", "poetry": "2.4.3"}
    lock = {
        "abi": abi,
        "artifacts": [{key: artifact[key] for key in ("package", "version", "filename", "sha256", "kind", "tags")}],
        "manager": {"name": manager, "version": versions[manager]},
        "platform": "macos-arm64",
        "schema": "specfact-macos-offline-manager-lock-v1",
        "selection": {"environment": "default", "groups": ["test"]},
    }
    lock_path = root / "locks" / f"{manager}.json"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_bytes(_canonical(lock))
    unsigned = {
        "abi": abi,
        "acquisition_executed_project_code": False,
        "artifacts": [artifact],
        "corpus_identity": "1" * 64,
        "manager": lock["manager"],
        "manager_lock": {
            "path": f"locks/{manager}.json",
            "sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        },
        "platform": "macos-arm64",
        "project": "fixture-project",
        "schema": "specfact-macos-project-acquisition-v1",
        "source": {
            "archive_path": "source.tar.gz",
            "archive_sha256": "2" * 64,
            "archive_url": "https://github.com/example/project/archive/" + "3" * 40 + ".tar.gz",
            "commit": "3" * 40,
            "inventory": {"pyproject.toml": {"mode": 0o644, "sha256": "4" * 64, "size": 1}},
            "tree_sha256": "5" * 64,
            "trusted_fetch": {
                "archive_sha256": "2" * 64,
                "archive_url": "https://github.com/example/project/archive/" + "3" * 40 + ".tar.gz",
                "authenticated_transport": True,
                "commit": "3" * 40,
                "git_tree": "6" * 40,
                "method": "git-checkout",
                "schema": "specfact-trusted-source-fetch-v1",
                "source_url": "https://github.com/example/project.git",
                "tree_sha256": "5" * 64,
            },
            "url": "https://github.com/example/project.git",
        },
    }
    content_sha256 = hashlib.sha256(_canonical(unsigned)).hexdigest()
    signed = {**unsigned, "content_sha256": content_sha256}
    descriptor = {
        **signed,
        "signature": {
            "algorithm": "test",
            "key_id": "fixture",
            "value": hashlib.sha256(_canonical(signed)).hexdigest(),
        },
    }
    descriptor_path = root / "descriptor.json"
    descriptor_path.write_bytes(_canonical(descriptor))
    wheel.chmod(0o400)
    return descriptor_path, lock_path, wheelhouse, tmp_path / "prepared", descriptor


def _verify(payload: bytes, signature: dict[str, str]) -> bool:
    return signature == {
        "algorithm": "test",
        "key_id": "fixture",
        "value": hashlib.sha256(payload).hexdigest(),
    }


@pytest.mark.parametrize("manager", ["pip", "hatch", "uv", "poetry"])
def test_installs_exact_authenticated_wheel_closure_for_closed_managers(tmp_path: Path, manager: str) -> None:
    descriptor, lock, wheelhouse, output, expected = _bundle(tmp_path, manager=manager)

    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor,
        manager_lock_path=lock,
        wheelhouse=wheelhouse,
        output=output,
        verifier=_verify,
    )

    assert evidence["schema"] == "specfact-native-project-preparation-evidence-v1"
    assert evidence["status"] == "COMPLETE"
    assert evidence["manager"] == expected["manager"]
    assert evidence["abi"] == "cp313"
    assert evidence["platform"] == "macos-arm64"
    assert evidence["acquisition_content_sha256"] == expected["content_sha256"]
    assert evidence["project_code_executed"] is False
    assert evidence["build_hooks_executed"] is False
    assert evidence["network_used"] is False
    assert evidence["host_manager_used"] is False
    assert evidence["artifact_count"] == 1
    assert evidence["file_count"] == 3
    assert (output / "fixture_dep/__init__.py").read_bytes() == b"VALUE = 2\n"
    assert (output / ".specfact-preparation-evidence.json").read_bytes() == _canonical(evidence) + b"\n"


def test_preserves_native_extension_bytes_from_compatible_arm64_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.0", ("", "", ""), ""))
    native = b"\xcf\xfa\xed\xfe" + bytes(range(32))
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        abi="cp313",
        filename="fixture_dep-2.0-cp311-abi3-macosx_14_0_arm64.whl",
        entries={
            "fixture_dep/native.abi3.so": native,
            "fixture_dep-2.0.dist-info/METADATA": b"Name: fixture-dep\nVersion: 2.0\n",
        },
    )

    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor,
        manager_lock_path=lock,
        wheelhouse=wheelhouse,
        output=output,
        verifier=_verify,
    )

    assert evidence["native_extension_count"] == 1
    assert (output / "fixture_dep/native.abi3.so").read_bytes() == native


@pytest.mark.parametrize("scheme", ["purelib", "platlib"])
def test_data_scheme_wheel_cannot_report_complete_with_misplaced_module(tmp_path: Path, scheme: str) -> None:
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        entries={
            f"fixture_dep-2.0.data/{scheme}/fixture_dep/__init__.py": b"VALUE = 2\n",
            "fixture_dep-2.0.dist-info/METADATA": b"Name: fixture-dep\nVersion: 2.0\n",
        },
    )

    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor,
        manager_lock_path=lock,
        wheelhouse=wheelhouse,
        output=output,
        verifier=_verify,
    )

    assert evidence["status"] == "INCOMPLETE"
    assert ".data" in evidence["diagnostic"]
    assert evidence["unsupported_artifacts"] == ["fixture_dep-2.0-py3-none-any.whl"]
    assert not output.exists()


@pytest.mark.parametrize("platform_tag", ["arm64", "universal2"])
def test_rejects_wheel_requiring_newer_macos_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform_tag: str
) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.7", ("", "", ""), ""))
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        filename=f"fixture_dep-2.0-cp313-cp313-macosx_26_0_{platform_tag}.whl",
    )

    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel tag"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )
    assert not output.exists()


def test_accepts_wheel_with_compatible_macos_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("26.0", ("", "", ""), ""))
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        filename="fixture_dep-2.0-cp313-cp313-macosx_14_0_arm64.whl",
    )

    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor,
        manager_lock_path=lock,
        wheelhouse=wheelhouse,
        output=output,
        verifier=_verify,
    )

    assert evidence["status"] == "COMPLETE"
    assert (output / "fixture_dep/__init__.py").read_bytes() == b"VALUE = 2\n"


@pytest.mark.parametrize("platform_tag", ["arm64", "universal2"])
@pytest.mark.parametrize(
    ("interpreter", "wheel_abi"),
    [
        ("cp313", "cp313t"),
        ("cp313", "cp312"),
        ("cp313", "cp313d"),
        ("cp313", "abi3t"),
        ("py3", "cp313"),
        ("py3", "abi3"),
        ("cp314", "abi3"),
        ("cp31", "abi3"),
        ("cp3013", "abi3"),
        ("cp313t", "abi3"),
        ("cp312", "cp312"),
    ],
)
def test_rejects_incompatible_full_wheel_abi_before_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interpreter: str, wheel_abi: str, platform_tag: str
) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.7", ("", "", ""), ""))
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        abi="cp313",
        filename=f"fixture_dep-2.0-{interpreter}-{wheel_abi}-macosx_14_0_{platform_tag}.whl",
    )

    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel tag"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )

    assert not output.exists()


@pytest.mark.parametrize("selected_abi", ["cp311", "cp312", "cp313"])
@pytest.mark.parametrize("platform_tag", ["arm64", "universal2"])
@pytest.mark.parametrize("pair", ["exact", "stable-current", "cp32-abi3", "cp310-abi3", "none", "py3-none"])
def test_preserves_compatible_complete_native_wheel_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected_abi: str, platform_tag: str, pair: str
) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.7", ("", "", ""), ""))
    interpreter, wheel_abi = {
        "exact": (selected_abi, selected_abi),
        "stable-current": (selected_abi, "abi3"),
        "none": (selected_abi, "none"),
        "py3-none": ("py3", "none"),
    }.get(pair, tuple(pair.split("-", 1)))
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        abi=selected_abi,
        filename=f"fixture_dep-2.0-{interpreter}-{wheel_abi}-macosx_14_0_{platform_tag}.whl",
    )

    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor,
        manager_lock_path=lock,
        wheelhouse=wheelhouse,
        output=output,
        verifier=_verify,
    )

    assert evidence["status"] == "COMPLETE"
    assert evidence["abi"] == selected_abi
    assert (output / "fixture_dep/__init__.py").read_bytes() == b"VALUE = 2\n"


@pytest.mark.parametrize("pair", ["cp313-cp313", "cp311-abi3"])
def test_platform_independent_wheels_cannot_claim_a_native_abi(tmp_path: Path, pair: str) -> None:
    descriptor, lock, wheelhouse, output, _ = _bundle(tmp_path, filename=f"fixture_dep-2.0-{pair}-any.whl")

    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel tag"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )

    assert not output.exists()


def test_rejects_native_wheel_when_host_macos_release_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("", ("", "", ""), ""))
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        filename="fixture_dep-2.0-cp313-cp313-macosx_14_0_arm64.whl",
    )

    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel tag"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )
    assert not output.exists()


def test_sdist_returns_actionable_incomplete_without_partial_output(tmp_path: Path) -> None:
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        manager="hatch",
        filename="fixture_dep-2.0.tar.gz",
        kind="sdist",
    )

    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor,
        manager_lock_path=lock,
        wheelhouse=wheelhouse,
        output=output,
        verifier=_verify,
    )

    assert evidence["status"] == "INCOMPLETE"
    assert (
        evidence["diagnostic"] == "build hook required; sealed adapter does not execute project code or host toolchains"
    )
    assert evidence["project_code_executed"] is False
    assert evidence["build_hooks_executed"] is False
    assert not output.exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("descriptor-signature", "authentication"),
        ("descriptor-noncanonical", "canonical"),
        ("lock", "manager lock"),
        ("wheel", "digest"),
        ("extra-wheel", "wheelhouse closure"),
        ("manager", "manager"),
        ("platform", "platform"),
        ("abi", "ABI"),
    ],
)
def test_rejects_substituted_or_unsupported_inputs(tmp_path: Path, mutation: str, message: str) -> None:
    descriptor_path, lock_path, wheelhouse, output, descriptor = _bundle(tmp_path)
    if mutation == "descriptor-signature":
        descriptor["signature"]["value"] = "0" * 64
        descriptor_path.write_bytes(_canonical(descriptor))
    elif mutation == "descriptor-noncanonical":
        descriptor_path.write_text(json.dumps(descriptor, indent=2), encoding="utf-8")
    elif mutation == "lock":
        lock = json.loads(lock_path.read_text())
        lock["selection"]["groups"] = ["dev"]
        lock_path.write_bytes(_canonical(lock))
    elif mutation == "wheel":
        wheel = next(wheelhouse.iterdir())
        changed = bytearray(wheel.read_bytes())
        changed[-1] ^= 0xFF
        wheel.chmod(0o600)
        wheel.write_bytes(changed)
        wheel.chmod(0o400)
    elif mutation == "extra-wheel":
        (wheelhouse / "extra-1.0-py3-none-any.whl").write_bytes(b"extra")
    elif mutation == "manager":
        descriptor["manager"] = {"name": "conda", "version": "1"}
        _resign_descriptor(descriptor_path, descriptor)
    elif mutation == "platform":
        descriptor["platform"] = "linux-x86_64"
        _resign_descriptor(descriptor_path, descriptor)
    else:
        descriptor["abi"] = "cp314"
        _resign_descriptor(descriptor_path, descriptor)

    with pytest.raises(native_project_manager.NativeProjectPreparationError, match=message):
        native_project_manager.prepare_project(
            descriptor_path=descriptor_path,
            manager_lock_path=lock_path,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )
    assert not output.exists()


def _resign_descriptor(path: Path, descriptor: dict[str, Any]) -> None:
    unsigned = {key: value for key, value in descriptor.items() if key not in {"content_sha256", "signature"}}
    descriptor["content_sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()
    signed = {key: value for key, value in descriptor.items() if key != "signature"}
    descriptor["signature"] = {
        "algorithm": "test",
        "key_id": "fixture",
        "value": hashlib.sha256(_canonical(signed)).hexdigest(),
    }
    path.write_bytes(_canonical(descriptor))


@pytest.mark.parametrize(
    "unsafe_name",
    ["../escape.py", "/absolute.py", "pkg\\windows.py", "pkg/../../escape.py"],
)
def test_rejects_wheel_path_escape(tmp_path: Path, unsafe_name: str) -> None:
    descriptor, lock, wheelhouse, output, _ = _bundle(tmp_path, entries={unsafe_name: b"escape"})
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel path"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )
    assert not output.exists()
    assert not (tmp_path / "escape.py").exists()


def test_rejects_symlink_special_file_casefold_and_cross_wheel_collision(tmp_path: Path) -> None:
    descriptor, lock, wheelhouse, output, descriptor_value = _bundle(tmp_path)
    wheel = next(wheelhouse.iterdir())
    wheel.chmod(0o600)
    with zipfile.ZipFile(wheel, "w") as archive:
        link = zipfile.ZipInfo("fixture_dep/link.py")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "target.py")
    wheel.chmod(0o400)
    _rebind_wheel(descriptor, lock, wheel, descriptor_value)
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="link or special"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )

    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path / "casefold",
        entries={"pkg/A.py": b"a", "pkg/a.py": b"b"},
    )
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="case-insensitive"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )


def _rebind_wheel(descriptor_path: Path, lock_path: Path, wheel: Path, descriptor: dict[str, Any]) -> None:
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    descriptor["artifacts"][0]["sha256"] = digest
    descriptor["artifacts"][0]["size"] = wheel.stat().st_size
    lock = json.loads(lock_path.read_text())
    lock["artifacts"][0]["sha256"] = digest
    lock_path.write_bytes(_canonical(lock))
    descriptor["manager_lock"]["sha256"] = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    _resign_descriptor(descriptor_path, descriptor)


def _add_second_wheel(
    descriptor_path: Path,
    lock_path: Path,
    wheelhouse: Path,
    descriptor: dict[str, Any],
    entries: dict[str, bytes],
) -> None:
    filename = "second_dep-1.0-py3-none-any.whl"
    wheel = _wheel(wheelhouse, filename=filename, entries=entries)
    record = {
        **descriptor["artifacts"][0],
        "filename": filename,
        "package": "second-dep",
        "version": "1.0",
        "url": f"https://files.pythonhosted.org/packages/aa/{filename}",
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "size": wheel.stat().st_size,
    }
    descriptor["artifacts"].append(record)
    lock = json.loads(lock_path.read_text())
    lock["artifacts"].append({key: record[key] for key in ("package", "version", "filename", "sha256", "kind", "tags")})
    lock_path.write_bytes(_canonical(lock))
    descriptor["manager_lock"]["sha256"] = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    _resign_descriptor(descriptor_path, descriptor)
    wheel.chmod(0o400)


def test_accepts_repeated_explicit_directory_across_disjoint_wheels(tmp_path: Path) -> None:
    descriptor, lock, wheelhouse, output, value = _bundle(
        tmp_path, entries={"shared/": b"", "shared/first.py": b"FIRST = 1\n"}
    )
    _add_second_wheel(descriptor, lock, wheelhouse, value, {"shared/": b"", "shared/second.py": b"SECOND = 2\n"})

    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor,
        manager_lock_path=lock,
        wheelhouse=wheelhouse,
        output=output,
        verifier=_verify,
    )

    assert evidence["status"] == "COMPLETE"
    assert evidence["artifact_count"] == 2
    assert evidence["file_count"] == 2
    assert (output / "shared/first.py").read_bytes() == b"FIRST = 1\n"
    assert (output / "shared/second.py").read_bytes() == b"SECOND = 2\n"


@pytest.mark.parametrize(
    "second_entries",
    [
        {"shared/": b"", "shared/first.py": b"duplicate"},
        {"shared": b"file instead of directory"},
    ],
)
def test_repeated_directory_still_rejects_file_and_type_collisions(
    tmp_path: Path, second_entries: dict[str, bytes]
) -> None:
    descriptor, lock, wheelhouse, output, value = _bundle(
        tmp_path, entries={"shared/": b"", "shared/first.py": b"FIRST = 1\n"}
    )
    _add_second_wheel(descriptor, lock, wheelhouse, value, second_entries)

    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel output collision"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )
    assert not output.exists()


def test_rejects_wrong_wheel_platform_and_existing_or_symlink_output(tmp_path: Path) -> None:
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path / "x86",
        filename="fixture_dep-2.0-cp313-cp313-macosx_14_0_x86_64.whl",
    )
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel tag"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )

    descriptor, lock, wheelhouse, output, _ = _bundle(tmp_path / "existing")
    output.mkdir()
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="output"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )


def test_limits_zip_member_count_and_uncompressed_bytes_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_project_manager, "MAX_FILES", 1)
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path,
        entries={"pkg/a.py": b"a", "pkg/b.py": b"b"},
    )
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="file count"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )
    assert not output.exists()


def test_rejects_uncompressed_byte_limit_and_bundle_path_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_project_manager, "MAX_UNPACKED_BYTES", 1)
    descriptor, lock, wheelhouse, output, _ = _bundle(tmp_path / "bytes", entries={"pkg/a.py": b"ab"})
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="uncompressed byte"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )

    descriptor, lock, wheelhouse, output, _ = _bundle(tmp_path / "paths")
    substituted = tmp_path / "substituted-wheelhouse"
    substituted.symlink_to(wheelhouse, target_is_directory=True)
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="exact cached bundle"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=substituted,
            output=output,
            verifier=_verify,
        )


def test_interrupted_atomic_publication_removes_partial_output_and_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor, lock, wheelhouse, output, _ = _bundle(tmp_path)

    def interrupted(_source: Path, _destination: Path) -> None:
        raise OSError("interrupted")

    monkeypatch.setattr(native_project_manager.os, "rename", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor,
            manager_lock_path=lock,
            wheelhouse=wheelhouse,
            output=output,
            verifier=_verify,
        )

    assert not output.exists()
    assert not (output.parent / f".{output.name}.installing").exists()
    assert not list(output.parent.glob(f".{output.name}.*.partial"))


def _sign_for_broker(
    descriptor_path: Path,
    private_key: ed25519.Ed25519PrivateKey,
    public_pem: bytes,
) -> None:
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    signed = {key: value for key, value in descriptor.items() if key != "signature"}
    descriptor["signature"] = {
        "algorithm": "Ed25519-SHA256",
        "key_id": hashlib.sha256(public_pem).hexdigest(),
        "value": base64.b64encode(private_key.sign(_canonical(signed))).decode("ascii"),
    }
    descriptor_path.write_bytes(_canonical(descriptor))


def _broker_invocation(
    tmp_path: Path,
    *,
    manager: str = "pip",
    kind: str = "wheel",
) -> tuple[Path, Path, Path, Path, Path, ed25519.Ed25519PrivateKey, bytes]:
    descriptor, _lock, _wheelhouse, _prepared, _value = _bundle(
        tmp_path / "staging",
        manager=manager,
        filename="fixture_dep-2.0.tar.gz" if kind == "sdist" else "fixture_dep-2.0-py3-none-any.whl",
        kind=kind,
    )
    project = tmp_path / "project"
    project.mkdir(mode=0o755)
    bundle = project / ".specfact-native-project"
    shutil.move(str(descriptor.parent), bundle)
    descriptor = bundle / "descriptor.json"

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    capsule = tmp_path / "capsule"
    trust = capsule / "trust"
    trust.mkdir(parents=True, mode=0o700)
    key_path = trust / "project-acquisition-public.pem"
    key_path.write_bytes(public_pem)
    key_path.chmod(0o400)
    capsule.chmod(0o700)
    _sign_for_broker(descriptor, private_key, public_pem)

    output = tmp_path / "output"
    output.mkdir(mode=0o700)
    for name in ("managed-stdout.bin", "managed-stderr.bin"):
        path = output / name
        path.write_bytes(b"")
        path.chmod(0o600)
    temporary = tmp_path / "temporary"
    temporary.mkdir(mode=0o700)
    project.chmod(0o555)
    return capsule, project, output, temporary, descriptor, private_key, public_pem


def _invoke_broker(
    monkeypatch: pytest.MonkeyPatch,
    capsule: Path,
    project: Path,
    output: Path,
    temporary: Path,
    manager: str,
) -> int:
    monkeypatch.setattr(
        native_project_manager.sys,
        "argv",
        [
            "native_project_manager",
            str(capsule),
            str(project),
            str(output),
            str(temporary),
            manager,
        ],
    )
    return native_project_manager.main()


def test_broker_entry_point_prepares_fixed_layout_and_writes_canonical_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(tmp_path)

    exit_code = _invoke_broker(monkeypatch, capsule, project, output, temporary, "pip")

    assert exit_code == native_project_manager.EXIT_COMPLETE
    assert (output / "site-packages/fixture_dep/__init__.py").read_bytes() == b"VALUE = 2\n"
    result_path = output / "project-preparation.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result == {
        "evidence": result["evidence"],
        "schema": "specfact-native-project-preparation-result-v1",
        "status": "COMPLETE",
    }
    assert result["evidence"]["manager"] == {"name": "pip", "version": "26.2.1"}
    assert result["evidence"]["network_used"] is False
    assert result["evidence"]["project_code_executed"] is False
    assert result_path.read_bytes() == _canonical(result) + b"\n"


def test_broker_entry_point_returns_explicit_incomplete_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(
        tmp_path,
        manager="hatch",
        kind="sdist",
    )

    exit_code = _invoke_broker(monkeypatch, capsule, project, output, temporary, "hatch")

    assert exit_code == native_project_manager.EXIT_INCOMPLETE
    result = json.loads((output / "project-preparation.json").read_text(encoding="utf-8"))
    assert result["status"] == "INCOMPLETE"
    assert result["evidence"]["status"] == "INCOMPLETE"
    assert not (output / "site-packages").exists()


@pytest.mark.parametrize(
    "mutation",
    ["algorithm", "key-id", "base64", "signature-size", "signature-value", "signature-text-bound"],
)
def test_broker_entry_point_rejects_non_ed25519_sha256_envelopes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    capsule, project, output, temporary, descriptor_path, _private_key, _public_pem = _broker_invocation(tmp_path)
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if mutation == "algorithm":
        descriptor["signature"]["algorithm"] = "ed25519"
    elif mutation == "key-id":
        descriptor["signature"]["key_id"] = "0" * 64
    elif mutation == "base64":
        descriptor["signature"]["value"] = "not+strict/base64%"
    elif mutation == "signature-size":
        descriptor["signature"]["value"] = base64.b64encode(b"x" * 65).decode("ascii")
    elif mutation == "signature-value":
        descriptor["signature"]["value"] = base64.b64encode(b"x" * 64).decode("ascii")
    else:
        descriptor["signature"]["value"] = "A" * (native_project_manager.MAX_SIGNATURE_TEXT_BYTES + 1)
    descriptor_path.write_bytes(_canonical(descriptor))

    exit_code = _invoke_broker(monkeypatch, capsule, project, output, temporary, "pip")

    assert exit_code == native_project_manager.EXIT_INVALID_REQUEST
    result = json.loads((output / "project-preparation.json").read_text(encoding="utf-8"))
    assert result["status"] == "REJECTED"
    assert result["evidence"]["project_code_executed"] is False
    assert not (output / "site-packages").exists()


def test_broker_entry_point_rejects_manager_key_and_output_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(tmp_path)
    assert _invoke_broker(monkeypatch, capsule, project, output, temporary, "uv") == (
        native_project_manager.EXIT_INVALID_REQUEST
    )

    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(
        tmp_path / "mutable-key"
    )
    (capsule / "trust/project-acquisition-public.pem").chmod(0o600)
    assert _invoke_broker(monkeypatch, capsule, project, output, temporary, "pip") == (
        native_project_manager.EXIT_INVALID_REQUEST
    )

    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(
        tmp_path / "wrong-key-type"
    )
    key = capsule / "trust/project-acquisition-public.pem"
    rsa_pem = (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    key.chmod(0o600)
    key.write_bytes(rsa_pem)
    key.chmod(0o400)
    assert _invoke_broker(monkeypatch, capsule, project, output, temporary, "pip") == (
        native_project_manager.EXIT_INVALID_REQUEST
    )

    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(
        tmp_path / "output-collision"
    )
    (output / "unexpected").write_bytes(b"")
    assert _invoke_broker(monkeypatch, capsule, project, output, temporary, "pip") == (
        native_project_manager.EXIT_OUTPUT_COLLISION
    )
    assert not (output / "project-preparation.json").exists()


def test_broker_entry_point_requires_both_broker_output_files_and_bounded_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(tmp_path)
    (output / "managed-stderr.bin").unlink()
    assert _invoke_broker(monkeypatch, capsule, project, output, temporary, "pip") == (
        native_project_manager.EXIT_OUTPUT_COLLISION
    )

    capsule, project, output, temporary, _descriptor, _private_key, _public_pem = _broker_invocation(
        tmp_path / "oversized-key"
    )
    key = capsule / "trust/project-acquisition-public.pem"
    key.chmod(0o600)
    key.write_bytes(b"x" * (native_project_manager.MAX_PUBLIC_KEY_BYTES + 1))
    key.chmod(0o400)
    assert _invoke_broker(monkeypatch, capsule, project, output, temporary, "pip") == (
        native_project_manager.EXIT_INVALID_REQUEST
    )


@pytest.mark.parametrize("selected_abi", ["cp311", "cp312", "cp313"])
@pytest.mark.parametrize("platform_tag", ["any", "macosx_14_0_arm64", "macosx_14_0_universal2"])
def test_minor_specific_pure_wheels_prepare_authenticated_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected_abi: str, platform_tag: str
) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.7", ("", "", ""), ""))
    interpreter = selected_abi.replace("cp", "py", 1)
    descriptor, lock, wheelhouse, output, _ = _bundle(
        tmp_path, abi=selected_abi, filename=f"fixture_dep-2.0-{interpreter}-none-{platform_tag}.whl"
    )
    evidence = native_project_manager.prepare_project(
        descriptor_path=descriptor, manager_lock_path=lock, wheelhouse=wheelhouse, output=output, verifier=_verify
    )
    assert evidence["status"] == "COMPLETE"
    assert evidence["abi"] == selected_abi
    assert (output / "fixture_dep/__init__.py").read_bytes() == b"VALUE = 2\n"


@pytest.mark.parametrize(
    "tag",
    [
        "py314-none-any",
        "py3013-none-any",
        "py313-cp313-any",
        "py314-none-macosx_14_0_arm64",
        "py313-cp313-macosx_14_0_arm64",
        "py313-none-macosx_14_0_x86_64",
        "py313-none-macosx_26_0_arm64",
    ],
)
def test_minor_specific_pure_wheels_retain_admission_restrictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tag: str
) -> None:
    monkeypatch.setattr(platform, "mac_ver", lambda: ("14.7", ("", "", ""), ""))
    descriptor, lock, wheelhouse, output, _ = _bundle(tmp_path, abi="cp313", filename=f"fixture_dep-2.0-{tag}.whl")
    with pytest.raises(native_project_manager.NativeProjectPreparationError, match="wheel tag"):
        native_project_manager.prepare_project(
            descriptor_path=descriptor, manager_lock_path=lock, wheelhouse=wheelhouse, output=output, verifier=_verify
        )
    assert not output.exists()
