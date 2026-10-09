"""Dedicated candidate tests; never enable a production backend."""

import importlib.util
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "scripts/macos_managed_boundary/python_candidate.py"


def candidate():
    spec = importlib.util.spec_from_file_location("python_candidate_test", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_versions_are_explicit():
    module = candidate()
    assert module.version_key("3.11") == "311"
    assert module.version_key("3.12") == "312"
    assert module.version_key("3.13") == "313"
    for value in ("3.10", "3.14", "3.11.1", "../3.11", "311"):
        with pytest.raises(ValueError):
            module.version_key(value)


def test_inventory_rejects_changes_and_symlinks(tmp_path):
    module = candidate()
    directory = tmp_path / "payload"
    directory.mkdir(mode=0o700)
    path = directory / "code.py"
    path.write_text("pass\n")
    path.chmod(0o444)
    directory.chmod(0o555)
    expected = module.inventory(directory)
    module.verify_inventory(directory, expected)
    path.chmod(0o644)
    with pytest.raises(ValueError):
        module.verify_inventory(directory, expected)
    path.chmod(0o444)
    directory.chmod(0o755)
    (directory / "alias").symlink_to(path)
    with pytest.raises(ValueError):
        module.inventory(directory)


def test_safe_summary_never_contains_raw_paths_or_output():
    module = candidate()
    summary = module.safe_summary([{"passed": True, "output": "/secret", "pid": 42}])
    assert summary == {
        "candidate_passed": True,
        "cases": 1,
        "passed": 1,
        "production_approved": False,
        "signed_boundary_verified": False,
        "signing_mode": "ad-hoc",
    }
    assert not module.safe_summary([])["candidate_passed"]
    assert not module.safe_summary([{"passed": False}])["candidate_passed"]


def test_status_requires_verified_entry_and_expected_exit():
    module = candidate()
    status = {"exit": 0, "signal": 0, "traced": True, "output": "python-entry-ns=101\npython-clean-ok\n"}
    marker = {"exec": 123, "verified_ns": 100, "held": False}
    module.verify_status(status, marker, 123, "clean")
    for invalid in (None, {**marker, "exec": 124}, {**marker, "verified_ns": 102}, {**marker, "held": True}):
        with pytest.raises(ValueError):
            module.verify_status(status, invalid, 123, "clean")
    with pytest.raises(ValueError):
        module.verify_status({**status, "exit": 7}, marker, 123, "clean")


def test_input_version_must_match_and_host_alias_rejects(tmp_path):
    module = candidate()
    with pytest.raises(ValueError):
        module.prepare(tmp_path, tmp_path / "missing", "3.14")


def test_bootstrap_keeps_kernel_boundary():
    text = SOURCE.with_suffix(".c").read_text()
    assert "PT_TRACE_ME" in text and "PT_SIGEXC" in text
    assert "execve(FIXED_TARGET" in text
    assert "-I" in text and "-S" in text and "-B" in text
    assert "process-fork" not in text
    assert "(deny default)" in SOURCE.read_text()
    assert "init(PYTHON_PROFILE" in text


def test_profile_explicitly_denies_exception_port_replacement(tmp_path):
    module = candidate()
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "python3.11").write_text("fixture")
    assert "(deny mach-task-exception-port-set)" in module.profile(tmp_path)


def test_second_exec_is_terminated_not_readmitted():
    module = candidate()
    status = {"exit": -1, "signal": 5, "traced": True, "output": "python-entry-ns=101\npython-second-exec\n"}
    module.verify_status(status, {"exec": 123, "verified_ns": 100, "held": False}, 123, "reexec")
    with pytest.raises(ValueError):
        module.verify_status({**status, "signal": 0}, {"exec": 123, "verified_ns": 100, "held": False}, 123, "reexec")


def test_prepare_copies_runtime_bytes_without_candidate_execution(tmp_path, monkeypatch):
    module = candidate()
    runtime = tmp_path / "input"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "bin" / "python3.11").write_bytes(b"candidate-not-executed")
    stdlib = runtime / "lib" / "python3.11"
    (stdlib / "encodings").mkdir(parents=True)
    (stdlib / "site-packages").mkdir()
    (stdlib / "os.py").write_text("pass\n")
    (stdlib / "encodings" / "__init__.py").write_bytes(b"")
    (stdlib / "site-packages" / "untrusted.py").write_text("raise RuntimeError\n")
    monkeypatch.setattr(
        module.macho,
        "inventory",
        lambda _: {"images": [{"architectures": ["arm64"], "rpaths": [], "dependencies": []}]},
    )
    root = tmp_path / "prepared"
    root.mkdir()
    prepared = module.prepare(root, runtime, "3.11")
    import zipfile

    with zipfile.ZipFile(prepared["payload"] / "lib/python311.zip") as archive:
        assert sorted(archive.namelist()) == ["encodings/__init__.py", "os.py"]
        assert all(item.compress_type == zipfile.ZIP_STORED for item in archive.infolist())
    assert prepared["target"].read_bytes() == b"candidate-not-executed"
    assert (runtime / "bin/python3.11").read_bytes() == b"candidate-not-executed"


def test_prepare_rejects_foreign_dylib_and_external_rpath(tmp_path, monkeypatch):
    module = candidate()
    runtime = tmp_path / "input"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "bin/python3.11").write_bytes(b"candidate-not-executed")
    (runtime / "lib/python3.11").mkdir(parents=True)
    (runtime / "lib/python3.11/os.py").write_text("pass\n")
    for index, image in enumerate(
        (
            {"architectures": ["arm64"], "rpaths": [], "dependencies": [{"name": "/opt/homebrew/lib/foreign.dylib"}]},
            {"architectures": ["arm64"], "rpaths": ["@executable_path/../../outside"], "dependencies": []},
            {"architectures": ["x86_64", "arm64"], "rpaths": [], "dependencies": []},
        )
    ):
        monkeypatch.setattr(module.macho, "inventory", lambda _, image=image: {"images": [image]})
        root = tmp_path / f"rejected-{index}"
        root.mkdir()
        with pytest.raises(ValueError):
            module.prepare(root, runtime, "3.11")


def test_inventory_rejects_byte_and_entry_substitution(tmp_path):
    module = candidate()
    path = tmp_path / "code.py"
    path.write_text("original")
    original = module.inventory(tmp_path)
    path.write_text("replaced")
    with pytest.raises(ValueError):
        module.verify_inventory(tmp_path, original)
    path.write_text("original")
    (tmp_path / "extra").mkdir()
    with pytest.raises(ValueError):
        module.verify_inventory(tmp_path, original)


@pytest.mark.parametrize("version", ["3.11", "3.12", "3.13"])
def test_stdlib_source_preserves_frozen_module_paths_and_zip_bytes(tmp_path, version):
    import hashlib
    import zipfile

    module = candidate()
    runtime = tmp_path / "input"
    stdlib = runtime / "lib" / f"python{version}"
    (stdlib / "collections").mkdir(parents=True)
    (stdlib / "site-packages").mkdir()
    sources = {
        "os.py": b"pass\n",
        "_collections_abc.py": b"class Iterable: pass\n",
        "collections/__init__.py": b"pass\n",
        "collections/abc.py": b"from _collections_abc import *\n",
        "dataclasses.py": b"pass\n",
    }
    for name, content in sources.items():
        (stdlib / name).write_bytes(content)
    (stdlib / "site-packages/untrusted.py").write_bytes(b"untrusted")
    destination = tmp_path / "payload"
    (destination / "lib" / f"python{version}").mkdir(parents=True)
    inputs = {}
    module._stdlib(runtime, destination, version, inputs)
    with zipfile.ZipFile(destination / "lib" / f"python{version.replace('.', '')}.zip") as archive:
        for name, content in sources.items():
            assert (destination / "lib" / f"python{version}" / name).read_bytes() == archive.read(name) == content
            assert inputs[f"stdlib/{name}"] == hashlib.sha256(content).hexdigest()
    assert not (destination / "lib" / f"python{version}/site-packages").exists()


@pytest.mark.parametrize("kind", ["minimal", "analyzers"])
def test_profiles_retain_broker_exception_denials_without_unknown_operations(tmp_path, kind):
    import re

    from scripts.macos_managed_boundary import python_analyzers

    module = candidate()
    (tmp_path / "bin").mkdir()
    target = tmp_path / "bin/python3.11"
    target.write_text("fixture")
    if kind == "minimal":
        policy = module.profile(tmp_path)
    else:
        (tmp_path / "domain").mkdir()
        prepared = {"payload": tmp_path, "signed_images": [{"path": "bin/python3.11"}]}
        policy = python_analyzers.plan_profile(prepared, tmp_path / "domain", tmp_path, target)
    worker = SOURCE.with_name("control_worker.c").read_text()
    definition = worker.split("#define CONTROL_EXCEPTION_PORT_POLICY", 1)[1].split("/*", 1)[0]
    expected = "".join(re.findall(r'"([^"\n]*)"', definition))
    assert expected and expected in policy
    assert "(deny default)" in policy
    assert policy.count("(deny mach-task-exception-port-set)") == 1
