import hashlib
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


def project(tmp_path, monkeypatch, capsys, rows):
    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("name") == "Project independent review failure privately")
    source = step["run"].split("<<'PY_REVIEW_FAILURE'\n", 1)[1].rsplit("PY_REVIEW_FAILURE", 1)[0]
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"findings": [], "analyzer_evidence": rows}))
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_LOG", str(tmp_path / "missing"))
    exec(compile(source, "trusted-failure-projection", "exec"), {})
    return json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("damage", ["valid", "missing", "incomplete", "duplicate", "hash", "size"])
def test_failure_projection_rejects_uncommitted_original(tmp_path, monkeypatch, capsys, damage):
    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("name") == "Project independent review failure privately")
    source = step["run"].split("<<'PY_REVIEW_FAILURE'\n", 1)[1].rsplit("PY_REVIEW_FAILURE", 1)[0]
    report_path = tmp_path / "original.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [],
                "assurance_status": "PASS",
                "overall_verdict": "PASS",
                "analyzer_evidence": [{"id": "pylint", "execution_state": "ran", "evidence_outcome": "PASS"}],
            }
        )
    )
    original_bytes = report_path.read_bytes()
    manifest = {
        "status": "COMPLETE",
        "binding": {},
        "required_exit": 1,
        "sha256": hashlib.sha256(original_bytes).hexdigest(),
        "bytes": len(original_bytes),
    }
    if damage == "incomplete":
        manifest["status"] = "UNAVAILABLE"
    elif damage == "hash":
        manifest["sha256"] = "0" * 64
    elif damage == "size":
        manifest["bytes"] = len(original_bytes) + 1
    if damage != "missing":
        text = json.dumps(manifest)
        if damage == "duplicate":
            text = text.replace('"status": "COMPLETE"', '"status": "COMPLETE", "status": "COMPLETE"')
        (tmp_path / "manifest.json").write_text(text)
    monkeypatch.setenv("REVIEW_REPORT", str(report_path))
    monkeypatch.setenv("REVIEW_LOG", str(tmp_path / "missing.log"))
    (tmp_path / "original-unavailable").write_bytes(original_bytes)
    exec(compile(source, "trusted-failure-projection", "exec"), {})
    result = json.loads(capsys.readouterr().out)
    if damage == "valid":
        assert result["report_outcome"] == "structured_report"
        assert result["assurance_status"] == "PASS"
        assert result["member_observations"][0]["evidence_outcome"] == "PASS"
    else:
        assert result["report_outcome"] == "unreadable_report"
        assert result["member_observations"] == []
        assert result["member_observation_source"] == "UNAVAILABLE"
        assert result["assurance_status"] == result["overall_verdict"] == "UNAVAILABLE"
        assert result["error_analyzers"] == result["unknown_analyzers"] == []
        assert "PASS" not in json.dumps(result)


def test_member_observation_preserves_side_reason_without_private_text(tmp_path, monkeypatch, capsys):
    rows = [
        {
            "id": "pylint",
            "execution_state": "ran",
            "evidence_outcome": "UNKNOWN",
            "diagnostic": "snapshot_member_incomplete",
            "differential_counts": {"unknown": 2},
            "base": {"execution_state": "ran", "evidence_outcome": "PASS", "diagnostic": ""},
            "head": {"execution_state": "error", "evidence_outcome": "UNKNOWN", "diagnostic": "PRIVATE_SECRET"},
        }
    ]
    result = project(tmp_path, monkeypatch, capsys, rows)
    observations = result["member_observations"]
    assert len(observations) == 3
    assert observations[0]["diagnostic_class"] == "snapshot_member_incomplete"
    assert observations[0]["differential_counts"] == {"unknown": 2}
    assert observations[2]["side"] == "head"
    assert observations[2]["diagnostic_class"] == "unclassified"
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize(
    "rows",
    [
        [{"id": "PRIVATE_SECRET"}],
        [{"id": "pylint"}, {"id": "pylint"}],
        [{"id": "pylint"}] * 11,
        [{"id": "pylint", "base": "PRIVATE_SECRET"}],
    ],
)
def test_invalid_member_inventory_has_no_public_rows(tmp_path, monkeypatch, capsys, rows):
    result = project(tmp_path, monkeypatch, capsys, rows)
    assert result["member_observations"] == []
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("count", [True, -1, 1000001, "PRIVATE_SECRET", 1.5])
def test_member_counts_reject_noninteger_or_unbounded_values(tmp_path, monkeypatch, capsys, count):
    row = {
        "id": "pylint",
        "execution_state": "PRIVATE_SECRET",
        "evidence_outcome": "PRIVATE_SECRET",
        "diagnostic": "timeout:PRIVATE_SECRET",
        "differential_counts": {"unknown": count, "PRIVATE_SECRET": 1},
    }
    result = project(tmp_path, monkeypatch, capsys, [row])
    observation = result["member_observations"][0]
    assert observation["execution_state"] == "UNAVAILABLE"
    assert observation["evidence_outcome"] == "UNAVAILABLE"
    assert observation["diagnostic_class"] == "unclassified"
    assert observation["differential_counts"] == {}
    assert "PRIVATE" not in json.dumps(result)


