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
        "pytest " + HOST_PROOF + " {args} && pytest tests "
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
    assert calls[0] == [module.sys.executable, "-m", "pytest", HOST_PROOF, "-n", "0"]
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
