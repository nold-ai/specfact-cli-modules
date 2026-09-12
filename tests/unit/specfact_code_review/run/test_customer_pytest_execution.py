"""Customer capsule test selection must use the repository's actual pytest suite."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specfact_code_review.run import runner


def _customer_run(monkeypatch: pytest.MonkeyPatch, root: Path) -> tuple[Any, list[Any]]:
    monkeypatch.chdir(root)
    runtime = SimpleNamespace(identity="sha256:" + "a" * 64, environment_id="linux-x86_64-cp312")
    monkeypatch.setattr(runner, "_prepare_capsule_runtime", lambda: (runtime, ""))
    monkeypatch.setattr(runner, "_cleanup_capsule_runtime", lambda _runtime: None)
    requests: list[Any] = []

    def execute(request: Any) -> dict[str, object]:
        requests.append(request)
        return {"execution_state": "ran", "evidence_outcome": "PASS", "findings": []}

    monkeypatch.setattr(runner, "_execute_capsule_member", execute)
    report = runner.run_capsule_review(sorted(root.rglob("*.py")), review_mode="full", bug_hunt=True)
    return report, requests


@pytest.mark.parametrize("configured", [False, True])
def test_local_capsule_executes_complete_customer_pytest_inventory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, configured: bool
) -> None:
    (tmp_path / "calculator.py").write_text("def add(left, right):\n    return left + right\n")
    test_root = tmp_path / "checks" if configured else tmp_path
    test_root.mkdir(exist_ok=True)
    name = "verify_calculator.py" if configured else "test_calculator.py"
    (test_root / name).write_text("def test_add():\n    assert 1 + 2 == 3\n")
    if configured:
        (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = checks\npython_files = verify_*.py\n")

    report, requests = _customer_run(monkeypatch, tmp_path)

    assert report.assurance_status == "PASS"
    assert all(row.get("environment_id") == "linux-x86_64-cp312" for row in report.analyzer_evidence or [])
    request = next(item for item in requests if item.member == "targeted-pytest-coverage")
    assert request.complete_pytest_inventory is True
    expected = f"checks/{name}::test_add" if configured else f"{name}::test_add"
    assert request.adapter_argv[-2:] == ("--", expected)
    assert "--cov-config" in request.adapter_argv
    assert request.config_roots
    assert all(not root.exists() for root in request.config_roots)


@pytest.mark.parametrize(
    ("extra", "diagnostic"),
    [
        ("", "local_pytest_inventory_empty"),
        (
            "import pytest\n@pytest.fixture(autouse=True)\ndef configure():\n    yield\n",
            "pytest_plugin_capability_unsupported",
        ),
    ],
)
def test_local_capsule_cannot_claim_tests_pass_without_a_supported_inventory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra: str, diagnostic: str
) -> None:
    (tmp_path / "calculator.py").write_text("VALUE = 1\n")
    if extra:
        (tmp_path / "conftest.py").write_text(extra)
        (tmp_path / "test_calculator.py").write_text("def test_value():\n    assert True\n")

    report, requests = _customer_run(monkeypatch, tmp_path)

    assert report.assurance_status == "UNKNOWN"
    assert report.ci_exit_code == 1
    assert all(row.get("environment_id") == "linux-x86_64-cp312" for row in report.analyzer_evidence or [])
    assert requests == []
    assert any(diagnostic in str(row.get("diagnostic")) for row in report.analyzer_evidence or [])


def test_capsule_pytest_child_preserves_sealed_imports_before_loading_pytest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import subprocess

    monkeypatch.setattr(runner, "__file__", "/opt/specfact/builtin/specfact_code_review/run/runner.py")
    monkeypatch.setenv("PYTHONPATH", "/untrusted/startup")
    monkeypatch.chdir(tmp_path)
    recorded: dict[str, Any] = {}

    def execute(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        recorded.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", execute)
    _result, coverage, observer, junit = runner._run_pytest_inventory_with_coverage(("test_calc.py::test_add",))
    for path in (coverage, observer, junit):
        path.unlink(missing_ok=True)

    command = recorded["command"]
    assert command[1:4] == ["-I", "-S", "-c"]
    script = command[4]
    assert script.index("/opt/specfact/analyzers") < script.index("import json, pathlib, sys, pytest")
    assert "/opt/specfact/builtin" in script
    assert "/opt/specfact/project-runtime/site-packages" in script
    assert "PYTHONPATH" not in recorded["env"]
    assert recorded["env"]["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"


def test_capsule_acquisition_failure_retains_abi_without_changing_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_capsule_environment_id", lambda: "linux-x86_64-cp313")
    report = runner._unknown_capsule_report(
        "oci_acquisition_failed:verified cache entry is missing",
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "full"},
    )

    assert report.assurance_status == "UNKNOWN"
    assert all(row.get("environment_id") == "linux-x86_64-cp313" for row in report.analyzer_evidence or [])
    assert all(
        row.get("diagnostic") == "oci_acquisition_failed:verified cache entry is missing"
        for row in report.analyzer_evidence or []
    )
