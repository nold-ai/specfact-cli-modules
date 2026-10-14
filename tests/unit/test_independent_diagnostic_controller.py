"""Exercise the inline diagnostic controller with controlled download bytes."""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
MARKER = "PY_DIAGNOSTIC_BOOTSTRAP"


@pytest.mark.parametrize("download", [b"print('SECRET_DOWNLOADED')", OSError("SECRET_NETWORK")])
def test_controller_rejects_unverified_bytes_before_execution(tmp_path, monkeypatch, capsys, download):
    import urllib.request

    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("name") == "Observe failed independent review privately")
    trusted = tmp_path / "trusted"
    (trusted / "venv/bin").mkdir(parents=True)
    (trusted / "venv/bin/python").symlink_to(sys.executable)
    (trusted / "review-attempted").touch()
    candidate = tmp_path / "candidate"
    (candidate / "scripts").mkdir(parents=True)
    (candidate / "scripts/independent_review_diagnostic.py").write_text("print('SECRET_CANDIDATE')\n")
    assert MARKER in step["run"]

    def fetch(*_args, **_kwargs):
        if isinstance(download, OSError):
            raise download
        return io.BytesIO(download)

    executions = []
    monkeypatch.setattr(urllib.request, "urlopen", fetch)
    monkeypatch.setattr(os, "execve", lambda *_args: executions.append(True))
    monkeypatch.setattr(sys, "argv", ["-", str(trusted), str(candidate)])
    source = step["run"].split(f"<<'{MARKER}'\n", 1)[1].rsplit(MARKER, 1)[0]
    with pytest.raises(SystemExit) as stopped:
        exec(compile(source, "reviewed-controller", "exec"), {"__name__": "__main__"})
    assert stopped.value.code == 0
    assert executions == []
    output = capsys.readouterr()
    assert "SECRET" not in output.out + output.err
    assert json.loads(output.out)["status"] == "DIAGNOSTIC_UNAVAILABLE"


def test_controller_runs_after_both_projections_with_optional_cap():
    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    diagnostic = next(item for item in steps if item.get("name") == "Observe failed independent review privately")
    projection = next(item for item in steps if item.get("name") == "Project independent review failure privately")
    assert steps.index(diagnostic) > steps.index(projection)
    assert diagnostic["timeout-minutes"] == 15
    assert "github.event.pull_request.head.sha == '826948e710112a80b61c31c46ec8e57da5a25f22'" in diagnostic["if"]
    assert "$GITHUB_WORKSPACE/scripts/independent_review_diagnostic.py" not in diagnostic["run"]


def test_controller_executes_only_authenticated_private_copy(tmp_path, monkeypatch):
    import urllib.request

    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("name") == "Observe failed independent review privately")
    payload = (ROOT / "scripts/independent_review_diagnostic.py").read_bytes()
    urls = []

    def fetch(url, **_kwargs):
        urls.append(url)
        return io.BytesIO(payload)

    executions = []
    monkeypatch.setattr(urllib.request, "urlopen", fetch)
    monkeypatch.setattr(os, "execve", lambda *args: executions.append(args))
    monkeypatch.setattr(sys, "argv", ["-", str(tmp_path), "/candidate"])
    source = step["run"].split(f"<<'{MARKER}'\n", 1)[1].rsplit(MARKER, 1)[0]
    exec(compile(source, "reviewed-controller", "exec"), {"__name__": "__main__"})
    assert len(executions) == 1
    executable, arguments, _environment = executions[0]
    assert executable == sys.executable
    assert arguments[:2] == [sys.executable, "-I"]
    copied = Path(arguments[2])
    assert copied.parent == tmp_path
    assert copied.read_bytes() == payload
    assert copied.stat().st_mode & 0o777 == 0o600
    assert urls == [
        "https://raw.githubusercontent.com/nold-ai/specfact-cli-modules/"
        "decb25a7b25536f127f7e7ecb89d6ea92264f7b8/scripts/independent_review_diagnostic.py"
    ]


def test_host_lifecycle_proofs_remain_required_in_both_test_routes():
    import tomllib

    proof = "tests/host/proof_independent_review_diagnostic.py"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert proof in project["tool"]["hatch"]["envs"]["default"]["scripts"]["test"]
    assert proof in (ROOT / "tools/smart_test_coverage.py").read_text()
    workflow = (ROOT / ".github/workflows/pr-orchestrator.yml").read_text()
    assert "run: hatch run test" in workflow


