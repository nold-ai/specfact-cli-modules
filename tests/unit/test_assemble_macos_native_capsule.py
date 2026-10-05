from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import assemble_macos_native_capsule as assembler, build_macos_native_capsule as builder
from tests.unit import test_build_macos_native_capsule as build_tests


managed_git_case = build_tests.managed_git_case


def test_assembly_cli_starts_without_repository_pythonpath(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(Path(assembler.__file__).resolve()), "--help"],
        cwd=tmp_path,
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "--analyzer-root" in result.stdout


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inventory(root: Path) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {".": {"kind": "directory", "mode": stat.S_IMODE(root.stat().st_mode)}}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            result[relative] = {"kind": "directory", "mode": stat.S_IMODE(path.stat().st_mode)}
        else:
            result[relative] = {
                "kind": "file",
                "mode": stat.S_IMODE(path.stat().st_mode),
                "sha256": _digest(path),
                "size": path.stat().st_size,
            }
    return result


@pytest.fixture
def assembly_case(tmp_path: Path):
    analyzer = tmp_path / "analyzer"
    payload = analyzer / "payload"
    files = {
        "bin/python3.12": b"python-image",
        "bin/ruff": b"ruff-image",
        "site-packages/semgrep/bin/semgrep-core": b"semgrep-image",
        "site-packages/semgrep/bin/libs/libdwarf.2.dylib": b"semgrep-dylib",
        "lib/python312.zip": b"stdlib archive",
        "lib/python3.12/os.py": b"name = 'posix'\n",
        "lib/python3.12/lib-dynload/loader.so": b"loader-image",
        "lib/libpython3.12.dylib": b"python-library",
        "site-packages/demo/main.py": b"VALUE = 1\n",
        "site-packages/demo-1.0.dist-info/licenses/license.txt": b"demo license\n",
        "trusted/python_analyzer_worker.py": b"print('fixture worker')\n",
        "trusted/specfact_code_review/run/native_worker.py": b"def main(): return 0\n",
        "trusted/specfact_code_review/run/native_tool_worker.py": b"def main(): return 0\n",
        "trusted/specfact_code_review/run/native_project_manager.py": b"def main(): return 0\n",
        "trusted/specfact_code_review/run/native_project_pip.py": b"def main(): return 0\n",
        "trusted/specfact_code_review/run/native_analyzer_view.py": b"VIEW_NAME = '.specfact-native-analyzers'\n",
        "trusted/specfact_code_review/run/native_child_worker.py": b"def main(): return 0\n",
        "trusted/specfact_code_review/run/native_managed_process.py": b"VERSION = 1\n",
        "trusted/specfact_code_review/run/native_project_hooks.py": b"def main(): return 0\n",
        "trusted/specfact_code_review/resources/keys/project-acquisition-public.pem": (
            b"-----BEGIN PUBLIC KEY-----\n"
            b"MCowBQYDK2VwAyEAI97L4DRdUtcB3lul4BtBsrpF5hWBu7z5Z5fNA6/AY18=\n"
            b"-----END PUBLIC KEY-----\n"
        ),
        "trusted/specfact_code_review/tools/analyzer.py": b"VALUE = 1\n",
        "node/bin/node": b"node-image",
        "node/basedpyright/index.js": b"'use strict';\n",
        "fixtures/clean.py": b"value = 1\n",
        "managers/pip/adapter.json": b"{}\n",
    }
    for name, data in files.items():
        path = payload / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(
            0o555
            if name in {"bin/python3.12", "bin/ruff", "node/bin/node", "site-packages/semgrep/bin/semgrep-core"}
            else 0o444
        )
    for path in sorted((item for item in payload.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o555)
    payload.chmod(0o555)
    native_paths = {
        "bin/python3.12",
        "bin/ruff",
        "node/bin/node",
        "site-packages/semgrep/bin/semgrep-core",
        "site-packages/semgrep/bin/libs/libdwarf.2.dylib",
    }
    candidate = {
        "version": "3.12",
        "payload": "/private/build/input/payload",
        "platform_evidence": {"system": "Darwin", "machine": "arm64"},
        "inventory": _inventory(payload),
        "native_closure": {"images": [{"path": name, "architectures": ["arm64"]} for name in sorted(native_paths)]},
        "signed_images": [
            {
                "path": name,
                "sha256": _digest(payload / name),
                "signing": "Format=Mach-O thin (arm64)\nflags=0x10002(adhoc,runtime)\nSignature=adhoc\n",
                "entitlements": "",
            }
            for name in sorted(native_paths)
        ],
        "profile_id": "cpython-analyzers-empty-entitlements-v1",
        "semgrep_plan_id": "semgrep-1.175.0-offline-ca-v2",
    }
    (analyzer / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")

    component = tmp_path / "component"
    component_files = {
        "bin/specfact-native-broker": b"broker-image",
        "bin/specfact-native-bootstrap": b"bootstrap-image",
        "bin/specfact-native-self-test": b"self-test-image",
        "bin/specfact-native-verifier": b"verifier-image",
        "policy/profile.sb": b"(version 1)(deny default)\n",
    }
    for name, data in component_files.items():
        path = component / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o755 if name.startswith("bin/") else 0o444)
    metadata = {
        "schema": "specfact-native-component-v1",
        "platform": "darwin-arm64",
        "status": "candidate",
        "minimum_macos": "14.0",
        "protocol": 1,
        "broker_designated_requirement": 'cdhash H"' + "a" * 40 + '"',
        "signing": {"mode": "adhoc", "hardened_runtime": True, "customer_signing_required": False},
        "outputs": sorted(name for name in component_files if name.startswith("bin/")),
        "plans": ["boundary.self-test.v1", "analyzer.ruff.v1", "project.pip.v1"],
        "production_eligible": False,
        "files": {name: _digest(component / name) for name in sorted(component_files)},
    }
    (component / "component.json").write_text(json.dumps(metadata), encoding="utf-8")
    return analyzer, component, tmp_path / "runtime"


def _signature(_path: Path) -> dict[str, object]:
    return {"format": "mach-o", "mode": "adhoc", "hardened_runtime": True, "architecture": "arm64"}


@pytest.fixture
def git_assembly_case(assembly_case, managed_git_case):
    analyzer, component, output = assembly_case
    artifact, _payload, signature = managed_git_case
    payload = analyzer / "payload"
    payload.chmod(0o755)
    receipt = builder.install_managed_git_input(artifact, payload, signature_inspector=lambda _path: signature)
    candidate_path = analyzer / "candidate.json"
    candidate = json.loads(candidate_path.read_bytes())
    candidate["managed_git"] = receipt
    candidate["inventory"] = _inventory(payload)
    candidate["native_closure"]["images"].append({"path": "git/bin/git", "architectures": ["arm64"]})
    candidate["signed_images"].append(
        {
            "path": "git/bin/git",
            "sha256": _digest(payload / "git/bin/git"),
            "signing": "Format=Mach-O thin (arm64)\nflags=0x10002(adhoc,runtime)\nSignature=adhoc\n",
            "entitlements": "",
        }
    )
    candidate_path.write_text(json.dumps(candidate))
    broker = component / "bin/specfact-native-broker"
    broker.write_bytes(b"broker-image\0" + receipt["signing"]["requirement"].encode() + b"\0")
    metadata_path = component / "component.json"
    metadata = json.loads(metadata_path.read_bytes())
    metadata["files"]["bin/specfact-native-broker"] = _digest(broker)
    metadata_path.write_text(json.dumps(metadata))

    def inspector(path):
        if path.name == "git":
            return {**signature, "architecture": "arm64"}
        return {**_signature(path), "cdhash": "a" * 40}

    return analyzer, component, output, receipt, inspector


def test_managed_git_assembly_maps_verified_input_and_binds_broker(git_assembly_case):
    analyzer, component, output, receipt, inspector = git_assembly_case
    result = assembler.assemble_macos_native_capsule(
        analyzer_root=analyzer,
        component_root=component,
        output_root=output,
        environment_id="darwin-arm64-cp312",
        signature_inspector=inspector,
    )
    assert (output / "tools/git").read_bytes() == (analyzer / "payload/git/bin/git").read_bytes()
    assert json.loads((output / "provenance/managed-git/input.json").read_bytes()) == receipt
    assert (output / "licenses/managed-git/Git-COPYING").is_file()
    assert not list(output.rglob("build.log"))
    metadata = json.loads((output / "provenance/native-component.json").read_bytes())
    assert metadata["managed_tool_requirements"] == {"tools/git": receipt["signing"]["requirement"]}
    assert "tools/git" in json.loads(result.closure.read_bytes())["managed-git-v1"]
    assert builder.verify_managed_git_runtime(output, signature_inspector=inspector) == receipt


@pytest.mark.parametrize("fault", ["broker-binding", "broker-identity", "receipt", "git-identity"])
def test_managed_git_assembly_rejects_substitution_before_outputs(git_assembly_case, fault):
    analyzer, component, output, _receipt, inspector = git_assembly_case
    if fault == "broker-binding":
        broker = component / "bin/specfact-native-broker"
        broker.write_bytes(b"broker-image")
        metadata_path = component / "component.json"
        metadata = json.loads(metadata_path.read_bytes())
        metadata["files"]["bin/specfact-native-broker"] = _digest(broker)
        metadata_path.write_text(json.dumps(metadata))
    elif fault == "broker-identity":
        original = inspector

        def inspector(path):
            return {**original(path), "cdhash": "c" * 40} if path.name == "specfact-native-broker" else original(path)
    elif fault == "git-identity":
        original = inspector

        def inspector(path):
            return {**original(path), "cdhash": "c" * 40} if path.name == "git" else original(path)
    else:
        receipt = analyzer / "payload/git/provenance/input.json"
        receipt.chmod(0o644)
        receipt.write_text("{}")
        receipt.chmod(0o444)
        candidate_path = analyzer / "candidate.json"
        candidate = json.loads(candidate_path.read_bytes())
        candidate["inventory"] = _inventory(analyzer / "payload")
        candidate_path.write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match=r"Git|git|broker"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=inspector,
        )
    assert not output.exists()
    assert not output.with_suffix(".closure.json").exists()


