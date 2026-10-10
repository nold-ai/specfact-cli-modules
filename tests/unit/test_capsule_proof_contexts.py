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

    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert (
        "pytest "
        + HOST_PROOF
        + " tests/native/proof_native_canonical_path.py "
        + CONTROLLER_SHELL_PROOF
        + " && pytest tests "
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
        CONTROLLER_SHELL_PROOF,
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
    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["native-boundary"]
    assert {row["runner"] for row in job["strategy"]["matrix"]["include"]} == {"macos-14", "macos-15", "macos-26"}
    recipes = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert NATIVE_PARSER in recipes
    for option in ("--self-test", "--failure-self-test", "--exception-self-test"):
        assert NATIVE_BROKER + " " + option in recipes
    assert "scripts/check_macos_boundary_ci_receipts.py" in recipes
    assert '"--repetitions", "100"' in (ROOT / "scripts/check_macos_boundary_ci_receipts.py").read_text(
        encoding="utf-8"
    )
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
    workflow = yaml.safe_load((ROOT / ".github/workflows/native-capsule-release.yml").read_text(encoding="utf-8"))
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
    (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n", encoding="utf-8")
    assert native_failure_summary(tmp_path, "3.11") == {
        "abi": "3.11",
        "case": "python-clean",
        "phase": "request-wait",
        "state": state,
    }
    raw["failed_case"] = "/private/untrusted"
    (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n", encoding="utf-8")
    assert native_failure_summary(tmp_path, "3.11") == {"abi": "3.11"}
    raw["failed_case"] = "python-clean"
    raw["last_worker_state"]["wait_pending"] = 1
    (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n", encoding="utf-8")
    assert native_failure_summary(tmp_path, "3.11") == {"abi": "3.11", "case": "python-clean", "phase": "request-wait"}


def test_native_failure_projection_rejects_non_scalar_identity(tmp_path):
    import json

    from tests.native.proof_python_candidate_matrix import native_failure_summary

    for field in ("failed_case", "failure_phase"):
        raw: dict[str, object] = {"failed_case": "python-clean", "failure_phase": "request-wait"}
        raw[field] = []
        (tmp_path / "diagnostics.log").write_text(json.dumps(raw) + "\n", encoding="utf-8")
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
    (root / "diagnostics.log").write_text(json.dumps(marker), encoding="utf-8")


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

    workflow = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text(encoding="utf-8"))
    step = next(item for item in workflow["jobs"]["changes"]["steps"] if item.get("id") == "filter")
    paths = yaml.safe_load(step["with"]["filters"])["capsule"]
    assert any(fnmatchcase(path, pattern) for pattern in paths)
    assert not any(fnmatchcase("tests/unit/specfact_project/unrelated.py", pattern) for pattern in paths)
    customer = workflow["jobs"]["customer-capsules"]
    assert "needs.changes.outputs.capsule_changed" in customer["if"]
    assert not customer.get("continue-on-error", False)


@pytest.mark.parametrize("surface", ["full", "smart", "native_ci", "discovery"])
def test_compiled_canonical_proofs_have_required_compiler_context(surface):
    assertions = {
        "full": _assert_canonical_full,
        "smart": _assert_canonical_smart,
        "native_ci": _assert_canonical_native_ci,
        "discovery": _assert_canonical_discovery,
    }
    assertions[surface]("tests/native/proof_native_canonical_path.py")


def _assert_canonical_full(proof):
    import tomllib

    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    command = configuration["tool"]["hatch"]["envs"]["default"]["scripts"]["test"]
    assert "pytest " + HOST_PROOF + " " + proof + " " + CONTROLLER_SHELL_PROOF + " && pytest tests " in command


def _assert_canonical_smart(proof):
    assert '"' + proof + '"' in (ROOT / "tools/smart_test_coverage.py").read_text(encoding="utf-8")


def _assert_canonical_native_ci(proof):
    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text(encoding="utf-8"))
    for name in ("native-boundary", "canonical-linux"):
        job = workflow["jobs"][name]
        assert not job.get("continue-on-error", False) and "if" not in job
        assert proof in "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert workflow["jobs"]["canonical-linux"]["runs-on"] == "ubuntu-24.04"


def _assert_canonical_discovery(proof):
    assert (ROOT / proof).is_file()
    plan = ProjectPlan(ROOT, manager="hatch", pytest_config={"testpaths": ["tests"], "python_files": ["test_*.py"]})
    portable = ROOT / "tests/unit/test_native_analyzer_inputs.py"
    assert select_test_paths(plan, [portable, ROOT / proof], full=False) == (portable.relative_to(ROOT).as_posix(),)
    assert not (ROOT / "tests/unit/test_native_canonical_path.py").exists()


@pytest.fixture(name="indexed_review")
def indexed_workflow_fixture(monkeypatch):
    import copy

    from scripts import check_capsule_deferral as checker

    names = ("pr-orchestrator", "capsule-customer-execution")
    indexed = {
        name: checker._yaml_mapping((ROOT / f".github/workflows/{name}.yml").read_text(encoding="utf-8"))
        for name in names
    }
    baseline = copy.deepcopy(indexed)
    calls = []

    def read_git(command, *, text):
        assert command[:2] == ["git", "show"] and text is True
        revision, path = command[2].split(":", 1)
        assert revision in ("", "baseline")
        name = Path(path).stem
        calls.append((revision, name))
        return yaml.safe_dump((baseline if revision else indexed)[name], sort_keys=False)

    monkeypatch.setattr(checker.subprocess, "check_output", read_git)
    return checker, indexed, baseline, calls


def test_portable_indexed_validator_reads_both_trees_and_admits_exact_execution(indexed_review):
    checker, _indexed, _baseline, calls = indexed_review
    paths = ["scripts/check_capsule_deferral.py"]
    checker.validate_indexed_scheduling(paths, paths, "baseline")
    assert set(calls) == {
        (revision, name) for revision in ("", "baseline") for name in ("pr-orchestrator", "capsule-customer-execution")
    }


@pytest.mark.parametrize("case", ["event", "caller", "consumer", "detector", "candidate", "independent", "budget"])
def test_portable_indexed_validator_rejects_execution_changes(indexed_review, case):
    checker, indexed, _baseline, _calls = indexed_review
    workflow = indexed["pr-orchestrator"]
    jobs = workflow["jobs"]
    mutations = {
        "event": lambda: workflow["on"].update(pull_request={"types": ["closed"]}),
        "caller": lambda: jobs["customer-capsules"].update(env={}),
        "consumer": lambda: jobs["quality"].update(needs=["changes"]),
        "detector": lambda: jobs["changes"].update(**{"runs-on": "macos-14"}),
        "candidate": lambda: indexed["capsule-customer-execution"]["jobs"]["customer"].update(
            **{"runs-on": "macos-14"}
        ),
        "independent": lambda: indexed["capsule-customer-execution"]["jobs"]["independent-review"].update(
            **{"continue-on-error": True}
        ),
        "budget": lambda: checker._unique_step(
            indexed["capsule-customer-execution"]["jobs"]["independent-review"], "independent_review"
        ).update(run="exit 0"),
    }
    mutations[case]()
    with pytest.raises(ValueError):
        checker.validate_indexed_scheduling(
            ["scripts/check_capsule_deferral.py"], ["scripts/check_capsule_deferral.py"], "baseline"
        )


@pytest.mark.parametrize("source", ["on: {}\non: {}", "[]", "on: {true: 1, true: 2}"])
def test_portable_indexed_parser_rejects_ambiguous_mappings(source):
    from scripts import check_capsule_deferral as checker

    with pytest.raises(ValueError):
        checker._yaml_mapping(source)


@pytest.mark.parametrize("paths", [[], ["tools/unrelated.py"], ["scripts/uncovered.py"]])
def test_portable_indexed_validator_rejects_uncovered_surface(indexed_review, paths):
    checker, _indexed, _baseline, _calls = indexed_review
    with pytest.raises(ValueError):
        checker.validate_indexed_scheduling(paths, paths, "baseline")


@pytest.mark.parametrize("inherited_destination", [False, True])
def test_portable_review_source_policy_measures_scripts(tmp_path, monkeypatch, inherited_destination):
    import json
    import os
    import subprocess
    import sys
    import tomllib

    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["coverage"]["run"]
    monkeypatch.chdir(tmp_path)
    for name in ("src", "packages", "tools", "scripts"):
        (tmp_path / name).mkdir()
    if inherited_destination:
        blocked = tmp_path / "not-a-directory"
        blocked.write_text("owned blocker", encoding="utf-8")
        monkeypatch.setenv("COVERAGE_FILE", str(blocked / "collector"))
    script = tmp_path / "scripts/check_capsule_deferral.py"
    script.write_text("def validate():\n    return True\n\nassert validate()\n", encoding="utf-8")
    probe = """import coverage, json, runpy, sys
from pathlib import Path
script = Path(sys.argv[1])
collector = coverage.Coverage(source=json.loads(sys.argv[2]), branch=True, data_file=None, config_file=False)
collector.start()
try:
    runpy.run_path(str(script))
finally:
    collector.stop()
assert str(script) in collector.get_data().measured_files(), "reviewed script excluded from evidence"
assert collector.analysis2(str(script))[3] == []
"""
    result = subprocess.run(
        [sys.executable, "-c", probe, str(script), json.dumps(configuration["source"])],
        env={key: value for key, value in os.environ.items() if key != "COVERAGE_FILE"},
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "case",
    [
        "root_key",
        "conditional",
        "duplicate_step",
        "output",
        "filter_impl",
        "negative_rule",
        "baseline_rule",
        "call_event",
        "python_matrix",
        "branches",
        "ignore",
        "caller_dependency",
    ],
)
def test_portable_validator_rejects_additional_scheduling_breaks(indexed_review, case):
    checker, indexed, _baseline, _calls = indexed_review
    orchestration = indexed["pr-orchestrator"]
    changes = orchestration["jobs"]["changes"]
    filter_step = checker._unique_step(changes, "filter")
    reusable = indexed["capsule-customer-execution"]
    mutations = {
        "root_key": lambda: orchestration.update(unsupported=True),
        "conditional": lambda: changes.update(**{"if": "false"}),
        "duplicate_step": lambda: changes["steps"].append(filter_step.copy()),
        "output": lambda: changes["outputs"].update(capsule_changed="false"),
        "filter_impl": lambda: filter_step.update(uses="unverified/filter@v1"),
        "negative_rule": lambda: filter_step["with"].update(filters="capsule: ['!**']"),
        "baseline_rule": lambda: filter_step["with"].update(filters="capsule: ['scripts/check_capsule_deferral.py']"),
        "call_event": lambda: reusable["on"].pop("workflow_call"),
        "python_matrix": lambda: reusable["jobs"]["customer"]["strategy"]["matrix"].update(python=["3.11"]),
        "branches": lambda: orchestration["on"].update(pull_request={"branches": ["main"]}),
        "ignore": lambda: orchestration["on"].update(pull_request={"paths-ignore": ["**"]}),
        "caller_dependency": lambda: orchestration["jobs"]["customer-capsules"].update(needs=[]),
    }
    mutations[case]()
    with pytest.raises(ValueError):
        checker.validate_indexed_scheduling(
            ["scripts/check_capsule_deferral.py"], ["scripts/check_capsule_deferral.py"], "baseline"
        )


def test_portable_validator_admits_review_surface_exemptions_and_budget_adaptation(indexed_review):
    checker, indexed, baseline, _calls = indexed_review
    for tree in (indexed, baseline):
        tree["pr-orchestrator"]["on"]["pull_request"] = None
    step = checker._unique_step(
        baseline["capsule-customer-execution"]["jobs"]["independent-review"], "independent_review"
    )
    prefix, suffix = step["run"].rsplit("subprocess.run(sys.argv[1:],timeout=1800,check=False)", 1)
    step["run"] = prefix + "subprocess.run(sys.argv[1:],timeout=300,check=False)" + suffix
    paths = ["packages/specfact-code-review/src/app.py"]
    candidate = [
        *paths,
        "TDD_EVIDENCE.md",
        "README.md",
        "openspec/changes/code-review-native-platform-execution/spec.md",
    ]
    checker.validate_indexed_scheduling(paths, candidate, "baseline")


@pytest.mark.parametrize("candidate", [["docs/guide.md"], ["scripts/check_capsule_deferral.py", "tools/unrelated.py"]])
def test_portable_validator_rejects_excluded_or_unreviewed_delta(indexed_review, candidate):
    checker, indexed, _baseline, _calls = indexed_review
    indexed["pr-orchestrator"]["on"]["pull_request"] = {"paths-ignore": ["**/*.md", "docs/**"]}
    with pytest.raises(ValueError):
        checker.validate_indexed_scheduling(["scripts/check_capsule_deferral.py"], candidate, "baseline")


@pytest.mark.parametrize("valid", [True, False])
def test_portable_validator_main_preserves_failure_exit(indexed_review, monkeypatch, capsys, valid):
    checker, _indexed, _baseline, _calls = indexed_review
    args = ["checker", "scripts/check_capsule_deferral.py", "scripts/check_capsule_deferral.py", "baseline"]
    monkeypatch.setattr(checker.sys, "argv", args if valid else ["checker"])
    assert checker.main() == (0 if valid else 1)
    output = capsys.readouterr()
    assert bool(output.err) is not valid
    assert "PRIVATE" not in output.err


@pytest.mark.parametrize("setup_seconds", [0, 120, 480])
def test_independent_job_can_complete_both_maximum_legal_phases(setup_seconds):
    import re

    workflow = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["independent-review"]
    review = next(step for step in job["steps"] if step.get("id") == "independent_review")
    phase_limits = [int(value) for value in re.findall(r"timeout=(\d+),check=False", review["run"])]
    assert phase_limits == [1800, 1800], "Preparation and review keep their independent finite caps"
    completion_seconds = setup_seconds + sum(phase_limits) + 60
    assert completion_seconds < job["timeout-minutes"] * 60, "Legal preparation must not truncate legal review"
    assert job["timeout-minutes"] * 60 - sum(phase_limits) == 15 * 60
    assert workflow["jobs"]["customer"]["timeout-minutes"] == 90


@pytest.mark.parametrize("job_minutes,accepted", [(75, True), (45, False), (60, False), (90, False)])
def test_portable_validator_admits_only_complete_approved_job_budget(indexed_review, job_minutes, accepted):
    checker, indexed, baseline, _calls = indexed_review
    baseline["capsule-customer-execution"]["jobs"]["independent-review"]["timeout-minutes"] = 45
    indexed["capsule-customer-execution"]["jobs"]["independent-review"]["timeout-minutes"] = job_minutes
    paths = ["scripts/check_capsule_deferral.py"]
    if accepted:
        checker.validate_indexed_scheduling(paths, paths, "baseline")
    else:
        with pytest.raises(ValueError):
            checker.validate_indexed_scheduling(paths, paths, "baseline")


CONTROLLER_SHELL_PROOF = "tests/host/proof_capsule_review_projection_shell.py"


@pytest.mark.parametrize("surface", ["full", "smart", "native_ci", "discovery", "trigger"])
def test_controller_shell_proofs_have_required_host_context(surface):
    checks = {
        "full": _assert_controller_shell_full,
        "smart": _assert_controller_shell_smart,
        "native_ci": _assert_controller_shell_ci,
        "discovery": _assert_controller_shell_discovery,
        "trigger": _assert_controller_shell_trigger,
    }
    checks[surface]()


def _assert_controller_shell_full():
    import tomllib

    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    command = configuration["tool"]["hatch"]["envs"]["default"]["scripts"]["test"]
    assert CONTROLLER_SHELL_PROOF + " && pytest tests " in command


def _assert_controller_shell_smart():
    assert '"' + CONTROLLER_SHELL_PROOF + '"' in (ROOT / "tools/smart_test_coverage.py").read_text(encoding="utf-8")


def _assert_controller_shell_ci():
    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text(encoding="utf-8"))
    for job_name in ("canonical-linux", "native-boundary"):
        job = workflow["jobs"][job_name]
        assert not job.get("continue-on-error", False) and "if" not in job
        assert CONTROLLER_SHELL_PROOF in "\n".join(str(step.get("run", "")) for step in job["steps"])


def _assert_controller_shell_discovery():
    assert (ROOT / CONTROLLER_SHELL_PROOF).is_file()
    plan = ProjectPlan(ROOT, manager="hatch", pytest_config={"testpaths": ["tests"], "python_files": ["test_*.py"]})
    portable = ROOT / "tests/unit/test_capsule_proof_contexts.py"
    assert select_test_paths(plan, [portable, ROOT / CONTROLLER_SHELL_PROOF], full=False) == (
        portable.relative_to(ROOT).as_posix(),
    )


def _assert_controller_shell_trigger():
    workflow = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text(encoding="utf-8"))
    filter_step = next(step for step in workflow["jobs"]["changes"]["steps"] if step.get("id") == "filter")
    assert CONTROLLER_SHELL_PROOF in yaml.safe_load(filter_step["with"]["filters"])["capsule"]


def test_controller_import_isolation_proof_has_no_complexity_warning():
    from radon.complexity import cc_visit

    from specfact_code_review.tools.radon_runner import _allowed_paths, _map_radon_complexity_findings

    host = ROOT / CONTROLLER_SHELL_PROOF
    path = host if host.exists() else ROOT / "tests/unit/test_capsule_review_projection.py"
    blocks = [
        {"name": block.name, "lineno": block.lineno, "complexity": block.complexity}
        for block in cc_visit(path.read_text(encoding="utf-8"))
        if host.exists() or block.name == "test_actual_projector_launch_excludes_untrusted_imports"
    ]
    findings = _map_radon_complexity_findings({str(path): blocks}, _allowed_paths([path]))
    assert findings == [], [(finding.rule, finding.message) for finding in findings]
