"""Native pytest selection determines the required execution inventory."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import target_pytest


OBSERVE_SCRIPT = """
import importlib.util,json,sys
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('observer_module',sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for name in ('pytest_xdist_node_collection_finished','pytest_testnodedown'):
    pytest.hookimpl(optionalhook=True)(getattr(module.Observer,name))
observer=module.Observer()
code=pytest.main(['test_case.py','-q'],plugins=[observer])
Path('observation.json').write_text(json.dumps({
    'exit_code':int(code),'collected':sorted(observer.collected),
    'deselected':sorted(getattr(observer,'deselected',())),
    'records':observer.records,
}))
"""


def _observe(root: Path, addopts: str, source: str) -> dict:
    (root / "pytest.ini").write_text(f"[pytest]\naddopts = {addopts}\n")
    (root / "test_case.py").write_text(source)
    environment = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": ""}
    completed = subprocess.run(
        [sys.executable, "-c", OBSERVE_SCRIPT, str(Path(target_pytest.__file__).resolve())],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads((root / "observation.json").read_text())


@pytest.mark.parametrize("addopts", ["-k keep", "--deselect=test_case.py::test_drop"])
def test_native_addopts_deselection_does_not_require_removed_tests(tmp_path: Path, addopts: str) -> None:
    observation = _observe(tmp_path, addopts, "def test_keep(): pass\ndef test_drop(): pass\n")
    assert observation["exit_code"] == 0
    assert observation["collected"] == ["test_case.py::test_keep"]
    assert observation["deselected"] == ["test_case.py::test_drop"]
    assert {row["nodeid"] for row in observation["records"] if row["phase"] == "call"} == set(observation["collected"])


def test_final_native_inventory_honors_plugin_collection_changes(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text(
        "def pytest_collection_modifyitems(items):\n"
        "    items[:] = [item for item in items if item.name == 'test_keep']\n"
    )
    observation = _observe(tmp_path, "", "def test_keep(): pass\ndef test_drop(): pass\n")
    assert observation["exit_code"] == 0
    assert observation["collected"] == ["test_case.py::test_keep"]
    assert observation["deselected"] == ["test_case.py::test_drop"]


def test_interrupted_native_run_retains_unexecuted_selected_items(tmp_path: Path) -> None:
    observation = _observe(tmp_path, "-x", "def test_first(): assert False\ndef test_later(): pass\n")
    assert observation["exit_code"] == 1
    assert observation["collected"] == ["test_case.py::test_first", "test_case.py::test_later"]
    assert observation["deselected"] == []
    assert {row["nodeid"] for row in observation["records"] if row["phase"] == "call"} == {"test_case.py::test_first"}


@pytest.mark.parametrize("local_finish_first", [True, False])
def test_final_inventory_preserves_distributed_selected_items(local_finish_first: bool) -> None:
    observer = target_pytest.Observer()
    session = SimpleNamespace(items=[])
    if local_finish_first:
        observer.pytest_collection_finish(session)
    observer.pytest_xdist_node_collection_finished(None, ["test_case.py::test_keep"])
    observer.pytest_xdist_node_collection_finished(None, ["test_case.py::test_keep"])
    if not local_finish_first:
        observer.pytest_collection_finish(session)
    assert observer.collected == {"test_case.py::test_keep"}
    assert not observer.deselected


def test_empty_distributed_selection_has_controller_only_deselection_inventory() -> None:
    observer = target_pytest.Observer()
    observer.pytest_xdist_node_collection_finished(None, [])
    assert not observer.collected
    assert observer.deselection_inventory == "controller_observed"