def test_assembles_complete_deterministic_runtime_and_builder_closure(assembly_case, tmp_path: Path) -> None:
    analyzer, component, output = assembly_case
    first = assembler.assemble_macos_native_capsule(
        analyzer_root=analyzer,
        component_root=component,
        output_root=output,
        environment_id="darwin-arm64-cp312",
        signature_inspector=_signature,
    )
    second = assembler.assemble_macos_native_capsule(
        analyzer_root=analyzer,
        component_root=component,
        output_root=tmp_path / "runtime-two",
        environment_id="darwin-arm64-cp312",
        signature_inspector=_signature,
    )

    assert (output / "python/bin/python3").read_bytes() == b"python-image"
    assert (output / "bin/specfact-native-broker").read_bytes() == b"broker-image"
    assert (output / "bin/specfact-native-verifier").read_bytes() == b"verifier-image"
    assert (output / "tools/ruff").read_bytes() == b"ruff-image"
    assert (output / "tools/node").read_bytes() == b"node-image"
    assert (output / "tools/semgrep-core").read_bytes() == b"semgrep-image"
    assert (output / "tools/libs/libdwarf.2.dylib").read_bytes() == b"semgrep-dylib"
    assert (output / "trust/project-acquisition-public.pem").is_file()
    assert (output / "python/lib/python3.12/lib-dynload/.specfact-empty").is_file()
    assert (output / "policy/profile.sb").is_file()
    site = output / "python/lib/python3.12/site-packages"
    assert (site / "python_analyzer_worker.py").is_file()
    assert (site / "demo/main.py").is_file()
    assert (site / "specfact_code_review/tools/analyzer.py").is_file()
    assert (site / "specfact_code_review/run/native_worker.py").is_file()
    assert (site / "specfact_code_review/run/native_tool_worker.py").is_file()
    assert (site / "specfact_code_review/run/native_project_manager.py").is_file()
    assert (output / "python/managers/pip/adapter.json").is_file()
    assert (output / "licenses/inventory.json").is_file()
    assert (output / "provenance/assembly.json").is_file()
    assert first.closure.read_bytes() == second.closure.read_bytes()
    closure = json.loads(first.closure.read_bytes())
    declared = [name for members in closure.values() for name in members]
    observed = sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file())
    assert sorted(declared) == observed
    assert len(declared) == len(set(declared))
    files = assembler.artifact_builder._walk_runtime(output)
    assert assembler.artifact_builder._validate_closure(closure, files) == closure
    assert all("/private/" not in path.read_text(errors="ignore") for path in output.glob("provenance/*.json"))
    assert first.runtime_digest == second.runtime_digest


