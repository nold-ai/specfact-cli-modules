"""Portable workers keep customer imports out of controller startup."""

from pathlib import Path

import pytest

from specfact_code_review.run.portable_worker import preparation_failure_snapshot, select_test_paths
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError


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
    from specfact_code_review.run.portable_worker import validate_observation

    with pytest.raises(ProjectRuntimeError, match="execution_incomplete"):
        validate_observation({"exit_code": 0, "collected": ["tests/test_a.py::test_a"], "records": []}, 0)


def test_pytest_early_stop_is_incomplete_even_with_real_failure() -> None:
    from specfact_code_review.run.portable_worker import validate_observation

    observation = {
        "exit_code": 1,
        "collected": ["a", "b"],
        "records": [{"nodeid": "a", "phase": "call", "outcome": "failed"}],
    }
    with pytest.raises(ProjectRuntimeError, match=r"unexecuted.*b"):
        validate_observation(observation, 1)


def test_pytest_success_requires_coverage_evidence() -> None:
    from specfact_code_review.run.portable_worker import validate_observation

    observation = {
        "exit_code": 0,
        "collected": ["a"],
        "records": [{"nodeid": "a", "phase": "call", "outcome": "passed"}],
    }
    with pytest.raises(ProjectRuntimeError, match="coverage_missing"):
        validate_observation(observation, 0)


def test_failed_pytest_startup_cannot_reuse_previous_observation(tmp_path, monkeypatch) -> None:
    import json
    from types import SimpleNamespace

    from specfact_code_review.run import portable_worker, target_launch

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
    monkeypatch.setattr(target_launch, "target_command", lambda *args: ["child"])
    monkeypatch.setattr(portable_worker.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    assert portable_worker.run_portable_pytest([tmp_path / "app.py"], ("portable-pytest-v2", "{}"))
    assert not observation.exists()
