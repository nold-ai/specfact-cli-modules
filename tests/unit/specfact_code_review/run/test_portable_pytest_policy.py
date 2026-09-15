"""Native pytest resolves portable coverage thresholds and test support roots."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from specfact_code_review.run import target_pytest


OBSERVE_POLICY = """
import importlib.util, json, sys
from pathlib import Path
import pytest
spec = importlib.util.spec_from_file_location('target_observer', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.SNAPSHOT_ROOT = Path(sys.argv[2])
for name in ('pytest_xdist_node_collection_finished', 'pytest_testnodedown'):
    pytest.hookimpl(optionalhook=True)(getattr(module.Observer, name))
observer = module.Observer()
code = pytest.main(json.loads(sys.argv[4]), plugins=[observer])
Path(sys.argv[3]).write_text(json.dumps({
    'exit_code': int(code),
    'coverage_threshold': getattr(observer, 'coverage_threshold', None),
    'test_roots': getattr(observer, 'test_roots', None),
    'pytest_root': getattr(observer, 'pytest_root', None),
    'records': observer.records,
    'collected': sorted(observer.collected),
    'deselected': sorted(observer.deselected),
}))
raise SystemExit(int(code))
"""


def _observe_policy(root: Path, output: Path, arguments: list[str]) -> dict:
    environment = {
        **os.environ,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_ADDOPTS": "",
        "COVERAGE_FILE": str(output.with_suffix(".coverage")),
    }
    command = [
        sys.executable,
        "-c",
        OBSERVE_POLICY,
        str(Path(target_pytest.__file__).resolve()),
        str(root),
        str(output),
        json.dumps(
            [
                "-q",
                "-p",
                "pytest_cov",
                "--cov=.",
                "--cov-report=",
                "-o",
                f"cache_dir={output.with_suffix('.cache')}",
                *arguments,
            ]
        ),
    ]
    result = subprocess.run(command, cwd=root, env=environment, text=True, capture_output=True, check=False, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output.read_text())


@pytest.mark.parametrize(
    "arguments,expected", [([], 70.0), (["--cov-fail-under=60"], 60.0), (["--cov-config=alternate.ini"], 90.0)]
)
def test_native_coverage_threshold_preserves_configuration_and_cli_precedence(
    tmp_path: Path, arguments: list[str], expected: float
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text("[pytest]\n")
    (project / ".coveragerc").write_text("[report]\nfail_under = 70\n")
    (project / "alternate.ini").write_text("[report]\nfail_under = 90\n")
    (project / "test_policy.py").write_text("def test_valid(): assert True\n")
    result = _observe_policy(project, tmp_path / "policy.json", arguments)
    assert result["coverage_threshold"] == expected


@pytest.mark.parametrize(
    "configuration,testpaths,expected",
    [
        ("pytest.ini", "tests", ["tests"]),
        ("pytest.ini", "tests/*", ["tests/unit"]),
        ("pytest.ini", ".", []),
        ("pytest.ini", "tests/unit/test_policy.py", []),
        ("tests/pytest.ini", ".", ["tests"]),
        ("tests/pytest.ini", "unit", ["tests/unit"]),
    ],
)
def test_native_test_support_roots_expand_from_configuration_root(
    tmp_path: Path, configuration: str, testpaths: str, expected: list[str]
) -> None:
    project = tmp_path / "project"
    (project / "tests/unit").mkdir(parents=True)
    (project / configuration).write_text(f"[pytest]\ntestpaths = {testpaths}\n")
    (project / "tests/unit/test_policy.py").write_text("def test_valid(): assert True\n")
    result = _observe_policy(project, tmp_path / "roots.json", ["-c", configuration])
    assert result["test_roots"] == expected


def test_native_test_support_roots_exclude_paths_outside_snapshot(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "test_external.py").write_text("def test_external(): assert True\n")
    (project / "test_policy.py").write_text("def test_valid(): assert True\n")
    (project / "pytest.ini").write_text("[pytest]\ntestpaths = ../outside\n")
    result = _observe_policy(project, tmp_path / "outside.json", ["test_policy.py"])
    assert result["test_roots"] == []


@pytest.mark.parametrize("directory", [".", "checks"])
def test_native_custom_test_nodeids_retain_their_configuration_root(tmp_path: Path, directory: str) -> None:
    project = tmp_path / "project"
    config_root = project / directory
    config_root.mkdir(parents=True)
    configuration = config_root / "pytest.ini"
    configuration.write_text("[pytest]\ntestpaths = check_app.py\npython_files = check_*.py\n")
    (config_root / "check_app.py").write_text("def test_valid(): assert True\n")
    result = _observe_policy(project, tmp_path / "root-context.json", ["-c", str(configuration)])
    assert result["collected"] == ["check_app.py::test_valid"]
    assert result["pytest_root"] == directory


def test_native_outside_configuration_root_is_explicit(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    configuration = tmp_path / "pytest.ini"
    configuration.write_text("[pytest]\n")
    (project / "test_policy.py").write_text("def test_valid(): assert True\n")
    result = _observe_policy(project, tmp_path / "outside-root.json", ["-c", str(configuration), "test_policy.py"])
    assert result["collected"] == ["project/test_policy.py::test_valid"]
    assert result["pytest_root"] == str(tmp_path.resolve())


@pytest.mark.parametrize("outcome", ["skip", "xfail", "xpass", "xpass-empty"])
def test_native_nonpassing_outcomes_preserve_phase_facts(tmp_path: Path, outcome: str) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text("[pytest]\n")
    body = "assert True" if outcome.startswith("xpass") else f"pytest.{outcome}('expected')"
    reason = "" if outcome == "xpass-empty" else "expected"
    marker = f"@pytest.mark.xfail(reason={reason!r}, strict=False)\n" if outcome.startswith("xpass") else ""
    (project / "test_policy.py").write_text(
        f"import pytest\n{marker}def test_affected(): {body}\ndef test_healthy(): assert True\n"
    )
    result = _observe_policy(project, tmp_path / "outcomes.json", [])
    affected = next(
        row for row in result["records"] if row["nodeid"].endswith("test_affected") and row["phase"] == "call"
    )
    assert affected["outcome"] == ("passed" if outcome.startswith("xpass") else "skipped")
    assert bool(affected["wasxfail"]) == (outcome not in {"skip", "xpass-empty"})
    if outcome == "xpass-empty":
        assert affected.get("has_xfail") is True
    assert result["collected"] == ["test_policy.py::test_affected", "test_policy.py::test_healthy"]