@pytest.mark.parametrize("stage", ["runtime", "closure"])
def test_failed_concurrent_assembly_preserves_another_invocations_outputs(assembly_case, monkeypatch, stage):
    analyzer, component, output = assembly_case
    closure = output.parent / f"{output.name}.closure.json"
    replace, opened = os.replace, os.open

    def publish(source, destination):
        if Path(destination) == output and stage == "runtime":
            output.mkdir()
            (output / "other-owner").write_text("successful invocation")
            closure.write_text("other closure")
            raise FileExistsError("another assembly completed")
        return replace(source, destination)

    def create(path, flags, *args, **kwargs):
        if Path(path) == closure and stage == "closure":
            closure.write_text("other closure")
        return opened(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "replace", publish)
    monkeypatch.setattr(os, "open", create)
    with pytest.raises(FileExistsError):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=_signature,
        )
    assert closure.read_text() == "other closure"
    if stage == "runtime":
        assert (output / "other-owner").read_text() == "successful invocation"
    else:
        assert not output.exists()


def test_isolated_getpath_resolves_fixed_workers_without_environment_override(
    assembly_case, monkeypatch: pytest.MonkeyPatch
) -> None:
    analyzer, component, output = assembly_case
    monkeypatch.setenv("PYTHONHOME", "/untrusted/home")
    monkeypatch.setenv("PYTHONPATH", "/untrusted/path")
    monkeypatch.setenv("PYTHONSTARTUP", "/untrusted/startup.py")
    assembler.assemble_macos_native_capsule(
        analyzer_root=analyzer,
        component_root=component,
        output_root=output,
        environment_id="darwin-arm64-cp312",
        signature_inspector=_signature,
    )

    paths = assembler.isolated_cpython_search_paths(output, "darwin-arm64-cp312")

    assert paths == (
        output / "python/lib/python312.zip",
        output / "python/lib/python3.12",
        output / "python/lib/python3.12/lib-dynload",
        output / "python/lib/python3.12/site-packages",
    )
    site = output / "python/lib/python3.12/site-packages/specfact_code_review/run"
    assert assembler.fixed_module_source(paths, "specfact_code_review.run.native_worker") == site / "native_worker.py"
    assert assembler.fixed_module_source(paths, "specfact_code_review.run.native_tool_worker") == (
        site / "native_tool_worker.py"
    )
    assert assembler.fixed_module_source(paths, "specfact_code_review.run.native_project_manager") == (
        site / "native_project_manager.py"
    )
    assert all("untrusted" not in str(path) for path in paths)