def test_host_controller_cases_are_outside_sealed_subject_discovery():
    import ast

    expected = {
        "test_preparation_shell_preserves_failure_and_projects_incomplete": 9,
        "test_required_parent_preserves_leaf_budget_and_expiry": 2,
    }
    host = ast.parse((ROOT / "tests/host/proof_independent_review_diagnostic.py").read_text())
    functions = {node.name: node for node in host.body if isinstance(node, ast.FunctionDef)}
    for name, count in expected.items():
        function = functions[name]
        parametrization = next(node for node in function.decorator_list if isinstance(node, ast.Call))
        assert isinstance(parametrization.args[1], ast.List)
        assert len(parametrization.args[1].elts) == count
    for path in ("test_capsule_review_projection.py", "test_independent_diagnostic_controller.py"):
        unit = ast.parse((ROOT / "tests/unit" / path).read_text())
        names = {node.name for node in unit.body if isinstance(node, ast.FunctionDef)}
        assert names.isdisjoint(expected)


def capture_functions():
    import ast
    import hashlib
    import stat

    workflow = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(
        (
            s
            for s in workflow["jobs"]["customer"]["steps"]
            if s.get("name") == "Prepare private original-report capture"
        ),
        None,
    )
    if step is None:
        return {}
    source = step["run"].split("<<'PY_CAPTURE'", 1)[1].split("\n", 1)[1].split("\nPY_CAPTURE", 1)[0]
    tree = ast.parse(source)
    nodes: list[ast.stmt] = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Assign))]
    namespace = {"os": os, "json": json, "hashlib": hashlib, "stat": stat, "Path": Path}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "capture-inert", "exec"), namespace)
    return namespace


def test_original_a_survives_fixed_destination_replay_b(tmp_path):
    source = tmp_path / "report.json"
    source.write_bytes(b'{"original":"A"}')
    ns = capture_functions()
    original = source
    if "capture_original" in ns:
        result = ns["capture_original"](
            source, tmp_path / "private", {"role": "candidate", "head": "a" * 40, "attempt": "1"}, 1
        )
        assert result["status"] == "COMPLETE"
        original = tmp_path / "private/original.json"
    source.write_bytes(b'{"replay":"B"}')
    assert original.read_bytes() == b'{"original":"A"}'


@pytest.mark.parametrize("case", ["missing", "symlink", "oversized", "duplicate", "binding", "partial"])
def test_capture_failure_is_explicit_and_never_commits_partial_original(tmp_path, monkeypatch, case):
    ns = capture_functions()
    source, destination = tmp_path / "source", tmp_path / "private"
    source.write_bytes(b'{"original":"A"}')
    binding = {"role": "candidate", "head": "a" * 40, "attempt": "1"}
    if case == "missing":
        source.unlink()
    elif case == "symlink":
        target = tmp_path / "target"
        target.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(target)
    elif case == "oversized":
        ns["LIMIT"] = 4
    elif case in ("duplicate", "binding"):
        assert ns["capture_original"](source, destination, binding, 1)["status"] == "COMPLETE"
        if case == "duplicate":
            path = destination / "manifest.json"
            path.write_text(
                path.read_text().replace('"status": "COMPLETE"', '"status": "COMPLETE", "status": "COMPLETE"')
            )
        else:
            binding = {**binding, "head": "b" * 40}
    else:
        original_write = ns["exclusive_bytes"]

        def partial_write(path, data):
            if path.name == "original.pending":
                original_write(path, data[:3])
                raise OSError("PRIVATE")
            original_write(path, data)

        ns["exclusive_bytes"] = partial_write
    result = ns["capture_original"](source, destination, binding, 1)
    assert result["status"] != "COMPLETE"
    if case not in ("duplicate", "binding"):
        assert not (destination / "original.json").exists()
    assert "PRIVATE" not in json.dumps(ns["original_projection"](result))


def test_capture_idempotence_keeps_a_after_b_and_refuses_changed_copy(tmp_path):
    ns = capture_functions()
    source, destination = tmp_path / "source", tmp_path / "private"
    source.write_bytes(b"A")
    binding = {"role": "candidate", "head": "a" * 40, "attempt": "1"}
    first = ns["capture_original"](source, destination, binding, 7)
    source.write_bytes(b"B")
    assert ns["capture_original"](source, destination, binding, 7) == first
    assert (destination / "original.json").read_bytes() == b"A"
    (destination / "original.json").write_bytes(b"C")
    assert ns["capture_original"](source, destination, binding, 7)["status"] == "UNAVAILABLE"


