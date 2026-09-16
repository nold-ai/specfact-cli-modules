"""Exercise target coverage hooks in process using actual Coverage measurement and export."""

import importlib.util
import io
import json
import runpy
from pathlib import Path
from types import ModuleType, SimpleNamespace

import coverage
import pytest

from specfact_code_review.run import target_coverage


@pytest.fixture(name="coverage_boundary")
def fixture_coverage_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide a fresh public-hook instance and real measured source for each boundary."""
    spec = importlib.util.spec_from_file_location("boundary_target_coverage", target_coverage.__file__)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    source = tmp_path / "source"
    source.mkdir()
    app = source / "app.py"
    app.write_text("def covered():\n    return 1\ndef untouched():\n    return 2\n")
    configuration = source / ".coveragerc"
    configuration.write_text("[run]\nsource = .\n[report]\nfail_under = 80\nprecision = 2\n")
    output = tmp_path / "private.json"
    monkeypatch.chdir(source)
    monkeypatch.setenv("SPECFACT_REVIEW_COVERAGE_REQUEST", "")
    monkeypatch.setenv("COVERAGE_FILE", str(tmp_path / ".coverage"))
    helper.configure(snapshot=source, output=output, directories=[])
    options = SimpleNamespace(
        cov_config=str(configuration),
        cov_source=[True],
        cov_report={},
        cov_fail_under=None,
        cov_precision=None,
        no_cov=False,
        no_cov_on_fail=False,
        collectonly=False,
        cov_branch=False,
        cov_append=False,
        cov_context=None,
    )
    return SimpleNamespace(
        helper=helper,
        source=source,
        app=app,
        configuration=configuration,
        output=output,
        options=options,
        manager=pytest.PytestPluginManager(),
    )


def _measure(boundary: SimpleNamespace, *, execute: bool = True) -> coverage.Coverage:
    """Record real executed Python statements under the disposable project's native config."""
    measured = coverage.Coverage(config_file=str(boundary.configuration), data_file=None)
    measured.start()
    try:
        if execute:
            namespace = runpy.run_path(str(boundary.app))
            assert namespace["covered"]() == 1
    finally:
        measured.stop()
    return measured


def _native_plugin(boundary: SimpleNamespace, *, execute: bool = True) -> SimpleNamespace:
    """Model pytest-cov's completed lifecycle with real Coverage data at its public boundary."""
    measured = _measure(boundary, execute=execute)
    total = measured.report(file=io.StringIO()) if execute else None
    options = SimpleNamespace(collectonly=False, no_cov_on_fail=False, cov_fail_under=80, cov_precision=2)
    plugin = SimpleNamespace(
        cov_controller=SimpleNamespace(cov=measured, topdir=str(boundary.source), failed_workers=[]),
        cov_total=total,
        failed=False,
        options=options,
        _should_report=lambda: True,
    )
    boundary.manager.register(plugin, "_cov")
    return plugin


def _start(boundary: SimpleNamespace) -> None:
    """Invoke the ordinary early pytest hook with the actual native plugin manager."""
    config = SimpleNamespace(known_args_namespace=boundary.options, pluginmanager=boundary.manager)
    boundary.helper.pytest_load_initial_conftests(config, None, [])


def _finish(boundary: SimpleNamespace, *, exit_code: int = 0, worker: bool = False) -> None:
    """Publish the upstream session outcome through the exported observation hook."""
    config = SimpleNamespace(workerinput={}) if worker else SimpleNamespace()
    boundary.helper.pytest_sessionfinish(SimpleNamespace(config=config, exitstatus=exit_code), exit_code)


def test_native_hooks_export_real_private_coverage_and_restore_cwd(coverage_boundary, tmp_path, monkeypatch) -> None:
    """Native policy and actual JSON lines survive export after customer cwd changes."""
    boundary = coverage_boundary
    plugin = _native_plugin(boundary)
    _start(boundary)
    assert boundary.helper.active_plugin() is plugin
    _finish(boundary, exit_code=1)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    receipt = boundary.helper.evidence()
    assert Path.cwd() == elsewhere
    assert receipt["coverage"] == json.loads(boundary.output.read_text())
    assert receipt["coverage"]["files"]["app.py"]["executed_lines"] == [1, 2, 3]
    assert receipt["coverage_policy"]["native_threshold_failed"] is True
    assert receipt["coverage_policy"]["measured_total"] == 75
    assert receipt["coverage_configuration"]["effective"]["threshold"] == 80
    assert receipt["coverage_diagnostic"] == ""


@pytest.mark.parametrize("configured", [True, False])
def test_reviewer_hooks_measure_real_code_without_native_aggregate_failure(coverage_boundary, configured) -> None:
    """The real owned pytest-cov collector exports evidence without activating native fail-under."""
    boundary = coverage_boundary
    if not configured:
        boundary.configuration.write_text("[report]\nfail_under = 80\nprecision = 2\n")
    _start(boundary)
    plugin = boundary.helper.active_plugin()
    assert plugin is not None
    try:
        namespace = runpy.run_path(str(boundary.app))
        assert namespace["covered"]() == 1
    finally:
        plugin.cov_controller.finish()
    _finish(boundary)
    receipt = boundary.helper.evidence()
    assert receipt["coverage_policy"] == {
        "mode": "reviewer",
        "threshold": 80,
        "precision": 2,
        "measured_total": 75.0,
        "native_threshold_failed": False,
    }
    assert receipt["coverage"]["files"]["app.py"]["missing_lines"] == [4]


