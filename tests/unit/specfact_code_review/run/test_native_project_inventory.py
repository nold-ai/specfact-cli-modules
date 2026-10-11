"""Native extension, cache, version and reviewed-source inventory proofs."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from dataclasses import replace
from functools import partial
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specfact_code_review.run import native_project_runtime
from specfact_code_review.run.native_project_catalog import ProjectArtifactLocator
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError
from tests.unit.specfact_code_review.run.native_project_runtime_fixtures import (
    _CPU_ARM64,
    _CPU_X86_64,
    _bundle,
    _fat_macho,
    _thin_macho,
)


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
    descriptor = json.loads((staged / "descriptor.json").read_text(encoding="utf-8"))
    content = descriptor["content_sha256"]
    acquisition_cache = tmp_path / "acquisitions"
    runtime_cache = tmp_path / "runtimes"
    downloads: list[str] = []
    executions: list[Path] = []

    def acquire(url: str, destination: Path) -> None:
        downloads.append(url)
        shutil.copytree(staged, destination)

    def verify(bundle: Path, *_args: object, **_kwargs: object) -> dict[str, Any]:
        value = json.loads((bundle / "descriptor.json").read_text(encoding="utf-8"))
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
    descriptor = json.loads((staged / "descriptor.json").read_text(encoding="utf-8"))
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
        lambda bundle, *_args, **_kwargs: json.loads((bundle / "descriptor.json").read_text(encoding="utf-8")),
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
        lambda bundle, *_args, **_kwargs: json.loads((bundle / "descriptor.json").read_text(encoding="utf-8")),
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
    assert (cache / "bindings" / native_project_runtime._cache_key(plan, runtime)).read_text(
        encoding="utf-8"
    ) == content + "\n"


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
    (tmp_path / "poetry.lock").write_text(lock, encoding="utf-8")
    assert native_project_runtime._validated_poetry_sources(tmp_path, [declaration]) == [declaration]
    with pytest.raises(ProjectRuntimeError, match="source_lock_mismatch"):
        native_project_runtime._validated_poetry_sources(tmp_path, [{**declaration, "commit": "0" * 40}])
    assert (tmp_path / "poetry.lock").read_text(encoding="utf-8") == lock


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

    def phase(_runtime, operation, _inputs, output):
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
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", phase)
    with pytest.raises(ProjectRuntimeError, match="preparation_incomplete:python_version"):
        native_project_runtime._inspect_project_site(
            SimpleNamespace(environment_id="darwin-arm64-cp311"), artifact, tmp_path
        )


def test_poetry_source_and_index_wheels_keep_separate_identities(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "pyproject.toml").write_text('[project]\nname="root"\nversion="1"\n', encoding="utf-8")
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

    def phase(_runtime, operation, inputs, output):
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
    (acquired / "resolution.json").write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ProjectRuntimeError, match="resolution_binding_mismatch"):
        native_project_runtime._admit_poetry_resolution(acquired, request)


@pytest.mark.parametrize("installed", [False, True])
def test_generated_project_module_does_not_discard_verified_source_root(tmp_path, installed):
    project = tmp_path / "project"
    (project / "src/customer").mkdir(parents=True)
    source = project / "src/customer/__init__.py"
    source.write_bytes(b"VALUE=7\n")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    if installed:
        (artifacts / "customer").mkdir()
        (artifacts / "customer/__init__.py").write_bytes(b"VALUE=7\n")
        (artifacts / "customer/_version.py").write_bytes(b"VERSION='generated'\n")
        _write_native_distribution_record(artifacts, "customer", ["customer/__init__.py", "customer/_version.py"])
    else:
        with zipfile.ZipFile(artifacts / "customer-1-py3-none-any.whl", "w") as wheel:
            wheel.writestr("customer/__init__.py", b"VALUE=7\n")
            wheel.writestr("customer/_version.py", b"VERSION='generated'\n")
    overlay = tmp_path / "overlay"
    assert native_project_runtime._bound_source_roots(project, artifacts, installed=installed) == []
    assert native_project_runtime._bound_source_roots(
        project, artifacts, installed=installed, generated_destination=overlay
    ) == ["src"]
    assert (overlay / "src/customer/_version.py").read_bytes() == b"VERSION='generated'\n"
    assert not (project / "src/customer/_version.py").exists()
    assert native_project_runtime._bound_source_roots(project, artifacts, installed=installed) == []
    source.write_bytes(b"VALUE=changed\n")
    assert native_project_runtime._bound_source_roots(project, artifacts, installed=installed) == []


def test_source_matching_budget_counts_only_matching_package_paths(tmp_path):
    project = tmp_path / "project"
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    with zipfile.ZipFile(wheels / "customer-1-py3-none-any.whl", "w") as archive:
        for index in range(320):
            package = f"customer_{index}"
            source = project / "src" / package / "__init__.py"
            source.parent.mkdir(parents=True)
            content = b"# " + b"x" * index + b"\n"
            source.write_bytes(content)
            archive.writestr(f"{package}/__init__.py", content)
    assert native_project_runtime._bound_source_roots(project, wheels) == ["src"]


def test_source_matching_uses_full_suffix_index_for_shared_package_tails(monkeypatch, tmp_path):
    project = tmp_path / "project"
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    with zipfile.ZipFile(wheels / "customer-1-py3-none-any.whl", "w") as archive:
        for index in range(3000):
            package = f"customer_{index}/common"
            source = project / "src" / package / "__init__.py"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"VALUE=7\n")
            archive.writestr(f"{package}/__init__.py", b"VALUE=7\n")
    original = native_project_runtime.PurePosixPath

    class CountedPath(original):
        checks = 0

        @property
        def parts(self):
            type(self).checks += 1
            return super().parts

    monkeypatch.setattr(native_project_runtime, "PurePosixPath", CountedPath)
    assert native_project_runtime._bound_source_roots(project, wheels) == ["src"]
    assert CountedPath.checks < 100000


def _write_native_distribution_record(site, name, paths):
    metadata = site / f"{name}-1.dist-info"
    metadata.mkdir()
    rows = []
    for relative in paths:
        payload = (site / relative).read_bytes()
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).decode().rstrip("=")
        rows.append(f"{relative},sha256={digest},{len(payload)}\n")
    (metadata / "RECORD").write_text("".join(rows), encoding="utf-8")
    return metadata / "RECORD"


@pytest.mark.parametrize(
    "case",
    list(product([True, False], ["_version.py", "_version.pyi"], ["matching", "changed", "ambiguous"], [False, True])),
)
def test_uv_generated_module_preserves_only_byte_bound_implicit_source(monkeypatch, tmp_path, case):
    lock_present, generated_name, source_binding, explicit_roots = case
    project = tmp_path / "project"
    package = project / "src/customer"
    package.mkdir(parents=True)
    (project / "pyproject.toml").write_text('[project]\nname="customer"\nversion="1"\n[tool.uv]\n', encoding="utf-8")
    source_bytes = b"VALUE='reviewed source'\n"
    (package / "__init__.py").write_bytes(source_bytes)
    if source_binding == "ambiguous":
        other = project / "other/customer"
        other.mkdir(parents=True)
        (other / "__init__.py").write_bytes(source_bytes)
    if lock_present:
        (project / "uv.lock").write_text("version=1\n", encoding="utf-8")
    plan = discover_project(project)
    assert not plan.source_roots
    if explicit_roots:
        plan = replace(plan, source_roots=("src",))
    artifact = tmp_path / "artifact"
    generated_bytes = b"VERSION='generated build'\n"
    calls = []

    context = (calls, lock_present, source_bytes, source_binding, generated_name, generated_bytes)
    monkeypatch.setattr(native_project_runtime, "_run_pip_phase", partial(_generated_uv_phase, context))
    inventory = native_project_runtime._prepare_project_on_demand(
        plan, SimpleNamespace(root=tmp_path / "capsule", environment_id="darwin-arm64-cp311"), artifact
    )
    _assert_generated_uv_preparation(
        (project, package, artifact),
        inventory,
        calls,
        (lock_present, source_bytes, source_binding, generated_name, generated_bytes, explicit_roots),
    )


def _assert_generated_uv_preparation(paths, inventory, calls, binding):
    project, package, artifact = paths
    lock_present, source_bytes, source_binding, generated_name, generated_bytes, explicit_roots = binding
    assert calls == ["uv", "inspect"]
    assert inventory["native_preparation"]["existing_lock_preserved"] is lock_present
    assert (project / "uv.lock").exists() is lock_present
    assert (package / "__init__.py").read_bytes() == source_bytes
    assert not (package / generated_name).exists()
    overlay = artifact / "source-overlay"
    if source_binding == "matching" and not explicit_roots:
        assert inventory["source_roots"] == ["src"]
        _assert_generated_source_overlay(overlay, generated_name, generated_bytes)
    else:
        assert inventory["source_roots"] == (["src"] if explicit_roots else [])
        assert not overlay.exists()


def _generated_uv_phase(context, _runtime, operation, inputs, destination):
    calls, lock_present, source_bytes, source_binding, generated_name, generated_bytes = context
    calls.append(operation)
    destination.mkdir()
    if operation == "uv":
        request = json.loads((inputs / ".specfact-uv.json").read_text(encoding="utf-8"))
        assert request["locked"] is lock_present
        _install_generated_uv_site(destination, (source_bytes, source_binding, generated_name, generated_bytes))
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


def _install_generated_uv_site(destination, binding):
    source_bytes, source_binding, generated_name, generated_bytes = binding
    site = destination / "site-packages"
    installed = site / "customer"
    installed.mkdir(parents=True)
    (installed / "__init__.py").write_bytes(
        source_bytes if source_binding != "changed" else b"VALUE='different build'\n"
    )
    (installed / generated_name).write_bytes(generated_bytes)
    (site / "unrelated_dependency.py").write_text("VALUE='dependency'\n", encoding="utf-8")
    _write_native_distribution_record(site, "customer", ["customer/__init__.py", f"customer/{generated_name}"])
    _write_native_distribution_record(site, "dependency", ["unrelated_dependency.py"])
    (destination / "prepared.lock").write_text("version=1\n", encoding="utf-8")


def _assert_generated_source_overlay(overlay, generated_name, generated_bytes):
    generated = overlay / "src/customer" / generated_name
    assert generated.read_bytes() == generated_bytes
    assert generated.stat().st_mode & 0o777 == 0o400
    assert {path.relative_to(overlay).as_posix() for path in overlay.rglob("*") if path.is_file()} == {
        f"src/customer/{generated_name}"
    }


@pytest.mark.parametrize("namespace", [False, True])
@pytest.mark.parametrize("generated_name", ["_version.py", "_version.pyi"])
@pytest.mark.parametrize(
    "ownership",
    [
        "valid",
        "same_owner",
        "outside_script",
        "missing",
        "unrecorded_generated",
        "ambiguous",
        "changed_digest",
        "malformed",
    ],
)
def test_uv_overlay_excludes_shared_package_dependencies(tmp_path, namespace, generated_name, ownership):
    project = tmp_path / "project"
    package = "ns/customer" if namespace else "customer"
    dependency = "ns/plugin" if namespace else ("otherlib" if ownership == "same_owner" else "customer/plugin")
    source = project / "src" / package
    source.mkdir(parents=True)
    source_bytes = b"VALUE='source'\n"
    (source / "__init__.py").write_bytes(source_bytes)
    site = tmp_path / "site"
    installed = site / package
    installed.mkdir(parents=True)
    (installed / "__init__.py").write_bytes(source_bytes)
    (installed / generated_name).write_bytes(b"VERSION='built'\n")
    foreign = site / dependency
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text(
        "from pathlib import Path\nVALUE=Path(__file__).with_name('data.txt').read_text()\n", encoding="utf-8"
    )
    (foreign / "data.txt").write_text("dependency resource\n", encoding="utf-8")
    record = _write_native_distribution_record(
        site, "customer", [f"{package}/__init__.py", f"{package}/{generated_name}"]
    )
    foreign_record = _write_native_distribution_record(site, "plugin", [f"{dependency}/__init__.py"])
    _mutate_distribution_ownership(record, foreign_record, ownership, installed, generated_name)
    overlay = tmp_path / "overlay"
    if ownership in {"ambiguous", "changed_digest", "malformed"}:
        with pytest.raises(ProjectRuntimeError, match="project_native_source_ownership_invalid"):
            native_project_runtime._bound_source_roots(project, site, installed=True, generated_destination=overlay)
    else:
        roots = native_project_runtime._bound_source_roots(project, site, installed=True, generated_destination=overlay)
        assert roots == (["src"] if ownership in {"valid", "same_owner", "outside_script"} else [])
    _assert_shared_package_overlay(overlay, (package, dependency, generated_name), ownership)
    assert (foreign / "data.txt").read_text(encoding="utf-8") == "dependency resource\n"
    assert not (source / generated_name).exists()


def _assert_shared_package_overlay(overlay, paths, ownership):
    package, dependency, generated_name = paths
    if ownership in {"valid", "same_owner", "outside_script"}:
        assert (overlay / "src" / package / generated_name).read_bytes() == b"VERSION='built'\n"
        assert not (overlay / "src" / dependency).exists()
        assert {path.relative_to(overlay).as_posix() for path in overlay.rglob("*") if path.is_file()} == {
            f"src/{package}/{generated_name}"
        }
    else:
        assert not overlay.exists()


def _mutate_distribution_ownership(record, foreign_record, ownership, installed, generated_name):
    site = record.parent.parent
    package = installed.relative_to(site).as_posix()
    if ownership == "same_owner":
        record.write_text(
            record.read_text(encoding="utf-8") + foreign_record.read_text(encoding="utf-8"), encoding="utf-8"
        )
        foreign_record.unlink()
    elif ownership == "outside_script":
        record.write_text(
            record.read_text(encoding="utf-8") + "../../../bin/tool.py,,\n/opt/external/tool.py,,\n", encoding="utf-8"
        )
    if ownership == "missing":
        record.unlink()
    elif ownership == "unrecorded_generated":
        record.write_text(
            "".join(
                line
                for line in record.read_text(encoding="utf-8").splitlines(keepends=True)
                if generated_name not in line
            ),
            encoding="utf-8",
        )
    elif ownership == "ambiguous":
        _write_native_distribution_record(site, "duplicate", [f"{package}/{generated_name}"])
    elif ownership == "changed_digest":
        (installed / generated_name).write_bytes(b"VERSION='changed after record'\n")
    elif ownership == "malformed":
        record.write_text("malformed,record\n", encoding="utf-8")


@pytest.mark.parametrize("ancestor", ["customer", "customer/sub"])
@pytest.mark.parametrize("initializer", ["__init__.py", "__init__.pyi"])
@pytest.mark.parametrize("attached", [False, True])
def test_uv_generated_ancestor_initializer_keeps_imports_on_reviewed_source(
    tmp_path, ancestor, initializer, attached, monkeypatch
):
    if attached:
        from specfact_code_review.run.target_bootstrap import _validate_python_arguments

        run = subprocess.run

        def attached_run(command, **options):
            _validate_python_arguments(command[1:])
            return run(command, **options)

        monkeypatch.setattr(subprocess, "run", attached_run)
    project = tmp_path / "project"
    source = project / "src/customer/sub/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE='original source'\n", encoding="utf-8")
    site = tmp_path / "site"
    installed = site / "customer/sub/module.py"
    installed.parent.mkdir(parents=True)
    installed.write_bytes(source.read_bytes())
    generated = site / ancestor / initializer
    generated.write_text("READY=True\n", encoding="utf-8")
    _write_native_distribution_record(site, "customer", ["customer/sub/module.py", f"{ancestor}/{initializer}"])
    overlay = tmp_path / "overlay"
    roots = native_project_runtime._bound_source_roots(project, site, installed=True, generated_destination=overlay)
    assert roots == ["src"]
    staged = tmp_path / "staged"
    shutil.copytree(project, staged)
    if overlay.exists():
        shutil.copytree(overlay, staged, dirs_exist_ok=True)
    (staged / "src/customer/sub/module.py").write_text("VALUE='edited reviewed source'\n", encoding="utf-8")
    child = subprocess.run(
        [
            sys.executable,
            "-P",
            "-B",
            "-c",
            "import sys,json;sys.path[:0]=sys.argv[1:];import customer.sub.module as selected;"
            + "print(json.dumps([selected.VALUE,selected.__file__]))",
            str(staged / "src"),
            str(site),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    value, imported = json.loads(child.stdout)
    assert value == "edited reviewed source"
    assert Path(imported) == staged / "src/customer/sub/module.py"
    assert (overlay / "src" / ancestor / initializer).read_bytes() == generated.read_bytes()
    assert not (project / "src" / ancestor / initializer).exists()
    assert source.read_text(encoding="utf-8") == "VALUE='original source'\n"


@pytest.mark.parametrize("budget", ["files", "bytes"])
def test_source_index_excludes_separate_vcs_budget_and_preserves_runtime_validation(tmp_path, monkeypatch, budget):
    source = tmp_path / "src/customer.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    metadata = tmp_path / ".git/objects/pack/fixture.pack"
    metadata.parent.mkdir(parents=True)
    metadata.write_bytes(b"x" * 1024)
    if budget == "files":
        monkeypatch.setattr(native_project_runtime, "_MAX_RUNTIME_FILES", 2)
        (metadata.parent / "fixture.idx").write_bytes(b"index")
    else:
        monkeypatch.setattr(native_project_runtime, "_MAX_RUNTIME_BYTES", 64)
    index = native_project_runtime._source_suffix_index(tmp_path)
    assert index[("customer.py",)] == [(native_project_runtime.PurePosixPath("src/customer.py"), source.stat().st_size)]
    with pytest.raises(ProjectRuntimeError, match="runtime_bounds_exceeded"):
        native_project_runtime._runtime_tree(tmp_path)
    source.write_bytes(b"x" * 128)
    if budget == "files":
        for name in ("other.py", "third.py"):
            (source.parent / name).touch()
    with pytest.raises(ProjectRuntimeError, match="bounds_exceeded"):
        native_project_runtime._source_suffix_index(tmp_path)
