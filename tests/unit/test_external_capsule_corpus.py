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


def test_reconstruction_materializes_real_source_without_mutating_template(tmp_path: Path) -> None:
    module = _load()
    fixture = tmp_path / "template"
    fixture.mkdir()
    template = fixture / "test_native.py.in"
    template.write_text("def test_native():\n    assert True\n")
    destination = tmp_path / "checkout"
    module.materialize_reconstruction(fixture, destination)
    assert (destination / "test_native.py").read_text() == template.read_text()
    assert not (destination / "test_native.py.in").exists()
    assert template.is_file()


def test_corpus_attempts_remaining_repositories_after_a_failure(tmp_path: Path, monkeypatch) -> None:
    import json

    module = _load()
    manifest = tmp_path / "corpus.json"
    manifest.write_text(json.dumps({"python": ["3.12"], "repositories": [{"name": "first"}, {"name": "second"}]}))
    monkeypatch.setattr(module, "MANIFEST", manifest)
    monkeypatch.setattr(module.sys, "argv", ["corpus", "--workspace", str(tmp_path / "work")])
    monkeypatch.setattr(module.sys, "version_info", type("Version", (), {"major": 3, "minor": 12})())
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(module.os, "getuid", lambda: 1000)
    attempted = []

    def run_entry(entry, workspace):
        attempted.append(entry["name"])
        if entry["name"] == "first":
            raise ValueError("controlled incomplete analysis")

    monkeypatch.setattr(module, "run_entry", run_entry)
    assert module.main() == 1
    assert attempted == ["first", "second"]


def test_host_baseline_rejects_startup_failure_without_test_execution(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"host.*execution"):
        _load().assert_host_execution(tmp_path / "missing.xml")


def test_host_baseline_rejects_only_setup_errors(tmp_path: Path) -> None:
    result = tmp_path / "tests.xml"
    result.write_text(
        '<testsuites><testsuite><testcase name="test_app"><error message="setup failed"/></testcase></testsuite></testsuites>'
    )
    with pytest.raises(ValueError, match=r"host.*execution"):
        _load().assert_host_execution(result)
