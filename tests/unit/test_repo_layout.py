from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


EXPECTED_BUNDLES = [
    "specfact-project",
    "specfact-backlog",
    "specfact-codebase",
    "specfact-spec",
    "specfact-govern",
]


def test_bundle_package_layout_exists() -> None:
    for bundle in EXPECTED_BUNDLES:
        pkg_name = bundle.replace("-", "_")
        path = ROOT / "packages" / bundle / "src" / pkg_name / "__init__.py"
        assert path.exists(), f"Missing package __init__: {path}"


def test_registry_index_exists() -> None:
    assert (ROOT / "registry" / "index.json").exists()


def test_module_manifests_exist() -> None:
    for bundle in EXPECTED_BUNDLES:
        manifest = ROOT / "packages" / bundle / "module-package.yaml"
        assert manifest.exists(), f"Missing module-package.yaml: {manifest}"