def preparation_functions():
    from itertools import islice

    from specfact_cli.registry.crypto_validator import verify_signature
    from specfact_cli.registry.module_installer import _module_artifact_payload_stable

    namespace = controller_definitions()
    namespace.update(
        islice=islice,
        yaml=yaml,
        verify_signature=verify_signature,
        _module_artifact_payload_stable=_module_artifact_payload_stable,
    )
    return namespace


@pytest.fixture
def signed_reviewer(tmp_path):
    import base64
    import hashlib

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from specfact_cli.registry.module_installer import _module_artifact_payload_stable

    namespace = preparation_functions()
    assert namespace["TRUSTED_KEY_SHA256"] == "4e54ffb02307e1a85c166c40aba6d1bc40fbb9a8ef40bf756f8870e5bb08d1c8"
    package = tmp_path / "package"
    source = package / namespace["ADAPTER_ENTRY"]
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n")
    runner = package / namespace["RUNNER_ENTRY"]
    runner.parent.mkdir(parents=True)
    runner.write_text("VALUE = 2\n")
    manifest = package / "module-package.yaml"
    metadata: dict[str, object] = {"name": "nold-ai/specfact-code-review", "version": "0.51.2"}
    manifest.write_text(yaml.safe_dump(metadata))
    payload = _module_artifact_payload_stable(package)
    namespace["EXPECTED_REVIEWER_PAYLOAD"] = hashlib.sha256(payload).hexdigest()
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    key_path = tmp_path / "key.pem"
    key_path.write_bytes(public)
    namespace["_bundled_public_key_path"] = lambda: key_path
    namespace["TRUSTED_KEY_SHA256"] = hashlib.sha256(public).hexdigest()
    metadata["integrity"] = {
        "checksum": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "signature": base64.b64encode(key.sign(payload)).decode(),
    }
    manifest.write_text(yaml.safe_dump(metadata))
    return namespace, package, source, key_path


def test_prepared_source_is_authenticated_but_not_invocation_authority(tmp_path, signed_reviewer):
    from types import SimpleNamespace

    namespace, package, source, _key = signed_reviewer
    authenticated = namespace["authenticated_reviewer_source"](package)
    assert authenticated is not None
    runtime = SimpleNamespace(root=tmp_path / "runtime")
    target = runtime.root / "opt/specfact/builtin/specfact_code_review/tools/pylint_runner.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    result = namespace["prepared_source_observation"](runtime, "head", authenticated)
    assert result["status"] == "MATCH"
    assert result["actual_loaded_adapter"] == result["effective_deadline"] == "UNAVAILABLE"
    assert result["adapter_sha256"] == authenticated["adapter_sha256"]
    target.write_text("PRIVATE_SECRET")
    result = namespace["prepared_source_observation"](runtime, "head", authenticated)
    assert result["status"] == "UNAVAILABLE"
    assert "adapter_sha256" not in result
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("damage", ["source", "manifest", "key", "symlink", "oversized"])
def test_preparation_refuses_tampered_identity(signed_reviewer, damage):
    namespace, package, source, key = signed_reviewer
    if damage == "source":
        source.write_text("PRIVATE_SECRET")
    elif damage == "manifest":
        (package / "module-package.yaml").write_text("PRIVATE_SECRET")
    elif damage == "key":
        key.write_text("PRIVATE_SECRET")
    elif damage == "symlink":
        source.unlink()
        source.symlink_to(key)
    else:
        (package / "module-package.yaml").write_bytes(b"x" * (256 * 1024 + 1))
    assert namespace["authenticated_reviewer_source"](package) is None


