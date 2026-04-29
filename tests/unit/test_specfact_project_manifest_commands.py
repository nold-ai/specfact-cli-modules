from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_specfact_project_manifest_includes_plan_command() -> None:
    manifest_path = REPO_ROOT / "packages" / "specfact-project" / "module-package.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    commands = manifest.get("commands", [])
    assert "project" in commands
    assert "plan" in commands
