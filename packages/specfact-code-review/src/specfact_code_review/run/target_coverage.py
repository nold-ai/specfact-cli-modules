"""Target-only collection keeps reviewer instrumentation separate from native policy.

PYTEST_DONT_REWRITE: the verified bootstrap preloads this assertion-free plugin;
customer assertion rewriting remains unchanged.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.metadata
import json
import keyword
import os
from pathlib import Path
from types import SimpleNamespace


_REQUEST = "SPECFACT_REVIEW_COVERAGE_REQUEST"
_SESSION = SimpleNamespace(observation=None)
_SUPPORTED = {"7.0.0", "7.1.0"}
_FILTERS = ("source", "source_pkgs", "source_dirs", "include", "omit")


def configure(*, snapshot: Path, output: Path, directories: list[str], modules: list[str] | None = None) -> None:
    """Publish controller-validated measurement locations to this pytest process tree."""
    os.environ[_REQUEST] = json.dumps(
        {"snapshot": str(snapshot), "output": str(output), "directories": directories, "modules": modules or []}
    )


def _request() -> dict:
    request = json.loads(os.environ[_REQUEST])
    for name in ("snapshot", "output"):
        if not isinstance(request.get(name), str) or not Path(request[name]).is_absolute():
            raise ValueError("project_pytest_coverage_request_invalid")
    directories = request.get("directories")
    if not isinstance(directories, list) or not all(
        isinstance(path, str) and Path(path).is_absolute() for path in directories
    ):
        raise ValueError("project_pytest_coverage_request_invalid")
    request["modules"] = _module_names(request.get("modules", []))
    return request


def _module_names(modules) -> list[str]:
    """Validate named coverage selectors independently of filesystem locations."""
    if not isinstance(modules, list) or not all(
        isinstance(name, str) and name.isidentifier() and not keyword.iskeyword(name) for name in modules
    ):
        raise ValueError("project_pytest_coverage_request_invalid")
    return modules


def _coverage_options(native):
    run = {key: native.get_option(f"run:{key}") for key in _FILTERS}
    run.update(branch=native.get_option("run:branch"), paths=native.get_option("paths"))
    report = {
        "fail_under": native.get_option("report:fail_under"),
        "precision": native.get_option("report:precision"),
        "include": native.get_option("report:include"),
        "omit": native.get_option("report:omit"),
    }
    return run, report


def _configuration(options):
    import coverage
    from coverage.exceptions import CoverageException

    try:
        native = coverage.Coverage(config_file=getattr(options, "cov_config", True))
    except CoverageException as exc:
        raise ValueError(f"{type(exc).__name__}:{exc}") from exc
    run, report = _coverage_options(native)
    threshold = getattr(options, "cov_fail_under", None)
    precision = getattr(options, "cov_precision", None)
    return (
        run,
        report,
        report["fail_under"] if threshold is None else threshold,
        report["precision"] if precision is None else precision,
    )


def _reviewer_sources(request, configured):
    if any(configured.values()):
        return [True]
    collisions = [name for name in request["modules"] if Path(name).is_dir()]
    if collisions:
        raise ValueError(
            f"project_pytest_coverage_module_selector_ambiguous:{','.join(collisions)}; "
            "a same-named directory exists at pytest startup; configure an explicit coverage source_pkgs "
            "selection to disambiguate installed modules"
        )
    return [request["snapshot"], *request["directories"], *request["modules"]]


def _reviewer(options, manager, request, configured):
    from pytest_cov.plugin import CovPlugin

    class ReviewerCoverage(CovPlugin):
        """Use native measurement/worker transfer without creating a native report gate."""

        def _should_report(self):
            # No native coverage was requested. The controller enforces per-file policy.
            return False

    owned = copy.copy(options)
    owned.cov_source = _reviewer_sources(request, configured)
    owned.cov_report = {}
    return ReviewerCoverage(owned, manager)


def pytest_load_initial_conftests(early_config, parser, args):
    """Native pytest-cov's tryfirst hook resolves explicit activation before this hook."""
    del parser, args
    if _REQUEST not in os.environ:
        return
    state = SimpleNamespace(
        request=None,
        plugin=None,
        mode="disabled",
        threshold=0,
        precision=0,
        configuration={},
        diagnostic="",
        session=None,
    )
    _SESSION.observation = state
    try:
        _prepare(early_config)
    except (AttributeError, ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        state.diagnostic = f"project_pytest_coverage_instrumentation_unavailable:{type(exc).__name__}:{exc}"


def _state() -> SimpleNamespace:
    state = _SESSION.observation
    if state is None:
        raise ValueError("project_pytest_coverage_plugin_not_activated")
    return state


def _prepare(config):
    state = _state()
    version = importlib.metadata.version("pytest-cov")
    if version not in _SUPPORTED:
        raise ValueError(f"unsupported_pytest_cov_contract:{version}; supported=7.0.0,7.1.0")
    request = _request()
    state.request = request
    options = config.known_args_namespace
    run, report, threshold, precision = _configuration(options)
    state.threshold, state.precision = threshold, precision
    state.configuration = {
        "run": run,
        "report": report,
        "cov_config": getattr(options, "cov_config", None),
        "cov_report": getattr(options, "cov_report", {}),
        "cov_source": getattr(options, "cov_source", None),
    }
    if getattr(options, "no_cov", False):
        state.diagnostic = "project_pytest_coverage_disabled:--no-cov; required reviewer evidence is unavailable"
        return
    if not hasattr(options, "cov_source") or any(
        config.pluginmanager.is_blocked(name) for name in ("pytest_cov", "pytest_cov.plugin")
    ):
        state.diagnostic = (
            "project_pytest_coverage_disabled:-p no:pytest_cov; required reviewer evidence is unavailable"
        )
        return
    native = config.pluginmanager.getplugin("_cov")
    if native is not None:
        state.mode, state.plugin = "native", native
        return
    state.mode = "reviewer"
    state.plugin = _reviewer(options, config.pluginmanager, request, {key: run[key] for key in _FILTERS})
    config.pluginmanager.register(state.plugin, "_specfact_reviewer_cov")


def pytest_sessionfinish(session, exitstatus):
    del exitstatus
    if _SESSION.observation is not None:
        _SESSION.observation.session = session


def active_plugin():
    """Return only the collector actually used for this execution."""
    return None if _SESSION.observation is None else _SESSION.observation.plugin


def _policy() -> dict:
    state = _state()
    from coverage.results import should_fail_under

    plugin = state.plugin
    total = None if plugin is None else plugin.cov_total
    failed = (
        state.mode == "native"
        and plugin is not None
        and total is not None
        and state.session is not None
        and int(state.session.exitstatus) == 1
        and not plugin.options.collectonly
        and plugin._should_report()
        and should_fail_under(total, state.threshold, state.precision)
    )
    return {
        "mode": state.mode,
        "threshold": state.threshold,
        "precision": state.precision,
        "measured_total": total,
        "native_threshold_failed": bool(failed),
    }


def _export() -> dict:
    state = _state()
    plugin = state.plugin
    if plugin is None:
        return {}
    if state.session is None or hasattr(state.session.config, "workerinput"):
        raise ValueError("project_pytest_coverage_controller_observation_missing")
    if plugin.failed and plugin.options.no_cov_on_fail:
        raise ValueError(
            "project_pytest_coverage_suppressed:--no-cov-on-fail; required reviewer evidence is unavailable"
        )
    controller = plugin.cov_controller
    run, report = _coverage_options(controller.cov)
    state.configuration["effective"] = {
        "run": run,
        "report": report,
        "threshold": plugin.options.cov_fail_under,
        "precision": plugin.options.cov_precision,
    }
    if getattr(controller, "failed_workers", ()):
        raise ValueError("project_pytest_coverage_worker_missing; inspect xdist worker coverage receipts")
    output = Path(state.request["output"])
    # Preserve native report destinations. This private export has its own authority.
    from coverage.exceptions import CoverageException

    try:
        with contextlib.chdir(controller.topdir):
            total = controller.cov.json_report(outfile=str(output))
    except CoverageException as exc:
        raise ValueError(f"{type(exc).__name__}:{exc}") from exc
    if state.mode == "reviewer":
        plugin.cov_total = total
    return json.loads(output.read_text(encoding="utf-8"))


def evidence() -> dict:
    """Export separately labelled evidence after native pytest reporting has completed."""
    if _SESSION.observation is None:
        return {"coverage": {}, "coverage_diagnostic": "project_pytest_coverage_plugin_not_activated"}
    state = _state()
    payload = {}
    if not state.diagnostic:
        try:
            payload = _export()
        except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            state.diagnostic = f"project_pytest_coverage_evidence_unavailable:{exc}"
    return {
        "coverage": payload,
        "coverage_policy": _policy(),
        "coverage_threshold": state.threshold,
        "coverage_configuration": state.configuration,
        "coverage_diagnostic": state.diagnostic,
    }
