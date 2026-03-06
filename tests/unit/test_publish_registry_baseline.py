from __future__ import annotations

from publish_bundle_selection import determine_registry_baseline_ref


def test_determine_registry_baseline_ref_uses_dev_for_dev_pushes() -> None:
    assert determine_registry_baseline_ref(current_branch="dev", default_branch="main") == "dev"


def test_determine_registry_baseline_ref_uses_current_branch_when_it_matches_default() -> None:
    assert determine_registry_baseline_ref(current_branch="main", default_branch="main") == "main"


def test_determine_registry_baseline_ref_falls_back_to_default_for_other_branches() -> None:
    assert determine_registry_baseline_ref(current_branch="bugfix/test", default_branch="main") == "main"