@pytest.mark.filterwarnings("ignore:No data was collected:coverage.exceptions.CoverageWarning")
def test_empty_collection_retains_precise_coverage_diagnostic(coverage_boundary) -> None:
    """A finished but empty native collector cannot fabricate coverage evidence."""
    boundary = coverage_boundary
    boundary.configuration.write_text("[run]\ninclude = absent-file.py\n")
    _native_plugin(boundary, execute=False)
    _start(boundary)
    _finish(boundary)
    receipt = boundary.helper.evidence()
    assert receipt["coverage"] == {}
    assert "No data to report" in receipt["coverage_diagnostic"]


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("worker", "project_pytest_coverage_controller_observation_missing"),
        ("no-session", "project_pytest_coverage_controller_observation_missing"),
        ("failed-worker", "project_pytest_coverage_worker_missing"),
        ("suppressed", "project_pytest_coverage_suppressed:--no-cov-on-fail"),
    ],
)
def test_upstream_incomplete_lifecycle_cannot_export_success(coverage_boundary, failure, expected) -> None:
    """Actual measured data cannot conceal missing workers or native report suppression."""
    boundary = coverage_boundary
    plugin = _native_plugin(boundary)
    plugin.cov_controller.failed_workers = ["gw0"] if failure == "failed-worker" else []
    plugin.failed = failure == "suppressed"
    plugin.options.no_cov_on_fail = failure == "suppressed"
    _start(boundary)
    if failure != "no-session":
        _finish(boundary, worker=failure == "worker")
    receipt = boundary.helper.evidence()
    assert receipt["coverage"] == {}
    assert expected in receipt["coverage_diagnostic"]
    assert not boundary.output.exists()


@pytest.mark.parametrize(
    ("field", "value"), [("snapshot", "relative"), ("output", None), ("directories", ["relative"]), ("directories", {})]
)
def test_invalid_public_request_is_an_actionable_early_diagnostic(coverage_boundary, monkeypatch, field, value) -> None:
    """Malformed request inputs fail before a collector can start or write an artifact."""
    boundary = coverage_boundary
    request = {"snapshot": str(boundary.source), "output": str(boundary.output), "directories": []}
    request[field] = value
    monkeypatch.setenv("SPECFACT_REVIEW_COVERAGE_REQUEST", json.dumps(request))
    _start(boundary)
    receipt = boundary.helper.evidence()
    assert "project_pytest_coverage_request_invalid" in receipt["coverage_diagnostic"]
    assert boundary.helper.active_plugin() is None
    assert not boundary.output.exists()


def test_invalid_native_coverage_config_is_named_before_measurement(coverage_boundary) -> None:
    """Coverage's real parser error survives the early-hook adapter."""
    boundary = coverage_boundary
    boundary.configuration.write_text("[report]\nprecision = invalid-number\n")
    _start(boundary)
    receipt = boundary.helper.evidence()
    assert "ConfigError" in receipt["coverage_diagnostic"]
    assert "invalid-number" in receipt["coverage_diagnostic"]
    assert str(boundary.configuration) in receipt["coverage_diagnostic"]
    assert boundary.helper.active_plugin() is None


def test_unsupported_pytest_cov_contract_is_named_before_measurement(coverage_boundary, monkeypatch) -> None:
    """An unsupported upstream lifecycle version cannot silently use a guessed collector."""
    boundary = coverage_boundary
    monkeypatch.setattr(boundary.helper.importlib.metadata, "version", lambda _name: "99.0.0")
    _start(boundary)
    receipt = boundary.helper.evidence()
    assert "unsupported_pytest_cov_contract:99.0.0" in receipt["coverage_diagnostic"]
    assert boundary.helper.active_plugin() is None
    assert not boundary.output.exists()


@pytest.mark.parametrize("disabled", ["option", "blocked", "missing-options"])
def test_explicit_disabled_collector_names_the_native_control(coverage_boundary, disabled) -> None:
    """Native plugin disablement remains an explicit incomplete-evidence result."""
    boundary = coverage_boundary
    boundary.options.no_cov = disabled == "option"
    if disabled == "blocked":
        boundary.manager.set_blocked("pytest_cov")
    if disabled == "missing-options":
        del boundary.options.cov_source
    _start(boundary)
    receipt = boundary.helper.evidence()
    expected = "--no-cov" if disabled == "option" else "-p no:pytest_cov"
    assert expected in receipt["coverage_diagnostic"]
    assert receipt["coverage_policy"]["mode"] == "disabled"
    assert boundary.helper.active_plugin() is None


def test_unconfigured_public_hooks_do_not_invent_a_collector(coverage_boundary, monkeypatch) -> None:
    """An absent request never starts measurement or manufactures an observation."""
    boundary = coverage_boundary
    monkeypatch.delenv("SPECFACT_REVIEW_COVERAGE_REQUEST")
    _start(boundary)
    _finish(boundary)
    helper: ModuleType = boundary.helper
    assert helper.active_plugin() is None
    assert helper.evidence()["coverage_diagnostic"] == "project_pytest_coverage_plugin_not_activated"
