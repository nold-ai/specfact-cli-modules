"""Native verification must follow actual build, acceptance and pytest inputs."""

import re
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]


def _schedules_native(path: str) -> bool:
    workflow = yaml.load((ROOT / ".github/workflows/native-capsule-release.yml").read_text(), Loader=yaml.BaseLoader)
    # The current filters use literal paths, segment stars and recursive stars.
    patterns = (re.escape(pattern) for pattern in workflow["on"]["pull_request"]["paths"])
    return any(re.fullmatch(pattern.replace(r"\*\*", ".*").replace(r"\*", "[^/]*"), path) for pattern in patterns)


@pytest.mark.parametrize(
    "path",
    [
        "scripts/native_release/prepare-ci.sh",
        "scripts/native_release/build.py",
        "scripts/native_analyzer_inputs/darwin-arm64-cp312.txt",
        "scripts/native_node_package.py",
        "scripts/native_z3_wheel.py",
        "scripts/native_runtime_inventory.py",
        "scripts/native_semgrep_parity.py",
        "scripts/assemble_macos_native_capsule.py",
        "scripts/build_macos_native_capsule.py",
        "scripts/build_macos_managed_uv.py",
        "scripts/build_macos_managed_git.py",
        "scripts/check_macos_boundary_ci_receipts.py",
        "scripts/external_capsule_corpus.py",
        "scripts/capsule_customer_gate.py",
        "scripts/macos_managed_boundary/python_analyzers.py",
        "scripts/macos_managed_boundary/control_mach.inc",
        "tests/fixtures/portable-runtime/corpus.json",
        "tests/native/proof_python_candidate_matrix.py",
        "tests/native/proof_macos_native_broker_wait.py",
        "packages/specfact-code-review/native/macos-arm64/build.sh",
        "pyproject.toml",
        "tests/conftest.py",
        "src/specfact_cli_modules/dev_bootstrap.py",
        "src/specfact_cli_modules/__init__.py",
        "tests/unit/native_release/test_workflow_inputs.py",
        ".github/workflows/native-capsule-release.yml",
    ],
)
def test_native_release_input_schedules_the_existing_matrix(path: str):
    assert (ROOT / path).is_file(), "The regression must exercise an actual repository input"
    assert _schedules_native(path), f"Native verification is missing input {path}"


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "packages/specfact-backlog/module-package.yaml",
        "tests/unit/test_publish_bundle_selection.py",
    ],
)
def test_unrelated_change_remains_filtered(path: str):
    assert (ROOT / path).is_file()
    assert not _schedules_native(path)


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("scripts/native_node_package.py", "scripts/*native*.py", True),
        ("scripts/native_release/build.py", "scripts/*native*.py", False),
        ("scripts/native_release/build.py", "scripts/native_release/**", True),
        ("scripts/native_release/nested/build.py", "scripts/native_release/**", True),
        ("scripts/native_release_other/build.py", "scripts/native_release/**", False),
        ("other/scripts/native_node_package.py", "scripts/*native*.py", False),
    ],
)
def test_filter_globs_respect_directory_boundaries(path, pattern, expected, monkeypatch):
    # These filters use literals and stars; a single star must not consume a slash.
    monkeypatch.setattr(yaml, "load", lambda *_args, **_kwargs: {"on": {"pull_request": {"paths": [pattern]}}})
    assert _schedules_native(path) is expected
