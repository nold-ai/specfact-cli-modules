"""Contract tests for the requirements-evidence GitHub Actions job."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_ROOT = "artifacts/requirements-evidence"
JSON_ARTIFACT = f"{ARTIFACTS_ROOT}/requirements-evidence.json"
SUMMARY_ARTIFACT = f"{ARTIFACTS_ROOT}/requirements-evidence.md"


def _workflow_steps() -> dict[str, dict[str, Any]]:
    workflow = cast(
        dict[str, Any],
        yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "requirements-evidence.yml").read_text(encoding="utf-8")),
    )
    steps = cast(list[dict[str, Any]], workflow["jobs"]["requirements-evidence"]["steps"])
    return {step["name"]: step for step in steps if "name" in step}


def test_requirements_evidence_workflow_runs_module_adapter_with_paired_core() -> None:
    steps = _workflow_steps()
    setup = steps["Install Hatch and paired core CLI"]
    gate = steps["Run requirements evidence gate"]

    assert setup["continue-on-error"] is True
    assert "hatch run pip install -e ./specfact-cli" in setup["run"]
    assert "hatch run pip install -e ./packages/specfact-requirements" not in setup["run"]
    assert gate["if"] == "steps.setup.outcome == 'success'"
    assert gate["continue-on-error"] is True
    assert gate["env"]["PYTHONPATH"] == "packages/specfact-project/src:packages/specfact-requirements/src"
    assert "scripts/requirements_evidence_gate.py" in gate["run"]
    assert f"--output {JSON_ARTIFACT}" in gate["run"]
    assert f"--summary {SUMMARY_ARTIFACT}" in gate["run"]


def _assert_fallback_step(fallback: dict[str, Any]) -> None:
    run = fallback["run"]
    assert fallback["if"] == "always()"
    assert fallback["env"] == {"SETUP_OUTCOME": "${{ steps.setup.outcome }}"}
    assert f"[ -f {JSON_ARTIFACT} ]" in run
    assert f"[ -f {SUMMARY_ARTIFACT} ]" in run
    assert "json.load" in run
    assert "exit 0" in run
    assert "scripts/requirements_evidence_fallback.py" in run
    assert f"--output {JSON_ARTIFACT}" in run
    assert f"--summary {SUMMARY_ARTIFACT}" in run
    assert '--stage "$EVIDENCE_STAGE"' in run


def _assert_publication_and_enforcement_steps(
    summary: dict[str, Any], upload: dict[str, Any], enforce: dict[str, Any]
) -> None:
    assert summary["if"] == "always()"
    assert summary["run"] == f'cat {SUMMARY_ARTIFACT} >> "$GITHUB_STEP_SUMMARY"'
    assert upload["if"] == "always()"
    assert upload["with"]["path"] == JSON_ARTIFACT
    assert enforce["if"] == "steps.setup.outcome == 'failure' || steps.run-evidence.outcome == 'failure'"


def test_requirements_evidence_workflow_recovers_only_when_the_artifact_pair_is_incomplete() -> None:
    steps = _workflow_steps()

    _assert_fallback_step(steps["Retain setup failure evidence"])
    _assert_publication_and_enforcement_steps(
        steps["Publish requirements evidence summary"],
        steps["Upload requirements evidence artifact"],
        steps["Enforce requirements evidence verdict"],
    )
