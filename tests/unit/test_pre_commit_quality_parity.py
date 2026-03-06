from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pre_commit_config() -> dict[str, object]:
    loaded = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def test_pre_commit_config_has_signature_and_modules_quality_hooks() -> None:
    config = _load_pre_commit_config()
    repos = config.get("repos")
    assert isinstance(repos, list)

    hook_ids = {
        hook.get("id")
        for repo in repos
        if isinstance(repo, dict)
        for hook in repo.get("hooks", [])
        if isinstance(hook, dict)
    }

    assert "verify-module-signatures" in hook_ids
    assert "modules-quality-checks" in hook_ids


def test_modules_pre_commit_script_enforces_required_quality_commands() -> None:
    script_path = REPO_ROOT / "scripts" / "pre-commit-quality-checks.sh"
    assert script_path.exists()

    script_text = script_path.read_text(encoding="utf-8")
    assert "hatch run format" in script_text
    assert "hatch run yaml-lint" in script_text
    assert "hatch run check-bundle-imports" in script_text
    assert "hatch run contract-test" in script_text
