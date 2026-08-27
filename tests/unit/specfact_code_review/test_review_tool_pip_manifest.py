"""Guard: code-review pip_dependencies cover all external review tools."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from packaging.requirements import Requirement

from specfact_code_review.tools.tool_availability import REVIEW_TOOL_PIP_PACKAGES


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PACKAGE = REPO_ROOT / "packages" / "specfact-code-review" / "module-package.yaml"


def _normalized_distribution(requirement: str) -> str:
    return Requirement(requirement).name.lower().replace("_", "-")


def test_review_tool_pip_packages_are_locked_not_host_dependencies() -> None:
    data = yaml.safe_load(MODULE_PACKAGE.read_text(encoding="utf-8"))
    pip_deps: list[str] = data["pip_dependencies"]
    declared = {_normalized_distribution(item) for item in pip_deps}
    for _tool_id, pip_name in REVIEW_TOOL_PIP_PACKAGES.items():
        normalized = _normalized_distribution(pip_name)
        assert normalized not in declared, f"Keep analyzer-only {pip_name!r} out of host pip_dependencies"

    lock_path = (
        REPO_ROOT
        / "packages/specfact-code-review/src/specfact_code_review/resources/contracts/pr-range-v1-toolchain-lock.json"
    )
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    expected = {_normalized_distribution(pip_name) for pip_name in REVIEW_TOOL_PIP_PACKAGES.values()}
    for environment in lock["environments"]:
        locked = {
            _normalized_distribution(str(component["id"]))
            for component in environment["components"]
            if component.get("kind") == "python_distribution"
        }
        missing = expected - locked
        assert not missing, f"{environment.get('python_abi')} is missing locked analyzers: {sorted(missing)}"


def test_module_package_authenticates_suppression_catalog_resource() -> None:
    data = yaml.safe_load(MODULE_PACKAGE.read_text(encoding="utf-8"))
    resource = "resources/contracts/pr-range-v1-suppression-catalog.json"

    assert data["authenticated_resources"][resource]["digest"].startswith("sha256:")
    assert data["authenticated_resources"][resource]["checkpoint_contract"] == "suppression_catalog_contract"


def test_module_package_authenticates_raw_project_runtime_schema_bytes() -> None:
    data = yaml.safe_load(MODULE_PACKAGE.read_text(encoding="utf-8"))
    resource = "resources/contracts/project-runtime-layer-v1.schema.json"
    resource_path = REPO_ROOT / "packages/specfact-code-review/src/specfact_code_review" / resource
    expected = "sha256:" + hashlib.sha256(resource_path.read_bytes()).hexdigest()

    assert data["authenticated_resources"][resource]["digest"] == expected
