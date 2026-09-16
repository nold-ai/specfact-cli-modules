"""Portable workers keep customer imports out of controller startup."""

import json
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specfact_code_review.run import portable_worker
from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.run.installed_coverage import CoverageBridge
from specfact_code_review.run.portable_worker import (
    preparation_failure_snapshot,
    select_test_paths,
    validate_observation,
)
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


def test_explicit_test_selection_preserves_hatch_plugin_config(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    source, test = tmp_path / "src/app.py", tmp_path / "tests/test_app.py"
    source.touch()
    test.touch()
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts="-p pytest_asyncio.plugin --import-mode=importlib"\ntestpaths=["tests"]\n'
    )
    plan = discover_project(tmp_path)
    assert select_test_paths(plan, [source, test], full=False) == ("tests/test_app.py",)
    assert "-p pytest_asyncio.plugin" in plan.pytest_config["addopts"]


def test_source_only_review_finds_corresponding_test(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    source, test = tmp_path / "calculator.py", tmp_path / "tests/test_calculator.py"
    source.touch()
    test.touch()
    assert select_test_paths(discover_project(tmp_path), [source], full=False) == ("tests/test_calculator.py",)


def test_no_corresponding_tests_is_actionable(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.touch()
    with pytest.raises(ProjectRuntimeError, match="test_selection_empty"):
        select_test_paths(discover_project(tmp_path), [source], full=False)


def test_preparation_failure_marks_only_dependent_members() -> None:
    rows = preparation_failure_snapshot("project_manager_ambiguous:poetry,uv")
    assert set(rows) == {"basedpyright", "pylint", "contracts", "targeted-pytest-coverage"}
    assert all(row["evidence_outcome"] == "UNKNOWN" for row in rows.values())
    assert all(row["diagnostic"] == "project_runtime_required" for row in rows.values())


def test_pytest_collection_only_cannot_pass() -> None:

    with pytest.raises(ProjectRuntimeError, match="execution_incomplete"):
        validate_observation({"exit_code": 0, "collected": ["tests/test_a.py::test_a"], "records": []}, 0)


def test_pytest_early_stop_is_incomplete_even_with_real_failure() -> None:

    observation = {
        "exit_code": 1,
        "collected": ["a", "b"],
        "records": [{"nodeid": "a", "phase": "call", "outcome": "failed"}],
    }
    with pytest.raises(ProjectRuntimeError, match=r"unexecuted.*b"):
        validate_observation(observation, 1)


def test_pytest_success_requires_coverage_evidence() -> None:

    observation = {
        "exit_code": 0,
        "collected": ["a"],
        "records": [{"nodeid": "a", "phase": "call", "outcome": "passed"}],
    }
    with pytest.raises(ProjectRuntimeError, match="coverage_missing"):
        validate_observation(observation, 0)


def test_failed_pytest_startup_cannot_reuse_previous_observation(tmp_path, monkeypatch) -> None:

    observation = tmp_path / "pytest-observation.json"
    observation.write_text(
        json.dumps(
            {
                "exit_code": 0,
                "collected": ["a"],
                "records": [{"nodeid": "a", "phase": "call", "outcome": "passed"}],
                "coverage": {"files": {"app.py": {}}},
            }
        )
    )
    monkeypatch.setattr(
        portable_worker,
        "Path",
        lambda value: observation if value == "/opt/specfact/tmp/pytest-observation.json" else Path(value),
    )
    monkeypatch.setattr(portable_worker, "target_command", lambda *args: ["child"])
    monkeypatch.setattr(portable_worker.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    assert portable_worker.run_portable_pytest([tmp_path / "app.py"], ("portable-pytest-v2", "{}"))
    assert not observation.exists()


@pytest.mark.parametrize("field", ["collection_errors", "internal_errors"])
def test_real_failure_does_not_hide_partial_pytest_execution(field) -> None:
    observation = {
        "exit_code": 1,
        "collected": ["a"],
        "records": [{"nodeid": "a", "phase": "call", "outcome": "failed"}],
        "coverage": {"files": {"app.py": {}}},
        field: ["controlled startup or collection error"],
    }
    with pytest.raises(ProjectRuntimeError, match=r"project_pytest_.*error"):
        validate_observation(observation, 1)


@pytest.mark.parametrize("configuration", [{}, {"testpaths": []}, {"testpaths": ""}])
def test_pytest_native_default_root_is_preserved(tmp_path: Path, configuration: dict) -> None:
    source = tmp_path / "app.py"
    source.touch()
    (tmp_path / "test_app.py").touch()
    plan = ProjectPlan(tmp_path, manager="pip", pytest_config=configuration)
    assert not select_test_paths(plan, [source], full=True)
    assert select_test_paths(plan, [source], full=False) == ("test_app.py",)


@pytest.mark.parametrize("name", [".venv", "venv", "custom-python"])
def test_default_test_discovery_excludes_environment_tests(tmp_path: Path, name: str) -> None:
    source = tmp_path / "app.py"
    source.touch()
    (tmp_path / "test_app.py").touch()
    environment = tmp_path / name
    environment.mkdir()
    (environment / "pyvenv.cfg").write_text("home=/usr/bin\n")
    (environment / "test_app.py").touch()
    assert select_test_paths(ProjectPlan(tmp_path, manager="pip"), [source], full=False) == ("test_app.py",)


@pytest.mark.parametrize("directory", ["build", "dist", ".cache", "package.egg", "_darcs", "CVS", "venv", "{arch}"])
def test_default_recursion_exclusions_prevent_false_test_ambiguity(tmp_path: Path, directory: str) -> None:
    source = tmp_path / "app.py"
    source.touch()
    for name in ("tests", directory):
        (tmp_path / name).mkdir()
        (tmp_path / name / "test_app.py").touch()
    assert select_test_paths(ProjectPlan(tmp_path, manager="pip"), [source], full=False) == ("tests/test_app.py",)


@pytest.mark.parametrize(
    "patterns", [["generated"], "generated", ["fixtures/generated"], "fixtures/generated", ["fixtures/*"]]
)
def test_custom_recursion_exclusions_replace_pytest_defaults(tmp_path: Path, patterns: object) -> None:
    source = tmp_path / "app.py"
    source.touch()
    for name in ("build", "fixtures/generated"):
        (tmp_path / name).mkdir(parents=True)
        (tmp_path / name / "test_app.py").touch()
    plan = ProjectPlan(tmp_path, manager="pip", pytest_config={"norecursedirs": patterns})
    assert select_test_paths(plan, [source], full=False) == ("build/test_app.py",)


@pytest.mark.parametrize("patterns", [[], ""])
def test_empty_recursion_exclusions_enable_default_excluded_directory(tmp_path: Path, patterns: object) -> None:
    source = tmp_path / "app.py"
    source.touch()
    (tmp_path / "build").mkdir()
    (tmp_path / "build/test_app.py").touch()
    plan = ProjectPlan(tmp_path, manager="pip", pytest_config={"norecursedirs": patterns})
    assert select_test_paths(plan, [source], full=False) == ("build/test_app.py",)


def test_explicit_test_root_is_not_pruned_by_recursion_defaults(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.touch()
    (tmp_path / "build").mkdir()
    (tmp_path / "build/test_app.py").touch()
    plan = ProjectPlan(tmp_path, manager="pip", pytest_config={"testpaths": ["build"]})
    assert select_test_paths(plan, [source], full=False) == ("build/test_app.py",)


@pytest.mark.parametrize("absolute", [True, False])
def test_recursion_exclusions_support_absolute_and_quoted_directory_names(tmp_path: Path, absolute: bool) -> None:
    source = tmp_path / "app.py"
    source.touch()
    for name in ("tests", "generated cache"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "test_app.py").touch()
    patterns = [str(tmp_path / "generated cache")] if absolute else '"generated cache"'
    plan = ProjectPlan(tmp_path, manager="pip", pytest_config={"norecursedirs": patterns})
    assert select_test_paths(plan, [source], full=False) == ("tests/test_app.py",)


@pytest.mark.parametrize("quote", ['"', "'"])
def test_quoted_pytest_paths_match_native_configuration(tmp_path: Path, monkeypatch, quote: str) -> None:
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    (tmp_path / "source tree").mkdir()
    (tmp_path / "integration tests").mkdir()
    source = tmp_path / "source tree/app name.py"
    source.touch()
    selected = tmp_path / "integration tests/test_app name.py"
    selected.write_text("def test_example(): assert True\n")
    configuration = tmp_path / "pytest.ini"
    configuration.write_text(
        "[pytest]\n"
        f"testpaths = {quote}integration tests{quote}\n"
        f"pythonpath = {quote}source tree{quote}\n"
        f"python_files = {quote}test_* name.py{quote}\n"
    )
    native = pytest.Config.fromdictargs({}, ["-c", str(configuration)])
    try:
        plan = discover_project(tmp_path)
        assert plan.source_roots == tuple(path.relative_to(tmp_path).as_posix() for path in native.getini("pythonpath"))
        assert not select_test_paths(plan, [source], full=True)
        assert select_test_paths(plan, [source], full=False) == (selected.relative_to(tmp_path).as_posix(),)
        assert select_test_paths(plan, [selected], full=False) == (selected.relative_to(tmp_path).as_posix(),)
    finally:
        native._ensure_unconfigure()


@pytest.mark.parametrize("option", ["pythonpath", "testpaths", "python_files", "norecursedirs"])
def test_invalid_pytest_quoting_names_configuration_option(tmp_path: Path, option: str) -> None:
    (tmp_path / "pytest.ini").write_text(f'[pytest]\n{option} = "unterminated\n')
    with pytest.raises(ProjectRuntimeError, match=f"project_pytest_config_invalid:pytest.ini:{option}"):
        discover_project(tmp_path)


def test_expanded_testpaths_reject_escaping_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "tests").mkdir(parents=True)
    source = root / "app.py"
    source.touch()
    outside = tmp_path / "external"
    outside.mkdir()
    (outside / "test_app.py").touch()
    (root / "tests/external").symlink_to(outside, target_is_directory=True)
    plan = ProjectPlan(root, manager="pip", pytest_config={"testpaths": ["tests/*"]})
    with pytest.raises(ProjectRuntimeError, match="project_test_path_escape"):
        select_test_paths(plan, [source], full=False)


def test_glob_testpaths_do_not_admit_excluded_environment(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.touch()
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv/test_app.py").touch()
    plan = ProjectPlan(tmp_path, manager="pip", pytest_config={"testpaths": [".venv/*.py"]})
    with pytest.raises(ProjectRuntimeError, match="project_test_selection_empty"):
        select_test_paths(plan, [source], full=False)


@pytest.fixture(name="observe_coverage_policy")
def fixture_observe_coverage_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[dict[str, Any], int], list[ReviewFinding]]:
    """Exercise the controller against serialized child evidence and a real exit status."""
    monkeypatch.chdir(tmp_path)
    observation_file = tmp_path / "pytest-observation.json"
    monkeypatch.setattr(
        portable_worker,
        "Path",
        lambda value: observation_file if value == "/opt/specfact/tmp/pytest-observation.json" else Path(value),
    )
    monkeypatch.setattr(
        portable_worker, "_portable_pytest_command", lambda *_args: (CoverageBridge((), (), {}, {}), ["child"])
    )

    def observe(observation: dict[str, Any], exit_code: int) -> list[ReviewFinding]:
        def complete(*_args: object, **_kwargs: object) -> SimpleNamespace:
            observation_file.write_text(json.dumps(observation), encoding="utf-8")
            return SimpleNamespace(returncode=exit_code)

        monkeypatch.setattr(portable_worker.subprocess, "run", complete)
        return portable_worker.run_portable_pytest([Path("test_app.py")], ("portable-pytest-v2", "{}"))

    return observe


def _coverage_observation(exit_code: int = 1) -> dict[str, Any]:
    """Give the controller completed tests with independently failing native coverage."""
    return {
        "exit_code": exit_code,
        "rootpath": str(Path.cwd()),
        "collected": ["test_app.py::test_app"],
        "records": [{"nodeid": "test_app.py::test_app", "phase": "call", "outcome": "passed"}],
        "coverage": {"files": {"test_app.py": {}}},
        "coverage_threshold": 80,
        "coverage_policy": {
            "mode": "native",
            "threshold": 80,
            "precision": 2,
            "measured_total": 46.88,
            "native_threshold_failed": True,
        },
    }


def test_native_aggregate_coverage_failure_has_explicit_blocking_finding(observe_coverage_policy) -> None:
    """A real native aggregate failure remains a failure even when every test passed."""
    findings = observe_coverage_policy(_coverage_observation(), 1)
    assert len(findings) == 1
    finding = findings[0]
    assert (finding.rule, finding.category, finding.severity) == ("TEST_COVERAGE_POLICY_FAILED", "testing", "error")
    assert all(value in finding.message for value in ("46.88", "80", "precision=2"))


@pytest.mark.parametrize("empty_records", [False, True])
def test_native_coverage_failure_retains_incomplete_and_failed_test_evidence(
    observe_coverage_policy, empty_records: bool
) -> None:
    """The aggregate finding supplements, rather than replaces, partial test evidence."""
    observation = _coverage_observation()
    observation["collection_errors"] = ["controlled collection failure"]
    observation["records"] = (
        [] if empty_records else [{"nodeid": "test_app.py::test_app", "phase": "call", "outcome": "failed"}]
    )
    findings = observe_coverage_policy(observation, 1)
    assert "TEST_COVERAGE_POLICY_FAILED" in {row.rule for row in findings}
    assert any("project_pytest_collection_error" in row.message for row in findings)
    assert ("TEST_OUTCOME_NOT_PASS" in {row.rule for row in findings}) is not empty_records


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mode", "unknown"),
        ("threshold", True),
        ("threshold", 101),
        ("threshold", float("nan")),
        ("precision", True),
        ("precision", -1),
        ("precision", 10),
        ("measured_total", "46.88"),
        ("measured_total", float("inf")),
        ("measured_total", None),
        ("native_threshold_failed", 1),
        ("mode", "reviewer"),
        ("mode", "disabled"),
    ],
)
def test_malformed_or_contradictory_coverage_policy_is_actionable(observe_coverage_policy, field, value) -> None:
    """Reject invalid evidence without attributing arbitrary nonzero exits to coverage."""
    observation = _coverage_observation()
    observation["coverage_policy"][field] = value
    findings = observe_coverage_policy(observation, 1)
    assert any("project_pytest_coverage_policy_invalid" in row.message for row in findings)
    assert not any(row.rule == "TEST_COVERAGE_POLICY_FAILED" for row in findings)


@pytest.mark.parametrize("policy", [None, [], {}, {"mode": "native"}])
def test_incomplete_coverage_policy_shape_is_actionable(observe_coverage_policy, policy) -> None:
    """A present but incomplete receipt cannot use the legacy missing-receipt path."""
    observation = _coverage_observation()
    observation["coverage_policy"] = policy
    findings = observe_coverage_policy(observation, 1)
    assert any("project_pytest_coverage_policy_invalid" in row.message for row in findings)


def test_native_coverage_failure_cannot_contradict_successful_exit(observe_coverage_policy) -> None:
    """A failed-policy receipt paired with exit zero must remain incomplete evidence."""
    findings = observe_coverage_policy(_coverage_observation(0), 0)
    assert any("project_pytest_coverage_policy_invalid" in row.message for row in findings)


@pytest.mark.parametrize("mode", ["native", "reviewer", "disabled", "legacy"])
@pytest.mark.parametrize("exit_code", [0, 1])
def test_unfailed_coverage_policy_preserves_existing_exit_behavior(observe_coverage_policy, mode, exit_code) -> None:
    """Neither reviewer collection nor an absent receipt explains an arbitrary exit one."""
    observation = _coverage_observation(exit_code)
    observation["coverage_policy"].update(mode=mode, measured_total=None, native_threshold_failed=False)
    if mode == "legacy":
        del observation["coverage_policy"]
    findings = observe_coverage_policy(observation, exit_code)
    assert not any(row.rule == "TEST_COVERAGE_POLICY_FAILED" for row in findings)
    assert bool(findings) is bool(exit_code)
    if exit_code:
        assert findings[0].message == "project_pytest_failure_without_observed_test"


@pytest.mark.parametrize(
    "diagnostic",
    [
        "project_pytest_coverage_disabled:--no-cov; required reviewer evidence unavailable",
        "project_pytest_coverage_xdist_unsupported:missing worker coverage",
        "project_pytest_coverage_export_failed:configured report suppression",
    ],
)
def test_specific_missing_coverage_diagnostic_preserves_other_failures(observe_coverage_policy, diagnostic) -> None:
    """Keep the exact target remedy together with native policy and actual test failures."""
    observation = _coverage_observation()
    observation["coverage"] = {}
    observation["coverage_diagnostic"] = diagnostic
    observation["records"][0]["outcome"] = "failed"
    findings = observe_coverage_policy(observation, 1)
    assert any(row.message == diagnostic for row in findings)
    assert {"TEST_COVERAGE_POLICY_FAILED", "TEST_OUTCOME_NOT_PASS"} <= {row.rule for row in findings}
    assert not any("project_pytest_coverage_missing" in row.message for row in findings)


@pytest.mark.parametrize("diagnostic", [None, False, 7, [], {"reason": "untrusted"}])
def test_malformed_missing_coverage_diagnostic_is_not_stringified(observe_coverage_policy, diagnostic) -> None:
    """Reject a malformed target diagnostic instead of formatting an arbitrary object."""
    observation = _coverage_observation()
    observation["coverage"] = {}
    observation["coverage_diagnostic"] = diagnostic
    findings = observe_coverage_policy(observation, 1)
    assert any("project_pytest_coverage_diagnostic_invalid" in row.message for row in findings)


@pytest.mark.parametrize("field", ["collection_errors", "internal_errors"])
def test_collection_errors_precede_missing_coverage_diagnostic(observe_coverage_policy, field) -> None:
    """Coverage reporting cannot hide earlier collection or plugin failures."""
    observation = _coverage_observation()
    observation["coverage"] = {}
    observation["coverage_diagnostic"] = "controlled coverage diagnostic"
    observation[field] = ["controlled collection or plugin failure"]
    findings = observe_coverage_policy(observation, 1)
    expected = "project_pytest_collection_error" if field == "collection_errors" else "project_pytest_internal_error"
    assert any(expected in row.message for row in findings)
    assert not any(row.message == observation["coverage_diagnostic"] for row in findings)


@pytest.mark.parametrize("diagnostic", ["", "absent"])
def test_empty_or_absent_missing_coverage_diagnostic_retains_legacy_remedy(observe_coverage_policy, diagnostic) -> None:
    """Older observers and empty diagnostic strings retain the established coverage error."""
    observation = _coverage_observation()
    observation["coverage"] = {}
    if diagnostic != "absent":
        observation["coverage_diagnostic"] = diagnostic
    findings = observe_coverage_policy(observation, 1)
    assert any("project_pytest_coverage_missing" in row.message for row in findings)
