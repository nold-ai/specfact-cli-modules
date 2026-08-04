"""Regression tests for generated command contract validation."""

from pathlib import Path

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_code_review_mount_targets_the_review_subapp() -> None:
    script = load_module_from_path("check_command_contract", REPO_ROOT / "scripts" / "check-command-contract.py")

    assert (
        "specfact_code_review.review.commands",
        "review_app",
        ("specfact", "code", "review"),
    ) in script.APP_MOUNTS
    assert ("specfact_spec.sdd.commands", "app", ("specfact", "spec", "sdd")) in script.APP_MOUNTS
