from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from scripts.native_release.platforms import REQUIRED_CHECKS
from specfact_code_review.run.portable_worker import select_test_paths
from specfact_code_review.run.runtime_models import ProjectPlan
from tests.unit.native_release.test_workflow_inputs import _schedules_native


ROOT = Path(__file__).resolve().parents[3]
PROOF = "tests/native/proof_native_execution.py"
UNIT = "tests/unit/specfact_code_review/run/test_native_execution.py"
CORPUS = "tests/fixtures/native-execution-proof/corpus.json"


def _functions(path: Path) -> dict[str, ast.FunctionDef]:
    if not path.is_file():
        return {}
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if getattr(node, "type_params", None) == []:
            del node.type_params
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def _dump(node: ast.AST) -> str:
    options = {"show_empty": True} if sys.version_info >= (3, 13) else {}
    return ast.dump(node, include_attributes=False, **options)


def _direct_calls(statements: list[ast.stmt]) -> dict[int, ast.Call]:
    return {
        index: node.value
        for index, node in enumerate(statements)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    }


@pytest.fixture
def corpus() -> dict:
    return json.loads((ROOT / CORPUS).read_text())


def test_explicit_owner_preserves_every_original_physical_definition(corpus):
    expected = corpus["physical_function_asts"]
    definitions = _functions(ROOT / PROOF)
    observed = {name: _dump(node) for name, node in definitions.items() if name.startswith("test_")}
    assert observed == expected, (
        f"Physical proof definitions differ: observed={sorted(observed)}, expected={sorted(expected)}"
    )


def test_portable_definitions_and_collected_inventory_remain_intact(corpus):
    definitions = _functions(ROOT / UNIT)
    expected = corpus["portable_function_asts"]
    observed = {name: _dump(definitions[name]) for name in expected if name in definitions}
    assert observed == expected
    assert "request" in definitions
    assert corpus["collections"]["1"]["portable"] == corpus["collections"]["100"]["portable"]
    assert len(corpus["collections"]["1"]["physical"]) == 9
    assert len(corpus["collections"]["100"]["physical"]) == 702
    assert len(set(corpus["collections"]["100"]["physical"])) == 702


def test_frozen_pid_consumers_keep_the_real_shared_alias(corpus):
    from tests.native.proof_macos_native_broker_wait import wait_worker_pid
    from tests.unit.specfact_code_review.run.test_native_execution import _worker_pid

    assert _worker_pid is wait_worker_pid
    for path, expected in corpus["frozen_file_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path


def test_actual_portable_selection_never_owns_physical_functions(corpus):
    plan = ProjectPlan(ROOT, manager="hatch", pytest_config={"testpaths": ["tests"], "python_files": ["test_*.py"]})
    selected = select_test_paths(plan, [ROOT / UNIT, ROOT / PROOF], full=False)
    assert selected == (UNIT,)
    leaked = {path: sorted(set(_functions(ROOT / path)) & set(corpus["physical_function_asts"])) for path in selected}
    assert not any(leaked.values()), f"Physical functions still enter portable selection: {leaked}"
    with pytest.raises(ValueError, match="project_test_selection_empty"):
        select_test_paths(plan, [ROOT / PROOF], full=False)


def test_acceptance_requires_proof_inside_runtime_before_receipt():
    candidate = _functions(ROOT / "scripts/native_release/acceptance.py")["candidate_acceptance"]
    runtime = next(node for node in candidate.body if isinstance(node, ast.With))
    direct_calls = list(_direct_calls(runtime.body).values())
    names = [ast.unparse(call.func) for call in direct_calls]
    assert "require_native_execution_proof" in names, f"Unconditional runtime calls lack physical proof: {names}"
    proof = direct_calls[names.index("require_native_execution_proof")]
    assert ast.unparse(proof.args[0]) == "runtime.root"
    assert names.index("delivered_boundary") < names.index("require_native_execution_proof")
    receipts = [
        index
        for index, call in _direct_calls(candidate.body).items()
        if ast.unparse(call.func) == "write_candidate_receipt"
    ]
    assert len(receipts) == 1 and receipts[0] > candidate.body.index(runtime)
    assert not any(isinstance(node, ast.Try) for node in ast.walk(candidate)), "Proof failures must reach the caller"


def test_release_receipts_require_native_execution():
    assert "native_execution" in REQUIRED_CHECKS, f"Release receipt checks omit physical execution: {REQUIRED_CHECKS}"


def test_all_physical_proof_inputs_schedule_native_acceptance():
    paths = [
        PROOF,
        CORPUS,
        UNIT,
        "tests/unit/test_capsule_proof_contexts.py",
        "tests/unit/native_release/test_physical_proof_ownership.py",
        "scripts/native_release/native_execution_proof.py",
    ]
    missing = [path for path in paths if not _schedules_native(path)]
    assert missing == [], f"Changed proof inputs do not schedule native acceptance: {missing}"


def test_existing_nine_cell_matrix_and_acceptance_remain_required():
    workflow = yaml.safe_load((ROOT / ".github/workflows/native-capsule-release.yml").read_text())
    execute = workflow["jobs"]["execute"]
    assert execute["strategy"]["matrix"]["runner"] == ["macos-14", "macos-15", "macos-26"]
    assert execute["strategy"]["matrix"]["python"] == ["3.11", "3.12", "3.13"]
    assert execute["timeout-minutes"] == 60
    assert not execute.get("continue-on-error", False)
    steps = [
        step for step in execute["steps"] if "scripts.native_release.acceptance --mode candidate" in step.get("run", "")
    ]
    assert len(steps) == 1 and not steps[0].get("if") and not steps[0].get("continue-on-error", False)
    assert workflow["jobs"]["sign-and-stage"]["needs"] == "execute"
