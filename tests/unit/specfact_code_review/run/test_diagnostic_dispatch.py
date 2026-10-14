"""Diagnostic opt-in cannot silently replace ordinary customer jobs."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


def _workflow():
    root = Path(__file__).resolve().parents[4]
    return yaml.safe_load((root / ".github/workflows/capsule-customer-execution.yml").read_text())


def test_dispatch_is_explicit_and_default_customer_paths_are_preserved():
    workflow = _workflow()
    events = workflow.get("on", workflow.get(True))
    assert events["workflow_dispatch"]["inputs"]["diagnostic_mode"]["default"] is False
    assert (
        workflow["jobs"]["customer"]["if"]
        == "${{ github.event_name != 'workflow_dispatch' || inputs.diagnostic_mode != true }}"
    )
    assert workflow["jobs"]["independent-review"]["if"] == "github.event_name == 'pull_request'"
    job = workflow["jobs"]["supplemental-diagnostic"]
    assert "matrix" not in job.get("strategy", {})
    assert "inputs.diagnostic_mode == true" in job["if"]
    assert "github.event_name == 'workflow_dispatch'" in job["if"]
    assert "codex/signed-diagnostic-sidecar-18" in job["if"]
    assert workflow["permissions"] == {"contents": "read"}


def test_diagnostic_run_is_fixed_signed_and_single_attempt():
    job = _workflow()["jobs"]["supplemental-diagnostic"]
    scripts = "\n".join(step.get("run", "") for step in job["steps"])
    assert "593656f675eaf4954b609aca51aa6504367dc02e" in scripts
    assert "5b451ec066e0ea5cbd8a97ef3b59d915ae54fe5b" in scripts
    assert 'test "$GITHUB_RUN_ATTEMPT" = 1' in scripts
    assert "SUPPLEMENTARY_DIAGNOSTIC_ONLY" in scripts
    assert "timeout=600" in scripts
    assert "--scope index --enforcement changed --bug-hunt" in scripts
    assert "4e54ffb02307e1a85c166c40aba6d1bc40fbb9a8ef40bf756f8870e5bb08d1c8" in scripts
    assert "verify_signature" in scripts
    assert "actual_loaded_adapter" not in scripts or "UNAVAILABLE" in scripts


@pytest.mark.parametrize("event", ["pull_request", "release", "push", "workflow_call", "workflow_dispatch"])
@pytest.mark.parametrize("diagnostic_input", [None, False, True, "malformed", {}])
def test_event_mode_truth_table(event, diagnostic_input):
    jobs = _workflow()["jobs"]
    context = {
        "github": SimpleNamespace(event_name=event, ref="refs/heads/codex/signed-diagnostic-sidecar-18"),
        "inputs": SimpleNamespace(diagnostic_mode=diagnostic_input),
        "true": True,
    }
    outcomes = {}
    for name in ("customer", "supplemental-diagnostic"):
        expression = jobs[name]["if"].removeprefix("${{").removesuffix("}}").strip()
        expression = expression.replace("||", "or").replace("&&", "and")
        outcomes[name] = eval(expression, {"__builtins__": {}}, context)
    diagnostic_requested = event == "workflow_dispatch" and diagnostic_input is True
    assert outcomes == {"customer": not diagnostic_requested, "supplemental-diagnostic": diagnostic_requested}
