"""Tests for bundle_dependencies → registry index validation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_validate_repo_module():
    """Load tools/validate_repo_manifests.py with a unique module name.

    Avoids ``sys.modules['validate_repo_manifests']`` collisions if another import
    path cached an older copy of the module during the same pytest session.
    """
    root = Path(__file__).resolve().parents[2]
    path = root / "tools" / "validate_repo_manifests.py"
    name = "specfact_cli_modules_validate_repo_manifests"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_validate_manifest_bundle_dependency_refs_flags_dangling_id(tmp_path: Path) -> None:
    v = _load_validate_repo_module()
    registry_path = tmp_path / "index.json"
    registry_path.write_text(
        json.dumps({"modules": [{"id": "nold-ai/specfact-project", "latest_version": "0.1.0"}]}),
        encoding="utf-8",
    )
    registry_ids = v.registry_module_ids(registry_path)
    manifest = tmp_path / "module-package.yaml"
    manifest.write_text(
        "name: nold-ai/specfact-code-review\n"
        "bundle_dependencies:\n"
        "  - nold-ai/specfact-project\n"
        "  - nold-ai/specfact-not-in-registry\n",
        encoding="utf-8",
    )
    errors = v.validate_manifest_bundle_dependency_refs(manifest, registry_ids)
    assert len(errors) == 1
    assert "specfact-not-in-registry" in errors[0]
    assert str(manifest) in errors[0]


def test_validate_registry_consistency_flags_bad_checksum(tmp_path: Path) -> None:
    v = _load_validate_repo_module()
    modules_dir = tmp_path / "registry" / "modules"
    modules_dir.mkdir(parents=True)
    registry_path = tmp_path / "index.json"
    tarball_name = "specfact-project-0.41.3.tar.gz"
    (modules_dir / f"{tarball_name}.sha256").write_text("deadbeef\n", encoding="utf-8")
    registry_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "id": "nold-ai/specfact-project",
                        "latest_version": "0.41.3",
                        "download_url": f"modules/{tarball_name}",
                        "checksum_sha256": "a3df973c103e0708bef7a6ad23ead9b45e3354ba2ecb878f4d64e753e163a817",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pkg = tmp_path / "packages" / "specfact-project"
    pkg.mkdir(parents=True)
    (pkg / "module-package.yaml").write_text(
        "name: nold-ai/specfact-project\n"
        "version: 0.41.3\n"
        "tier: official\n"
        "publisher:\n  name: nold-ai\n  email: hello@noldai.com\n"
        "description: d\n"
        "bundle_group_command: x\n",
        encoding="utf-8",
    )
    errors = v.validate_registry_consistency(tmp_path, registry_path)
    assert len(errors) == 1
    assert "does not match sidecar" in errors[0]


def test_validate_manifest_bundle_dependency_refs_ok_when_all_present(tmp_path: Path) -> None:
    v = _load_validate_repo_module()
    registry_path = tmp_path / "index.json"
    registry_path.write_text(
        json.dumps(
            {
                "modules": [
                    {"id": "nold-ai/specfact-project", "latest_version": "0.1.0"},
                    {"id": "nold-ai/specfact-codebase", "latest_version": "0.1.0"},
                ]
            }
        ),
        encoding="utf-8",
    )
    registry_ids = v.registry_module_ids(registry_path)
    manifest = tmp_path / "module-package.yaml"
    manifest.write_text(
        "name: nold-ai/specfact-code-review\nbundle_dependencies:\n  - nold-ai/specfact-codebase\n",
        encoding="utf-8",
    )
    assert v.validate_manifest_bundle_dependency_refs(manifest, registry_ids) == []