@pytest.mark.parametrize("version", ["3.10", "3.14", "3.12"])
def test_rejects_missing_or_mismatched_abi(assembly_case, version: str) -> None:
    analyzer, component, output = assembly_case
    candidate_path = analyzer / "candidate.json"
    candidate = json.loads(candidate_path.read_text())
    if version == "3.12":
        (analyzer / "payload/bin").chmod(0o755)
        (analyzer / "payload/bin/python3.12").unlink()
    else:
        candidate["version"] = version
        candidate_path.write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match=r"ABI|interpreter|environment|inventory"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=_signature,
        )


@pytest.mark.parametrize("fault", ["digest", "extra", "symlink", "case-collision"])
def test_rejects_modified_undeclared_or_unsafe_analyzer_payload(assembly_case, fault: str) -> None:
    analyzer, component, output = assembly_case
    payload = analyzer / "payload"
    payload.chmod(0o755)
    if fault == "digest":
        (payload / "trusted/python_analyzer_worker.py").chmod(0o644)
        (payload / "trusted/python_analyzer_worker.py").write_text("changed")
    elif fault == "extra":
        (payload / "undeclared.txt").write_text("extra")
    elif fault == "symlink":
        (payload / "link").symlink_to(payload / "fixtures/clean.py")
    else:
        candidate_path = analyzer / "candidate.json"
        candidate = json.loads(candidate_path.read_text())
        candidate["inventory"]["fixtures/CLEAN.py"] = dict(candidate["inventory"]["fixtures/clean.py"])
        candidate_path.write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match=r"inventory|undeclared|symlink|case"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=_signature,
        )


