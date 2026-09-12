"""The customer gate must reject incomplete analyzer evidence."""

import importlib.util
from pathlib import Path

import pytest


def _gate():
    path = Path(__file__).parents[2] / "scripts/capsule_customer_gate.py"
    spec = importlib.util.spec_from_file_location("capsule_customer_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("state,outcome", [("error", "UNKNOWN"), ("not_applicable", "NOT_APPLICABLE")])
def test_customer_gate_rejects_missing_analyzer_execution(state, outcome):
    gate = _gate()
    report = {
        "analyzer_evidence": [
            {"id": member, "execution_state": state, "evidence_outcome": outcome} for member in gate.ANALYZERS
        ]
    }
    with pytest.raises(ValueError, match="execution"):
        gate.validate_report(report, returncode=0, expected="clean")


def test_customer_gate_rejects_empty_evidence():
    with pytest.raises(ValueError, match="inventory"):
        _gate().validate_report({"analyzer_evidence": []}, returncode=0, expected="clean")


def test_customer_gate_requires_detected_defect_and_failure_exit():
    gate = _gate()
    report = {
        "analyzer_evidence": [
            {"id": member, "execution_state": "ran", "evidence_outcome": "PASS"} for member in gate.ANALYZERS
        ],
        "assurance_status": "PASS",
        "has_unknown_required_evidence": False,
        "findings": [],
    }
    with pytest.raises(ValueError, match="defect"):
        gate.validate_report(report, returncode=0, expected="defective")


@pytest.mark.parametrize(
    "status,exit_code", [(None, 0), ("PASS", 1), ("FAIL", 0), ("UNKNOWN", 1), ("NOT_APPLICABLE", 0)]
)
def test_customer_gate_rejects_inconsistent_repository_result(status, exit_code):
    gate = _gate()
    report = {
        "analyzer_evidence": [
            {"id": member, "execution_state": "ran", "evidence_outcome": "PASS"} for member in gate.ANALYZERS
        ],
        "assurance_status": status,
        "has_unknown_required_evidence": False,
    }
    with pytest.raises(ValueError, match="repository"):
        gate.validate_report(report, returncode=exit_code, expected="repository")
