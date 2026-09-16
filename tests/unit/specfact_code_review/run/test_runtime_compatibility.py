"""Per-analyzer dependency conflicts never silently substitute project versions."""

import importlib.util
import json
import shutil
import tomllib
from importlib import import_module
from importlib.metadata import distribution
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from specfact_code_review.run import target_bootstrap, target_launch
from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts
from specfact_code_review.run.runtime_domains import member_dependency_graphs


def test_incompatible_dependency_identifies_only_affected_member(tmp_path: Path) -> None:

    metadata = tmp_path / "pylint-4.0.7.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: pylint\nVersion: 4.0.7\nRequires-Dist: shared>=2\n"
    )
    inventory = {
        "installed": [{"metadata": {"name": "shared", "version": "1.0"}}],
        "environment": {"python_version": "3.12"},
    }
    conflicts = analyzer_dependency_conflicts(inventory, tmp_path)
    assert "shared" in conflicts["pylint"]
    assert ">=2" in conflicts["pylint"]
    assert "basedpyright" not in conflicts


@pytest.mark.parametrize("version", ["2.1", "2.1rc1"])
def test_compatible_common_project_package_is_not_rejected(tmp_path: Path, version: str) -> None:

    metadata = tmp_path / "pylint-4.0.7.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: pylint\nVersion: 4.0.7\nRequires-Dist: shared>=2\n"
    )
    inventory = {
        "installed": [
            {"metadata": {"name": "shared", "version": version}},
            {"metadata": {"name": "requests", "version": "2.32.4"}},
        ]
    }
    assert not analyzer_dependency_conflicts(inventory, tmp_path)


def _declared_development_dependencies(root: Path) -> dict[str, Requirement]:
    return {
        str(canonicalize_name(requirement.name)): requirement
        for value in tomllib.loads((root / "pyproject.toml").read_text())["tool"]["hatch"]["envs"]["default"][
            "dependencies"
        ]
        for requirement in (Requirement(value),)
    }


def _newest_declared_version(requirement: Requirement, pinned: Version, observed: str) -> Version:
    candidates = (pinned, Version(observed))
    return max(version for version in candidates if requirement.specifier.contains(version))


@pytest.mark.parametrize("environment_index", [0, 1, 2])
def test_declared_development_tools_admit_compatible_signed_entries(tmp_path: Path, environment_index: int) -> None:
    """Declared dev ranges must exclude the real incompatible native resolution."""
    root = Path(__file__).resolve().parents[4]
    contract = root / "packages/specfact-code-review/src/specfact_code_review/resources/contracts"
    environment = json.loads((contract / "pr-range-v1-toolchain-lock.json").read_text())["environments"][
        environment_index
    ]
    declared = _declared_development_dependencies(root)
    # Recorded native run 35068293754; raw inventory remains in the change evidence.
    observed = {"pylint": "4.0.8", "basedpyright": "1.40.1", "nodejs-wheel-binaries": "24.19.0"}
    inventory = {"installed": []}
    incompatible_inventory = {"installed": []}
    for component in environment["components"]:
        name = component["normalized_name"]
        if name not in observed:
            continue
        pinned = Version(component["version"])
        assert declared[name].specifier.contains(pinned), f"Declared {name} excludes signed entry {pinned}"
        selected = _newest_declared_version(declared[name], pinned, observed[name])
        metadata = tmp_path / f"{name}-{pinned}.dist-info"
        metadata.mkdir()
        dependency = "Requires-Dist: nodejs-wheel-binaries>=20.13.1\n" if name == "basedpyright" else ""
        (metadata / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {pinned}\n{dependency}")
        inventory["installed"].append({"metadata": {"name": name, "version": str(selected)}})
        incompatible_inventory["installed"].append({"metadata": {"name": name, "version": observed[name]}})
    assert {row["metadata"]["name"] for row in inventory["installed"]} == set(observed)
    assert not analyzer_dependency_conflicts(inventory, tmp_path)
    conflicts = analyzer_dependency_conflicts(incompatible_inventory, tmp_path)
    assert set(conflicts) == {"pylint", "basedpyright"}
    assert "nodejs-wheel-binaries" in conflicts["basedpyright"]


def _node_distribution(root: Path, name: str, version: str, module: str, requirement: str = "") -> None:
    """Write a bounded package inventory using the real BasedPyright dependency name."""
    metadata = root / f"{name.replace('-', '_')}-{version}.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
        + (f"Requires-Dist: {requirement}\n" if requirement else "")
    )
    payload = root / module / "__init__.py"
    payload.parent.mkdir()
    payload.write_text("ORIGIN = 'sealed-node'\n")
    (metadata / "RECORD").write_text(f"{module}/__init__.py,,\n")