def ledger_fixture(tmp_path):
    import hashlib
    from types import ModuleType

    from tests.unit.test_independent_member_observation import controller_definitions

    ns = controller_definitions()
    module = ModuleType("inert")
    module._prepare_capsule_runtime = lambda: "result"
    private = tmp_path / "observation-private"
    private.mkdir(mode=0o700)
    manifest = {
        "head": "a" * 40,
        "workflow_blob": "b" * 40,
        "controller_sha256": "c" * 64,
        "role": "independent",
        "attempt": "1:1",
    }
    binding = {
        **manifest,
        "payload_sha256": ns["EXPECTED_REVIEWER_PAYLOAD"],
        "runner_sha256": hashlib.sha256(b"inert").hexdigest(),
    }
    (private / "invocation.json").write_text(json.dumps(manifest))
    receipt = private / "receipt.jsonl"
    observer = ns["HostObservation"](
        module, {"_prepare_capsule_runtime": module._prepare_capsule_runtime}, receipt, binding
    )
    observer.install()
    assert module._prepare_capsule_runtime() == "result"
    observer.finish()
    return receipt


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "lost_final",
        "partial_tail",
        "duplicate",
        "unknown",
        "binding",
        "ordinal",
        "unmatched",
        "after_complete",
        "stale_attempt",
    ],
)
def test_complete_ledger_is_required_for_available_host_projection(tmp_path, case):
    receipt = ledger_fixture(tmp_path)
    lines = receipt.read_text().splitlines()
    if case == "lost_final":
        lines = lines[:-1]
    elif case == "duplicate":
        lines[0] = lines[0].replace('"event":"enter"', '"event":"enter","event":"enter"')
    elif case == "unknown":
        row = json.loads(lines[0])
        row["PRIVATE"] = "PRIVATE"
        lines[0] = json.dumps(row)
    elif case == "binding":
        lines[0] = lines[0].replace("a" * 40, "d" * 40)
    elif case == "ordinal":
        row = json.loads(lines[0])
        row["call"] = 2
        lines[0] = json.dumps(row)
    elif case == "unmatched":
        row = json.loads(lines[1])
        row["stage"] = "member_execute"
        lines[1] = json.dumps(row)
    elif case == "after_complete":
        lines.append(lines[0])
    receipt.write_text("\n".join(lines) + ("" if case == "partial_tail" else "\n"))
    result = capture_functions()["host_projection"](
        tmp_path, {"role": "independent", "head": "a" * 40, "attempt": "1:2" if case == "stale_attempt" else "1:1"}
    )
    assert result["host_observation_status"] == ("AVAILABLE" if case == "valid" else "PARTIAL")
    assert result["later_execution_unknown"] is (case != "valid")
    if case != "valid":
        assert result["member"] == result["last_observed_host_stage"] == "UNAVAILABLE"
    assert "PRIVATE" not in json.dumps(result)


def test_changing_source_has_no_committed_original(tmp_path, monkeypatch):
    from types import SimpleNamespace

    ns = capture_functions()
    source = tmp_path / "source"
    source.write_bytes(b"original")
    original_stat = os.fstat
    count = 0

    def changed_stat(descriptor):
        nonlocal count
        value = original_stat(descriptor)
        count += 1
        fields = {
            name: getattr(value, name)
            for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink")
        }
        fields["st_ctime_ns"] += count
        return SimpleNamespace(**fields)

    monkeypatch.setattr(os, "fstat", changed_stat)
    result = ns["capture_original"](
        source, tmp_path / "private", {"role": "candidate", "head": "a" * 40, "attempt": "1"}, 1
    )
    assert result["status"] == "CHANGED"
    assert not (tmp_path / "private/original.json").exists()


def test_public_original_projection_has_exact_finite_fields():
    manifest = {
        "status": "MISSING",
        "binding": {"role": "candidate"},
        "required_exit": 124,
        "sha256": None,
        "bytes": None,
    }
    result = capture_functions()["original_projection"](manifest)
    assert set(result) == {
        "schema_version",
        "role",
        "original_status",
        "required_exit",
        "report_sha256",
        "report_bytes",
        "diagnostic",
        "host_observation_status",
        "last_observed_host_stage",
        "member",
        "side",
        "event",
        "later_execution_unknown",
        "loaded_host_identity",
        "effective_host_timeout_seconds",
        "actual_loaded_guest_identity",
    }
    assert result["required_exit"] == 124 and result["effective_host_timeout_seconds"] is None
    assert result["actual_loaded_guest_identity"] == "UNAVAILABLE"


def test_capture_rejects_boolean_exit_in_saved_manifest(tmp_path):
    ns = capture_functions()
    source, destination = tmp_path / "source", tmp_path / "private"
    source.write_bytes(b"A")
    binding = {"role": "candidate", "head": "a" * 40, "attempt": "1"}
    assert ns["capture_original"](source, destination, binding, 1)["status"] == "COMPLETE"
    path = destination / "manifest.json"
    value = json.loads(path.read_text())
    value["required_exit"] = True
    path.write_text(json.dumps(value))
    assert ns["capture_original"](source, destination, binding, 1)["status"] == "UNAVAILABLE"
