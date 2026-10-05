"""Exact npm candidate evidence never grants production admission."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(name="policy")
def fixture_policy():
    spec = importlib.util.spec_from_file_location(
        "candidate_policy", ROOT / "scripts/native_analyzer_inputs/candidate_policy.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def npm_files():
    metadata = {
        "name": "basedpyright",
        "version": "1.39.10",
        "license": "MIT",
        "bin": {"basedpyright": "index.js"},
        "optionalDependencies": {"fsevents": "~2.3.3"},
    }
    return {
        "basedpyright/package.json": (json.dumps(metadata).encode(), 0o644),
        "basedpyright/LICENSE.txt": (b"MIT terms", 0o644),
        "basedpyright/index.js": (b"never execute", 0o644),
    }


def test_npm_evidence_binds_license_metadata_and_omission(policy):
    files = npm_files()
    receipt = policy.npm_evidence(files)
    assert receipt["distribution"] == "npm:basedpyright@1.39.10"
    assert receipt["licenses"]["basedpyright/LICENSE.txt"]["sha256"] == hashlib.sha256(b"MIT terms").hexdigest()
    assert receipt["omitted_optional_dependencies"] == {"fsevents": "~2.3.3"}
    assert receipt["dependency_admitted"] is False
    assert receipt["production_eligible"] is False


@pytest.mark.parametrize(
    "defect", ["required_dependency", "missing_license", "empty_license", "wrong_version", "unexpected_optional"]
)
def test_npm_metadata_or_license_gap_rejects(policy, defect):
    files = npm_files()
    metadata = json.loads(files["basedpyright/package.json"][0])
    if defect == "required_dependency":
        metadata["dependencies"] = {"nodejs-wheel-binaries": "*"}
    elif defect == "wrong_version":
        metadata["version"] = "1.39.11"
    elif defect == "unexpected_optional":
        metadata["optionalDependencies"]["extra"] = "*"
    elif defect == "empty_license":
        files["basedpyright/LICENSE.txt"] = (b"", 0o644)
    else:
        del files["basedpyright/LICENSE.txt"]
    files["basedpyright/package.json"] = (json.dumps(metadata).encode(), 0o644)
    with pytest.raises(ValueError):
        policy.npm_evidence(files)


def test_full_released_version_map_is_recorded_without_importing_runtime(policy):
    receipt = policy.version_evidence()
    assert len(receipt["released_analyzer_versions"]) == 10
    assert receipt["released_analyzer_versions"]["semgrep-clean"] == "1.144.0"
    assert receipt["candidate_semgrep"] == "1.175.0"
    assert receipt["version_policy_compatible"] is False
    assert set(receipt["policy_drift"]) == {"semgrep-clean", "semgrep-bugs"}


def test_proposed_version_policy_is_complete_explicit_and_never_relabels_release(policy):
    evidence = policy.version_evidence()
    assert evidence["proposed_analyzer_versions"]["semgrep-clean"] == "1.175.0"
    assert evidence["proposed_analyzer_versions"]["semgrep-bugs"] == "1.175.0"
    assert evidence["released_analyzer_versions"]["semgrep-clean"] == "1.144.0"
    assert evidence["proposed_semgrep_adapter"] == "specfact-semgrep-1.175.0-legacy-result-v1"
    assert evidence["production_policy_updated"] is False
    assert evidence["parent_required_updates"]


def test_proposed_policy_is_a_frozen_reviewed_input(policy):
    evidence = policy.version_evidence()
    assert evidence["proposed_policy_sha256"] == hashlib.sha256(policy.VERSION_POLICY_INPUT.read_bytes()).hexdigest()
    assert evidence["proposal_only"] is True
    assert evidence["proposed_dependency_pins"]["semgrep"] == "1.175.0"
    assert evidence["proposed_dependency_pins"]["mcp"] == "1.29.0"