def test_prepared_source_rejects_foreign_symlink(tmp_path, signed_reviewer):
    from types import SimpleNamespace

    namespace, package, source, _key = signed_reviewer
    authenticated = namespace["authenticated_reviewer_source"](package)
    runtime = SimpleNamespace(root=tmp_path / "runtime")
    target = runtime.root / "opt/specfact/builtin/specfact_code_review/tools/pylint_runner.py"
    target.parent.mkdir(parents=True)
    target.symlink_to(source)
    assert namespace["prepared_source_observation"](runtime, "base", authenticated)["status"] == "UNAVAILABLE"


def test_observation_does_not_add_subject_execution_or_change_authority():
    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("id") == "independent_review")
    script = step["run"]
    assert script.index("authenticated_source = authenticated_reviewer_source(") < script.index("os.chdir(sys.argv[1])")
    assert script.count("app(args=sys.argv[2:])") == 1
    assert script.count("prepare_runtime(plan, runtime=runtime)") == 1
    assert "--scope index --enforcement changed --bug-hunt" in script
    assert 'exit "$review_exit"' in script
    assert "timeout=600" in script
    assert not step.get("continue-on-error", False)


def controller_definitions():
    import ast
    import hashlib
    import os
    import stat
    import struct
    import sys
    import types

    workflow = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(
        s["run"] for s in workflow["jobs"]["independent-review"]["steps"] if s.get("id") == "independent_review"
    )
    source = recipe.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    tree = ast.parse(source)
    nodes: list[ast.stmt] = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Assign))]
    nodes = [
        n
        for n in nodes
        if not isinstance(n, ast.Assign) or all(isinstance(t, ast.Name) and t.id.isupper() for t in n.targets)
    ]
    namespace = {
        "ast": ast,
        "hashlib": hashlib,
        "os": os,
        "stat": stat,
        "struct": struct,
        "sys": sys,
        "types": types,
        "Path": Path,
        "json": json,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "controller-inert", "exec"), namespace)
    return namespace


def test_plain_host_observation_preserves_exact_call_objects(tmp_path):
    import types

    ns = controller_definitions()
    calls = []
    argument, result = object(), object()

    def producer(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    module = types.ModuleType("inert")
    module._prepare_capsule_runtime = producer
    if "HostObservation" not in ns:
        observed = []
        actual = module._prepare_capsule_runtime(argument, flag=argument)
    else:
        observation = ns["HostObservation"](
            module, {"_prepare_capsule_runtime": producer}, tmp_path / "receipt", {"head": "a" * 40}
        )
        observation.install()
        actual = module._prepare_capsule_runtime(argument, flag=argument)
        observation.finish()
        observed = [json.loads(line) for line in (tmp_path / "receipt").read_text().splitlines()]
    assert actual is result and calls == [((argument,), {"flag": argument})]
    assert [row["event"] for row in observed] == ["enter", "leave", "complete"]
    assert module._prepare_capsule_runtime is producer


@pytest.fixture
def inert_runner(tmp_path):
    import types

    ns = controller_definitions()
    package = tmp_path / "package"
    path = package / ns["RUNNER_ENTRY"]
    path.parent.mkdir(parents=True)
    source = "from __future__ import annotations\n"
    for name in ns["HOST_STAGES"]:
        signature = (
            '*, project_runtime_identity="not-applicable", environment_id=None'
            if name == "_prepare_capsule_runtime"
            else "value"
        )
        source += f"def {name}({signature}):\n    return tuple(x + 1 for x in (1, 2))\n"
    path.write_text(source)
    module = types.ModuleType("specfact_code_review.run.runner")
    module.__file__ = str(path)
    module.__spec__ = types.SimpleNamespace(origin=str(path))
    exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
    return ns, module, {"runner_source": source.encode()}, package


def test_admits_plain_loaded_functions_without_markers(inert_runner):
    ns, module, authenticated, package = inert_runner
    assert set(ns["admitted_functions"](module, authenticated, package)) == set(ns["HOST_STAGES"])


@pytest.mark.parametrize("damage", ["bytecode", "nested", "globals", "default", "alias", "origin"])
def test_refuses_same_metadata_but_foreign_function_identity(inert_runner, damage):
    import types

    ns, module, authenticated, package = inert_runner
    name = "_prepare_capsule_runtime"
    function = getattr(module, name)
    if damage == "bytecode":
        function.__code__ = function.__code__.replace(
            co_code=compile("pass", function.__code__.co_filename, "exec").co_code
        )
    elif damage == "nested":
        code = function.__code__
        constants = tuple(
            c.replace(co_consts=(*c.co_consts, "PRIVATE")) if type(c) is types.CodeType else c for c in code.co_consts
        )
        function.__code__ = code.replace(co_consts=constants)
    elif damage == "globals":
        other = types.FunctionType(function.__code__, dict(function.__globals__))
        other.__kwdefaults__ = function.__kwdefaults__
        setattr(module, name, other)
    elif damage == "default":
        function.__kwdefaults__ = {"project_runtime_identity": "not-applicable", "environment_id": False}
    elif damage == "alias":
        setattr(module, name, module._execute_capsule_member)
    else:
        module.__spec__.origin = "/foreign"
    assert ns["admitted_functions"](module, authenticated, package) is None


def test_code_constants_are_type_sensitive_and_bounded():
    compare = controller_definitions()["same_code"]
    assert not compare(True, 1)
    assert not compare(-0.0, 0.0)
    assert not compare((1,), (1,), [0])
    assert compare((True, -0.0, frozenset({"a"})), (True, -0.0, frozenset({"a"})))


@pytest.mark.parametrize("damage", ["field", "write", "short_write", "foreign", "install"])
def test_observer_failure_preserves_same_baseexception_and_original_arguments(tmp_path, monkeypatch, damage):
    import os
    import types

    ns = controller_definitions()
    sentinel = KeyboardInterrupt("PRIVATE")
    calls = []
    argument = object()

    def producer(*args, **kwargs):
        calls.append((args, kwargs))
        raise sentinel

    module = types.ModuleType("inert")
    module._prepare_capsule_runtime = producer
    observer = ns["HostObservation"](module, {"_prepare_capsule_runtime": producer}, tmp_path / "receipt", {})
    if damage == "install":

        def fail_wrapper(*_):
            raise RuntimeError("PRIVATE")

        observer.wrapper = fail_wrapper
    observer.install()
    if damage == "field":

        def fail_fields(*_):
            raise RuntimeError("PRIVATE")

        observer.fields = fail_fields
    elif damage == "write":

        def fail_write(*_):
            raise OSError("PRIVATE")

        monkeypatch.setattr(os, "write", fail_write)
    elif damage == "short_write":
        monkeypatch.setattr(os, "write", lambda *_: 0)
    with pytest.raises(KeyboardInterrupt) as raised:
        module._prepare_capsule_runtime(argument, flag=argument)

    def foreign():
        return None

    if damage == "foreign":
        module._prepare_capsule_runtime = foreign
    observer.finish()
    assert raised.value is sentinel
    assert calls == [((argument,), {"flag": argument})]
    assert observer.lost
    assert module._prepare_capsule_runtime is (foreign if damage == "foreign" else producer)
    assert not any(json.loads(line)["event"] == "complete" for line in (tmp_path / "receipt").read_text().splitlines())


def test_nested_calls_have_paired_ordinals_and_overflow_is_permanent(tmp_path):
    import types

    ns = controller_definitions()
    module = types.ModuleType("inert")

    def recursive(depth):
        return module._prepare_capsule_runtime(depth - 1) if depth else "same-result"

    module._prepare_capsule_runtime = recursive
    observer = ns["HostObservation"](module, {"_prepare_capsule_runtime": recursive}, tmp_path / "receipt", {})
    observer.install()
    assert module._prepare_capsule_runtime(17) == "same-result"
    assert module._prepare_capsule_runtime(0) == "same-result"
    observer.finish()
    records = [json.loads(line) for line in (tmp_path / "receipt").read_text().splitlines()]
    assert observer.lost and len(records) == 16
    assert [row["call"] for row in records] == list(range(1, 17))
    assert all(row["event"] == "enter" for row in records)


@pytest.mark.parametrize("mutation", ["code", "defaults", "alias"])
def test_post_admission_mutation_invalidates_without_changing_forwarded_call(tmp_path, mutation):
    from types import ModuleType

    module = ModuleType("inert")

    def producer(value=1):
        return value

    module._prepare_capsule_runtime = producer
    observer = controller_definitions()["HostObservation"](
        module, {"_prepare_capsule_runtime": producer}, tmp_path / "receipt", {}
    )
    observer.install()
    wrapper = module._prepare_capsule_runtime
    if mutation == "code":

        def changed(value=1):
            return value + 1

        producer.__code__ = changed.__code__
    elif mutation == "defaults":
        producer.__defaults__ = (2,)
    else:
        module._prepare_capsule_runtime = lambda value: value + 3
    assert wrapper(7) == (8 if mutation == "code" else 7)
    observer.finish()
    assert observer.lost
    assert (tmp_path / "receipt").read_bytes() == b""


def test_partial_installation_restores_owned_prefix(tmp_path):
    from types import ModuleType

    module = ModuleType("inert")

    def producer(value):
        return value

    module._prepare_capsule_runtime = module._materialize_claimed_project_runtime = producer
    originals = dict.fromkeys(("_prepare_capsule_runtime", "_materialize_claimed_project_runtime"), producer)
    observer = controller_definitions()["HostObservation"](module, originals, tmp_path / "receipt", {})
    make_wrapper = observer.wrapper

    def fail_second(name, original):
        if name == "_materialize_claimed_project_runtime":
            raise RuntimeError("PRIVATE")
        return make_wrapper(name, original)

    observer.wrapper = fail_second
    observer.install()
    assert module._prepare_capsule_runtime is module._materialize_claimed_project_runtime is producer
    argument = object()
    assert module._prepare_capsule_runtime(argument) is argument
    observer.finish()
    assert observer.lost and (tmp_path / "receipt").read_bytes() == b""


@pytest.mark.parametrize("binding_ok", [True, False])
def test_parent_controller_binding_controls_admission_before_subject(tmp_path, inert_runner, binding_ok):
    import hashlib

    ns, module, authenticated, package = inert_runner
    controller = tmp_path / "reviewer.py"
    controller.write_bytes(b"controlled generated controller")
    private = tmp_path / "observation-private"
    private.mkdir(mode=0o700)
    manifest = {
        "head": "a" * 40,
        "workflow_blob": "b" * 40,
        "role": "independent",
        "attempt": "1:1",
        "controller_sha256": hashlib.sha256(controller.read_bytes()).hexdigest() if binding_ok else "0" * 64,
    }
    (private / "invocation.json").write_text(json.dumps(manifest))
    authenticated.update(
        payload_sha256=ns["EXPECTED_REVIEWER_PAYLOAD"],
        runner_sha256=hashlib.sha256(authenticated["runner_source"]).hexdigest(),
    )
    original = module._prepare_capsule_runtime
    observer = ns["start_observation"](module, authenticated, package, controller)
    assert (observer is not None) is binding_ok
    assert module._prepare_capsule_runtime() == (2, 3)
    if observer is not None:
        observer.finish()
        records = [json.loads(line) for line in (private / "receipt.jsonl").read_text().splitlines()]
        assert [row["event"] for row in records] == ["enter", "leave", "complete"]
    else:
        assert not (private / "receipt.jsonl").exists()
    assert module._prepare_capsule_runtime is original


@pytest.mark.parametrize("oversized_record", [False, True])
def test_receipt_bounds_poison_observation_permanently(tmp_path, oversized_record):
    from types import ModuleType

    module = ModuleType("inert")

    def producer():
        return "same"

    module._prepare_capsule_runtime = producer
    observer = controller_definitions()["HostObservation"](
        module,
        {"_prepare_capsule_runtime": producer},
        tmp_path / "receipt",
        {"head": "x" * 2048} if oversized_record else {},
    )
    observer.install()
    for _ in range(70):
        assert module._prepare_capsule_runtime() == "same"
    observer.finish()
    data = (tmp_path / "receipt").read_bytes()
    assert observer.lost and len(data) <= 128 * 1024
    lines = data.splitlines(keepends=True)
    assert len(lines) <= 128 and all(len(line) <= 1024 for line in lines)
    assert not any(json.loads(line)["event"] == "complete" for line in lines)
