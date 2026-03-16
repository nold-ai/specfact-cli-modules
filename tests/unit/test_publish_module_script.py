from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import publish_module
from tests.unit._script_test_utils import block_contract_imports, load_module_from_path, run_python_script


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "publish_module.py"


def _load_publish_script():
    return load_module_from_path("publish_module_script", SCRIPT_PATH)


def test_publish_script_loads_without_beartype_or_icontract(monkeypatch) -> None:
    block_contract_imports(monkeypatch)

    publish_script = _load_publish_script()

    assert callable(publish_script.beartype)
    assert callable(publish_script.require)
    assert callable(publish_script.ensure)


def test_publish_module_can_compare_against_explicit_registry_index(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    bundle_dir = repo_root / "packages" / "specfact-backlog"
    registry_dir = repo_root / "registry"
    bundle_dir.mkdir(parents=True)
    registry_dir.mkdir(parents=True)

    (bundle_dir / "module-package.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-backlog",
                "version": "0.40.18",
                "core_compatibility": ">=0.40.0,<0.41.0",
            }
        ),
        encoding="utf-8",
    )
    (registry_dir / "index.json").write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "id": "nold-ai/specfact-backlog",
                        "latest_version": "0.40.18",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    baseline_path = tmp_path / "baseline-index.json"
    baseline_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "id": "nold-ai/specfact-backlog",
                        "latest_version": "0.40.17",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = publish_module.main(
        [
            "--bundle",
            "specfact-backlog",
            "--repo-root",
            str(repo_root),
            "--registry-index-path",
            str(baseline_path),
        ]
    )

    assert result == 0


def test_publish_module_rejects_when_explicit_registry_baseline_matches_manifest(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    bundle_dir = repo_root / "packages" / "specfact-backlog"
    registry_dir = repo_root / "registry"
    bundle_dir.mkdir(parents=True)
    registry_dir.mkdir(parents=True)

    (bundle_dir / "module-package.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-backlog",
                "version": "0.40.18",
                "core_compatibility": ">=0.40.0,<0.41.0",
            }
        ),
        encoding="utf-8",
    )
    (registry_dir / "index.json").write_text(
        json.dumps({"modules": []}),
        encoding="utf-8",
    )

    baseline_path = tmp_path / "baseline-index.json"
    baseline_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "id": "nold-ai/specfact-backlog",
                        "latest_version": "0.40.18",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = publish_module.main(
        [
            "--bundle",
            "specfact-backlog",
            "--repo-root",
            str(repo_root),
            "--registry-index-path",
            str(baseline_path),
        ]
    )

    assert result == 1


def test_publish_module_wrapper_runs_when_executed_as_script(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    bundle_dir = repo_root / "packages" / "specfact-backlog"
    registry_dir = repo_root / "registry"
    bundle_dir.mkdir(parents=True)
    registry_dir.mkdir(parents=True)

    (bundle_dir / "module-package.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-backlog",
                "version": "0.40.18",
                "core_compatibility": ">=0.40.0,<0.41.0",
            }
        ),
        encoding="utf-8",
    )
    (registry_dir / "index.json").write_text(json.dumps({"modules": []}), encoding="utf-8")

    result = run_python_script(
        REPO_ROOT / "scripts" / "publish-module.py",
        "--bundle",
        "specfact-backlog",
        "--repo-root",
        str(repo_root),
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout
