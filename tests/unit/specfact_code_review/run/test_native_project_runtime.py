"""Native project preparation and authenticated acquisition proofs."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tarfile
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import pytest

from specfact_code_review.run import native_project_runtime
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError
from tests.unit.specfact_code_review.run.native_project_runtime_fixtures import (
    _authenticated_bundle,
    _bundle,
    _download_archive_bytes,
    _DownloadResponse,
    _thin_macho,
)


def test_source_only_environment_uses_native_inventory_without_acquisition(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def phase(_runtime, operation, inputs, destination):
        calls.append(operation)
        assert json.loads((inputs / "request.json").read_text(encoding="utf-8")) == {}
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
            ),
            encoding="utf-8",
        )
        destination.chmod(0o500)

    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    destination = tmp_path / "runtime"
    native_project_runtime.prepare_source_environment(SimpleNamespace(environment_id="darwin-arm64-cp311"), destination)
    assert calls == ["install"]
    descriptor = json.loads((destination / "project-runtime.json").read_text(encoding="utf-8"))
    assert descriptor["inventory"]["environment"]["sys_platform"] == "darwin"
    assert descriptor["inventory"]["source_roots"] == []


def test_unfamiliar_dependency_project_uses_local_preparation_without_catalog(monkeypatch: Any, tmp_path: Path) -> None:
    project = tmp_path / "unfamiliar"
    project.mkdir()
    (project / "requirements.txt").write_text("idna==3.10\n", encoding="utf-8")
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
        (artifact / "site-packages/idna/__init__.py").write_text("__version__ = '3.10'\n", encoding="utf-8")
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
    (project / "requirements.txt").write_text("idna==3.10\n", encoding="utf-8")
    plan = discover_project(project)

    def substituted_copy(source, destination, **_kwargs):
        shutil.copytree(source, destination)
        (destination / "requirements.txt").write_text("idna==3.9\n", encoding="utf-8")

    monkeypatch.setattr(runtime_builder, "copy_project", substituted_copy)
    monkeypatch.setattr(
        native_project_runtime, "_run_pip_phase", lambda *_args: pytest.fail("substituted snapshot reached acquisition")
    )
    with pytest.raises(ProjectRuntimeError, match="project_runtime_source_changed_during_copy"):
        native_project_runtime._prepare_project_on_demand(plan, SimpleNamespace(), tmp_path / "artifact")


def test_selected_uv_without_project_metadata_rejects_before_acquisition(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("idna==3.10\n", encoding="utf-8")
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
        '[project]\nname="unfamiliar"\nversion="1"\n[tool.hatch.envs.review]\n'
        'skip-install=true\ndependencies=["idna==3.10"]\n',
        encoding="utf-8",
    )
    plan = discover_project(project)
    if workspace:
        (project / "backend").mkdir()
        (project / "backend/pyproject.toml").write_text('[project]\nname="backend"\nversion="1"\n', encoding="utf-8")
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
            request = json.loads((inputs / ".specfact-hook.json").read_text(encoding="utf-8"))
            calls.append(request["operation"])
            assert json.loads((inputs / ".specfact-hatch.json").read_text(encoding="utf-8"))["environment"] == "review"
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
                (destination / "site-packages/idna/__init__.py").write_text("__version__='3.10'\n", encoding="utf-8")
                result = {"manager": {"name": "hatch", "version": "1.18.0"}, "status": "COMPLETE"}
            (destination / "hook-result.json").write_text(json.dumps(result), encoding="utf-8")
        elif operation == "acquire":
            calls.append("acquire")
            assert json.loads((inputs / "request.json").read_text(encoding="utf-8"))["requirements"] == [
                "idna==3.10",
                *(["filelock==3.20.3"] if workspace else []),
            ]
            if workspace:
                assert (inputs / "wheels/backend-1-py3-none-any.whl").is_file()
            (destination / "wheels").mkdir()
            (destination / "wheel-manifest.json").write_text("{}", encoding="utf-8")
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
                ),
                encoding="utf-8",
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
    (project / "pyproject.toml").write_text('[project]\nname="unfamiliar"\nversion="1"\n[tool.uv]\n', encoding="utf-8")
    (project / "uv.lock").write_text("version=1\n", encoding="utf-8")
    plan = discover_project(project)
    calls = []

    def phase(_runtime, operation, inputs, destination):
        calls.append(operation)
        destination.mkdir()
        if operation == "uv":
            request = json.loads((inputs / ".specfact-uv.json").read_text(encoding="utf-8"))
            assert request["locked"] is True
            assert (inputs / "uv.lock").read_bytes() == (project / "uv.lock").read_bytes()
            (destination / "site-packages").mkdir()
            (destination / "prepared.lock").write_text("version=1\n", encoding="utf-8")
        else:
            assert operation == "inspect"
            assert (
                json.loads((inputs / "request.json").read_text(encoding="utf-8"))["schema"]
                == "native-site-inventory-v1"
            )
            (destination / "environment-inventory.json").write_text(
                json.dumps(
                    {
                        "installed": [],
                        "environment": {"sys_platform": "darwin", "python_full_version": "3.11.16"},
                        "member_graphs": {},
                        "analyzer_conflicts": {},
                    }
                ),
                encoding="utf-8",
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
        '[project]\nname="unfamiliar"\nversion="1"\n[tool.poetry]\npackage-mode=false\n', encoding="utf-8"
    )
    if lock_present:
        (project / "poetry.lock").write_text("locked fixture\n", encoding="utf-8")
    plan = discover_project(project)
    calls = []

    def dependencies(_runtime, requirements, root, name):
        assert requirements == ["poetry==2.4.3"]
        destination = root / name
        (destination / "site-packages").mkdir(parents=True)
        return destination

    def phase(_runtime, operation, inputs, destination):
        destination.mkdir()
        if operation == "hook":
            operation = json.loads((inputs / ".specfact-hook.json").read_text(encoding="utf-8"))["operation"]
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
            (destination / "hook-result.json").write_text(json.dumps(result), encoding="utf-8")
        elif operation == "acquire":
            value = json.loads((inputs / "request.json").read_text(encoding="utf-8"))
            if value["schema"] == "native-poetry-resolution-v1":
                assert set(inputs.iterdir()) == {inputs / "request.json", inputs / ".specfact-build-dependencies"}
                payload = '[metadata]\ncontent-hash="' + "a" * 64 + '"\n'
                (destination / "poetry.lock").write_text(payload, encoding="utf-8")
                (destination / "resolution.json").write_text(
                    json.dumps(
                        {
                            "manager": {"name": "poetry", "version": "2.4.3"},
                            "content_hash": "a" * 64,
                            "lock_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                        }
                    ),
                    encoding="utf-8",
                )
                calls.append(operation)
                return
            assert value["requirements"] == ["idna==3.10"]
            (destination / "wheels").mkdir()
            (destination / "wheel-manifest.json").write_text("{}", encoding="utf-8")
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
                ),
                encoding="utf-8",
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
    monkeypatch.setattr(native_project_runtime, "_runtime_tree", lambda _path, **_kwargs: inventory)
    assert native_project_runtime._bound_source_roots(project, wheels) == ["src"]
    assert inventory.calls == 1


def test_malformed_failure_receipt_preserves_incomplete_diagnostic(monkeypatch, tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "request.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(native_project_runtime.native_execution, "prepare_native_execution", SimpleNamespace)
    monkeypatch.setattr(native_project_runtime.native_execution, "BinaryNativeExecutionTransport", lambda lease: lease)

    class FailedSession:
        def __init__(self, _transport):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def launch(self, request):
            (request.output_root / "preparation-error.json").write_text("[]", encoding="utf-8")
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
    (project / "pyproject.toml").write_text('[build-system]\nrequires=[]\nbuild-backend="fixture"\n', encoding="utf-8")
    plan = discover_project(project)
    root = tmp_path / "preparation"
    root.mkdir()
    dependencies = root / "dependencies"
    dependencies.mkdir()
    monkeypatch.setattr(native_project_runtime, "_prepare_build_dependencies", lambda *_args: dependencies)

    def hook(_runtime, operation, _inputs, destination):
        assert operation == "hook"
        destination.mkdir()
        (destination / "hook-result.json").write_text(json.dumps(response), encoding="utf-8")

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
        (artifact / "site-packages/standalone.py").write_text("VALUE = 1\n", encoding="utf-8")
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

        def __enter__(self) -> Self:
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
        lambda selected, *_args, **_kwargs: json.loads((selected / "descriptor.json").read_text(encoding="utf-8")),
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
    assert (prepared.root / "site-packages/fixture_dep/__init__.py").read_text(encoding="utf-8") == "VALUE = 1\n"
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
    assert (
        descriptor["content_sha256"]
        == json.loads((bundle / "descriptor.json").read_text(encoding="utf-8"))["content_sha256"]
    )


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
            payload = b"14 comment=ok\n"
            member.size = len(payload)
            output.addfile(member, io.BytesIO(payload))
        member = tarfile.TarInfo("bundle/file")
        member.mode = 0o600
        output.addfile(member)
    monkeypatch.setattr(native_project_runtime, "_MAX_ACQUISITION_FILES", 2)
    calls = []
    original = tarfile.TarInfo.frombuf.__func__
    physical_headers = []
    original_member = native_project_runtime._AcquisitionTarInfo._proc_member

    def observe(cls, *arguments):
        calls.append(1)
        return original(cls, *arguments)

    def observe_member(member, source):
        physical_headers.append(member.type)
        return original_member(member, source)

    monkeypatch.setattr(tarfile.TarInfo, "frombuf", classmethod(observe))
    monkeypatch.setattr(native_project_runtime._AcquisitionTarInfo, "_proc_member", observe_member)
    with pytest.raises(ProjectRuntimeError, match="project_native_acquisition_archive_invalid"):
        native_project_runtime._extract_acquisition_archive(archive, tmp_path / "extracted")
    assert len(calls) <= 4
    assert len(physical_headers) == 4
    assert not (tmp_path / "extracted").exists()


def test_acquisition_archive_accepts_regular_member_at_exact_header_limit(monkeypatch, tmp_path):
    archive = tmp_path / "exact-headers.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.USTAR_FORMAT) as output:
        for name, payload in (("first", b"first bytes"), ("last", b"last bytes")):
            metadata = tarfile.TarInfo("metadata")
            metadata.type = tarfile.XGLTYPE
            metadata_payload = b"14 comment=ok\n"
            metadata.size = len(metadata_payload)
            output.addfile(metadata, io.BytesIO(metadata_payload))
            member = tarfile.TarInfo(f"bundle/{name}")
            member.mode = 0o600
            member.size = len(payload)
            output.addfile(member, io.BytesIO(payload))
    monkeypatch.setattr(native_project_runtime, "_MAX_ACQUISITION_FILES", 2)
    destination = tmp_path / "extracted"
    native_project_runtime._extract_acquisition_archive(archive, destination)
    assert (destination / "first").read_bytes() == b"first bytes"
    assert (destination / "last").read_bytes() == b"last bytes"


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
