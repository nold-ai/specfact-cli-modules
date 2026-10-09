"""Invalid pytest requests precede setup; valid selectors retain coverage ownership."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from specfact_code_review.run import installed_coverage, portable_worker
from specfact_code_review.run.installed_coverage import CoverageBridge


@pytest.mark.parametrize("value", [[], "invalid", None, True, 1])
def test_decoded_non_object_avoids_planning_with_invalid_request(monkeypatch, value):
    planner = Mock(return_value=CoverageBridge((), (), {}, {}))
    command = Mock(side_effect=AssertionError("invalid request must not launch"))
    monkeypatch.setattr(portable_worker, "plan_installed_coverage", planner)
    monkeypatch.setattr(portable_worker, "target_command", command)
    with pytest.raises(ValueError, match="project_pytest_request_invalid"):
        portable_worker._portable_pytest_command([], json.dumps(value))
    planner.assert_not_called()
    command.assert_not_called()


def test_unusable_request_precedes_failure_in_unused_setup(monkeypatch):
    planner = Mock(side_effect=OSError("unused installed metadata failure"))
    monkeypatch.setattr(portable_worker, "plan_installed_coverage", planner)
    with pytest.raises(ValueError, match="project_pytest_request_invalid"):
        portable_worker._portable_pytest_command([], "null")
    planner.assert_not_called()


@pytest.mark.parametrize(
    "encoded,expected",
    [
        (
            '{"selectors":["tests"]}',
            {
                "selectors": ["tests"],
                "coverage_directories": ["/owned/package"],
                "coverage_modules": ["owned"],
                "coverage_candidates": ["/owned/package/first.py", "/owned/package/second.py"],
            },
        ),
        (
            '{"selectors":["tests"],"coverage_modules":["untrusted"],"kept":1,"coverage_directories":["untrusted"],"coverage_candidates":["untrusted"]}',
            {
                "coverage_modules": ["owned"],
                "kept": 1,
                "selectors": ["tests"],
                "coverage_directories": ["/owned/package"],
                "coverage_candidates": ["/owned/package/first.py", "/owned/package/second.py"],
            },
        ),
    ],
)
def test_valid_objects_retain_exact_bridge_and_command(monkeypatch, encoded, expected):
    bridge = CoverageBridge(
        (Path("/owned/package"),),
        (),
        {},
        {"source.py": ("/owned/package/first.py",)},
        ("/owned/package/second.py",),
        ("owned",),
    )
    planner = Mock(return_value=bridge)
    command = Mock(return_value=["native-worker", "unchanged-arguments"])
    monkeypatch.setattr(portable_worker, "plan_installed_coverage", planner)
    monkeypatch.setattr(portable_worker, "target_command", command)
    files = [Path("source.py")]
    actual_bridge, actual_command = portable_worker._portable_pytest_command(files, encoded)
    assert actual_bridge is bridge and actual_command == ["native-worker", "unchanged-arguments"]
    command.assert_called_once()
    domain, arguments = command.call_args.args
    assert domain == "pytest-observe" and len(arguments) == 1
    assert json.loads(arguments[0]) == expected
    planner.assert_called_once_with(
        files, snapshot=Path(".").resolve(), site_packages=Path("/opt/specfact/project-runtime/site-packages")
    )


@pytest.mark.parametrize("names", [[], ["README.md", "types.pyi"]])
def test_no_python_inputs_avoid_ownership_setup(tmp_path, monkeypatch, names):
    metadata = Mock(side_effect=AssertionError("no ownership inputs"))
    snapshot_index = Mock(side_effect=AssertionError("no source inputs"))
    monkeypatch.setattr(installed_coverage, "_distribution_context", metadata)
    monkeypatch.setattr(installed_coverage, "_snapshot_index", snapshot_index)
    result = installed_coverage.plan_installed_coverage(
        [tmp_path / name for name in names], snapshot=tmp_path, site_packages=tmp_path / "site"
    )
    assert result == CoverageBridge((), (), {}, {})
    metadata.assert_not_called()
    snapshot_index.assert_not_called()


def test_nonempty_outside_source_retains_complete_ownership_path(tmp_path, monkeypatch):
    snapshot, site = tmp_path / "snapshot", tmp_path / "site"
    snapshot.mkdir()
    site.mkdir()
    outside = tmp_path / "outside.py"
    metadata = Mock(wraps=installed_coverage._distribution_context)
    monkeypatch.setattr(installed_coverage, "_distribution_context", metadata)
    result = installed_coverage.plan_installed_coverage([outside], snapshot=snapshot, site_packages=site)
    metadata.assert_called_once_with(snapshot.resolve(), site.resolve())
    assert result == CoverageBridge((), (), {}, {str(outside): ()})
