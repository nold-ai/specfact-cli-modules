"""The customer gate must reject incomplete analyzer evidence."""

import importlib.util
from pathlib import Path

import pytest


def _gate():
    path = Path(__file__).parents[2] / "scripts/capsule_customer_gate.py"
    spec = importlib.util.spec_from_file_location("capsule_customer_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("state,outcome", [("error", "UNKNOWN"), ("not_applicable", "NOT_APPLICABLE")])
def test_customer_gate_rejects_missing_analyzer_execution(state, outcome):
    gate = _gate()
    report = {
        "analyzer_evidence": [
            {"id": member, "execution_state": state, "evidence_outcome": outcome} for member in gate.ANALYZERS
        ]
    }
    with pytest.raises(ValueError, match="execution"):
        gate.validate_report(report, returncode=0, expected="clean")


def test_customer_gate_rejects_empty_evidence():
    with pytest.raises(ValueError, match="inventory"):
        _gate().validate_report({"analyzer_evidence": []}, returncode=0, expected="clean")


def test_customer_gate_requires_detected_defect_and_failure_exit():
    gate = _gate()
    report = {
        "analyzer_evidence": [
            {"id": member, "execution_state": "ran", "evidence_outcome": "PASS"} for member in gate.ANALYZERS
        ],
        "assurance_status": "PASS",
        "has_unknown_required_evidence": False,
        "findings": [],
    }
    with pytest.raises(ValueError, match="defect"):
        gate.validate_report(report, returncode=0, expected="defective")


@pytest.mark.parametrize(
    "status,exit_code", [(None, 0), ("PASS", 1), ("FAIL", 0), ("UNKNOWN", 1), ("NOT_APPLICABLE", 0)]
)
def test_customer_gate_rejects_inconsistent_repository_result(status, exit_code):
    gate = _gate()
    report = {
        "analyzer_evidence": [
            {"id": member, "execution_state": "ran", "evidence_outcome": "PASS"} for member in gate.ANALYZERS
        ],
        "assurance_status": status,
        "has_unknown_required_evidence": False,
    }
    with pytest.raises(ValueError, match="repository"):
        gate.validate_report(report, returncode=exit_code, expected="repository")


def _namespace_report(gate):
    return {
        "analyzer_evidence": [
            {
                "id": member,
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "diagnostic": "namespace_unavailable: bwrap: Creating new namespace failed: Operation not permitted",
                "capsule_identity": "sha256:" + "a" * 64,
            }
            for member in gate.ANALYZERS
        ],
        "assurance_status": "UNKNOWN",
        "has_unknown_required_evidence": True,
    }


def test_namespace_denial_requires_specific_verified_launcher_failure():
    gate = _gate()
    gate.validate_report(_namespace_report(gate), returncode=1, expected="namespace-denial")


@pytest.mark.parametrize("mutation", ["success", "generic", "missing-identity", "empty", "ran"])
def test_namespace_denial_rejects_unrelated_or_missing_failure(mutation):
    gate = _gate()
    report = _namespace_report(gate)
    returncode = 1
    if mutation == "success":
        returncode = 0
    elif mutation == "generic":
        report["analyzer_evidence"][0]["diagnostic"] = "capsule_execution_failed"
    elif mutation == "missing-identity":
        del report["analyzer_evidence"][0]["capsule_identity"]
    elif mutation == "empty":
        report["analyzer_evidence"] = []
    else:
        report["analyzer_evidence"][0]["execution_state"] = "ran"
    with pytest.raises(ValueError, match="namespace"):
        gate.validate_report(report, returncode=returncode, expected="namespace-denial")


@pytest.mark.parametrize("enabled,restricted", [("N", "1"), ("Y", "0")])
def test_namespace_denial_requires_ubuntu_baseline(tmp_path, monkeypatch, enabled, restricted):
    gate = _gate()
    paths = {tmp_path / "enabled": "Y", tmp_path / "restricted": "1"}
    for path, value in zip(paths, [enabled, restricted], strict=True):
        path.write_text(value)
    monkeypatch.setattr(gate, "_NAMESPACE_POLICY_FILES", paths)
    with pytest.raises(ValueError, match="baseline"):
        gate._namespace_baseline(tmp_path)
    assert (tmp_path / "namespace-policy.json").exists()


def test_namespace_denial_runs_before_allow_profile_and_uses_separate_cache():
    workflow = (Path(__file__).parents[2] / ".github/workflows/capsule-customer-execution.yml").read_text()
    assert workflow.index("--expect-namespace-denial") < workflow.index("sudo apparmor_parser")
    assert 'SPECFACT_CODE_REVIEW_CAPSULE_CACHE="$CUSTOMER_ROOT/denied-cache"' in workflow
    assert "${{ env.CUSTOMER_ROOT }}/denied-evidence/" in workflow


def test_warm_cache_requires_identical_capsule_composition():
    gate = _gate()
    cold = _namespace_report(gate)
    warm = _namespace_report(gate)
    warm["analyzer_evidence"][0]["capsule_identity"] = "sha256:" + "b" * 64
    with pytest.raises(ValueError, match="composition"):
        gate._validate_warm_composition(cold, warm)


def test_namespace_denial_checks_baseline_before_actual_review(tmp_path, monkeypatch):
    gate = _gate()
    enabled = tmp_path / "enabled"
    enabled.write_text("Y")
    monkeypatch.setattr(gate, "_NAMESPACE_POLICY_FILES", {enabled: "Y"})
    calls = []
    monkeypatch.setattr(gate, "_fixture", lambda root, defective: calls.append((root, defective)))
    monkeypatch.setattr(gate, "_review", lambda *args, **kwargs: (calls.append(args), _namespace_report(gate))[1])
    assert gate._run_namespace_denial(tmp_path) == []
    assert calls == [
        (tmp_path / "namespace-fixture", False),
        (tmp_path / "namespace-fixture", tmp_path, "namespace-denial", "namespace-denial"),
    ]


@pytest.mark.parametrize("name,umask,offline", [("cold", 0o022, "0"), ("warm", 0o077, "1"), ("alternate", 0o077, "0")])
def test_reviews_use_real_full_capsule_command_and_cache_mode(tmp_path, monkeypatch, capsys, name, umask, offline):
    import json
    from types import SimpleNamespace

    gate = _gate()
    report = _namespace_report(gate)
    report.update(assurance_status="PASS", has_unknown_required_evidence=False)
    for row in report["analyzer_evidence"]:
        row.update(execution_state="ran", evidence_outcome="PASS")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        (tmp_path / f"{name}.json").write_text(json.dumps(report))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", run)
    (tmp_path / "test_calculator.py").write_text(gate._FIXTURE_TEST_SOURCE)
    assert gate._review(tmp_path, tmp_path, name, "clean") == report
    command, options = calls[0]
    assert command[:9] == [
        str(Path(gate.sys.executable).absolute().parent / "specfact"),
        "code",
        "review",
        "run",
        "--scope",
        "full",
        "--enforcement",
        "full",
        "--bug-hunt",
    ]
    assert options["umask"] == umask
    assert options["env"]["SPECFACT_CODE_REVIEW_CAPSULE_OFFLINE"] == offline
    assert options["cwd"] == tmp_path
    progress = capsys.readouterr().out
    assert f"capsule review {name}: started; expected=clean" in progress
    assert f"capsule review {name}: finished; exit=0; assurance=PASS" in progress


def test_fixture_checks_private_and_sealed_mounts(tmp_path, monkeypatch):
    import runpy

    gate = _gate()
    root = tmp_path / "fixture"
    gate._fixture(root, defective=False)
    monkeypatch.syspath_prepend(str(root))
    fixture = runpy.run_path(str(root / "test_calculator.py"))
    fixture["_assert_private_write"](tmp_path)
    assert not (tmp_path / ".capsule-write-probe").exists()
    with pytest.raises(AssertionError, match="sealed capsule path was writable"):
        fixture["_assert_sealed_write_denied"](tmp_path)
    source = (root / "test_calculator.py").read_text()
    assert "_assert_capsule_filesystem()" in source.split("def test_add()", 1)[1]


def test_private_mount_proof_requires_successful_targeted_pytest(tmp_path):
    gate = _gate()
    report = _namespace_report(gate)
    with pytest.raises(ValueError, match="filesystem proof"):
        gate._write_filesystem_evidence(report, tmp_path, tmp_path, "cold")


def test_alternate_cache_review_compares_identities_and_keeps_repository_single(tmp_path, monkeypatch):
    gate = _gate()
    report = _namespace_report(gate)
    calls = []

    def review(root, evidence, name, expected, *, cache, mode):
        calls.append((name, root, cache))
        return report

    monkeypatch.setattr(gate, "_review", review)
    monkeypatch.setattr(gate, "_write_completed_filesystem_evidence", lambda *args: None)
    monkeypatch.setattr(gate, "_cache_identities", lambda cache: {"oci/blob": "same"})
    assert (
        gate._run_reviews(
            tmp_path, tmp_path / "cache", tmp_path / "repository", tmp_path / "clean", tmp_path / "defect"
        )
        == []
    )
    assert ("alternate", tmp_path / "clean", tmp_path / "cache-077") in calls
    assert sum(name == "repository" for name, _, _ in calls) == 1


def test_alternate_cache_requires_fresh_root(tmp_path, monkeypatch):
    gate = _gate()
    alternate = tmp_path / "cache-077"
    alternate.mkdir()
    (alternate / "old-cache").write_text("untrusted")
    with pytest.raises(ValueError, match=r"alternate.*empty"):
        gate._run_reviews(tmp_path, tmp_path / "cache", tmp_path, tmp_path, tmp_path)


def test_workflow_allows_only_positive_cache_variants():
    workflow = (Path(__file__).parents[2] / ".github/workflows/capsule-customer-execution.yml").read_text()
    assert '"$CUSTOMER_ROOT/cache-077/**/opt/specfact/bin/bwrap-static"' in workflow
    assert '"$CUSTOMER_ROOT/denied-cache/**/opt/specfact/bin/bwrap-static"' not in workflow


def test_defective_fixture_requires_actual_pytest_failure_witness():
    gate = _gate()
    report = _namespace_report(gate)
    report.update(assurance_status="FAIL", has_unknown_required_evidence=False, findings=[{"rule": "F401"}])
    for row in report["analyzer_evidence"]:
        row.update(execution_state="ran", evidence_outcome="FAIL" if row["id"] == "ruff" else "PASS")
    with pytest.raises(ValueError, match=r"pytest.*defect"):
        gate.validate_report(report, returncode=1, expected="defective")


def test_defective_fixture_contains_known_failing_pytest_assertion(tmp_path):
    root = tmp_path / "fixture"
    _gate()._fixture(root, defective=True)
    assert "assert add(2, 3) == 6" in (root / "test_calculator.py").read_text()


def test_filesystem_proof_waits_for_defective_pytest_execution(tmp_path, monkeypatch):
    gate = _gate()
    reports = {"cold": _namespace_report(gate)}
    calls = []
    monkeypatch.setattr(gate, "_write_filesystem_evidence", lambda *args: calls.append(args))
    gate._write_completed_filesystem_evidence(reports, tmp_path, tmp_path)
    assert calls == []
    defect = _namespace_report(gate)
    defect.update(assurance_status="FAIL", findings=[{"tool": "pytest", "rule": "TEST_OUTCOME_NOT_PASS"}])
    for row in defect["analyzer_evidence"]:
        row.update(
            execution_state="ran", evidence_outcome="FAIL" if row["id"] == "targeted-pytest-coverage" else "PASS"
        )
    reports["defective"] = defect
    gate._write_completed_filesystem_evidence(reports, tmp_path, tmp_path)
    assert len(calls) == 1


def test_sealed_mount_proof_rejects_unrelated_permission_failure(tmp_path, monkeypatch):
    import errno
    import runpy

    gate = _gate()
    root = tmp_path / "fixture"
    gate._fixture(root, defective=False)
    monkeypatch.syspath_prepend(str(root))
    fixture = runpy.run_path(str(root / "test_calculator.py"))

    def deny_access(*args, **kwargs):
        raise PermissionError(errno.EACCES, "wrong failure")

    monkeypatch.setattr(Path, "touch", deny_access)
    with pytest.raises(AssertionError, match="another reason"):
        fixture["_assert_sealed_write_denied"](tmp_path)


def test_installation_identity_rejects_changed_version_or_payload():
    gate = _gate()
    expected = {"name": "nold-ai/specfact-code-review", "version": "1.2.3", "integrity": {"checksum": "sha256:a"}}
    for observed in ({**expected, "version": "1.2.4"}, {**expected, "integrity": {"checksum": "sha256:b"}}):
        with pytest.raises(ValueError, match=r"installed.*identity"):
            gate._validate_installed_manifest(expected, observed)


def test_expected_installation_rejects_modified_registry_archive(tmp_path):
    import json

    gate = _gate()
    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "module.tar.gz").write_bytes(b"corrupted")
    (registry / "index.json").write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "id": "nold-ai/specfact-code-review",
                        "latest_version": "1.2.3",
                        "download_url": "module.tar.gz",
                        "checksum_sha256": "a" * 64,
                    }
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="registry archive"):
        gate._expected_installation(tmp_path)


def test_public_install_pins_registry_version_and_verifies_identity():
    workflow = (Path(__file__).parents[2] / ".github/workflows/capsule-customer-execution.yml").read_text()
    assert '--version "$EXPECTED_MODULE_VERSION" --source marketplace' in workflow
    assert "--verify-installation" in workflow
    assert "--installation-version" in workflow


def test_repository_slice_uses_original_dependency_compatible_source_and_tests():
    gate = _gate()
    assert gate._REPOSITORY_PATHS == ("publish_bundle_selection.py", "tests/unit/test_publish_bundle_selection.py")


def test_installed_identity_requires_signature_and_records_pinned_receipt(tmp_path, monkeypatch):
    import json

    import yaml
    from specfact_cli.registry import module_installer

    gate = _gate()
    expected = gate._expected_installation(Path(__file__).parents[2])
    package = tmp_path / "specfact-code-review"
    package.mkdir()
    (package / "module-package.yaml").write_text(yaml.safe_dump(expected))
    key = tmp_path / "public.pem"
    key.write_text("public test key")
    monkeypatch.setattr(module_installer, "USER_MODULES_ROOT", tmp_path)
    monkeypatch.setattr(module_installer, "_bundled_public_key_path", lambda: key)
    monkeypatch.setattr(
        gate, "_release_checkout_identity", lambda repository: {"commit": "a" * 40, "release_tag": "release"}
    )
    calls = []

    def verify(*args, **kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(module_installer, "verify_module_artifact", verify)
    gate._verify_installation(Path(__file__).parents[2], tmp_path / "evidence")
    assert calls == [
        {
            "allow_unsigned": False,
            "require_integrity": True,
            "require_signature": True,
            "public_key_pem": "public test key",
        }
    ]
    receipt = json.loads((tmp_path / "evidence/installed-identity.json").read_text())
    assert receipt["version"] == expected["version"]
    assert receipt["integrity"] == expected["integrity"]
    assert receipt["signature_verified"] is True


def test_repository_review_uses_explicit_paths_without_conflicting_scope(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    gate = _gate()
    report = _namespace_report(gate)
    report.update(assurance_status="PASS", has_unknown_required_evidence=False)
    for row in report["analyzer_evidence"]:
        row.update(execution_state="ran", evidence_outcome="PASS")
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        (tmp_path / "repository.json").write_text(json.dumps(report))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", run)
    gate._review(tmp_path, tmp_path, "repository", "repository")
    assert commands[0][4:6] == list(gate._REPOSITORY_PATHS)
    assert "--scope" not in commands[0]


def test_customer_review_environment_excludes_ambient_overrides_and_credentials(tmp_path, monkeypatch):
    gate = _gate()
    poisoned = {
        "PATH": "/untrusted/bin",
        "PYTHONPATH": "/untrusted/python",
        "PYTHONHOME": "/untrusted/home",
        "LD_PRELOAD": "/untrusted/library.so",
        "GH_TOKEN": "secret",
        "GITHUB_TOKEN": "secret",
        "AWS_SECRET_ACCESS_KEY": "secret",
        "SPECFACT_MODULE_PUBLIC_KEY_PEM": "untrusted key",
        "SPECFACT_CODE_REVIEW_DEV_HOST_COMPAT": "1",
        "SPECFACT_CODE_REVIEW_TARGETED_TEST_TIMEOUT": "0",
        "SPECFACT_MODULES_ROOTS": "/untrusted/modules",
        "SPECFACT_ALLOW_UNSIGNED": "1",
    }
    for name, value in poisoned.items():
        monkeypatch.setenv(name, value)
    environment = gate._review_environment(cache=tmp_path, offline=False, mode="public")
    assert all(name not in environment for name in poisoned if name != "PATH")
    assert environment["PATH"] != poisoned["PATH"]
    assert environment["SPECFACT_CODE_REVIEW_CAPSULE_CACHE"] == str(tmp_path)
    assert environment["PYTHONNOUSERSITE"] == "1"


def test_candidate_review_preserves_only_required_workflow_context(tmp_path, monkeypatch):
    gate = _gate()
    monkeypatch.setenv("SPECFACT_MODULES_ROOTS", str(tmp_path / "candidate"))
    monkeypatch.setenv("GITHUB_REPOSITORY", "nold-ai/specfact-cli-modules")
    monkeypatch.setenv("GITHUB_WORKFLOW_REF", "workflow-ref")
    monkeypatch.setenv("ACTIONS_RUNTIME_TOKEN", "secret")
    environment = gate._review_environment(cache=tmp_path, offline=True, mode="candidate")
    assert environment["SPECFACT_MODULES_ROOTS"] == str(tmp_path / "candidate")
    assert environment["GITHUB_WORKFLOW_REF"] == "workflow-ref"
    assert environment["SPECFACT_ALLOW_UNSIGNED"] == "1"
    assert "ACTIONS_RUNTIME_TOKEN" not in environment


def test_workflow_triggers_for_shared_gate_and_public_artifact_inputs():
    workflow = (Path(__file__).parents[2] / ".github/workflows/capsule-customer-execution.yml").read_text()
    orchestrator = (Path(__file__).parents[2] / ".github/workflows/pr-orchestrator.yml").read_text()
    pr_trigger = orchestrator.split("            capsule:", 1)[1].split("      - id: out", 1)[0]
    assert "  workflow_call:" in workflow
    assert "  pull_request:" not in workflow
    for path in (
        "registry/**",
        "scripts/link_dev_module.py",
        "publish_bundle_selection.py",
        "tests/unit/test_capsule_customer_gate.py",
        "tests/unit/test_publish_bundle_selection.py",
    ):
        assert path in pr_trigger


def _orchestrator_workflow():
    import yaml

    return yaml.load(
        (Path(__file__).parents[2] / ".github/workflows/pr-orchestrator.yml").read_text(), Loader=yaml.BaseLoader
    )


def test_required_quality_runs_capsule_assertion_even_after_dependency_failure():
    workflow = _orchestrator_workflow()
    quality = workflow["jobs"]["quality"]
    assert "customer-capsules" in quality["needs"]
    assert "always()" in quality["if"]
    assert quality["steps"][0]["name"] == "Require signature and customer capsule prerequisites"
    assert workflow["jobs"]["customer-capsules"]["uses"] == "./.github/workflows/capsule-customer-execution.yml"


@pytest.mark.parametrize(
    "required,result,signature,expected",
    [
        ("true", "success", "success", 0),
        ("true", "failure", "success", 1),
        ("true", "skipped", "success", 1),
        ("true", "cancelled", "success", 1),
        ("false", "skipped", "success", 0),
        ("false", "skipped", "failure", 1),
    ],
)
def test_quality_prerequisite_step_cannot_turn_capsule_failure_into_success(required, result, signature, expected):
    import subprocess

    step = _orchestrator_workflow()["jobs"]["quality"]["steps"][0]
    assert step["name"] == "Require signature and customer capsule prerequisites"
    result = subprocess.run(
        ["/bin/bash", "-c", step["run"]],
        capture_output=True,
        text=True,
        check=False,
        env={"CAPSULE_REQUIRED": required, "CAPSULE_RESULT": result, "SIGNATURE_RESULT": signature},
    )
    assert result.returncode == expected


def test_minimum_core_smoke_uses_current_authenticated_lock_not_completed_checkpoint():
    workflow = _orchestrator_workflow()
    smoke = workflow["jobs"]["minimum-core-schema-compatibility"]
    assert "verify-module-signatures" in smoke["needs"]
    steps = {step["name"]: step for step in smoke["steps"] if "name" in step}
    execution = steps["Run signed analyzer capsule from prefetched cache and empty Bubblewrap smoke"]["run"]
    assert "IMPLEMENTATION_CHECKPOINT.json" not in execution
    assert 'module_manifest["authenticated_resources"][resource_key]["digest"]' in execution
    prefetch = steps["Prefetch signed analyzer capsule into credential-free cache"]["run"]
    assert 'environment["oci"]["manifest"]' in prefetch
    assert 'cp311) manifest="sha256:' not in prefetch


def _materialization_namespace_report(gate):
    report = _namespace_report(gate)
    for row in report["analyzer_evidence"]:
        del row["capsule_identity"]
        row["environment_id"] = "linux-x86_64-cp312"
        row["diagnostic"] = (
            "capsule_materialization_failed:namespace_unavailable:stage=offline-install:launcher=sha256:"
            + "a" * 64
            + ":bwrap: loopback: Operation not permitted"
        )
    return report


def test_namespace_denial_accepts_verified_offline_install_launcher(tmp_path, monkeypatch):
    gate = _gate()
    monkeypatch.setenv("MATRIX_PYTHON", "3.12")
    report = _materialization_namespace_report(gate)
    gate.validate_report(report, returncode=1, expected="namespace-denial")
    identity = gate._namespace_denial_identity(report)
    assert identity == {
        "stage": "offline-install",
        "launcher_digest": "sha256:" + "a" * 64,
        "environment_id": "linux-x86_64-cp312",
    }


@pytest.mark.parametrize("mutation", ["wrong-abi", "missing-abi", "missing-digest", "mixed-launcher", "generic"])
def test_namespace_denial_rejects_unverified_early_failures(monkeypatch, mutation):
    gate = _gate()
    monkeypatch.setenv("MATRIX_PYTHON", "3.12")
    report = _materialization_namespace_report(gate)
    row = report["analyzer_evidence"][0]
    if mutation == "wrong-abi":
        row["environment_id"] = "linux-x86_64-cp313"
    elif mutation == "missing-abi":
        del row["environment_id"]
    elif mutation == "missing-digest":
        row["diagnostic"] = row["diagnostic"].replace("sha256:" + "a" * 64, "missing")
    elif mutation == "mixed-launcher":
        row["diagnostic"] = row["diagnostic"].replace("a" * 64, "b" * 64)
    else:
        row["diagnostic"] = "capsule_materialization_failed:offline-install:some analyzer failure"
    with pytest.raises(ValueError, match="namespace"):
        gate.validate_report(report, returncode=1, expected="namespace-denial")


def test_public_install_uses_clean_environment_and_explicit_main_marketplace():
    workflow = (Path(__file__).parents[2] / ".github/workflows/capsule-customer-execution.yml").read_text()
    assert "env -i" in workflow
    assert "SPECFACT_MODULES_BRANCH=main" in workflow
    assert '"$CUSTOMER_ROOT/venv/bin/specfact" module install' in workflow


def test_candidate_installation_uses_separate_published_registry_snapshot():
    import yaml

    workflow = yaml.load(
        (Path(__file__).parents[2] / ".github/workflows/capsule-customer-execution.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    steps = {step["name"]: step for step in workflow["jobs"]["customer"]["steps"] if "name" in step}
    baseline = steps["Checkout published registry baseline for candidate installation"]
    assert baseline["if"] == "github.event_name == 'pull_request'"
    assert baseline["uses"] == "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5"
    assert baseline["with"] == {
        "repository": "nold-ai/specfact-cli-modules",
        "ref": "main",
        "path": ".customer-published-registry",
        "sparse-checkout": "registry",
        "persist-credentials": "false",
    }
    installation = steps["Install official signed module anonymously"]["run"]
    assert 'INSTALLATION_REPOSITORY="$GITHUB_WORKSPACE"' in installation
    assert 'if [ "$MODE" = "candidate" ]; then' in installation
    assert 'INSTALLATION_REPOSITORY="$GITHUB_WORKSPACE/.customer-published-registry"' in installation
    assert installation.count('--repository "$INSTALLATION_REPOSITORY"') == 2
    assert '--repository "$GITHUB_WORKSPACE"' in steps["Exercise cold and warm fixtures and modules repository"]["run"]


def test_targeted_fixture_preserves_clean_inputs_and_has_real_unrelated_failure(tmp_path, monkeypatch):
    import runpy

    gate = _gate()
    clean = tmp_path / "clean"
    targeted = tmp_path / "targeted"
    gate._fixture(clean, defective=False)
    gate._fixture(targeted, defective=False, unrelated_failure=True)
    for name in ("calculator.py", "test_calculator.py"):
        assert (targeted / name).read_bytes() == (clean / name).read_bytes()
    unrelated = runpy.run_path(str(targeted / "test_unrelated.py"))
    with pytest.raises(AssertionError):
        unrelated["test_unrelated"]()


def test_targeted_review_selects_only_calculator_and_reuses_offline_cache(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    gate = _gate()
    report = _namespace_report(gate)
    report.update(assurance_status="PASS", has_unknown_required_evidence=False)
    for row in report["analyzer_evidence"]:
        row.update(execution_state="ran", evidence_outcome="PASS")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        (tmp_path / "targeted.json").write_text(json.dumps(report))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", run)
    gate._review(tmp_path, tmp_path, "targeted", "clean", cache=tmp_path / "cache")
    command, options = calls[0]
    assert command[4] == "calculator.py"
    assert "--scope" not in command
    assert "test_unrelated.py" not in command
    assert options["env"]["SPECFACT_CODE_REVIEW_CAPSULE_OFFLINE"] == "1"


def test_customer_gate_always_adds_separate_targeted_regression(tmp_path, monkeypatch):
    gate = _gate()
    calls = []
    monkeypatch.setattr(gate, "_fixture", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_repository_slice", lambda repository, evidence: repository)
    monkeypatch.setattr(gate, "_run_reviews", lambda *args, **kwargs: ["existing failure"])
    monkeypatch.setattr(gate, "_run_targeted_review", lambda *args, **kwargs: calls.append(args) or [])
    assert gate._run_customer_reviews(tmp_path, tmp_path / "cache", tmp_path / "repository") == ["existing failure"]
    assert calls == [(tmp_path, tmp_path / "cache")]
