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
    import ast
    import hashlib
    from itertools import islice

    from specfact_cli.registry.crypto_validator import verify_signature
    from specfact_cli.registry.module_installer import _module_artifact_payload_stable

    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("id") == "independent_review")
    source = step["run"].split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    tree = ast.parse(source)
    nodes: list[ast.stmt] = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        or (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id in {"TRUSTED_KEY_SHA256", "ADAPTER_ENTRY"}
                for target in node.targets
            )
        )
    ]
    namespace = {
        "hashlib": hashlib,
        "islice": islice,
        "yaml": yaml,
        "verify_signature": verify_signature,
        "_module_artifact_payload_stable": _module_artifact_payload_stable,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "trusted-preparation", "exec"), namespace)
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
    manifest = package / "module-package.yaml"
    metadata: dict[str, object] = {"name": "nold-ai/specfact-code-review", "version": "0.51.2"}
    manifest.write_text(yaml.safe_dump(metadata))
    payload = _module_artifact_payload_stable(package)
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
