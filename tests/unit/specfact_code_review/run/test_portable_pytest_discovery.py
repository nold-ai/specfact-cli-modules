"""Full review delegates discovery to actual target pytest configuration."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from specfact_code_review.run import target_pytest
from specfact_code_review.run.portable_worker import select_test_paths, validate_observation
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError


OBSERVE_DISCOVERY = """
import importlib.util, json, sys
from pathlib import Path
import pytest
spec = importlib.util.spec_from_file_location('observer_module', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for name in ('pytest_xdist_node_collection_finished', 'pytest_testnodedown'):
    pytest.hookimpl(optionalhook=True)(getattr(module.Observer, name))
observer = module.Observer()
output = Path(sys.argv[2])
coverage_output = output.with_suffix('.coverage.json')
args = ['-q', '-p', 'pytest_cov', '--cov=.',
        '--cov-report=json:' + str(coverage_output),
        '-o', 'cache_dir=' + str(output.with_suffix('.cache')),
        *json.loads(sys.argv[3])]
code = pytest.main(args, plugins=[observer])
output.write_text(json.dumps({
    'exit_code': int(code), 'collected': sorted(observer.collected),
    'deselected': sorted(observer.deselected), 'records': observer.records,
    'collection_errors': observer.collection_errors,
    'internal_errors': observer.internal_errors,
    'pytest_version': pytest.__version__,
    'coverage': json.loads(coverage_output.read_text()) if coverage_output.is_file() else {},
}))
raise SystemExit(int(code))
"""


def _observe_discovery(root: Path, output: Path, selectors: tuple[str, ...]) -> tuple[dict, str]:
    environment = {
        **os.environ,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_ADDOPTS": "",
        "COVERAGE_FILE": str(output.with_suffix(".coverage")),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            OBSERVE_DISCOVERY,
            str(Path(target_pytest.__file__).resolve()),
            str(output),
            json.dumps(selectors),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    observation = json.loads(output.read_text())
    assert observation["exit_code"] == completed.returncode
    return observation, completed.stdout + completed.stderr


@pytest.mark.parametrize(
    ("configuration", "expected", "warns"),
    [
        ("testpaths = absent", ["tests/test_app.py", "other/test_else.py"], True),
        ("testpaths = absent tests", ["tests/test_app.py"], False),
        ("testpaths = tests/*.py", ["tests/test_app.py"], False),
        ("testpaths = absent*", ["tests/test_app.py", "other/test_else.py"], True),
        ("testpaths = tests\naddopts = other/test_else.py", ["other/test_else.py"], False),
        ("testpaths =", ["tests/test_app.py", "other/test_else.py"], False),
    ],
)
def test_full_review_matches_native_discovery(
    tmp_path: Path, configuration: str, expected: list[str], warns: bool
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pytest.ini").write_text(f"[pytest]\n{configuration}\n")
    for name in ("tests/test_app.py", "other/test_else.py"):
        test = root / name
        test.parent.mkdir(exist_ok=True)
        test.write_text("def test_valid(): assert 2 + 2 == 4\n")
    native, native_output = _observe_discovery(root, tmp_path / "native.json", ())
    selectors = select_test_paths(discover_project(root), [], full=True)
    portable, portable_output = _observe_discovery(root, tmp_path / "portable.json", selectors)
    assert native["exit_code"] == 0, native_output
    assert portable["exit_code"] == 0, portable_output
    expected_nodes = sorted(f"{name}::test_valid" for name in expected)
    assert native["collected"] == portable["collected"] == expected_nodes
    assert portable["records"] == native["records"]
    warning = "No files were found in testpaths"
    assert (warning in native_output) == (warning in portable_output) == warns
    validate_observation(portable, portable["exit_code"])


@pytest.mark.parametrize("selection", ["source", "test", "mixed"])
def test_targeted_review_does_not_expand_into_full_discovery(tmp_path: Path, selection: str) -> None:
    source = tmp_path / "app.py"
    source.touch()
    selected = tmp_path / "test_app.py"
    selected.write_text("def test_selected(): assert True\n")
    (tmp_path / "test_other.py").write_text("def test_other(): assert False\n")
    files = {"source": [source], "test": [selected], "mixed": [source, selected]}[selection]
    selectors = select_test_paths(discover_project(tmp_path), files, full=False)
    observation, output = _observe_discovery(tmp_path, tmp_path / "portable.json", selectors)
    assert observation["exit_code"] == 0, output
    assert observation["collected"] == ["test_app.py::test_selected"]
    validate_observation(observation, 0)


@pytest.mark.parametrize("has_failure", [True, False])
def test_native_fallback_preserves_failure_and_empty_execution(tmp_path: Path, has_failure: bool) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = absent\n")
    if has_failure:
        (tmp_path / "test_case.py").write_text("def test_defect(): assert 2 + 2 == 5\n")
    selectors = select_test_paths(discover_project(tmp_path), [], full=True)
    observation, output = _observe_discovery(tmp_path, tmp_path / "portable.json", selectors)
    assert "No files were found in testpaths" in output
    if has_failure:
        assert observation["exit_code"] == 1, output
        assert any(row["phase"] == "call" and row["outcome"] == "failed" for row in observation["records"])
        validate_observation(observation, 1)
    else:
        assert observation["exit_code"] == 5, output
        with pytest.raises(ProjectRuntimeError, match="execution_incomplete"):
            validate_observation(observation, 5)
