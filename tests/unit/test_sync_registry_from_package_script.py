from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sync_registry_from_package.py"


def _minimal_registry(module_id: str, version: str, checksum: str, download_url: str) -> dict:
    return {
        "modules": [
            {
                "id": module_id,
                "latest_version": version,
                "download_url": download_url,
                "checksum_sha256": checksum,
                "tier": "official",
                "publisher": {"name": "nold-ai", "email": "hello@noldai.com"},
                "description": "test",
            }
        ]
    }


def test_sync_registry_tarball_bytes_match_for_identical_trees(tmp_path: Path) -> None:
    """Tar/gzip layers use fixed metadata so two runs produce identical artifact bytes."""

    def _write_minimal_repo(root: Path) -> str:
        (root / "registry" / "modules").mkdir(parents=True)
        (root / "registry" / "signatures").mkdir(parents=True)
        bundle = "specfact-syncregdet"
        bdir = root / "packages" / bundle
        bdir.mkdir(parents=True)
        old_ver = "0.1.0"
        old_name = f"{bundle}-{old_ver}.tar.gz"
        (root / "registry" / "modules" / old_name).write_bytes(b"old")
        (root / "registry" / "modules" / f"{old_name}.sha256").write_text(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n", encoding="utf-8"
        )
        manifest = {
            "name": "nold-ai/specfact-syncregdet",
            "version": "0.1.1",
            "tier": "official",
            "publisher": {"name": "nold-ai", "email": "hello@noldai.com"},
            "description": "test bundle",
            "bundle_group_command": "syncregdet",
            "integrity": {"checksum": "sha256:deadbeef", "signature": "dummy"},
        }
        (bdir / "module-package.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        (bdir / "README.md").write_text("hello", encoding="utf-8")
        reg_path = root / "registry" / "index.json"
        reg_path.write_text(
            json.dumps(
                _minimal_registry(
                    "nold-ai/specfact-syncregdet",
                    old_ver,
                    "a" * 64,
                    f"modules/{old_name}",
                ),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return bundle

    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    bundle = _write_minimal_repo(root_a)
    _write_minimal_repo(root_b)
    cmd_a = [sys.executable, str(SCRIPT), "--repo-root", str(root_a), "--bundle", bundle]
    cmd_b = [sys.executable, str(SCRIPT), "--repo-root", str(root_b), "--bundle", bundle]
    subprocess.run(cmd_a, check=True, cwd=str(REPO_ROOT))
    subprocess.run(cmd_b, check=True, cwd=str(REPO_ROOT))
    art_a = root_a / "registry" / "modules" / f"{bundle}-0.1.1.tar.gz"
    art_b = root_b / "registry" / "modules" / f"{bundle}-0.1.1.tar.gz"
    assert art_a.read_bytes() == art_b.read_bytes()


def test_sync_registry_from_package_updates_index_and_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "registry" / "modules").mkdir(parents=True)
    (root / "registry" / "signatures").mkdir(parents=True)
    bundle = "specfact-syncregtest"
    bdir = root / "packages" / bundle
    bdir.mkdir(parents=True)
    old_ver = "0.1.0"
    old_name = f"{bundle}-{old_ver}.tar.gz"
    (root / "registry" / "modules" / old_name).write_bytes(b"old")
    (root / "registry" / "modules" / f"{old_name}.sha256").write_text(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n", encoding="utf-8"
    )
    manifest = {
        "name": "nold-ai/specfact-syncregtest",
        "version": "0.1.1",
        "tier": "official",
        "publisher": {"name": "nold-ai", "email": "hello@noldai.com"},
        "description": "test bundle",
        "bundle_group_command": "syncregtest",
        "integrity": {"checksum": "sha256:deadbeef"},
    }
    (bdir / "module-package.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    (bdir / "README.md").write_text("hello", encoding="utf-8")

    reg_path = root / "registry" / "index.json"
    reg_path.write_text(
        json.dumps(
            _minimal_registry(
                "nold-ai/specfact-syncregtest",
                old_ver,
                "a" * 64,
                f"modules/{old_name}",
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root), "--bundle", bundle],
        check=True,
        cwd=str(REPO_ROOT),
    )

    data = json.loads(reg_path.read_text(encoding="utf-8"))
    mod = next(m for m in data["modules"] if m["id"] == "nold-ai/specfact-syncregtest")
    assert mod["latest_version"] == "0.1.1"
    assert mod["download_url"] == f"modules/{bundle}-0.1.1.tar.gz"

    art = root / "registry" / "modules" / f"{bundle}-0.1.1.tar.gz"
    assert art.is_file()
    side = art.with_suffix(art.suffix + ".sha256")
    assert side.is_file()
    assert mod["checksum_sha256"] == side.read_text(encoding="utf-8").strip().split()[0]


def test_sync_registry_from_package_cli_requires_bundle() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert proc.returncode != 0
