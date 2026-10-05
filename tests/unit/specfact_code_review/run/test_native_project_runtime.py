from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import shutil
import struct
import sys
import tarfile
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from specfact_code_review.run import native_project_runtime
from specfact_code_review.run.native_project_catalog import ProjectArtifactLocator
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


_CPU_ARM64 = 0x0100000C
_CPU_X86_64 = 0x01000007
_LC_LOAD_DYLIB = 0xC
_LC_RPATH = 0x8000001C
_ACQUISITION_SOURCE = Path(__file__).resolve().parents[4] / "scripts/macos_managed_boundary/project_acquisition.py"


def test_source_only_environment_uses_native_inventory_without_acquisition(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def phase(runtime, operation, inputs, destination):
        calls.append(operation)
        assert json.loads((inputs / "request.json").read_text()) == {}
        assert not list((inputs / "wheels").iterdir())
        destination.mkdir()
        (destination / "site-packages").mkdir()
        (destination / "environment-inventory.json").write_text(
            json.dumps(
                {
                    "installed": [],
                    "environment": {"sys_platform": "darwin", "python_full_version": "3.11.16"},
                    "member_graphs": {"pylint": {"installed": [], "sealed_imports": []}},
                    "analyzer_conflicts": {},
                }
            )
        )
        destination.chmod(0o500)

    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    destination = tmp_path / "runtime"
    native_project_runtime.prepare_source_environment(SimpleNamespace(environment_id="darwin-arm64-cp311"), destination)
    assert calls == ["install"]
    descriptor = json.loads((destination / "project-runtime.json").read_text())
    assert descriptor["inventory"]["environment"]["sys_platform"] == "darwin"
    assert descriptor["inventory"]["source_roots"] == []


def test_unfamiliar_dependency_project_uses_local_preparation_without_catalog(monkeypatch: Any, tmp_path: Path) -> None:
    project = tmp_path / "unfamiliar"
    project.mkdir()
    (project / "requirements.txt").write_text("idna==3.10\n")
    plan = discover_project(project)
    runtime = SimpleNamespace(
        backend="darwin-arm64", environment_id="darwin-arm64-cp312", identity="sha256:" + "d" * 64
    )
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_NATIVE_PROJECT_BUNDLE", raising=False)
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_URL", raising=False)
    monkeypatch.setattr(
        native_project_runtime,
        "resolve_project_artifact",
        lambda *_args, **_kwargs: pytest.fail("customer projects must not need publisher catalog entries"),
    )
    calls = []

    def prepare(selected, selected_runtime, artifact):
        calls.append((selected.identity, selected_runtime.identity))
        (artifact / "site-packages/idna").mkdir(parents=True)
        (artifact / "site-packages/idna/__init__.py").write_text("__version__ = '3.10'\n")
        return {
            "environment": {"python_full_version": "3.12.14"},
            "analyzer_conflicts": {},
            "member_graphs": {},
            "native_extensions": [],
            "pytest_arguments": [],
        }

    monkeypatch.setattr(native_project_runtime, "_prepare_project_on_demand", prepare, raising=False)
    first = native_project_runtime.prepare_native_project_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache")
    second = native_project_runtime.prepare_native_project_runtime(
        plan, runtime=runtime, cache_root=tmp_path / "cache", offline=True
    )
    assert calls == [(plan.identity, runtime.identity)]
    assert first.identity == second.identity
    assert first.descriptor["provenance"]["authority"] == "local_build"


def test_copied_snapshot_is_bound_to_discovered_plan_before_acquisition(monkeypatch, tmp_path: Path) -> None:
    from specfact_code_review.run import runtime_builder

    project = tmp_path / "project"
    project.mkdir()
    (project / "requirements.txt").write_text("idna==3.10\n")
    plan = discover_project(project)

    def substituted_copy(source, destination, **_kwargs):
        shutil.copytree(source, destination)
        (destination / "requirements.txt").write_text("idna==3.9\n")

    monkeypatch.setattr(runtime_builder, "copy_project", substituted_copy)
    monkeypatch.setattr(
        native_project_runtime, "_run_pip_phase", lambda *_args: pytest.fail("substituted snapshot reached acquisition")
    )
    with pytest.raises(ProjectRuntimeError, match="project_runtime_source_changed_during_copy"):
        native_project_runtime._prepare_project_on_demand(plan, SimpleNamespace(), tmp_path / "artifact")


def test_selected_uv_without_project_metadata_rejects_before_acquisition(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("idna==3.10\n")
    plan = replace(discover_project(tmp_path), manager="uv")
    monkeypatch.setattr(native_project_runtime, "_build_project_wheel", lambda *_args: pytest.fail("hook ran"))
    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", lambda *_args: pytest.fail("acquisition ran"))
    with pytest.raises(ProjectRuntimeError, match="project_native_uv_configuration_missing"):
        native_project_runtime._prepare_project_on_demand(plan, SimpleNamespace(), tmp_path / "artifact")


@pytest.mark.parametrize("workspace,explicit_roots", [(False, False), (True, False), (True, True)])
def test_hatch_prepares_an_unfamiliar_environment_without_project_catalog(
    monkeypatch, tmp_path: Path, workspace: bool, explicit_roots: bool
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname="unfamiliar"\nversion="1"\n[tool.hatch.envs.review]\nskip-install=true\ndependencies=["idna==3.10"]\n'
    )
    plan = discover_project(project)
    if workspace:
        (project / "backend").mkdir()
        (project / "backend/pyproject.toml").write_text('[project]\nname="backend"\nversion="1"\n')
        (project / "backend/src/backend").mkdir(parents=True)
        (project / "backend/src/backend/__init__.py").write_bytes(b"VALUE=73\n")
        plan = discover_project(project)
    if explicit_roots:
        plan = replace(plan, source_roots=("src",))
    runtime = SimpleNamespace(root=tmp_path / "capsule", environment_id="darwin-arm64-cp311")
    calls = []

    def manager_dependencies(_runtime, requirements, root, name):
        assert requirements == ["hatch==1.18.0", "uv==0.12.13"]
        path = root / name
        (path / "site-packages").mkdir(parents=True)
        return path

    def phase(_runtime, operation, inputs, destination):
        destination.mkdir()
        if operation == "hook":
            request = json.loads((inputs / ".specfact-hook.json").read_text())
            calls.append(request["operation"])
            assert json.loads((inputs / ".specfact-hatch.json").read_text())["environment"] == "review"
            if request["operation"] == "hatch.describe":
                result = {
                    "requirements": ["idna==3.10"],
                    "extras": [],
                    "groups": [],
                    "skip_install": True,
                    "dev_mode": True,
                    "locked": False,
                    "workspace": [{"name": "backend", "path": "backend", "extras": ["extra"]}] if workspace else [],
                }
            else:
                (destination / "site-packages/idna").mkdir(parents=True)
                (destination / "site-packages/idna/__init__.py").write_text("__version__='3.10'\n")
                result = {"manager": {"name": "hatch", "version": "1.18.0"}, "status": "COMPLETE"}
            (destination / "hook-result.json").write_text(json.dumps(result))
        elif operation == "acquire":
            calls.append("acquire")
            assert json.loads((inputs / "request.json").read_text())["requirements"] == [
                "idna==3.10",
                *(["filelock==3.20.3"] if workspace else []),
            ]
            if workspace:
                assert (inputs / "wheels/backend-1-py3-none-any.whl").is_file()
            (destination / "wheels").mkdir()
            (destination / "wheel-manifest.json").write_text("{}")
        else:
            calls.append("inspect")
            (destination / "environment-inventory.json").write_text(
                json.dumps(
                    {
                        "installed": [],
                        "environment": {"sys_platform": "darwin", "python_full_version": "3.11.16"},
                        "member_graphs": {},
                        "analyzer_conflicts": {},
                    }
                )
            )

    monkeypatch.setattr(native_project_runtime, "_prepare_build_dependencies", manager_dependencies)

    def build_member(selected_plan, _runtime, snapshot, _root, wheels, *, editable=False, workspace_snapshot=None):
        assert snapshot.name == "backend" and selected_plan.extras == ("extra",) and editable
        assert workspace_snapshot is not None and snapshot.parent == workspace_snapshot
        calls.append("workspace.build")
        wheels.mkdir()
        with zipfile.ZipFile(wheels / "backend-1-py3-none-any.whl", "w") as archive:
            archive.writestr("backend/__init__.py", b"VALUE=73\n")
        return ["filelock==3.20.3"]

    monkeypatch.setattr(native_project_runtime, "_build_project_wheel", build_member)
    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    monkeypatch.setattr(
        native_project_runtime, "resolve_project_artifact", lambda *_a: pytest.fail("project publisher catalog used")
    )
    artifact = tmp_path / "artifact"
    inventory = native_project_runtime._prepare_project_on_demand(plan, runtime, artifact)
    assert calls == [
        "hatch.describe",
        *(["workspace.build"] if workspace else []),
        "acquire",
        "hatch.install",
        "inspect",
    ]
    assert inventory["native_preparation"]["manager"] == {"name": "hatch", "version": "1.18.0"}
    assert inventory["native_preparation"]["project_catalog_used"] is False
    if workspace:
        assert inventory["source_roots"] == [*(["src"] if explicit_roots else []), "backend/src"]


def test_uv_prepares_actual_locked_project_without_catalog(monkeypatch, tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="unfamiliar"\nversion="1"\n[tool.uv]\n')
    (project / "uv.lock").write_text("version=1\n")
    plan = discover_project(project)
    calls = []

    def phase(_runtime, operation, inputs, destination):
        calls.append(operation)
        destination.mkdir()
        if operation == "uv":
            request = json.loads((inputs / ".specfact-uv.json").read_text())
            assert request["locked"] is True
            assert (inputs / "uv.lock").read_bytes() == (project / "uv.lock").read_bytes()
            (destination / "site-packages").mkdir()
            (destination / "prepared.lock").write_text("version=1\n")
        else:
            assert operation == "inspect"
            assert json.loads((inputs / "request.json").read_text())["schema"] == "native-site-inventory-v1"
            (destination / "environment-inventory.json").write_text(
                json.dumps(
                    {
                        "installed": [],
                        "environment": {"sys_platform": "darwin", "python_full_version": "3.11.16"},
                        "member_graphs": {},
                        "analyzer_conflicts": {},
                    }
                )
            )

    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    monkeypatch.setattr(
        native_project_runtime, "resolve_project_artifact", lambda *_a: pytest.fail("project catalog used")
    )
    inventory = native_project_runtime._prepare_project_on_demand(
        plan, SimpleNamespace(root=tmp_path / "capsule", environment_id="darwin-arm64-cp311"), tmp_path / "artifact"
    )
    assert calls == ["uv", "inspect"]
    assert inventory["native_preparation"]["manager"] == {"name": "uv", "version": "0.12.13"}


@pytest.mark.parametrize("lock_present", [True, False])
def test_poetry_prepares_locked_dependency_environment_without_catalog(monkeypatch, tmp_path: Path, lock_present):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname="unfamiliar"\nversion="1"\n[tool.poetry]\npackage-mode=false\n'
    )
    if lock_present:
        (project / "poetry.lock").write_text("locked fixture\n")
    plan = discover_project(project)
    calls = []

    def dependencies(runtime, requirements, root, name):
        assert requirements == ["poetry==2.4.3"]
        destination = root / name
        (destination / "site-packages").mkdir(parents=True)
        return destination

    def phase(runtime, operation, inputs, destination):
        destination.mkdir()
        if operation == "hook":
            operation = json.loads((inputs / ".specfact-hook.json").read_text())["operation"]
            if lock_present:
                assert (inputs / "poetry.lock").read_bytes() == (project / "poetry.lock").read_bytes()
            result = {
                "requirements": ["idna==3.10"],
                "groups": ["main"],
                "extras": [],
                "locked": True,
                "lock_preserved": True,
                "package_mode": False,
                "manager": {"name": "poetry", "version": "2.4.3"},
                "hook_provenance": "local_build",
                "production_eligible": False,
            }
            if operation == "poetry.describe" and not (inputs / "poetry.lock").exists():
                result.update(
                    locked=False,
                    lock_preserved=False,
                    resolution={
                        "schema": "native-poetry-resolution-v1",
                        "content_hash": "a" * 64,
                        "pyproject": {
                            "project": {"name": "unfamiliar", "version": "1"},
                            "tool": {"poetry": {"package-mode": False}},
                        },
                        "groups": ["main"],
                        "extras": [],
                    },
                )
            if operation == "poetry.install":
                (destination / "site-packages").mkdir()
                result["status"] = "COMPLETE"
            (destination / "hook-result.json").write_text(json.dumps(result))
        elif operation == "acquire":
            value = json.loads((inputs / "request.json").read_text())
            if value["schema"] == "native-poetry-resolution-v1":
                assert set(inputs.iterdir()) == {inputs / "request.json", inputs / ".specfact-build-dependencies"}
                payload = '[metadata]\ncontent-hash="' + "a" * 64 + '"\n'
                (destination / "poetry.lock").write_text(payload)
                (destination / "resolution.json").write_text(
                    json.dumps(
                        {
                            "manager": {"name": "poetry", "version": "2.4.3"},
                            "content_hash": "a" * 64,
                            "lock_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                        }
                    )
                )
                calls.append(operation)
                return
            assert value["requirements"] == ["idna==3.10"]
            (destination / "wheels").mkdir()
            (destination / "wheel-manifest.json").write_text("{}")
        else:
            assert operation == "inspect"
            (destination / "environment-inventory.json").write_text(
                json.dumps(
                    {
                        "installed": [],
                        "environment": {"sys_platform": "darwin", "python_full_version": "3.11.16"},
                        "member_graphs": {},
                        "analyzer_conflicts": {},
                    }
                )
            )
        calls.append(operation)

    monkeypatch.setattr(native_project_runtime, "_prepare_build_dependencies", dependencies)
    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    monkeypatch.setattr(
        native_project_runtime, "resolve_project_artifact", lambda *_a: pytest.fail("project catalog used")
    )
    inventory = native_project_runtime._prepare_project_on_demand(
        plan, SimpleNamespace(root=tmp_path / "capsule", environment_id="darwin-arm64-cp311"), tmp_path / "artifact"
    )
    expected = ["poetry.describe", "acquire", "poetry.install", "inspect"]
    assert calls == (expected if lock_present else ["poetry.describe", "acquire", *expected])
    assert (project / "poetry.lock").exists() == lock_present
    assert inventory["native_preparation"]["generated_preparation_lock"] == (not lock_present)
    if not lock_present:
        assert (tmp_path / "artifact/preparation.lock").is_file()
    assert inventory["native_preparation"]["manager"] == {"name": "poetry", "version": "2.4.3"}


def test_built_wheel_binds_src_layout_to_matching_snapshot_bytes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "src/sample").mkdir(parents=True)
    (project / "src/sample/__init__.py").write_bytes(b"VALUE=1\n")
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    with zipfile.ZipFile(wheels / "sample-1-py3-none-any.whl", "w") as archive:
        archive.writestr("sample/__init__.py", b"VALUE=1\n")
    assert native_project_runtime._bound_source_roots(project, wheels) == ["src"]
    (project / "src/sample/__init__.py").write_bytes(b"VALUE=2\n")
    assert native_project_runtime._bound_source_roots(project, wheels) == []


def test_installed_project_bytes_bind_uv_src_layout_without_explicit_roots(tmp_path):
    project = tmp_path / "project"
    (project / "src/customer").mkdir(parents=True)
    (project / "src/customer/__init__.py").write_bytes(b"VALUE=7\n")
    site = tmp_path / "site"
    (site / "customer").mkdir(parents=True)
    (site / "customer/__init__.py").write_bytes(b"VALUE=7\n")
    (site / "unrelated").mkdir()
    (site / "unrelated/__init__.py").write_bytes(b"VALUE=99\n")
    assert native_project_runtime._bound_source_roots(project, site, installed=True) == ["src"]
    (site / "customer/__init__.py").write_bytes(b"VALUE=8\n")
    assert native_project_runtime._bound_source_roots(project, site, installed=True) == []


def test_source_root_matching_indexes_inventory_once(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "src/sample").mkdir(parents=True)
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    with zipfile.ZipFile(wheels / "sample-1-py3-none-any.whl", "w") as archive:
        for index in range(20):
            name = f"module_{index}.py"
            (project / "src/sample" / name).write_bytes(b"VALUE=1\n")
            archive.writestr(f"sample/{name}", b"VALUE=1\n")

    class ObservedInventory(dict):
        calls = 0

        def items(self):
            self.calls += 1
            return super().items()

    inventory = ObservedInventory(native_project_runtime._runtime_tree(project))
    monkeypatch.setattr(native_project_runtime, "_runtime_tree", lambda _path: inventory)
    assert native_project_runtime._bound_source_roots(project, wheels) == ["src"]
    assert inventory.calls == 1


def test_malformed_failure_receipt_preserves_incomplete_diagnostic(monkeypatch, tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "request.json").write_text("{}")
    monkeypatch.setattr(
        native_project_runtime.native_execution, "prepare_native_execution", lambda **kwargs: SimpleNamespace(**kwargs)
    )
    monkeypatch.setattr(native_project_runtime.native_execution, "BinaryNativeExecutionTransport", lambda lease: lease)

    class FailedSession:
        def __init__(self, _transport):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def launch(self, request):
            (request.output_root / "preparation-error.json").write_text("[]")
            return 1

        def wait(self, *_args):
            return SimpleNamespace(returncode=74)

    monkeypatch.setattr(native_project_runtime.native_execution, "NativeExecutionSession", FailedSession)
    with pytest.raises(ProjectRuntimeError, match="project_native_preparation_incomplete:hook:manager worker failed"):
        native_project_runtime._run_pip_phase(
            SimpleNamespace(native_lease=object()), "hook", inputs, tmp_path / "output"
        )


@pytest.mark.parametrize("response", [[], {"requirements": [1]}, {"requirements": "bad"}])
def test_malformed_hook_response_is_actionable_incomplete(monkeypatch, tmp_path: Path, response) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[build-system]\nrequires=[]\nbuild-backend="fixture"\n')
    plan = discover_project(project)
    root = tmp_path / "preparation"
    root.mkdir()
    dependencies = root / "dependencies"
    dependencies.mkdir()
    monkeypatch.setattr(native_project_runtime, "_prepare_build_dependencies", lambda *_args: dependencies)

    def hook(_runtime, operation, _inputs, destination):
        assert operation == "hook"
        destination.mkdir()
        (destination / "hook-result.json").write_text(json.dumps(response))

    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", hook)
    with pytest.raises(ProjectRuntimeError, match=r"project_native_build_(result|requirements)_invalid"):
        native_project_runtime._build_project_wheel(plan, SimpleNamespace(), project, root, root / "wheels")


@pytest.mark.parametrize(
    "declaration",
    ["dependencies = []", "dependencies = ['requests>=2']", "dependencies = []\ndynamic = ['dependencies']"],
)
def test_package_still_prepares_and_installs_its_root(monkeypatch: Any, tmp_path: Path, declaration: str) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        f"[project]\nname = 'standalone'\nversion = '1.0'\n{declaration}\n", encoding="utf-8"
    )
    plan = discover_project(project, config_path=None)
    runtime = SimpleNamespace(
        backend="darwin-arm64",
        environment_id="darwin-arm64-cp312",
        identity="sha256:" + "d" * 64,
    )
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_NATIVE_PROJECT_BUNDLE", raising=False)
    monkeypatch.setattr(
        native_project_runtime,
        "resolve_project_artifact",
        lambda *_args, **_kwargs: pytest.fail("dependency-free project must not fetch a bundle"),
    )
    calls = []

    def prepare_root(_plan, _runtime, artifact):
        calls.append(_plan.identity)
        (artifact / "site-packages").mkdir(parents=True)
        (artifact / "site-packages/standalone.py").write_text("VALUE = 1\n")
        return {"environment": {"python_full_version": "3.12.14"}, "member_graphs": {}, "analyzer_conflicts": {}}

    monkeypatch.setattr(native_project_runtime, "_prepare_project_on_demand", prepare_root)

    prepared = native_project_runtime.prepare_native_project_runtime(
        plan, runtime=runtime, cache_root=tmp_path / "cache"
    )

    assert prepared.descriptor["project_identity"] == plan.identity
    assert prepared.descriptor["provenance"]["protected_pr_eligible"] is False
    assert (prepared.root / "site-packages").is_dir()
    assert (prepared.root / "site-packages/standalone.py").is_file()
    assert calls == [plan.identity]
    reused = native_project_runtime.prepare_native_project_runtime(
        plan, runtime=runtime, cache_root=tmp_path / "cache", offline=True
    )
    assert reused.identity == prepared.identity


def _macho_string_command(command: int, value: str, *, value_offset: int) -> bytes:
    encoded = value.encode("utf-8") + b"\0"
    size = (value_offset + len(encoded) + 7) & ~7
    payload = bytearray(size)
    struct.pack_into("<III", payload, 0, command, size, value_offset)
    payload[value_offset : value_offset + len(encoded)] = encoded
    return bytes(payload)


def _thin_macho(
    *,
    cpu: int = _CPU_ARM64,
    filetype: int = 8,
    loads: tuple[str, ...] = (),
    rpaths: tuple[str, ...] = (),
) -> bytes:
    commands = [_macho_string_command(_LC_LOAD_DYLIB, name, value_offset=24) for name in loads]
    commands.extend(_macho_string_command(_LC_RPATH, path, value_offset=12) for path in rpaths)
    body = b"".join(commands)
    return struct.pack("<8I", 0xFEEDFACF, cpu, 0, filetype, len(commands), len(body), 0, 0) + body


def _fat_macho(*slices: tuple[int, bytes]) -> bytes:
    table_size = 8 + len(slices) * 20
    offset = (table_size + 7) & ~7
    table = bytearray(struct.pack(">II", 0xCAFEBABE, len(slices)))
    payload = bytearray(offset)
    payload[:8] = table
    entries = bytearray()
    for cpu, image in slices:
        entries.extend(struct.pack(">IIIII", cpu, 0, offset, len(image), 3))
        payload.extend(image)
        offset += len(image)
        padding = (-offset) % 8
        payload.extend(b"\0" * padding)
        offset += padding
    payload[8 : 8 + len(entries)] = entries
    return bytes(payload)


def _bundle(root: Path, plan: ProjectPlan) -> Path:
    bundle = root / "bundle"
    (bundle / "locks").mkdir(parents=True)
    (bundle / "wheelhouse").mkdir()
    descriptor = {
        "schema": "specfact-macos-project-acquisition-v1",
        "corpus_identity": plan.identity,
        "abi": "cp312",
        "platform": "macos-arm64",
        "manager": {"name": "pip", "version": "26.2.1"},
        "content_sha256": "a" * 64,
        "signature": {"algorithm": "Ed25519-SHA256", "key_id": "b" * 64, "value": "fixture"},
    }
    (bundle / "descriptor.json").write_text(json.dumps(descriptor), encoding="utf-8")
    (bundle / "locks/pip.json").write_text("{}", encoding="utf-8")
    return bundle


def _authenticated_bundle(root: Path, plan: ProjectPlan, capsule: Path) -> Path:
    spec = importlib.util.spec_from_file_location("focused_project_acquisition", _ACQUISITION_SOURCE)
    assert spec is not None and spec.loader is not None
    acquisition = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = acquisition
    spec.loader.exec_module(acquisition)
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    trust = capsule / "trust"
    trust.mkdir(parents=True)
    public_key = trust / "project-acquisition-public.pem"
    public_key.write_bytes(public_pem)
    public_key.chmod(0o444)
    source_archive = root / "source-input.tar.gz"
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source_archive, "w:gz") as archive:
        payload = b"[project]\nname='fixture'\nversion='1.0'\n"
        member = tarfile.TarInfo("project/pyproject.toml")
        member.size = len(payload)
        member.mode = 0o644
        member.mtime = 0
        archive.addfile(member, io.BytesIO(payload))
    wheel = root / "fixture_dep-2.0-py3-none-any.whl"
    wheel.write_bytes(b"authenticated wheel fixture")
    commit = "1" * 40
    request = {
        "schema": "specfact-macos-project-acquisition-request-v1",
        "project": "fixture",
        "corpus_identity": plan.identity,
        "source": {
            "url": "https://github.com/example/fixture.git",
            "commit": commit,
            "archive_url": f"https://github.com/example/fixture/archive/{commit}.tar.gz",
        },
        "manager": {"name": "pip", "version": "26.2.1"},
        "selection": {"groups": ["default"], "environment": "default"},
        "abi": "cp312",
        "platform": "macos-arm64",
        "network": "trusted-acquisition-only",
        "execute_project_code": False,
    }

    def sign(payload: bytes) -> dict[str, str]:
        return {
            "algorithm": "Ed25519-SHA256",
            "key_id": hashlib.sha256(public_pem).hexdigest(),
            "value": base64.b64encode(private_key.sign(payload)).decode("ascii"),
        }

    def verify_source(selected: dict[str, Any], archive_sha256: str, tree_sha256: str) -> dict[str, Any]:
        return {
            "schema": "specfact-trusted-source-fetch-v1",
            "method": "github-commit-api-and-archive",
            "source_url": selected["source"]["url"],
            "archive_url": selected["source"]["archive_url"],
            "commit": selected["source"]["commit"],
            "git_tree": "2" * 40,
            "archive_sha256": archive_sha256,
            "tree_sha256": tree_sha256,
            "authenticated_transport": True,
        }

    destination = root / "signed-bundle"
    acquisition.create_acquisition_bundle(
        request,
        source_archive,
        artifacts=[
            {
                "package": "fixture-dep",
                "version": "2.0",
                "filename": wheel.name,
                "url": f"https://files.pythonhosted.org/packages/aa/{wheel.name}",
                "path": wheel,
                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            }
        ],
        destination=destination,
        signer=sign,
        source_verifier=verify_source,
    )
    return destination