@pytest.fixture(name="node_analyzers")
def sealed_node_analyzer_fixture(tmp_path: Path) -> Path:
    """Model the signed entries and the wheel's actual Requires-Dist metadata."""
    sealed = tmp_path / "sealed"
    sealed.mkdir()
    _node_distribution(sealed, "basedpyright", "1.39.10", "basedpyright", "nodejs-wheel-binaries>=20.13.1")
    _node_distribution(sealed, "nodejs-wheel-binaries", "24.16.0", "nodejs_wheel")
    for name in ("pylint", "crosshair-tool", "pytest", "pytest-cov"):
        _node_distribution(sealed, name, "1.0", name.replace("-", "_"))
    return sealed


def test_basedpyright_node_version_conflict_is_explicit(node_analyzers: Path) -> None:
    """A compatible upstream range cannot replace a sealed member entry."""
    inventory = {"installed": [{"metadata": {"name": "nodejs-wheel-binaries", "version": "24.19.0"}}]}
    assert analyzer_dependency_conflicts(inventory, node_analyzers) == {
        "basedpyright": "project_analyzer_dependency_incompatible:"
        "nodejs-wheel-binaries: target=24.19.0, sealed entry=24.16.0"
    }


def _mount_node_member(tmp_path: Path, sealed: Path, graph: dict, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Materialize only the real launcher's admitted paths, without invoking bwrap."""
    member = tmp_path / "member"
    member.mkdir()
    (tmp_path / "project-runtime.json").write_text(
        json.dumps({"inventory": {"member_graphs": {"basedpyright": graph}}})
    )
    monkeypatch.setattr(target_launch, "PROJECT", tmp_path)
    monkeypatch.setattr(target_launch, "SEALED", sealed)
    monkeypatch.setattr(target_launch, "MEMBER", member)
    mounts = target_launch.member_mounts("basedpyright")
    for index, argument in enumerate(mounts):
        if argument == "--ro-bind":
            shutil.copytree(mounts[index + 1], mounts[index + 2])
    return member


@pytest.mark.parametrize("project_version", [None, "24.16.0"], ids=["absent", "matching"])
def test_basedpyright_node_closure_keeps_verified_import(
    tmp_path: Path, node_analyzers: Path, monkeypatch: pytest.MonkeyPatch, project_version: str | None
) -> None:
    """Matching or absent target Node must remain available through the sealed finder."""
    installed = (
        [] if project_version is None else [{"metadata": {"name": "nodejs-wheel-binaries", "version": project_version}}]
    )
    inventory = {"installed": installed}
    assert not analyzer_dependency_conflicts(inventory, node_analyzers)
    graph = member_dependency_graphs(inventory, node_analyzers)["basedpyright"]
    member = _mount_node_member(tmp_path, node_analyzers, graph, monkeypatch)
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", member)
    finder = target_bootstrap.DomainFinder(graph)
    finder.names.update(target_bootstrap._TOOL_IMPORTS["basedpyright"])
    spec = finder.find_spec("nodejs_wheel")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.ORIGIN == "sealed-node"
    assert module.__file__ is not None
    assert Path(module.__file__).is_relative_to(member)
    assert (member / "nodejs_wheel_binaries-24.16.0.dist-info/METADATA").is_file()
    assert next(row for row in graph["installed"] if row["name"] == "nodejs-wheel-binaries")["origin"] == "analyzer"


def test_unrelated_legacy_node_distribution_is_not_restricted(node_analyzers: Path) -> None:
    """A project package with the obsolete name is outside this member closure."""
    inventory = {"installed": [{"metadata": {"name": "nodejs-wheel", "version": "99.0"}}]}
    assert not analyzer_dependency_conflicts(inventory, node_analyzers)
    graph = member_dependency_graphs(inventory, node_analyzers)["basedpyright"]
    assert "nodejs-wheel" not in {row["name"] for row in graph["installed"]}
    assert "nodejs_wheel" in graph["sealed_imports"]


def test_declared_core_dependency_supplies_registry_handoff() -> None:
    """Hermetic Hatch inputs must include the real registry API used by review."""
    root = Path(__file__).resolve().parents[4]
    declared = _declared_development_dependencies(root)
    requirement = declared.get("specfact-cli")
    assert requirement is not None, "Core installed by developer bootstrap is not a declared target dependency"
    installed = distribution("specfact-cli")
    assert str(requirement.specifier) == f"=={installed.version}", "Declare the verified immutable core release"
    for module_name, entry in (
        ("module_discovery", "discover_all_modules_for_project_with_shadowed"),
        ("module_installer", "verify_module_artifact"),
    ):
        module = import_module(f"specfact_cli.registry.{module_name}")
        assert callable(getattr(module, entry)), f"Declared core does not supply registry API {entry}"
