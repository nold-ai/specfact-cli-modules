"""Native project-corpus plans fail closed before production integration."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "scripts/macos_managed_boundary/project_corpus.py"


def api() -> Any:
    spec = importlib.util.spec_from_file_location("macos_project_corpus_test", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _verified(plan: dict[str, Any], *, incomplete: str | None = None) -> dict[str, Any]:
    evidence = {
        "broker_verified": True,
        "plan_id": plan["plan_id"],
        "domain": plan["domain"],
        "corpus_identity": plan["corpus_identity"],
        "returncode": 0,
        "stdout": "",
        "stderr": "",
    }
    if plan["domain_kind"] == "preparation":
        evidence["prepared"] = True
        evidence["descriptor_sha256"] = "a" * 64
        evidence["source_identity"] = plan["source_identity"]
    else:
        evidence.update(
            {
                "collected": [plan["tests"][0]],
                "executed": [plan["tests"][0]],
                "pytest_plugins": ["pytest_cov.plugin"],
                "coverage_files": [plan["sources"][0]],
                "native_extension": {
                    "imported": True,
                    "architecture": "arm64",
                    "generic_arm64": True,
                    "closure_admitted": True,
                },
            }
        )
    if incomplete:
        evidence["incomplete"] = incomplete
    return evidence


def _materialize(plans: tuple[dict[str, Any], dict[str, Any]]) -> None:
    source = Path(plans[0]["source_root"])
    for relative in (*plans[0]["sources"], *plans[0]["tests"]):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# pinned corpus fixture\n")


def test_manifest_selects_all_four_managers_and_reconstruction() -> None:
    module = api()
    corpus = module.load_corpus()
    assert {entry["manager"] for entry in corpus["repositories"]} == {"pip", "hatch", "uv", "poetry"}
    assert corpus["reconstructions"][0]["manager"] == "hatch"
    assert corpus["python"] == ["3.11", "3.12", "3.13"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("manager", "brew"),
        ("paths", ["../host.py"]),
        ("paths", ["/tmp/host.py"]),
        ("groups", ["tests; /bin/sh"]),
        ("environment", "../../host"),
    ],
)
def test_manifest_rejects_untrusted_selection(tmp_path: Path, field: str, value: object) -> None:
    module = api()
    corpus = json.loads(module.MANIFEST.read_text())
    corpus["repositories"][0][field] = value
    manifest = tmp_path / "corpus.json"
    manifest.write_text(json.dumps(corpus))
    with pytest.raises(ValueError, match="corpus"):
        module.load_corpus(manifest)


def test_manager_plans_are_fixed_and_domains_are_separate(tmp_path: Path) -> None:
    module = api()
    corpus = module.load_corpus()
    commands = {}
    for entry in corpus["repositories"]:
        plans = module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")
        preparation, execution = plans
        assert preparation["domain_kind"] == "preparation"
        assert execution["domain_kind"] == "execution"
        assert preparation["domain"] != execution["domain"]
        assert not Path(preparation["domain"]).is_relative_to(Path(execution["domain"]))
        assert not Path(execution["domain"]).is_relative_to(Path(preparation["domain"]))
        assert preparation["environment"] == module.FIXED_ENVIRONMENT
        assert execution["environment"] == module.FIXED_ENVIRONMENT
        assert all("homebrew" not in arg.lower() for plan in plans for arg in plan["argv"])
        assert all(arg not in {"sh", "bash", "/bin/sh", "/usr/bin/env"} for plan in plans for arg in plan["argv"])
        commands[entry["manager"]] = preparation["argv"]
    assert commands["pip"][1:5] == ["-I", "-m", "pip", "install"]
    assert "--offline" in commands["hatch"]
    assert "--offline" in commands["uv"] and "--frozen" in commands["uv"]
    assert "--no-interaction" in commands["poetry"] and "--only" in commands["poetry"]


@pytest.mark.parametrize("manager", ["pip", "hatch", "uv", "poetry"])
def test_manager_plan_consumes_authenticated_acquisition_not_upstream_lock(tmp_path: Path, manager: str) -> None:
    module = api()
    entry = next(item for item in module.load_corpus()["repositories"] if item["manager"] == manager)
    acquisition = tmp_path / "acquisition" / manager
    (acquisition / "wheelhouse").mkdir(parents=True)
    descriptor = acquisition / "descriptor.json"
    lock = acquisition / "locks" / f"{manager}.json"
    lock.parent.mkdir()
    descriptor.write_text("{}")
    lock.write_text("{}")
    plans = module.build_plans(
        entry,
        tmp_path / "run",
        Path("/capsule"),
        "3.13",
        acquisition={
            "root": str(acquisition),
            "descriptor": str(descriptor),
            "manager_lock": str(lock),
            "content_sha256": "a" * 64,
        },
    )
    preparation = plans[0]
    assert preparation["acquisition_content_sha256"] == "a" * 64
    assert preparation["wheelhouse"] == str(acquisition / "wheelhouse")
    assert str(descriptor) in preparation["argv"]
    assert str(lock) in preparation["argv"]
    assert not any(argument.endswith(("requirements.lock", "hatch.lock")) for argument in preparation["argv"])


def test_acquisition_binding_rejects_path_or_digest_substitution(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    root = tmp_path / "acquisition"
    (root / "wheelhouse").mkdir(parents=True)
    descriptor = root / "descriptor.json"
    lock = root / "locks/pip.json"
    lock.parent.mkdir()
    descriptor.write_text("{}")
    lock.write_text("{}")
    acquisition = {
        "root": str(root),
        "descriptor": str(descriptor),
        "manager_lock": str(lock),
        "content_sha256": "a" * 64,
    }
    plans = module.build_plans(entry, tmp_path / "run", Path("/capsule"), "3.13", acquisition=acquisition)
    assert module.validate_acquisition_binding(plans[0], acquisition) is None
    with pytest.raises(ValueError, match="acquisition"):
        module.validate_acquisition_binding(plans[0], {**acquisition, "content_sha256": "b" * 64})
    with pytest.raises(ValueError, match="acquisition"):
        module.validate_acquisition_binding(plans[0], {**acquisition, "descriptor": str(tmp_path / "other.json")})


@pytest.mark.parametrize("manager", ["pip", "hatch", "uv", "poetry"])
def test_authenticated_offline_manager_preparation_matrix(tmp_path: Path, manager: str) -> None:
    module = api()
    entry = next(item for item in module.load_corpus()["repositories"] if item["manager"] == manager)
    acquisition_root = tmp_path / "acquisition" / manager
    source = acquisition_root / "source"
    wheelhouse = acquisition_root / "wheelhouse"
    lock = acquisition_root / "locks" / f"{manager}.json"
    descriptor = acquisition_root / "descriptor.json"
    wheelhouse.mkdir(parents=True)
    lock.parent.mkdir()
    descriptor.write_text("authenticated descriptor fixture")
    lock.write_text("authenticated manager lock fixture")
    for relative in entry["paths"]:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# authenticated source fixture\n")
    acquisition = {
        "root": str(acquisition_root),
        "descriptor": str(descriptor),
        "manager_lock": str(lock),
        "content_sha256": "a" * 64,
    }
    payload = tmp_path / "capsule"
    adapter = payload / "bin" / f"specfact-{manager}-adapter"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text("sealed adapter")
    plans = module.build_plans(entry, tmp_path / "run", payload, "3.13", acquisition=acquisition)
    module.materialize_acquired_source(plans[0], acquisition)
    observed = []

    def execute(plan: dict[str, Any]) -> dict[str, Any]:
        observed.append(plan)
        assert plan["environment"] == module.FIXED_ENVIRONMENT
        assert not any("TOKEN" in name or "PASSWORD" in name for name in plan["environment"])
        assert plan["argv"][1] == "--offline"
        return {
            "broker_verified": True,
            "plan_id": plan["plan_id"],
            "domain": plan["domain"],
            "corpus_identity": plan["corpus_identity"],
            "source_identity": plan["source_identity"],
            "returncode": 0,
        }

    result = module.prepare_with_fixed_adapter(plans[0], execute=execute)
    assert result["outcome"] == "PASS"
    assert result["manager"] == manager
    assert len(observed) == 1


def test_fixed_adapter_rejects_mutated_argv_environment_and_host_executable(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    acquisition_root = tmp_path / "acquisition"
    (acquisition_root / "wheelhouse").mkdir(parents=True)
    (acquisition_root / "source").mkdir()
    descriptor = acquisition_root / "descriptor.json"
    lock = acquisition_root / "locks/pip.json"
    lock.parent.mkdir()
    descriptor.write_text("descriptor")
    lock.write_text("lock")
    acquisition = {
        "root": str(acquisition_root),
        "descriptor": str(descriptor),
        "manager_lock": str(lock),
        "content_sha256": "a" * 64,
    }
    plan = module.build_plans(entry, tmp_path / "run", tmp_path / "capsule", "3.13", acquisition=acquisition)[0]
    for mutation in (
        {"argv": ["/bin/sh", "-c", "id"]},
        {"environment": {**plan["environment"], "PIP_INDEX_URL": "https://example.invalid"}},
        {"executable": "/usr/local/bin/pip"},
    ):
        result = module.prepare_with_fixed_adapter({**plan, **mutation}, execute=lambda value: {})
        assert result["outcome"] == "INCOMPLETE"
        assert "fixed manager adapter" in result["reason"]
        assert "no host fallback" in result["reason"]


def test_offline_sdist_build_hook_failure_is_incomplete_and_partial_output_is_removed(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    acquisition_root = tmp_path / "acquisition"
    source = acquisition_root / "source"
    (acquisition_root / "wheelhouse").mkdir(parents=True)
    descriptor = acquisition_root / "descriptor.json"
    lock = acquisition_root / "locks/pip.json"
    lock.parent.mkdir()
    descriptor.write_text("authenticated descriptor")
    lock.write_text("sdist build-hook lock")
    for relative in entry["paths"]:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# source\n")
    acquisition = {
        "root": str(acquisition_root),
        "descriptor": str(descriptor),
        "manager_lock": str(lock),
        "content_sha256": "a" * 64,
    }
    payload = tmp_path / "capsule"
    adapter = payload / "bin/specfact-pip-adapter"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("sealed adapter")
    plan = module.build_plans(entry, tmp_path / "run", payload, "3.13", acquisition=acquisition)[0]
    module.materialize_acquired_source(plan, acquisition)

    def execute(selected: dict[str, Any]) -> dict[str, Any]:
        return {
            "broker_verified": True,
            "plan_id": selected["plan_id"],
            "domain": selected["domain"],
            "corpus_identity": selected["corpus_identity"],
            "source_identity": selected["source_identity"],
            "returncode": 1,
            "stderr": "external SDK compiler unavailable",
        }

    result = module.prepare_with_fixed_adapter(plan, execute=execute)
    assert result["outcome"] == "INCOMPLETE"
    assert result["reason"] == "external SDK/toolchain required; no host fallback"
    assert not Path(plan["prepared_output"]).exists()


def test_acquired_pip_uses_sealed_adapter_not_legacy_internal_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    acquisition_root = tmp_path / "acquisition"
    (acquisition_root / "wheelhouse").mkdir(parents=True)
    descriptor = acquisition_root / "descriptor.json"
    lock = acquisition_root / "locks/pip.json"
    lock.parent.mkdir()
    descriptor.write_text("descriptor")
    lock.write_text("lock")
    acquisition = {
        "root": str(acquisition_root),
        "descriptor": str(descriptor),
        "manager_lock": str(lock),
        "content_sha256": "a" * 64,
    }
    payload = tmp_path / "capsule"
    plan = module.build_plans(entry, tmp_path / "run", payload, "3.13", acquisition=acquisition)[0]
    observed = []
    from scripts.macos_managed_boundary import python_analyzers

    def execute(
        root: Path,
        candidate: dict[str, Any],
        domain: Path,
        target: Path,
        argv: list[str],
        *,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        observed.append((root, candidate, domain, target, argv, request))
        return {"broker_verified": True, "returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(python_analyzers, "execute", execute)
    result = module.native_manager_executor(tmp_path, {"payload": payload})(plan)
    assert result["returncode"] == 0
    assert len(observed) == 1
    assert observed[0][3] == payload / "bin/specfact-pip-adapter"
    assert observed[0][4] == plan["argv"]


def test_project_cannot_select_arbitrary_argv(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    entry["argv"] = ["/bin/sh", "-c", "id"]
    with pytest.raises(ValueError, match=r"corpus.*field"):
        module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")


def test_managed_transport_binds_plan_domain_and_identity(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    plans = module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")
    _materialize(plans)
    observed = []

    def transport(envelope: dict[str, Any]) -> dict[str, Any]:
        observed.append(envelope)
        return _verified(envelope["plan"])

    evidence = module.run_entry(entry, plans, transport)
    assert evidence["outcome"] == "PASS"
    assert [item["plan"]["domain_kind"] for item in observed] == ["preparation", "execution"]
    assert all(item["request"]["tool"] == item["plan"]["plan_id"] for item in observed)
    assert all(item["request"]["cwd"] == item["plan"]["domain"] for item in observed)


def test_unverified_or_cross_domain_response_is_incomplete(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    plans = module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")
    _materialize(plans)

    def transport(envelope: dict[str, Any]) -> dict[str, Any]:
        evidence = _verified(envelope["plan"])
        if envelope["plan"]["domain_kind"] == "execution":
            evidence["domain"] = str(tmp_path / "preparation")
        return evidence

    result = module.run_entry(entry, plans, transport)
    assert result["outcome"] == "INCOMPLETE"
    assert "domain" in result["reason"] and "no host fallback" in result["reason"]


def test_missing_or_wrong_pinned_source_is_incomplete(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    plans = module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")
    assert module.run_entry(entry, plans, lambda envelope: _verified(envelope["plan"]))["outcome"] == "INCOMPLETE"
    _materialize(plans)

    def transport(envelope: dict[str, Any]) -> dict[str, Any]:
        evidence = _verified(envelope["plan"])
        if envelope["plan"]["domain_kind"] == "preparation":
            evidence["source_identity"] = "0" * 40
        return evidence

    result = module.run_entry(entry, plans, transport)
    assert result["outcome"] == "INCOMPLETE"
    assert "source identity" in result["reason"] and "no host fallback" in result["reason"]


def test_unsupported_spawning_is_actionable_incomplete(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    plans = module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")
    _materialize(plans)

    def transport(envelope: dict[str, Any]) -> dict[str, Any]:
        return _verified(
            envelope["plan"],
            incomplete="managed subprocess incomplete: project requested preexec_fn; no host fallback",
        )

    result = module.run_entry(entry, plans, transport)
    assert result["outcome"] == "INCOMPLETE"
    assert "preexec_fn" in result["reason"] and "no host fallback" in result["reason"]


@pytest.mark.parametrize(
    "missing",
    ["collected", "executed", "pytest_plugins", "coverage_files", "native_extension"],
)
def test_execution_requires_tests_plugin_coverage_and_arm64_extension(tmp_path: Path, missing: str) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    plans = module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")
    _materialize(plans)

    def transport(envelope: dict[str, Any]) -> dict[str, Any]:
        evidence = _verified(envelope["plan"])
        if envelope["plan"]["domain_kind"] == "execution":
            evidence.pop(missing)
        return evidence

    result = module.run_entry(entry, plans, transport)
    assert result["outcome"] == "INCOMPLETE"
    assert "required execution evidence" in result["reason"]


def test_malformed_execution_evidence_is_incomplete(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["repositories"][0]
    plans = module.build_plans(entry, tmp_path, Path("/capsule"), "3.13")
    _materialize(plans)

    def transport(envelope: dict[str, Any]) -> dict[str, Any]:
        evidence = _verified(envelope["plan"])
        if envelope["plan"]["domain_kind"] == "execution":
            evidence["collected"] = {"project-selected": "command"}
        return evidence

    result = module.run_entry(entry, plans, transport)
    assert result["outcome"] == "INCOMPLETE"
    assert "malformed" in result["reason"] and "no host fallback" in result["reason"]


@pytest.mark.parametrize("manager", ["pip", "hatch", "uv", "poetry"])
def test_fixed_manager_adapter_requires_sealed_executable_and_lock(tmp_path: Path, manager: str) -> None:
    module = api()
    entry = next(item for item in module.load_corpus()["repositories"] if item["manager"] == manager)
    plans = module.build_plans(entry, tmp_path, tmp_path / "capsule", "3.13")
    _materialize(plans)
    result = module.prepare_with_fixed_adapter(plans[0])
    assert result["outcome"] == "INCOMPLETE"
    assert result["manager"] == manager
    assert result["missing_artifacts"]
    assert "no host fallback" in result["reason"]


def test_fixed_pip_adapter_executes_exact_broker_command_and_seals_output(tmp_path: Path) -> None:
    module = api()
    entry = next(item for item in module.load_corpus()["repositories"] if item["manager"] == "pip")
    payload = tmp_path / "capsule"
    plans = module.build_plans(entry, tmp_path, payload, "3.13")
    _materialize(plans)
    source = Path(plans[0]["source_root"])
    (source / "requirements.lock").write_text("fixture==1 --hash=sha256:" + "a" * 64 + "\n")
    (payload / "bin").mkdir(parents=True)
    (payload / "bin/python3.13").write_text("sealed interpreter")
    (payload / "site-packages/pip").mkdir(parents=True)
    observed = []

    def execute(plan: dict[str, Any]) -> dict[str, Any]:
        observed.append(plan["argv"])
        return {
            "broker_verified": True,
            "plan_id": plan["plan_id"],
            "domain": plan["domain"],
            "corpus_identity": plan["corpus_identity"],
            "source_identity": plan["source_identity"],
            "returncode": 0,
        }

    result = module.prepare_with_fixed_adapter(plans[0], execute=execute)
    assert result["outcome"] == "PASS"
    assert observed == [plans[0]["argv"]]
    assert observed[0][1:5] == ["-I", "-m", "pip", "install"]
    assert "--no-index" in observed[0] and "--require-hashes" in observed[0]
    assert result["descriptor_sha256"] and result["inventory_sha256"]


def test_fixed_manager_workflow_hands_sealed_output_to_execution_request(tmp_path: Path) -> None:
    module = api()
    entry = next(item for item in module.load_corpus()["repositories"] if item["manager"] == "pip")
    payload = tmp_path / "capsule"
    plans = module.build_plans(entry, tmp_path, payload, "3.13")
    _materialize(plans)
    source = Path(plans[0]["source_root"])
    (source / "requirements.lock").write_text("fixture==1 --hash=sha256:" + "a" * 64 + "\n")
    (payload / "bin").mkdir(parents=True)
    (payload / "bin/python3.13").write_text("sealed interpreter")
    (payload / "site-packages/pip").mkdir(parents=True)

    def prepare(plan: dict[str, Any]) -> dict[str, Any]:
        return {
            "broker_verified": True,
            "plan_id": plan["plan_id"],
            "domain": plan["domain"],
            "corpus_identity": plan["corpus_identity"],
            "source_identity": plan["source_identity"],
            "returncode": 0,
        }

    def execute(envelope: dict[str, Any]) -> dict[str, Any]:
        plan = envelope["plan"]
        assert Path(plan["prepared_input"]).is_dir()
        evidence = _verified(plan)
        evidence["descriptor_sha256"] = plan["descriptor_sha256"]
        evidence["inventory_sha256"] = plan["inventory_sha256"]
        return evidence

    result = module.run_fixed_entry(entry, plans, prepare, execute)
    assert result["outcome"] == "PASS"
    assert result["descriptor_sha256"]
    assert result["inventory_sha256"]


def test_prepared_inventory_is_deterministic_and_handoff_is_domain_bound(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["reconstructions"][0]
    plans = module.build_plans(entry, tmp_path, tmp_path / "capsule", "3.13")
    module.materialize_local_reconstruction(entry, Path(plans[0]["source_root"]))
    prepared = Path(plans[0]["prepared_output"])
    module.copy_declared_project(plans[0], prepared)
    first = module.seal_prepared_output(plans[0])
    second = module.seal_prepared_output(plans[0])
    assert first == second
    handed = module.handoff_prepared_output(plans[0], plans[1], first)
    assert handed["descriptor_sha256"] == first["descriptor_sha256"]
    assert handed["inventory_sha256"] == first["inventory_sha256"]
    assert module.verify_prepared_output(Path(plans[1]["prepared_input"]), first["inventory"]) is None

    other = dict(plans[1], domain=str(tmp_path / "foreign-execution"))
    with pytest.raises(ValueError, match="execution domain"):
        module.handoff_prepared_output(plans[0], other, first)


def test_prepared_output_tampering_blocks_handoff_and_execution(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["reconstructions"][0]
    plans = module.build_plans(entry, tmp_path, tmp_path / "capsule", "3.13")
    module.materialize_local_reconstruction(entry, Path(plans[0]["source_root"]))
    module.copy_declared_project(plans[0], Path(plans[0]["prepared_output"]))
    sealed = module.seal_prepared_output(plans[0])
    selected = Path(plans[0]["prepared_output"]) / plans[0]["sources"][0]
    selected.write_text("tampered\n")
    with pytest.raises(ValueError, match="inventory"):
        module.handoff_prepared_output(plans[0], plans[1], sealed)


def test_external_build_toolchain_is_actionable_incomplete(tmp_path: Path) -> None:
    module = api()
    entry = module.load_corpus()["reconstructions"][0]
    plans = module.build_plans(entry, tmp_path, tmp_path / "capsule", "3.13")
    source = Path(plans[0]["source_root"])
    module.materialize_local_reconstruction(entry, source)
    (source / "native.c").write_text("int fixture(void) { return 0; }\n")
    result = module.prepare_with_fixed_adapter(plans[0])
    assert result["outcome"] == "INCOMPLETE"
    assert result["reason"] == "external SDK/toolchain required; no host fallback"
    assert not Path(plans[0]["prepared_output"]).exists()


def test_matrix_requires_every_manager_and_never_claims_production(tmp_path: Path) -> None:
    module = api()
    corpus = module.load_corpus()

    def transport(envelope: dict[str, Any]) -> dict[str, Any]:
        return _verified(envelope["plan"])

    for entry in corpus["repositories"]:
        _materialize(module.build_plans(entry, tmp_path, Path("/capsule"), "3.13"))
    report = module.run_matrix(tmp_path, Path("/capsule"), "3.13", transport, corpus=corpus)
    assert report == {
        "schema": "specfact-macos-project-corpus-v1",
        "abi": "3.13",
        "managers": ["hatch", "pip", "poetry", "uv"],
        "projects": 4,
        "passed": 4,
        "incomplete": 0,
        "candidate_passed": True,
        "production_approved": False,
    }


def test_available_manager_matrix_preserves_exact_source_and_artifact_blockers(tmp_path: Path) -> None:
    module = api()
    payload = tmp_path / "capsule"
    matrix = module.available_manager_matrix(tmp_path, payload, "3.13")
    assert [row["manager"] for row in matrix["rows"]] == ["pip", "hatch", "uv", "poetry"]
    assert matrix["passed"] == 0 and matrix["incomplete"] == 4
    assert matrix["production_approved"] is False
    for row in matrix["rows"]:
        assert row["outcome"] == "INCOMPLETE"
        assert row["missing_artifacts"]
        assert "no host fallback" in row["reason"]


def test_physical_prepared_project_observer() -> None:
    selected = os.environ.get("SPECFACT_MACOS_PROJECT_CANDIDATE")
    if not selected:
        pytest.skip("maintainer native analyzer candidate not selected")
    assert platform.system() == "Darwin" and platform.machine() == "arm64"
    result = api().run_physical_observer(Path(selected))
    assert result["broker_verified"] is True
    assert result["pytest_executed"] is True
    assert result["plugin_loaded"] is True
    assert result["coverage_recorded"] is True
    assert result["native_extension_imported"] is True
    assert result["native_extension_architecture"] == "arm64"
    assert result["production_approved"] is False


def test_physical_hatch_reconstruction_reports_exact_missing_artifacts() -> None:
    selected = os.environ.get("SPECFACT_MACOS_PROJECT_CANDIDATE")
    if not selected:
        pytest.skip("maintainer native analyzer candidate not selected")
    result = api().run_physical_reconstruction_admission(Path(selected))
    assert result["manager"] == "hatch"
    assert result["broker_verified"] is True
    assert result["outcome"] == "INCOMPLETE"
    assert "lock:hatch.lock" in result["missing_artifacts"]
    assert "sealed-distribution:pyodbc" in result["missing_artifacts"]
    assert "sealed-distribution:pytest-asyncio" in result["missing_artifacts"]
    assert "no host fallback" in result["reason"]
    assert result["production_approved"] is False
