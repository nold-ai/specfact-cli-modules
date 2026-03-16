from __future__ import annotations

from pathlib import Path

import yaml

from scripts import link_dev_module
from tests.unit._script_test_utils import run_python_script


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_module_source(source_dir: Path) -> None:
    source_dir.mkdir(parents=True)
    (source_dir / "src").mkdir()
    (source_dir / "src" / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source_dir / ".semgrep").mkdir()
    (source_dir / ".semgrep" / "rules.yaml").write_text("rules: []\n", encoding="utf-8")
    (source_dir / "module-package.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-example",
                "version": "0.1.0",
                "commands": ["example"],
                "core_compatibility": ">=0.40.0,<1.0.0",
                "description": "Example module.",
                "integrity": {
                    "checksum": "sha256:deadbeef",
                    "signature": "signed",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_link_dev_module_creates_shadow_symlinks_and_unsigned_manifest(tmp_path: Path) -> None:
    source_dir = tmp_path / "packages" / "specfact-example"
    shadow_root = tmp_path / "runtime" / ".specfact" / "modules"
    _write_module_source(source_dir)

    target_dir = link_dev_module.link_dev_module(
        "specfact-example",
        source_dir=source_dir,
        shadow_root=shadow_root,
    )

    assert target_dir == shadow_root / "specfact-example"
    assert (target_dir / "src").is_symlink()
    assert (target_dir / ".semgrep").is_symlink()
    manifest = yaml.safe_load((target_dir / "module-package.yaml").read_text(encoding="utf-8"))
    assert "integrity" not in manifest


def test_link_dev_module_requires_force_to_replace_existing_target(tmp_path: Path) -> None:
    source_dir = tmp_path / "packages" / "specfact-example"
    shadow_root = tmp_path / "runtime" / ".specfact" / "modules"
    _write_module_source(source_dir)
    target_dir = shadow_root / "specfact-example"
    target_dir.mkdir(parents=True)

    result = link_dev_module.main(
        [
            "specfact-example",
            "--source-dir",
            str(source_dir),
            "--shadow-root",
            str(shadow_root),
        ]
    )

    assert result == 1


def test_link_dev_module_wrapper_runs_as_script(tmp_path: Path) -> None:
    source_dir = tmp_path / "packages" / "specfact-example"
    shadow_root = tmp_path / "runtime" / ".specfact" / "modules"
    _write_module_source(source_dir)

    result = run_python_script(
        REPO_ROOT / "scripts" / "link_dev_module.py",
        "specfact-example",
        "--source-dir",
        str(source_dir),
        "--shadow-root",
        str(shadow_root),
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Use SPECFACT_ALLOW_UNSIGNED=1" in result.stdout
