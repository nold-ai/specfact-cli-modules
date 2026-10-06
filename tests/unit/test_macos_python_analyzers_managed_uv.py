"""Maintained manager provenance must survive real preparation orchestration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import assemble_macos_native_capsule as assembler, build_macos_managed_uv as uv_builder
from scripts.macos_managed_boundary import python_analyzers as analyzers
from tests.unit import test_assemble_macos_native_capsule as assembly_tests, test_build_macos_managed_uv as uv_tests


upstream = uv_tests.upstream
assembly_case = assembly_tests.assembly_case


@pytest.fixture
def uv_artifact(tmp_path, upstream):
    binary = tmp_path / "uv-image"
    binary.write_bytes(b"maintained signed image")
    toolchain = tmp_path / "rust"
    (toolchain / "bin").mkdir(parents=True)
    for name in ("rustc", "cargo"):
        (toolchain / "bin" / name).write_bytes(name.encode())
    artifact = tmp_path / "uv-artifact"
    artifact.mkdir()
    uv_builder.write_artifacts(artifact, binary, "1.96.0", upstream, toolchain, "a" * 64)
    uv_builder.validate_artifact(artifact)
    return artifact


def _prepare_case(monkeypatch, tmp_path, artifact):
    (tmp_path / "venv/bin").mkdir(parents=True)
    (tmp_path / "venv/bin/python").write_bytes(b"input interpreter")
    root = tmp_path / "prepared"
    root.mkdir()
    payload = root / "payload"
    payload.mkdir()
    target = payload / "python"
    target.write_bytes(b"interpreter")
    commands = []
    details = (
        f"Identifier={uv_builder.SIGNING_IDENTIFIER}\n"
        "Format=Mach-O thin (arm64)\nflags=0x10002(adhoc,runtime)\nSignature=adhoc\n"
    )

    def command(argv):
        commands.append(argv)
        if "--force" in argv:
            image = Path(argv[-1])
            image.write_bytes(image.read_bytes() + b"changed-signature")
        return SimpleNamespace(stderr=details, stdout="")

    monkeypatch.setenv("SPECFACT_MANAGED_UV_ARTIFACT", str(artifact))
    monkeypatch.delenv("SPECFACT_MANAGED_GIT_ARTIFACT", raising=False)
    monkeypatch.setattr(analyzers.python, "prepare", lambda *_args: {"payload": payload, "target": target})
    monkeypatch.setattr(analyzers, "copy_site", lambda *_args: {})
    monkeypatch.setattr(analyzers, "validate_semgrep", lambda _candidate: None)
    monkeypatch.setattr(analyzers, "copy_node", lambda _payload: {})
    monkeypatch.setattr(analyzers.macho, "_inspect_image", lambda *_args: None)
    monkeypatch.setattr(
        analyzers,
        "static_inventory",
        lambda _payload: {"images": [{"path": "uv/bin/uv", "architectures": ["arm64"]}]},
    )
    monkeypatch.setattr(analyzers.control.STARTUP, "command", command)
    return root, commands


def test_preparation_preserves_verified_uv_image(monkeypatch, tmp_path, uv_artifact):
    root, commands = _prepare_case(monkeypatch, tmp_path, uv_artifact)
    before = (uv_artifact / "bin/uv").read_bytes()
    candidate = analyzers.prepare(root, tmp_path / "venv", "3.13")
    assert (root / "payload/uv/bin/uv").read_bytes() == before
    assert uv_builder.validate_artifact(root / "payload/uv") == candidate["managed_uv"]
    assert all("--force" not in command for command in commands)
    assert candidate["signed_images"][0]["sha256"] == candidate["managed_uv"]["binary_sha256"]


def test_preparation_rejects_uv_artifact_mutation_during_native_inventory(monkeypatch, tmp_path, uv_artifact):
    root, _commands = _prepare_case(monkeypatch, tmp_path, uv_artifact)
    calls = 0

    def inventory(payload):
        nonlocal calls
        calls += 1
        if calls == 2:
            license_path = payload / "uv/licenses/LICENSE-MIT"
            license_path.chmod(0o644)
            license_path.write_bytes(b"changed license")
            license_path.chmod(0o444)
        return {"images": [{"path": "uv/bin/uv", "architectures": ["arm64"]}]}

    monkeypatch.setattr(analyzers, "static_inventory", inventory)
    with pytest.raises(ValueError, match="digest"):
        analyzers.prepare(root, tmp_path / "venv", "3.13")


def _add_uv_input(case, artifact):
    analyzer, _component, _output = case
    payload = analyzer / "payload"
    payload.chmod(0o755)
    shutil.copytree(artifact, payload / "uv")
    payload.chmod(0o555)
    metadata = analyzer / "candidate.json"
    candidate = json.loads(metadata.read_text())
    candidate["managed_uv"] = uv_builder.validate_artifact(payload / "uv")
    candidate["inventory"] = assembly_tests._inventory(payload)
    candidate["native_closure"]["images"].append({"path": "uv/bin/uv", "architectures": ["arm64"]})
    candidate["signed_images"].append(
        {
            "path": "uv/bin/uv",
            "sha256": uv_builder.digest(payload / "uv/bin/uv"),
            "signing": "Format=Mach-O thin (arm64)\nflags=0x10002(adhoc,runtime)\nSignature=adhoc\n",
            "entitlements": "",
        }
    )
    metadata.write_text(json.dumps(candidate))
    return candidate


@pytest.mark.parametrize("fault", ["missing", "receipt", "binary", "license"])
def test_assembly_rechecks_complete_uv_provenance(assembly_case, uv_artifact, fault):
    analyzer, component, output = assembly_case
    candidate = _add_uv_input(assembly_case, uv_artifact)
    if fault == "missing":
        del candidate["managed_uv"]
    elif fault == "receipt":
        candidate["managed_uv"]["binary_sha256"] = "0" * 64
    else:
        name = "uv/bin/uv" if fault == "binary" else "uv/licenses/LICENSE-MIT"
        image = analyzer / "payload" / name
        mode = image.stat().st_mode & 0o777
        image.chmod(0o644)
        image.write_bytes(b"changed bytes")
        image.chmod(mode)
        candidate["inventory"] = assembly_tests._inventory(analyzer / "payload")
        if fault == "binary":
            candidate["signed_images"][-1]["sha256"] = uv_builder.digest(analyzer / "payload" / name)
    (analyzer / "candidate.json").write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match=r"uv|digest|provenance"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=assembly_tests._signature,
        )
    assert not output.exists()


def test_assembly_preserves_verified_uv_bytes_and_receipt(assembly_case, uv_artifact):
    analyzer, component, output = assembly_case
    candidate = _add_uv_input(assembly_case, uv_artifact)
    before = (uv_artifact / "bin/uv").read_bytes()
    assembler.assemble_macos_native_capsule(
        analyzer_root=analyzer,
        component_root=component,
        output_root=output,
        environment_id="darwin-arm64-cp312",
        signature_inspector=assembly_tests._signature,
    )
    assert (output / "tools/uv").read_bytes() == before
    assert (analyzer / "payload/uv/bin/uv").read_bytes() == before
    receipt = json.loads((output / "provenance/analyzer.json").read_text())
    assert receipt["managed_uv"] == candidate["managed_uv"]
    assert receipt["production_eligible"] is False
