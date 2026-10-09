"""Keep every proof in a required executable context without altering capsule policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

from specfact_code_review.run.portable_worker import select_test_paths
from specfact_code_review.run.runtime_models import ProjectPlan


ROOT = Path(__file__).resolve().parents[2]
HOST_PROOF = "tests/host/proof_capsule_deferred_review_ci.py"
NATIVE_PARSER = "tests/native/proof_macos_managed_uv_child.py"
NATIVE_BROKER = "tests/native/proof_macos_native_broker_wait.py"


def test_full_and_smart_host_runs_require_the_retained_host_proof(monkeypatch):
    import tomllib

    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert (
        "pytest " + HOST_PROOF + " tests/native/proof_native_canonical_path.py && pytest tests "
        in configuration["tool"]["hatch"]["envs"]["default"]["scripts"]["test"]
    )
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("context_smart_test", ROOT / "tools/smart_test_coverage.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, **_kwargs: (
            calls.append(command) or type("Result", (), {"returncode": 0 if len(calls) == 1 else 7})()
        ),
    )
    assert module._run_pytest(["-n", "0"]) == 7
    assert calls[0] == [
        module.sys.executable,
        "-m",
        "pytest",
        HOST_PROOF,
        "tests/native/proof_native_canonical_path.py",
    ]
    assert calls[1][:4] == [module.sys.executable, "-m", "pytest", "tests"]
    assert calls[1][-2:] == ["-n", "0"]
    assert set(calls[1][4:-2]) == {
        "--ignore=tests/unit/test_capsule_deferred_review_ci.py",
        "--ignore=tests/unit/test_macos_managed_uv_child.py",
        "--ignore=tests/unit/test_macos_native_broker_wait.py",
        "--ignore=tests/unit/test_macos_python_candidate.py",
    }


def test_native_parser_and_broker_proofs_remain_required_on_every_os():
    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text())
    job = workflow["jobs"]["native-boundary"]
    assert {row["runner"] for row in job["strategy"]["matrix"]["include"]} == {"macos-14", "macos-15", "macos-26"}
    recipes = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert NATIVE_PARSER in recipes
    for option in ("--self-test", "--failure-self-test", "--exception-self-test"):
        assert NATIVE_BROKER + " " + option in recipes
    assert "scripts/check_macos_boundary_ci_receipts.py" in recipes
    assert '"--repetitions", "100"' in (ROOT / "scripts/check_macos_boundary_ci_receipts.py").read_text()
    assert not job.get("continue-on-error", False)


def test_explicit_proof_modules_do_not_enter_default_capsule_selection():
    proofs = [ROOT / name for name in (HOST_PROOF, NATIVE_PARSER, NATIVE_BROKER)]
    assert all(path.is_file() for path in proofs)
    assert all(not (ROOT / "tests" / context / "__init__.py").exists() for context in ("host", "native", "support"))
    portable = ROOT / "tests/unit/test_native_analyzer_inputs.py"
    plan = ProjectPlan(ROOT, manager="hatch", pytest_config={"testpaths": ["tests"], "python_files": ["test_*.py"]})
    assert select_test_paths(plan, [portable, *proofs], full=False) == (portable.relative_to(ROOT).as_posix(),)
    with pytest.raises(ValueError, match="project_test_selection_empty"):
        select_test_paths(plan, proofs, full=False)


def test_all_three_python_native_inputs_are_required_in_the_secret_free_job():
    workflow = yaml.safe_load((ROOT / ".github/workflows/native-capsule-release.yml").read_text())
    job = workflow["jobs"]["tools"]
    recipes = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert "tests/native/proof_python_candidate_matrix.py" in recipes
    assert "for abi in cp311 cp312 cp313" in recipes
    assert "proof-work-$abi" in recipes
    assert 'cd "$RUNNER_TEMP/proof-work-$abi"' in recipes
    assert "SPECFACT_CPYTHON_CANDIDATE_INPUTS" in recipes
    assert all(version in recipes for version in ("3.11", "3.12", "3.13"))
    assert not job.get("continue-on-error", False)
    assert "environment" not in job
    assert "secrets." not in recipes


def test_native_failure_projection_contains_only_fixed_case_and_boolean_state(tmp_path):
    import json

    from tests.native.proof_python_candidate_matrix import native_failure_summary

    state = {"wait_accepted": True, "wait_pending": False, "worker_reaped": True, "output_closed": True}
    raw = {
        "failed_case": "python-clean",
        "failure_phase": "request-wait",
        "last_worker_state": state,
        "diagnostic": "/private/raw",
        "failure_origin": True,
        "pid": 123,
    }
    (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n")
    assert native_failure_summary(tmp_path, "3.11") == {
        "abi": "3.11",
        "case": "python-clean",
        "phase": "request-wait",
        "state": state,
    }
    raw["failed_case"] = "/private/untrusted"
    (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n")
    assert native_failure_summary(tmp_path, "3.11") == {"abi": "3.11"}
    raw["failed_case"] = "python-clean"
    raw["last_worker_state"]["wait_pending"] = 1
    (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n")
    assert native_failure_summary(tmp_path, "3.11") == {"abi": "3.11", "case": "python-clean", "phase": "request-wait"}


def test_native_failure_projection_rejects_non_scalar_identity(tmp_path):
    import json

    from tests.native.proof_python_candidate_matrix import native_failure_summary

    for field in ("failed_case", "failure_phase"):
        raw: dict[str, object] = {"failed_case": "python-clean", "failure_phase": "request-wait"}
        raw[field] = []
        (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n")
        assert native_failure_summary(tmp_path, "3.11") == {"abi": "3.11"}
    assert native_failure_summary(tmp_path, "/private/value") == {}


def _result_fixture():
    history = [{"opcode": 1, "response": {"handle": 9, "pid": 321}}, {"opcode": 2, "fields": {"handle": 9}}]
    fields = {
        "stage": "output_encoding",
        "worker_exited": True,
        "worker_signalled": False,
        "entry_marker_present": True,
    }
    return history, fields


def _write_result_marker(root, fields):
    import json

    marker = {
        "failed_case": "python-clean",
        "failure_phase": "request-wait",
        "last_worker_result": fields,
        "raw": "/private/value",
    }
    (root / "diagnostics.log").write_text(json.dumps(marker))


def test_native_result_projection_requires_matching_worker(tmp_path):
    import json

    from scripts.macos_managed_boundary.control import STATE
    from tests.native.proof_python_candidate_matrix import native_failure_summary

    history, fields = _result_fixture()
    events = json.dumps({"control_result": 321, **fields, "raw": "/private/value"})
    assert STATE.wait_observations(events, history, "request-wait") == {"last_worker_result": fields}
    assert STATE.last_worker_result(events, history, "request-wait") == fields
    assert STATE.last_worker_result(events, history, "request-launch") == {}
    assert STATE.last_worker_result(events.replace("321", "999"), history, "request-wait") == {}
    _write_result_marker(tmp_path, fields)
    assert native_failure_summary(tmp_path, "3.11") == {
        "abi": "3.11",
        "case": "python-clean",
        "phase": "request-wait",
        "result": fields,
    }


def test_native_result_projection_rejects_unknown_stages_and_nonboolean_fields(tmp_path):
    import json

    from scripts.macos_managed_boundary.control import STATE
    from tests.native.proof_python_candidate_matrix import native_failure_summary

    history, fields = _result_fixture()
    for invalid in ({**fields, "stage": "/private/value"}, {**fields, "stage": []}, {**fields, "worker_exited": 1}):
        _write_result_marker(tmp_path, invalid)
        assert native_failure_summary(tmp_path, "3.11") == {
            "abi": "3.11",
            "case": "python-clean",
            "phase": "request-wait",
        }
        assert STATE.last_worker_result(json.dumps({"control_result": 321, **invalid}), history, "request-wait") == {}
    assert STATE.last_worker_result("[" * 4000, history, "request-wait") == {}


def test_native_output_class_projection_rejects_unknown_payloads():
    from scripts.macos_managed_boundary.control import STATE

    _, fields = _result_fixture()
    for kind in (
        "profile_initialization",
        "python_initialization",
        "python_path_configuration",
        "loader",
        "unclassified",
    ):
        classified = {**fields, "output_class": kind}
        assert STATE.project_worker_result({**classified, "raw": "/private/value"}) == classified
    for payload in ("/private/value", [], False):
        assert STATE.project_worker_result({**fields, "output_class": payload}) == {}


@pytest.mark.parametrize(
    "path",
    [
        NATIVE_BROKER,
        "tests/unit/test_native_broker_cleanup.py",
        "tests/unit/specfact_code_review/run/test_native_project_runtime.py",
    ],
)
def test_proof_only_changes_schedule_blocking_customer_review(path):
    from fnmatch import fnmatchcase

    workflow = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    step = next(item for item in workflow["jobs"]["changes"]["steps"] if item.get("id") == "filter")
    paths = yaml.safe_load(step["with"]["filters"])["capsule"]
    assert any(fnmatchcase(path, pattern) for pattern in paths)
    assert not any(fnmatchcase("tests/unit/specfact_project/unrelated.py", pattern) for pattern in paths)
    customer = workflow["jobs"]["customer-capsules"]
    assert "needs.changes.outputs.capsule_changed" in customer["if"]
    assert not customer.get("continue-on-error", False)


@pytest.mark.parametrize("surface", ["full", "smart", "native_ci", "discovery"])
def test_compiled_canonical_proofs_have_required_compiler_context(surface):
    proof = "tests/native/proof_native_canonical_path.py"
    if surface == "full":
        import tomllib

        configuration = tomllib.loads((ROOT / "pyproject.toml").read_text())
        command = configuration["tool"]["hatch"]["envs"]["default"]["scripts"]["test"]
        assert "pytest " + HOST_PROOF + " " + proof + " && pytest tests " in command
    elif surface == "smart":
        assert '"' + proof + '"' in (ROOT / "tools/smart_test_coverage.py").read_text()
    elif surface == "native_ci":
        workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text())
        for name in ("native-boundary", "canonical-linux"):
            job = workflow["jobs"][name]
            assert not job.get("continue-on-error", False) and "if" not in job
            assert proof in "\n".join(str(step.get("run", "")) for step in job["steps"])
        assert workflow["jobs"]["canonical-linux"]["runs-on"] == "ubuntu-24.04"
    else:
        assert (ROOT / proof).is_file()
        plan = ProjectPlan(ROOT, manager="hatch", pytest_config={"testpaths": ["tests"], "python_files": ["test_*.py"]})
        portable = ROOT / "tests/unit/test_native_analyzer_inputs.py"
        assert select_test_paths(plan, [portable, ROOT / proof], full=False) == (portable.relative_to(ROOT).as_posix(),)
        assert not (ROOT / "tests/unit/test_native_canonical_path.py").exists()
