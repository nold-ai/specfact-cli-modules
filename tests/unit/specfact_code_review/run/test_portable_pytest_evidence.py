"""Portable evidence must enforce the same non-pass and source coverage gates."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import portable_worker


def _record(nodeid, outcome="passed", phase="call", wasxfail="") -> dict[str, object]:
    return {"nodeid": nodeid, "phase": phase, "outcome": outcome, "wasxfail": wasxfail}


def _observation(*records, coverage=None, threshold=None):
    return {
        "exit_code": 0,
        "collected": list(dict.fromkeys(record["nodeid"] for record in records)),
        "records": list(records),
        "coverage": {"files": coverage or {"src/app.py": {"summary": {"percent_covered": 100.0}}}},
        "coverage_threshold": threshold,
        "test_roots": ["tests"],
    }


def _run(tmp_path, monkeypatch, observation, names=("src/app.py", "tests/test_app.py")):
    monkeypatch.chdir(tmp_path)
    files = [tmp_path / name for name in names]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("VALUE = 1\n")
    output = tmp_path / "observation.json"
    monkeypatch.setattr(
        portable_worker,
        "Path",
        lambda value: output if value == "/opt/specfact/tmp/pytest-observation.json" else Path(value),
    )
    monkeypatch.setattr(portable_worker, "target_command", lambda *args: ["observed-worker"])

    def execute(*_args, **_kwargs):
        output.write_text(json.dumps(observation))
        return SimpleNamespace(returncode=observation["exit_code"])

    monkeypatch.setattr(portable_worker.subprocess, "run", execute)
    return portable_worker.run_portable_pytest(files, ("portable-pytest-v2", "{}"))


@pytest.mark.parametrize(
    "outcome,phase,xfail",
    [
        ("skipped", "setup", ""),
        ("skipped", "call", ""),
        ("skipped", "call", "known bug"),
        ("passed", "call", "known bug"),
        ("failed", "teardown", ""),
    ],
)
def test_mixed_non_pass_outcomes_cannot_pass(tmp_path, monkeypatch, outcome, phase, xfail):
    observation = _observation(
        _record("tests/test_app.py::test_pass"),
        _record("tests/test_app.py::test_other", outcome, phase, xfail),
    )
    if outcome == "failed":
        observation["exit_code"] = 1
    findings = _run(tmp_path, monkeypatch, observation)
    assert any(item.rule == "TEST_OUTCOME_NOT_PASS" and item.severity == "error" for item in findings)
    if outcome != "failed":
        assert not any(item.rule == "tool_error" for item in findings)


@pytest.mark.parametrize(
    "coverage,threshold,expected",
    [
        ({"src/other.py": {"summary": {"percent_covered": 100}}}, None, "tool_error"),
        ({"src/app.py": {"summary": {"percent_covered": 20}}}, None, "TEST_COVERAGE_LOW"),
        (
            {"src/app.py": {"summary": {"percent_covered": 85}}, "src/other.py": {"summary": {"percent_covered": 100}}},
            90,
            "TEST_COVERAGE_LOW",
        ),
        ({"src/app.py": {"summary": {"percent_covered": 79}}}, 20, "TEST_COVERAGE_LOW"),
    ],
)
def test_each_reviewed_source_requires_sufficient_coverage(tmp_path, monkeypatch, coverage, threshold, expected):
    observation = _observation(_record("tests/test_app.py::test_pass"), coverage=coverage, threshold=threshold)
    findings = _run(tmp_path, monkeypatch, observation)
    assert any(item.rule == expected and item.severity == "error" for item in findings)


def test_healthy_coverage_excludes_test_support_and_type_stubs(tmp_path, monkeypatch):
    observation = _observation(_record("tests/test_app.py::test_pass"))
    assert not _run(
        tmp_path,
        monkeypatch,
        observation,
        (
            "src/app.py",
            "tests/test_app.py",
            "tests/support.py",
            "conftest.py",
            "src/app.pyi",
        ),
    )


def test_actual_custom_test_module_is_not_a_production_coverage_target(tmp_path, monkeypatch):
    observation = _observation(_record("checks/check_app.py::test_pass"))
    observation["test_roots"] = []
    assert not _run(tmp_path, monkeypatch, observation, ("src/app.py", "checks/check_app.py"))


def test_deselected_test_module_does_not_require_production_coverage(tmp_path, monkeypatch):
    observation = _observation(_record("checks/check_app.py::test_pass"))
    observation["deselected"] = ["checks/check_other.py::test_other"]
    observation["test_roots"] = []
    assert not _run(tmp_path, monkeypatch, observation, ("src/app.py", "checks/check_other.py"))


def test_project_root_as_test_root_cannot_exempt_production_sources(tmp_path, monkeypatch):
    observation = _observation(
        _record("tests/test_app.py::test_pass"),
        coverage={"src/other.py": {"summary": {"percent_covered": 100}}},
    )
    observation["test_roots"] = ["."]
    assert any(item.rule == "tool_error" for item in _run(tmp_path, monkeypatch, observation))


def test_customer_nonempty_initializer_cannot_use_specfact_omit_exemption(tmp_path, monkeypatch):
    observation = _observation(_record("tests/test_app.py::test_pass"))
    assert any(
        item.rule == "tool_error"
        for item in _run(
            tmp_path,
            monkeypatch,
            observation,
            ("src/customer/__init__.py", "tests/test_app.py"),
        )
    )


def test_real_failure_remains_visible_alongside_missing_coverage(tmp_path, monkeypatch):
    observation = _observation(
        _record("tests/test_app.py::test_pass", "failed"),
        coverage={"src/other.py": {"summary": {"percent_covered": 100}}},
    )
    observation["exit_code"] = 1
    findings = _run(tmp_path, monkeypatch, observation)
    assert {"TEST_OUTCOME_NOT_PASS", "tool_error"} <= {item.rule for item in findings}


@pytest.mark.parametrize("threshold", ["bad", -1, 101, float("nan"), float("inf"), True])
def test_invalid_effective_threshold_cannot_pass(tmp_path, monkeypatch, threshold):
    observation = _observation(_record("tests/test_app.py::test_pass"), threshold=threshold)
    assert any(item.rule == "tool_error" for item in _run(tmp_path, monkeypatch, observation))


def test_empty_reason_xpass_cannot_pass(tmp_path, monkeypatch):
    record = _record("tests/test_app.py::test_xpass")
    record["has_xfail"] = True
    observation = _observation(record)
    findings = _run(tmp_path, monkeypatch, observation)
    assert any(item.rule == "TEST_OUTCOME_NOT_PASS" for item in findings)


def test_nested_pytest_root_resolves_custom_test_modules(tmp_path, monkeypatch):
    observation = _observation(_record("check_app.py::test_pass"))
    observation["pytest_root"] = "checks"
    observation["test_roots"] = []
    assert not _run(tmp_path, monkeypatch, observation, ("src/app.py", "checks/check_app.py"))


def test_package_discovery_root_does_not_exempt_production_source(tmp_path, monkeypatch):
    observation = _observation(
        _record("package/tests/test_app.py::test_pass"),
        coverage={"package/app.py": {"summary": {"percent_covered": 0}}},
    )
    observation["test_roots"] = ["package"]
    findings = _run(tmp_path, monkeypatch, observation, ("package/app.py", "package/tests/test_app.py"))
    assert any(item.rule == "TEST_COVERAGE_LOW" for item in findings)


def test_external_pytest_root_is_incomplete(tmp_path, monkeypatch):
    observation = _observation(_record("tests/test_app.py::test_pass"))
    observation["pytest_root"] = str(tmp_path.parent)
    findings = _run(tmp_path, monkeypatch, observation)
    assert any(item.rule == "tool_error" and "pytest_root" in item.message for item in findings)


@pytest.mark.parametrize("pytest_root", ["checks", "absolute"])
def test_nested_nonpass_finding_uses_snapshot_relative_path(tmp_path, monkeypatch, pytest_root):
    nodeid = "check_app.py::test_failure"
    observation = _observation(_record(nodeid, "failed"))
    observation["exit_code"] = 1
    observation["pytest_root"] = str(tmp_path / "checks") if pytest_root == "absolute" else pytest_root
    findings = _run(tmp_path, monkeypatch, observation, ("src/app.py", "checks/check_app.py"))
    failed = [finding for finding in findings if finding.rule == "TEST_OUTCOME_NOT_PASS"]
    assert len(failed) == 1
    assert failed[0].file == "checks/check_app.py"
    assert nodeid in failed[0].message
    assert observation["records"][0]["nodeid"] == nodeid
    assert observation["collected"] == [nodeid]


@pytest.mark.parametrize(
    "pytest_root,nodeid", [("../outside", "check_app.py::test_failure"), (".", "../check_app.py::test_failure")]
)
def test_escaping_outcome_path_is_incomplete_without_false_attribution(tmp_path, monkeypatch, pytest_root, nodeid):
    observation = _observation(_record(nodeid, "failed"))
    observation["exit_code"] = 1
    observation["pytest_root"] = pytest_root
    findings = _run(tmp_path, monkeypatch, observation)
    assert any(finding.rule == "tool_error" for finding in findings)
    assert not any(finding.rule == "TEST_OUTCOME_NOT_PASS" for finding in findings)