def test_prepares_authenticated_bundle_through_closed_native_project_plan(monkeypatch: Any, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    plan = ProjectPlan(project, manager="pip", source_identity="sha256:" + "c" * 64)
    bundle = _bundle(tmp_path, plan)
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    runtime = SimpleNamespace(
        backend="darwin-arm64",
        environment_id="darwin-arm64-cp312",
        identity="sha256:" + "d" * 64,
        root=capsule,
        native_lease=object(),
    )
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_NATIVE_PROJECT_BUNDLE", str(bundle))
    captured: dict[str, object] = {}

    def prepare(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        staged = Path(str(kwargs["project_snapshot"]))
        assert (staged / ".specfact-native-project/descriptor.json").is_file()
        assert staged.stat().st_mode & 0o222 == 0
        return SimpleNamespace(output_root=Path(str(kwargs["output_root"])))

    class Session:
        def __init__(self, _transport: object) -> None:
            self.request: SimpleNamespace | None = None

        def __enter__(self) -> Session:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def launch(self, request: SimpleNamespace) -> int:
            self.request = request
            site = request.output_root / "site-packages/fixture_dep"
            site.mkdir(parents=True)
            (site / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
            (site / "native.so").write_bytes(_thin_macho(loads=("/usr/lib/libSystem.B.dylib",)))
            (request.output_root / "project-preparation.json").write_text(
                json.dumps(
                    {
                        "schema": "specfact-native-project-preparation-result-v1",
                        "status": "COMPLETE",
                        "evidence": {
                            "schema": "specfact-native-project-preparation-evidence-v1",
                            "status": "COMPLETE",
                            "manager": {"name": "pip", "version": "26.2.1"},
                            "artifact_count": 1,
                            "file_count": 1,
                            "native_extension_count": 1,
                            "network_used": False,
                            "host_manager_used": False,
                            "project_code_executed": False,
                            "build_hooks_executed": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            return 9

        def wait(self, handle: int, timeout_ms: int) -> SimpleNamespace:
            assert (handle, timeout_ms) == (9, 900_000)
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(native_project_runtime.native_execution, "prepare_native_execution", prepare)
    monkeypatch.setattr(native_project_runtime.native_execution, "BinaryNativeExecutionTransport", lambda lease: lease)
    monkeypatch.setattr(native_project_runtime.native_execution, "NativeExecutionSession", Session)
    monkeypatch.setattr(
        native_project_runtime,
        "_verify_acquisition_bundle",
        lambda selected, *_args, **_kwargs: json.loads((selected / "descriptor.json").read_text()),
    )

    monkeypatch.setattr(
        native_project_runtime,
        "_inspect_project_site",
        lambda *_args: {
            "environment": {"python_full_version": "3.12.14"},
            "installed": [],
            "member_graphs": {},
            "analyzer_conflicts": {},
        },
    )
    prepared = native_project_runtime.prepare_native_project_runtime(
        plan,
        runtime=runtime,
        cache_root=tmp_path / "cache",
    )

    assert captured["plan_id"] == "project.pip.v1"
    assert captured["budget"].output_bytes == 64 << 20
    assert prepared.descriptor["environment_id"] == "darwin-arm64-cp312"
    assert (prepared.root / "site-packages/fixture_dep/__init__.py").read_text() == "VALUE = 1\n"
    assert prepared.descriptor["inventory"]["native_preparation"]["status"] == "COMPLETE"
    assert prepared.descriptor["inventory"]["native_extensions"][0]["path"] == ("fixture_dep/native.so")


def test_verifies_publisher_signature_source_lock_wheels_and_cache_bytes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    plan = ProjectPlan(project, manager="pip", source_identity="sha256:" + "c" * 64)
    capsule = tmp_path / "capsule"
    runtime = SimpleNamespace(root=capsule, environment_id="darwin-arm64-cp312")
    bundle = _authenticated_bundle(tmp_path / "publisher", plan, capsule)

    descriptor = native_project_runtime._verify_acquisition_bundle(bundle, plan, runtime)
    assert descriptor["corpus_identity"] == plan.identity
    assert descriptor["acquisition_executed_project_code"] is False

    wheel = bundle / "wheelhouse" / descriptor["artifacts"][0]["filename"]
    wheel.chmod(0o600)
    wheel.write_bytes(b"substituted")
    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_authentication_failed"):
        native_project_runtime._verify_acquisition_bundle(bundle, plan, runtime)


def test_extracts_bounded_bundle_archive_then_reverifies_exact_bytes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    plan = ProjectPlan(project, manager="pip", source_identity="sha256:" + "c" * 64)
    capsule = tmp_path / "capsule"
    runtime = SimpleNamespace(root=capsule, environment_id="darwin-arm64-cp312")
    bundle = _authenticated_bundle(tmp_path / "publisher", plan, capsule)
    archive = tmp_path / "bundle.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        output.add(bundle, arcname="bundle", recursive=True)
    extracted = tmp_path / "extracted"

    native_project_runtime._extract_acquisition_archive(archive, extracted)

    descriptor = native_project_runtime._verify_acquisition_bundle(extracted, plan, runtime)
    assert descriptor["content_sha256"] == json.loads((bundle / "descriptor.json").read_text())["content_sha256"]


@pytest.mark.parametrize("limit", ["members", "payload"])
def test_acquisition_archive_stops_traversal_at_first_exceeded_bound(monkeypatch, tmp_path, limit):
    archive = tmp_path / "too-many.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.USTAR_FORMAT) as output:
        for index in range(20):
            member = tarfile.TarInfo(f"bundle/file-{index}")
            member.size = 1
            member.mode = 0o600
            output.addfile(member, io.BytesIO(b"x"))
    observed = []
    original = tarfile.TarFile.next

    def observe(source):
        member = original(source)
        if member is not None:
            observed.append(member.name)
        return member

    monkeypatch.setattr(tarfile.TarFile, "next", observe)
    if limit == "members":
        monkeypatch.setattr(native_project_runtime, "_MAX_ACQUISITION_FILES", 2)
    else:
        monkeypatch.setattr(native_project_runtime, "_MAX_ACQUISITION_ARCHIVE_BYTES", 2)
    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_archive_invalid"):
        native_project_runtime._extract_acquisition_archive(archive, tmp_path / "extracted")
    assert len(observed) <= 4
    assert not (tmp_path / "extracted").exists()


def test_acquisition_archive_rejects_oversized_pax_before_metadata_parsing(monkeypatch, tmp_path):
    archive = tmp_path / "oversized-pax.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.USTAR_FORMAT) as output:
        member = tarfile.TarInfo("metadata")
        member.type = tarfile.XHDTYPE
        member.size = 64 * 1024 + 1
        output.addfile(member, io.BytesIO(b"0" * member.size))
    calls = []
    original = tarfile.TarInfo._proc_pax

    def observe(member, source):
        calls.append(member.size)
        return original(member, source)

    monkeypatch.setattr(tarfile.TarInfo, "_proc_pax", observe)
    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_archive_invalid"):
        native_project_runtime._extract_acquisition_archive(archive, tmp_path / "extracted")
    assert not calls


def test_acquisition_archive_bounds_global_headers_even_without_file_members(monkeypatch, tmp_path):
    archive = tmp_path / "global-headers.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.USTAR_FORMAT) as output:
        for _ in range(20):
            member = tarfile.TarInfo("metadata")
            member.type = tarfile.XGLTYPE
            output.addfile(member)
        member = tarfile.TarInfo("bundle/file")
        member.mode = 0o600
        output.addfile(member)
    monkeypatch.setattr(native_project_runtime, "_MAX_ACQUISITION_FILES", 2)
    calls = []
    original = tarfile.TarInfo.frombuf.__func__

    def observe(cls, *arguments):
        calls.append(1)
        return original(cls, *arguments)

    monkeypatch.setattr(tarfile.TarInfo, "frombuf", classmethod(observe))
    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_archive_invalid"):
        native_project_runtime._extract_acquisition_archive(archive, tmp_path / "extracted")
    assert len(calls) <= 4


def test_rejects_bundle_when_combined_files_exceed_limit(monkeypatch: Any, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    plan = ProjectPlan(project, manager="pip", source_identity="sha256:" + "c" * 64)
    capsule = tmp_path / "capsule"
    runtime = SimpleNamespace(root=capsule, environment_id="darwin-arm64-cp312")
    bundle = _authenticated_bundle(tmp_path / "publisher", plan, capsule)
    total = sum(path.stat().st_size for path in bundle.rglob("*") if path.is_file())
    monkeypatch.setattr(native_project_runtime, "_MAX_ACQUISITION_BUNDLE_BYTES", total)
    native_project_runtime._verify_acquisition_bundle(bundle, plan, runtime)
    monkeypatch.setattr(native_project_runtime, "_MAX_ACQUISITION_BUNDLE_BYTES", total - 1)

    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_authentication_failed"):
        native_project_runtime._verify_acquisition_bundle(bundle, plan, runtime)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "bundle/../../escape", "bundle\\escape"])
def test_rejects_escaping_acquisition_archive_paths(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "unsafe.tar"
    with tarfile.open(archive, "w") as output:
        payload = b"x"
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        member.mode = 0o600
        output.addfile(member, io.BytesIO(payload))

    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_archive_invalid"):
        native_project_runtime._extract_acquisition_archive(archive, tmp_path / "extracted")


def _download_archive_bytes() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        payload = b"fixture"
        member = tarfile.TarInfo("bundle/fixture.txt")
        member.size = len(payload)
        member.mode = 0o600
        archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


class _DownloadResponse(io.BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def test_catalog_https_download_enforces_outer_digest_and_size(monkeypatch: Any, tmp_path: Path) -> None:
    payload = _download_archive_bytes()
    opener = SimpleNamespace(open=lambda *_args, **_kwargs: _DownloadResponse(payload))
    monkeypatch.setattr(native_project_runtime.urllib.request, "build_opener", lambda *_args: opener)
    destination = tmp_path / "accepted"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()

    native_project_runtime._download_acquisition_bundle(
        "https://artifacts.example.invalid/project.tar",
        destination,
        expected_digest=digest,
        expected_size=len(payload),
        transport="https",
    )
    assert (destination / "fixture.txt").read_bytes() == b"fixture"

    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_archive_digest_mismatch"):
        native_project_runtime._download_acquisition_bundle(
            "https://artifacts.example.invalid/project.tar",
            tmp_path / "rejected",
            expected_digest="sha256:" + "0" * 64,
            expected_size=len(payload),
            transport="https",
        )


def test_catalog_ghcr_download_uses_bounded_authenticated_registry_reader(monkeypatch: Any, tmp_path: Path) -> None:
    payload = _download_archive_bytes()
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    observed: dict[str, object] = {}

    def open_blob(**kwargs: object) -> _DownloadResponse:
        observed.update(kwargs)
        return _DownloadResponse(payload)

    monkeypatch.setattr(native_project_runtime.native_backend, "_open_registry_blob", open_blob)
    destination = tmp_path / "accepted"

    native_project_runtime._download_acquisition_bundle(
        f"https://ghcr.io/v2/nold-ai/specfact-project-runtimes/blobs/{digest}",
        destination,
        expected_digest=digest,
        expected_size=len(payload),
        transport="ghcr",
    )

    assert (destination / "fixture.txt").read_bytes() == b"fixture"
    assert observed["repository"] == "nold-ai/specfact-project-runtimes"
    assert observed["digest"] == digest
    assert observed["size"] == len(payload)
    assert observed["max_redirects"] == 4


def test_admits_thin_arm64_extension_and_records_bounded_inventory(tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    extension = site_packages / "fixture/native.so"
    extension.parent.mkdir(parents=True)
    extension.write_bytes(_thin_macho(loads=("/usr/lib/libSystem.B.dylib",)))

    inventory = native_project_runtime._admit_native_extensions(
        site_packages,
        capsule_root=tmp_path / "capsule",
        declared_count=1,
    )

    assert inventory == [
        {
            "architectures": ("arm64",),
            "needed": ("/usr/lib/libSystem.B.dylib",),
            "origin": "project",
            "path": "fixture/native.so",
            "resolved": ("/usr/lib/libSystem.B.dylib",),
            "rpaths": (),
            "sha256": inventory[0]["sha256"],
        }
    ]
    assert inventory[0]["sha256"].startswith("sha256:")


@pytest.mark.parametrize(
    "payload",
    [
        _thin_macho(cpu=_CPU_X86_64),
    ],
    ids=["x86-only"],
)
def test_rejects_non_arm64_or_mixed_native_extension(tmp_path: Path, payload: bytes) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    (site_packages / "native.so").write_bytes(payload)

    with pytest.raises(ProjectRuntimeError, match="project_native_macho_architecture_unsupported"):
        native_project_runtime._admit_native_extensions(
            site_packages,
            capsule_root=tmp_path / "capsule",
            declared_count=1,
        )


def test_admits_universal2_extension_through_its_native_arm64_slice(tmp_path: Path) -> None:
    site = tmp_path / "site-packages"
    site.mkdir()
    (site / "native.so").write_bytes(
        _fat_macho(
            (_CPU_ARM64, _thin_macho(loads=("/usr/lib/libSystem.B.dylib",))),
            (_CPU_X86_64, _thin_macho(cpu=_CPU_X86_64)),
        )
    )
    records = native_project_runtime._admit_native_extensions(site, capsule_root=tmp_path / "capsule", declared_count=1)
    assert records[0]["architectures"] == ("arm64", "x86_64")
    assert records[0]["resolved"] == ("/usr/lib/libSystem.B.dylib",)


def test_rejects_native_extension_with_unsafe_load_path(tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    (site_packages / "native.so").write_bytes(_thin_macho(loads=("/opt/homebrew/lib/libambient.dylib",)))

    with pytest.raises(ProjectRuntimeError, match="project_native_macho_absolute_load_path"):
        native_project_runtime._admit_native_extensions(
            site_packages,
            capsule_root=tmp_path / "capsule",
            declared_count=1,
        )


def test_rejects_symlink_in_extracted_project_runtime(tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    target = tmp_path / "native.so"
    target.write_bytes(_thin_macho())
    (site_packages / "native.so").symlink_to(target)

    with pytest.raises(ProjectRuntimeError, match="project_native_runtime_symlink"):
        native_project_runtime._admit_native_extensions(
            site_packages,
            capsule_root=tmp_path / "capsule",
            declared_count=1,
        )


def test_rejects_native_extension_identity_change_during_inventory(monkeypatch: Any, tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    extension = site_packages / "native.so"
    extension.write_bytes(_thin_macho())
    original = native_project_runtime.runtime_native._macho_inventory

    def mutate(root: Path, candidates: list[Path]) -> list[dict[str, Any]] | None:
        inventory = original(root, candidates)
        extension.write_bytes(_thin_macho(loads=("/usr/lib/libSystem.B.dylib",)))
        return inventory

    monkeypatch.setattr(native_project_runtime.runtime_native, "_macho_inventory", mutate)

    with pytest.raises(ProjectRuntimeError, match="project_native_runtime_identity_changed"):
        native_project_runtime._admit_native_extensions(
            site_packages,
            capsule_root=tmp_path / "capsule",
            declared_count=1,
        )


def test_cold_acquisition_installs_authenticated_content_and_reuses_it_offline(
    monkeypatch: Any, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    plan = ProjectPlan(project, manager="pip", source_identity="sha256:" + "c" * 64)
    runtime = SimpleNamespace(
        backend="darwin-arm64",
        environment_id="darwin-arm64-cp312",
        identity="sha256:" + "d" * 64,
        root=tmp_path / "capsule",
        native_lease=object(),
    )
    staged = _bundle(tmp_path / "publisher", plan)
    descriptor = json.loads((staged / "descriptor.json").read_text())
    content = descriptor["content_sha256"]
    acquisition_cache = tmp_path / "acquisitions"
    runtime_cache = tmp_path / "runtimes"
    downloads: list[str] = []
    executions: list[Path] = []

    def acquire(url: str, destination: Path) -> None:
        downloads.append(url)
        shutil.copytree(staged, destination)

    def verify(bundle: Path, *_args: object, **_kwargs: object) -> dict[str, Any]:
        value = json.loads((bundle / "descriptor.json").read_text())
        if value.get("content_sha256") != content or (bundle / "CORRUPT").exists():
            raise ProjectRuntimeError("project_native_acquisition_authentication_failed")
        return value

    def execute(_plan: ProjectPlan, _runtime: object, bundle: Path, artifact: Path) -> dict[str, Any]:
        executions.append(bundle)
        (artifact / "site-packages").mkdir(parents=True)
        inventory = {
            "environment": {"python_full_version": "3.12.14"},
            "analyzer_conflicts": {},
            "member_graphs": {},
            "native_extensions": [],
            "native_preparation": {"status": "COMPLETE"},
            "pytest_arguments": [],
        }
        (artifact / "inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        return inventory

    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_CACHE", str(acquisition_cache))
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_NATIVE_PROJECT_BUNDLE", raising=False)
    monkeypatch.setattr(native_project_runtime, "_download_acquisition_bundle", acquire)
    monkeypatch.setattr(native_project_runtime, "_verify_acquisition_bundle", verify)
    monkeypatch.setattr(native_project_runtime, "_execute", execute)

    url = "https://ghcr.io/v2/nold-ai/project-runtime/blobs/sha256:fixture"
    first = native_project_runtime.prepare_native_project_runtime(
        plan,
        runtime=runtime,
        cache_root=runtime_cache,
        acquisition_url=url,
    )
    shutil.rmtree(first.root)
    second = native_project_runtime.prepare_native_project_runtime(
        plan,
        runtime=runtime,
        cache_root=runtime_cache,
        offline=True,
    )

    assert downloads == [url]
    assert executions == [acquisition_cache / content, acquisition_cache / content]
    assert second.descriptor["project_identity"] == plan.identity
    assert not list(acquisition_cache.glob("*.partial"))


def test_automatic_catalog_locator_binds_download_digest_and_size(monkeypatch: Any, tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "c" * 64)
    runtime = SimpleNamespace(
        backend="darwin-arm64",
        environment_id="darwin-arm64-cp312",
        identity="sha256:" + "d" * 64,
        root=tmp_path / "capsule",
    )
    staged = _bundle(tmp_path / "publisher", plan)
    descriptor = json.loads((staged / "descriptor.json").read_text())
    observed: dict[str, object] = {}
    locator = ProjectArtifactLocator(
        url="https://ghcr.io/v2/nold-ai/specfact-project-runtimes/blobs/sha256:" + "e" * 64,
        digest="sha256:" + "e" * 64,
        size=8192,
        transport="ghcr",
    )

    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_CACHE", str(tmp_path / "acquisitions"))
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_NATIVE_PROJECT_BUNDLE", raising=False)
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_URL", raising=False)
    monkeypatch.setattr(native_project_runtime, "resolve_project_artifact", lambda *_args, **_kwargs: locator)

    def acquire(url: str, destination: Path, **kwargs: object) -> None:
        observed.update(url=url, **kwargs)
        shutil.copytree(staged, destination)

    monkeypatch.setattr(native_project_runtime, "_download_acquisition_bundle", acquire)
    monkeypatch.setattr(
        native_project_runtime,
        "_verify_acquisition_bundle",
        lambda bundle, *_args, **_kwargs: json.loads((bundle / "descriptor.json").read_text()),
    )

    selected = native_project_runtime._resolve_acquisition_bundle(
        plan,
        runtime,
        offline=False,
        acquisition_url=None,
    )

    assert selected.name == descriptor["content_sha256"]
    assert observed == {
        "url": locator.url,
        "expected_digest": locator.digest,
        "expected_size": locator.size,
        "transport": "ghcr",
    }


def test_explicit_url_override_does_not_consult_catalog(monkeypatch: Any, tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "c" * 64)
    runtime = SimpleNamespace(
        environment_id="darwin-arm64-cp312",
        identity="sha256:" + "d" * 64,
        root=tmp_path / "capsule",
    )
    staged = _bundle(tmp_path / "publisher", plan)
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_CACHE", str(tmp_path / "acquisitions"))
    monkeypatch.setattr(
        native_project_runtime,
        "resolve_project_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("explicit override consulted catalog")),
    )
    monkeypatch.setattr(
        native_project_runtime,
        "_download_acquisition_bundle",
        lambda _url, destination, **_kwargs: shutil.copytree(staged, destination),
    )
    monkeypatch.setattr(
        native_project_runtime,
        "_verify_acquisition_bundle",
        lambda bundle, *_args, **_kwargs: json.loads((bundle / "descriptor.json").read_text()),
    )

    native_project_runtime._resolve_acquisition_bundle(
        plan,
        runtime,
        offline=False,
        acquisition_url="https://artifacts.example.invalid/project.tar",
    )


def test_interrupted_cold_acquisition_leaves_no_reusable_partial(monkeypatch: Any, tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "c" * 64)
    runtime = SimpleNamespace(
        backend="darwin-arm64",
        environment_id="darwin-arm64-cp312",
        identity="sha256:" + "d" * 64,
        root=tmp_path / "capsule",
    )
    acquisition_cache = tmp_path / "acquisitions"

    def interrupted(_url: str, destination: Path) -> None:
        destination.mkdir()
        (destination / "descriptor.json").write_text("{}", encoding="utf-8")
        raise OSError("interrupted")

    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_CACHE", str(acquisition_cache))
    monkeypatch.setattr(native_project_runtime, "_download_acquisition_bundle", interrupted)

    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_failed"):
        native_project_runtime.prepare_native_project_runtime(
            plan,
            runtime=runtime,
            cache_root=tmp_path / "runtimes",
            acquisition_url="https://ghcr.io/v2/nold-ai/project-runtime/blobs/sha256:fixture",
        )

    assert not list(acquisition_cache.rglob("*.partial"))
    assert not (acquisition_cache / "bindings").exists()


def test_concurrent_acquisition_publication_verifies_winner(monkeypatch: Any, tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "c" * 64)
    runtime = SimpleNamespace(environment_id="darwin-arm64-cp312", identity="sha256:" + "d" * 64)
    cache = tmp_path / "acquisitions"
    cache.mkdir()
    staged = tmp_path / "staged"
    staged.mkdir()
    content = "a" * 64
    verified: list[Path] = []

    def verify(path: Path, *_args: object, **_kwargs: object) -> dict[str, Any]:
        verified.append(path)
        return {"content_sha256": content}

    def race(_source: Path, destination: Path) -> None:
        destination.mkdir()
        raise OSError(17, "concurrent winner")

    monkeypatch.setattr(native_project_runtime, "_verify_acquisition_bundle", verify)
    monkeypatch.setattr(native_project_runtime.os, "rename", race)

    selected = native_project_runtime._install_acquisition_bundle(staged, cache, plan, runtime)

    assert selected == cache / content
    assert verified == [staged, cache / content]
    assert (cache / "bindings" / native_project_runtime._cache_key(plan, runtime)).read_text() == content + "\n"


def test_corrupt_authenticated_cache_is_rejected_without_network(monkeypatch: Any, tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "c" * 64)
    runtime = SimpleNamespace(
        backend="darwin-arm64",
        environment_id="darwin-arm64-cp312",
        identity="sha256:" + "d" * 64,
        root=tmp_path / "capsule",
    )
    acquisition_cache = tmp_path / "acquisitions"
    binding = acquisition_cache / "bindings" / native_project_runtime._cache_key(plan, runtime)
    binding.parent.mkdir(parents=True)
    content = "a" * 64
    binding.write_text(content + "\n", encoding="ascii")
    binding.chmod(0o600)
    (acquisition_cache / content).mkdir()

    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PROJECT_ACQUISITION_CACHE", str(acquisition_cache))
    monkeypatch.setattr(
        native_project_runtime,
        "_verify_acquisition_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ProjectRuntimeError("project_native_acquisition_authentication_failed")
        ),
    )
    monkeypatch.setattr(
        native_project_runtime,
        "_download_acquisition_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("offline path used network")),
    )

    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_authentication_failed"):
        native_project_runtime.prepare_native_project_runtime(
            plan,
            runtime=runtime,
            cache_root=tmp_path / "runtimes",
            offline=True,
        )


def test_poetry_source_declarations_must_match_unchanged_lock(tmp_path):
    declaration = {
        "schema": "native-locked-git-v1",
        "name": "poetry-core",
        "version": "2.4.1",
        "url": "https://github.com/python-poetry/poetry-core.git",
        "reference": "HEAD",
        "commit": "b9663e42c808543377ae523611c4cfad68016f30",
        "subdirectory": "",
    }
    lock = """[[package]]
name="poetry-core"
version="2.4.1"
[package.source]
type="git"
url="https://github.com/python-poetry/poetry-core.git"
reference="HEAD"
resolved_reference="b9663e42c808543377ae523611c4cfad68016f30"
"""
    (tmp_path / "poetry.lock").write_text(lock)
    assert native_project_runtime._validated_poetry_sources(tmp_path, [declaration]) == [declaration]
    with pytest.raises(ProjectRuntimeError, match="source_lock_mismatch"):
        native_project_runtime._validated_poetry_sources(tmp_path, [{**declaration, "commit": "0" * 40}])
    assert (tmp_path / "poetry.lock").read_text() == lock


@pytest.mark.parametrize(
    "environment,environment_id",
    [
        ({}, "darwin-arm64-cp311"),
        ({"python_full_version": "3.11.15"}, "darwin-arm64-cp311"),
        ({"python_full_version": "3.13.12"}, "darwin-arm64-cp313"),
    ],
)
def test_native_inventory_requires_exact_signed_patch_version(monkeypatch, environment, environment_id):
    from specfact_code_review.run import runtime_interpreter

    monkeypatch.setattr(runtime_interpreter, "signed_versions", lambda: {"darwin-arm64-cp311": "3.11.16"})
    inventory = {"installed": [], "environment": environment, "member_graphs": {}, "analyzer_conflicts": {}}
    with pytest.raises(ProjectRuntimeError, match="preparation_incomplete:python_version"):
        native_project_runtime._record_native_inventory(SimpleNamespace(environment_id=environment_id), inventory)


def test_native_inventory_exact_version_preserves_keys(monkeypatch):
    from specfact_code_review.run import runtime_interpreter

    monkeypatch.setattr(runtime_interpreter, "signed_versions", lambda: {"darwin-arm64-cp311": "3.11.16"})
    inventory = {
        "installed": [],
        "environment": {"python_full_version": "3.11.16"},
        "member_graphs": {},
        "analyzer_conflicts": {},
    }
    assert (
        native_project_runtime._record_native_inventory(SimpleNamespace(environment_id="darwin-arm64-cp311"), inventory)
        is inventory
    )
    assert set(inventory) == {"installed", "environment", "member_graphs", "analyzer_conflicts"}


def test_fresh_site_inventory_cannot_claim_alternate_native_patch(monkeypatch, tmp_path):
    from specfact_code_review.run import runtime_interpreter

    monkeypatch.setattr(runtime_interpreter, "signed_versions", lambda: {"darwin-arm64-cp311": "3.11.16"})
    artifact = tmp_path / "artifact"
    (artifact / "site-packages").mkdir(parents=True)

    def phase(runtime, operation, inputs, output):
        assert operation == "inspect"
        output.mkdir()
        (output / "environment-inventory.json").write_text(
            json.dumps(
                {
                    "installed": [],
                    "environment": {"python_full_version": "3.11.15"},
                    "member_graphs": {},
                    "analyzer_conflicts": {},
                }
            )
        )

    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    with pytest.raises(ProjectRuntimeError, match="preparation_incomplete:python_version"):
        native_project_runtime._inspect_project_site(
            SimpleNamespace(environment_id="darwin-arm64-cp311"), artifact, tmp_path
        )


def test_poetry_source_and_index_wheels_keep_separate_identities(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "pyproject.toml").write_text('[project]\nname="root"\nversion="1"\n')
    dependencies = tmp_path / "manager"
    (dependencies / "site-packages").mkdir(parents=True)
    index_wheels = tmp_path / "index-wheels"
    source_wheels = tmp_path / "source-wheels"
    index_wheels.mkdir()
    source_wheels.mkdir()
    filename = "poetry_core-2.4.1-py3-none-any.whl"
    (index_wheels / filename).write_bytes(b"index artifact for independent build requirements")
    (source_wheels / filename).write_bytes(b"exact locked Git source build")
    plan = ProjectPlan(snapshot, manager="poetry")
    root = tmp_path / "private"
    root.mkdir()

    def phase(runtime, operation, inputs, output):
        assert operation == "hook"
        assert (inputs / "wheelhouse" / filename).read_bytes().startswith(b"index artifact")
        assert (inputs / ".specfact-poetry-source-wheels" / filename).read_bytes().startswith(b"exact locked Git")
        output.mkdir()

    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    native_project_runtime._manager_phase(
        plan,
        object(),
        snapshot,
        dependencies,
        root,
        "poetry.install",
        wheels=index_wheels,
        sources=[],
        source_wheels=source_wheels,
    )


@pytest.mark.parametrize(
    "environment_id,exact_version",
    [("darwin-arm64-cp311", "3.11.16"), ("darwin-arm64-cp312", "3.12.14"), ("darwin-arm64-cp313", "3.13.14")],
)
def test_all_known_native_versions_bind_to_resource(environment_id, exact_version):
    inventory = {"environment": {"python_full_version": exact_version}}
    assert (
        native_project_runtime._record_native_inventory(SimpleNamespace(environment_id=environment_id), inventory)
        is inventory
    )


@pytest.mark.parametrize("tamper", ["digest", "binding", "manager"])
def test_poetry_generated_lock_receipt_binding_rejected(tmp_path, tamper):
    from specfact_code_review.run.native_project_poetry import VERSION

    acquired = tmp_path / "acquired"
    acquired.mkdir()
    payload = b"generated lock data"
    (acquired / "poetry.lock").write_bytes(payload)
    request = {"content_hash": "a" * 64}
    receipt = {
        "manager": {"name": "poetry", "version": VERSION},
        "content_hash": request["content_hash"],
        "lock_sha256": hashlib.sha256(payload).hexdigest(),
    }
    if tamper == "digest":
        receipt["lock_sha256"] = "0" * 64
    elif tamper == "binding":
        receipt["content_hash"] = "0" * 64
    else:
        receipt["manager"]["version"] = "2.4.2"
    (acquired / "resolution.json").write_text(json.dumps(receipt))
    with pytest.raises(ProjectRuntimeError, match="resolution_binding_mismatch"):
        native_project_runtime._admit_poetry_resolution(acquired, request)
