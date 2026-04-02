"""Tests for bundle_dependencies → registry index validation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_validate_repo_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "tools" / "validate_repo_manifests.py"
    spec = importlib.util.spec_from_file_location("validate_repo_manifests", path)
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
