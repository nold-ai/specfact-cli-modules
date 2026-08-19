"""Guard: code-review pip_dependencies cover all external review tools."""

from __future__ import annotations

from pathlib import Path

import yaml
from packaging.requirements import Requirement

from specfact_code_review.tools.tool_availability import REVIEW_TOOL_PIP_PACKAGES


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PACKAGE = REPO_ROOT / "packages" / "specfact-code-review" / "module-package.yaml"


def test_module_package_lists_all_review_tool_pip_packages() -> None:
    data = yaml.safe_load(MODULE_PACKAGE.read_text(encoding="utf-8"))
    pip_deps: list[str] = data["pip_dependencies"]
    declared = {Requirement(item).name.lower().replace("_", "-") for item in pip_deps}
    for _tool_id, pip_name in REVIEW_TOOL_PIP_PACKAGES.items():
        normalized = Requirement(pip_name).name.lower().replace("_", "-")
        assert normalized not in declared, f"Keep analyzer-only {pip_name!r} out of host pip_dependencies"

    lock_path = (
        REPO_ROOT
        / "packages/specfact-code-review/src/specfact_code_review/resources/contracts/pr-range-v1-toolchain-lock.json"
    )
    lock_text = lock_path.read_text(encoding="utf-8")
    for pip_name in REVIEW_TOOL_PIP_PACKAGES.values():
        assert Requirement(pip_name).name.lower().replace("_", "-") in lock_text


def test_module_package_authenticates_suppression_catalog_resource() -> None:
    data = yaml.safe_load(MODULE_PACKAGE.read_text(encoding="utf-8"))
    resource = "resources/contracts/pr-range-v1-suppression-catalog.json"

    assert data["authenticated_resources"][resource]["digest"].startswith("sha256:")
    assert data["authenticated_resources"][resource]["checkpoint_contract"] == "suppression_catalog_contract"