@pytest.mark.parametrize(
    "name",
    [
        "trusted/specfact_code_review/run/native_worker.py",
        "trusted/specfact_code_review/run/native_tool_worker.py",
        "trusted/specfact_code_review/run/native_project_manager.py",
    ],
)
def test_rejects_analyzer_payload_missing_a_trusted_runtime_entrypoint(assembly_case, name: str) -> None:
    analyzer, component, output = assembly_case
    payload = analyzer / "payload"
    candidate_path = analyzer / "candidate.json"
    candidate = json.loads(candidate_path.read_text())
    path = payload / name
    path.parent.chmod(0o755)
    path.unlink()
    path.parent.chmod(0o555)
    candidate["inventory"].pop(name)
    candidate_path.write_text(json.dumps(candidate))

    with pytest.raises(ValueError, match="trusted worker"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=_signature,
        )


@pytest.mark.parametrize("fault", ["partial", "digest", "extra", "platform", "signing"])
def test_rejects_partial_modified_or_mismatched_native_component(assembly_case, fault: str) -> None:
    analyzer, component, output = assembly_case
    metadata_path = component / "component.json"
    metadata = json.loads(metadata_path.read_text())
    if fault == "partial":
        (component / "bin/specfact-native-bootstrap").unlink()
    elif fault == "digest":
        (component / "bin/specfact-native-broker").write_text("changed")
    elif fault == "extra":
        (component / "generated_requirements.h").write_text("undeclared")
    elif fault == "platform":
        metadata["platform"] = "linux-x86_64"
        metadata_path.write_text(json.dumps(metadata))
    else:
        metadata["signing"]["mode"] = "developer-id"
        metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match=r"component|digest|undeclared|platform|signing"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=_signature,
        )


def test_rejects_observed_native_signature_or_architecture_mismatch(assembly_case) -> None:
    analyzer, component, output = assembly_case
    with pytest.raises(ValueError, match=r"signature|architecture"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=lambda _path: {
                "format": "mach-o",
                "mode": "adhoc",
                "hardened_runtime": True,
                "architecture": "x86_64",
            },
        )


def test_output_is_fresh_private_and_input_bytes_are_not_mutated(assembly_case) -> None:
    analyzer, component, output = assembly_case
    before = _digest(component / "bin/specfact-native-broker")
    output.mkdir()
    with pytest.raises(ValueError, match="must not exist"):
        assembler.assemble_macos_native_capsule(
            analyzer_root=analyzer,
            component_root=component,
            output_root=output,
            environment_id="darwin-arm64-cp312",
            signature_inspector=_signature,
        )
    assert _digest(component / "bin/specfact-native-broker") == before


def test_payload_copy_is_streamed_without_path_read_bytes(assembly_case, monkeypatch: pytest.MonkeyPatch) -> None:
    analyzer, component, output = assembly_case
    protected = analyzer / "payload/site-packages/demo/main.py"
    original = Path.read_bytes

    def guarded(path: Path) -> bytes:
        if path == protected:
            raise AssertionError("ordinary payload files must be streamed")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    assembler.assemble_macos_native_capsule(
        analyzer_root=analyzer,
        component_root=component,
        output_root=output,
        environment_id="darwin-arm64-cp312",
        signature_inspector=_signature,
    )


def test_cli_exposes_only_assembly_inputs() -> None:
    parser = assembler.build_parser()
    options = {action.dest for action in parser._actions}
    assert {"analyzer_root", "component_root", "output_root", "environment_id"}.issubset(options)
    assert options.isdisjoint({"sign", "download", "compile"})
