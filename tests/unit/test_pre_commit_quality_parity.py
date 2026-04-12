from __future__ import annotations

import itertools
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pre_commit_config() -> dict[str, object]:
    loaded = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def test_pre_commit_config_has_signature_and_modules_quality_hooks() -> None:
    config = _load_pre_commit_config()
    assert config.get("fail_fast") is True
    repos = config.get("repos")
    assert isinstance(repos, list)

    hook_ids: set[str] = set()
    ordered_hook_ids: list[str] = []
    seen: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks", []):
            if not isinstance(hook, dict):
                continue
            hook_id = hook.get("id")
            if not isinstance(hook_id, str):
                continue
            hook_ids.add(hook_id)
            if hook_id not in seen:
                ordered_hook_ids.append(hook_id)
                seen.add(hook_id)

    assert "verify-module-signatures" in hook_ids
    assert "modules-quality-checks" in hook_ids
    assert "specfact-code-review-gate" not in hook_ids

    expected_order = [
        "verify-module-signatures",
        "modules-quality-checks",
    ]
    index_map = {hook_id: index for index, hook_id in enumerate(ordered_hook_ids)}
    for earlier, later in itertools.pairwise(expected_order):
        assert index_map[earlier] < index_map[later]


def test_modules_pre_commit_script_enforces_required_quality_commands() -> None:
    script_path = REPO_ROOT / "scripts" / "pre-commit-quality-checks.sh"
    assert script_path.exists()

    script_text = script_path.read_text(encoding="utf-8")
    assert "hatch run format" in script_text
    assert "hatch run yaml-lint" in script_text
    assert "hatch run check-bundle-imports" in script_text
    assert "hatch run lint" in script_text
    assert "hatch run contract-test" in script_text
    assert "pre_commit_code_review.py" in script_text
    assert "run_code_review_gate" in script_text
    assert "contract-test-status" in script_text
