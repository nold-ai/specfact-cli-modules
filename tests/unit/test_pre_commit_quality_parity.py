from __future__ import annotations

import itertools
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]

_EXPECTED_HOOK_ORDER = [
    "verify-module-signatures",
    "modules-block1-format",
    "modules-block1-yaml",
    "modules-block1-bundle",
    "modules-block1-lint",
    "modules-block2",
]

_REQUIRED_HOOK_IDS = frozenset(_EXPECTED_HOOK_ORDER)
_FORBIDDEN_HOOK_IDS = frozenset({"modules-quality-checks", "specfact-code-review-gate"})

_REQUIRED_SCRIPT_FRAGMENTS = (
    "hatch run format",
    "hatch run yaml-lint",
    "hatch run check-bundle-imports",
    "hatch run lint",
    "hatch run contract-test",
    "pre_commit_code_review.py",
    "run_code_review_gate",
    "contract-test-status",
    "print_block1_overview",
    "Block 1 — stage 1/4",
    "Block 1 — stage 4/4",
    "block1-format",
    "block1-yaml",
    "run_block2",
)


def _load_pre_commit_config() -> dict[str, object]:
    loaded = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _collect_ordered_hook_ids(repos: object) -> tuple[set[str], list[str]]:
    if not isinstance(repos, list):
        return set(), []

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
    return hook_ids, ordered_hook_ids


def _assert_pairwise_hook_order(ordered_hook_ids: list[str], expected_order: list[str]) -> None:
    index_map = {hook_id: index for index, hook_id in enumerate(ordered_hook_ids)}
    for earlier, later in itertools.pairwise(expected_order):
        assert index_map[earlier] < index_map[later]


def test_pre_commit_config_has_signature_and_modules_quality_hooks() -> None:
    config = _load_pre_commit_config()
    assert config.get("fail_fast") is True

    hook_ids, ordered_hook_ids = _collect_ordered_hook_ids(config.get("repos"))
    assert _REQUIRED_HOOK_IDS.issubset(hook_ids)
    assert hook_ids.isdisjoint(_FORBIDDEN_HOOK_IDS)
    _assert_pairwise_hook_order(ordered_hook_ids, _EXPECTED_HOOK_ORDER)


def test_modules_pre_commit_script_enforces_required_quality_commands() -> None:
    script_path = REPO_ROOT / "scripts" / "pre-commit-quality-checks.sh"
    assert script_path.exists()

    script_text = script_path.read_text(encoding="utf-8")
    for fragment in _REQUIRED_SCRIPT_FRAGMENTS:
        assert fragment in script_text
