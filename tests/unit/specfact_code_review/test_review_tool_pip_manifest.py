"""Guard: code-review pip_dependencies cover all external review tools."""

from __future__ import annotations

from pathlib import Path

import yaml

from specfact_code_review.tools.tool_availability import REVIEW_TOOL_PIP_PACKAGES


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PACKAGE = REPO_ROOT / "packages" / "specfact-code-review" / "module-package.yaml"


def test_module_package_lists_all_review_tool_pip_packages() -> None:
    data = yaml.safe_load(MODULE_PACKAGE.read_text(encoding="utf-8"))
    pip_deps: list[str] = data["pip_dependencies"]
    declared = set(pip_deps)
    for _tool_id, pip_name in REVIEW_TOOL_PIP_PACKAGES.items():
        assert pip_name in declared, f"Add {pip_name!r} to specfact-code-review module-package.yaml pip_dependencies"
