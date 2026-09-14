"""The external corpus accepts findings, but cannot accept incomplete execution."""

import importlib.util
from pathlib import Path

import pytest


def _load():
    source = Path(__file__).parents[2] / "scripts/external_capsule_corpus.py"
    spec = importlib.util.spec_from_file_location("external_capsule_corpus", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_gate_rejects_unknown_despite_fail_status() -> None:
    module = _load()
    with pytest.raises(ValueError, match="incomplete"):
        module.assert_completed_report({"assurance_status": "FAIL", "has_unknown_required_evidence": True})


def test_external_gate_requires_actual_test_execution() -> None:
    module = _load()
    with pytest.raises(ValueError, match="test execution"):
        module.assert_completed_report({"assurance_status": "PASS", "analyzer_evidence": []})


def test_external_gate_rejects_missing_analyzer_even_with_real_tests() -> None:
    report = {
        "assurance_status": "PASS",
        "analyzer_evidence": [
            {
                "id": "targeted-pytest-coverage",
                "evidence_outcome": "PASS",
                "target_execution": {
                    "collected": ["test_app.py::test_app"],
                    "records": [{"nodeid": "test_app.py::test_app", "phase": "call", "outcome": "passed"}],
                    "coverage": {"files": {"app.py": {}}},
                },
            }
        ],
    }
    with pytest.raises(ValueError, match="roster"):
        _load().assert_completed_report(report)
