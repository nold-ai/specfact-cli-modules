"""C14 red tests for signed analyzer capsules and project runtime layers."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


SUPPORTED_ABIS = ("cp311", "cp312", "cp313")
ANALYZER_COMPONENTS = {
    "pytest": "9.0.3",
    "coverage": "7.15.4",
    "basedpyright": "1.39.10",
    "pylint": "4.0.7",
    "ruff": "0.15.12",
    "crosshair-tool": "0.0.109",
    "radon": "6.0.1",
    "semgrep": "1.136.0",
}


@pytest.fixture
def toolchain_api() -> Any:
    from specfact_code_review.run import toolchain

    return toolchain


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def _valid_environment(abi: str) -> dict[str, Any]:
    components = [
        {
            "kind": "python_distribution",
            "id": name,
            "version": version,
            "specifier": f"=={version}",
            "wheel": f"{name}-{version}-{abi}-manylinux_2_17_x86_64.whl",
            "wheel_sha256": _digest(chr(97 + index)),
            "record_digest": _digest(chr(107 + index)),
            "entry_point": name,
            "interpreter": "/opt/specfact/python/bin/python",
        }
        for index, (name, version) in enumerate(sorted(ANALYZER_COMPONENTS.items()))
    ]
    return {
        "id": f"linux-x86_64-{abi}",
        "environment_kind": "analyzer_runtime_capsule",
        "platform": "linux-x86_64",
        "python_abi": abi,
        "oci": {
            "registry": "https://ghcr.io",
            "repository": "nold-ai/specfact-review-runtime",
            "manifest": _digest("1"),
            "config": _digest("2"),
            "layers": [
                {
                    "digest": _digest("3"),
                    "diff_id": _digest("4"),
                    "media_type": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "size": 4096,
                }
            ],
            "redirect_allowlist": ["ghcr.io", "pkg-containers.githubusercontent.com"],
        },
        "paths": {
            "root": "/opt/specfact",
            "interpreter": "/opt/specfact/python/bin/python",
            "stdlib": "/opt/specfact/python/lib/python3",
            "extensions": "/opt/specfact/python/lib/python3/lib-dynload",
            "loader": "/opt/specfact/lib/ld-linux-x86-64.so.2",
            "libraries": "/opt/specfact/lib",
            "bootstrap": "/opt/specfact/bootstrap/runner.py",
            "wheelhouse": "/opt/specfact/wheelhouse",
        },
        "components": components,
        "dependency_edges": [["pytest", "pluggy"], ["pytest-cov", "coverage"], ["crosshair-tool", "z3-solver"]],
        "bootstrap_allowlist": ["pip", "setuptools", "wheel"],
        "native_tools": [
            {
                "kind": "native_executable",
                "id": "bwrap-static",
                "path": "/opt/specfact/bin/bwrap-static",
                "format": "ELF",
                "architecture": "x86_64",
                "linkage": "static",
                "interpreter": [],
                "needed": [],
                "sha256": _digest("5"),
            }
        ],
        "wheelhouse": {
            item["wheel"]: {"sha256": item["wheel_sha256"], "size": 1024, "platform": "manylinux_2_17_x86_64"}
            for item in components
        },
        "root_manifest_digest": _digest("6"),
        "closure_digest": _digest("7"),
    }


def _valid_lock() -> dict[str, Any]:
    return {
        "schema": "toolchain-lock-schema-1",
        "profile": "pr-range-v1",
        "environments": [_valid_environment(abi) for abi in SUPPORTED_ABIS],
        "projection_digest": _digest("8"),
    }


def test_pr_range_rejects_unpinned_or_mismatched_loader_toolchain(toolchain_api: Any) -> None:
    lock = _valid_lock()
    lock["environments"][0]["components"][0]["specifier"] = ">=1"

    result = toolchain_api.validate_toolchain_lock(lock)

    assert result.status == "UNKNOWN"
    assert result.reason == "unpinned_toolchain_component"


def test_toolchain_identity_is_portable_across_install_roots(toolchain_api: Any, tmp_path: Path) -> None:
    lock = _valid_lock()
    left = toolchain_api.canonical_toolchain_identity(lock, storage_root=tmp_path / "left")
    right = toolchain_api.canonical_toolchain_identity(lock, storage_root=tmp_path / "right")

    assert left == right
    assert str(tmp_path) not in left.digest


def test_signed_toolchain_lock_closes_complete_dependency_graph(toolchain_api: Any) -> None:
    result = toolchain_api.validate_toolchain_lock(_valid_lock())

    assert result.status == "PASS"
    assert {component.name for component in result.components} >= set(ANALYZER_COMPONENTS)
    assert {"pluggy", "nodejs-wheel-binaries", "z3-solver"} <= {component.name for component in result.components}


def test_locked_analyzer_environment_excludes_host_core_packages(toolchain_api: Any) -> None:
    result = toolchain_api.validate_toolchain_lock(
        _valid_lock(),
        host_distributions={"specfact-cli": "0.55.1", "pydantic": "2.13.4"},
    )

    assert result.status == "PASS"
    assert "specfact-cli" not in result.analyzer_distributions


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_locked_analyzer_environment_rejects_extra_or_missing_members(toolchain_api: Any, mutation: str) -> None:
    lock = _valid_lock()
    components = lock["environments"][0]["components"]
    if mutation == "missing":
        components.pop()
    else:
        components.append({"kind": "python_distribution", "id": "ambient", "version": "1", "specifier": "==1"})

    result = toolchain_api.validate_toolchain_lock(lock)

    assert result.status == "UNKNOWN"


def test_runtime_capsule_closes_interpreter_native_runtime(toolchain_api: Any) -> None:
    result = toolchain_api.validate_toolchain_lock(_valid_lock())

    assert result.status == "PASS"
    for environment in result.environments:
        assert environment.interpreter.startswith("/opt/specfact/")
        assert environment.stdlib
        assert environment.extensions
        assert environment.dynamic_loader
        assert environment.shared_libraries
        assert environment.bootstrap


def test_runtime_capsule_identity_is_portable_across_storage_roots(toolchain_api: Any, tmp_path: Path) -> None:
    lock = _valid_lock()
    first = toolchain_api.materialize_capsule(lock, environment_id="linux-x86_64-cp312", storage_root=tmp_path / "a")
    second = toolchain_api.materialize_capsule(lock, environment_id="linux-x86_64-cp312", storage_root=tmp_path / "b")

    assert first.identity == second.identity
    assert first.root != second.root


@pytest.mark.parametrize("cache_hit", [True, False])
def test_runtime_capsule_acquires_pinned_oci_layers_from_registry_or_verified_cache(
    toolchain_api: Any, tmp_path: Path, cache_hit: bool
) -> None:
    result = toolchain_api.acquire_oci_distribution(
        _valid_lock()["environments"][0]["oci"],
        cache_root=tmp_path / "cache",
        simulate_cache_hit=cache_hit,
    )

    assert result.status == "PASS"
    assert result.source == ("verified_cache" if cache_hit else "signed_registry")
    assert all(record.digest.startswith("sha256:") for record in result.records)


def test_runtime_capsule_fresh_cache_miss_installs_only_pinned_wheelhouse(toolchain_api: Any, tmp_path: Path) -> None:
    result = toolchain_api.materialize_capsule(
        _valid_lock(),
        environment_id="linux-x86_64-cp312",
        storage_root=tmp_path,
        empty_cache=True,
    )

    assert result.status == "PASS"
    assert result.install_policy.indexes_enabled is False
    assert set(result.installed_distributions) == set(result.locked_distributions) | set(result.bootstrap_distributions)


def test_offline_install_executes_verified_bubblewrap_from_same_open_descriptor(
    toolchain_api: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"signed static bubblewrap"
    bubblewrap = tmp_path / "opt/specfact/bin/bwrap-static"
    bubblewrap.parent.mkdir(parents=True)
    bubblewrap.write_bytes(payload)
    bubblewrap.chmod(0o755)
    environment = {
        "paths": {
            "analyzers": "/opt/specfact/analyzers",
            "interpreter": "/opt/specfact/python/bin/python",
            "loader": "/opt/specfact/lib/ld-linux-x86-64.so.2",
            "libraries": "/opt/specfact/lib",
            "wheelhouse": "/opt/specfact/wheelhouse",
        },
        "native_tools": [
            {
                "id": "bubblewrap-static",
                "path": "/opt/specfact/bin/bwrap-static",
                "launch_mode": "same-open-descriptor",
                "executable_sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
            }
        ],
    }

    def observe_launch(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        descriptor = kwargs["pass_fds"][0]
        assert command[0] == f"/proc/self/fd/{descriptor}"
        os.lseek(descriptor, 0, os.SEEK_SET)
        assert os.read(descriptor, len(payload)) == payload
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(toolchain_api.subprocess, "run", observe_launch)

    toolchain_api._offline_install(tmp_path, environment, ())


def test_checkpoint_binds_canonical_toolchain_lock_projection(toolchain_api: Any) -> None:
    lock = _valid_lock()

    canonical = toolchain_api.canonical_json_digest({k: v for k, v in lock.items() if k != "projection_digest"})

    assert toolchain_api.validate_checkpoint_projection(lock, canonical).status == "PASS"
    assert toolchain_api.validate_checkpoint_projection(lock, _digest("f")).status == "UNKNOWN"


@pytest.mark.parametrize(
    "redirects",
    [
        ["http://ghcr.io/v2/blob"],
        ["https://evil.example/v2/blob"],
        ["https://ghcr.io/v2/blob", "https://evil.example/blob"],
    ],
)
def test_runtime_capsule_rejects_redirect_downgrade_or_credential_forwarding(
    toolchain_api: Any, tmp_path: Path, redirects: list[str]
) -> None:
    result = toolchain_api.acquire_oci_distribution(
        _valid_lock()["environments"][0]["oci"],
        cache_root=tmp_path,
        redirect_chain=redirects,
        credential="secret",
    )

    assert result.status == "UNKNOWN"
    assert not any(hop.credential_sent for hop in result.unauthorized_hops)


@pytest.mark.parametrize("field", ["registry", "repository", "manifest", "layers"])
def test_runtime_capsule_rejects_movable_or_unsafe_oci_source(toolchain_api: Any, field: str) -> None:
    lock = _valid_lock()
    oci = lock["environments"][0]["oci"]
    oci[field] = "latest" if field != "layers" else []

    result = toolchain_api.validate_toolchain_lock(lock)

    assert result.status == "UNKNOWN"


def _installed_payload(root: Path) -> dict[str, Any]:
    package = root / "specfact_code_review"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VERSION='1.0.0'\n", encoding="utf-8")
    (package / "builtin.py").write_text("def main(): return 0\n", encoding="utf-8")
    resources = package / "resources"
    resources.mkdir()
    (resources / "policy.json").write_text('{"policy":"sealed"}\n', encoding="utf-8")
    entries = []
    for path in sorted(item for item in package.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        entries.append(f"{relative}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    checksum = "sha256:" + hashlib.sha256("\n".join(entries).encode()).hexdigest()
    return {
        "module_name": "nold-ai/specfact-code-review",
        "version": "1.0.0",
        "checksum": checksum,
        "signature": "signature",
        "key_fingerprint": _digest("b"),
        "loader_origin": "official-marketplace",
        "installed_root": str(root),
    }


def _core_0_55_1_discovered_install(root: Path, *, user_modules_root: Path) -> tuple[Any, str, Path]:
    from specfact_cli.models.module_package import IntegrityInfo, ModulePackageMetadata, PublisherInfo
    from specfact_cli.registry.module_discovery import DiscoveredModule

    metadata = _installed_payload(root)
    registry_id = metadata["module_name"]
    (root / ".specfact-registry-id").write_text(registry_id, encoding="utf-8")
    (root / ".specfact-install-verified-checksum").write_text(metadata["checksum"], encoding="utf-8")
    public_key = root.parent / "module-signing-public.pem"
    public_key.write_text("approved public key bytes\n", encoding="utf-8")
    package_metadata = ModulePackageMetadata(
        name=registry_id,
        version=metadata["version"],
        publisher=PublisherInfo(name="nold-ai", email="security@nold.ai"),
        integrity=IntegrityInfo(checksum=metadata["checksum"], signature=metadata["signature"]),
    )
    return DiscoveredModule(root, package_metadata, "user"), registry_id, public_key


def test_builtin_module_payload_manifest_covers_complete_signed_package(toolchain_api: Any, tmp_path: Path) -> None:
    metadata = _installed_payload(tmp_path / "installed")

    result = toolchain_api.verify_installed_module_payload(metadata)

    assert result.status == "PASS"
    assert {entry.path for entry in result.manifest} == {
        "specfact_code_review/__init__.py",
        "specfact_code_review/builtin.py",
        "specfact_code_review/resources/policy.json",
    }


def test_builtin_analyzers_boot_from_signed_capsule_payload_without_controller_paths(
    toolchain_api: Any, tmp_path: Path
) -> None:
    payload = toolchain_api.verify_installed_module_payload(_installed_payload(tmp_path / "installed"))
    capsule = toolchain_api.install_builtin_payload(payload, capsule_root=tmp_path / "capsule")

    assert capsule.status == "PASS"
    assert capsule.destination == "/opt/specfact/builtin/specfact_code_review"
    assert all("controller" not in path for path in capsule.import_paths)


@pytest.mark.parametrize("mutation", ["missing", "content", "symlink"])
def test_builtin_analyzer_missing_or_drifted_payload_is_unknown(
    toolchain_api: Any, tmp_path: Path, mutation: str
) -> None:
    metadata = _installed_payload(tmp_path / "installed")
    target = Path(metadata["installed_root"]) / "specfact_code_review/builtin.py"
    if mutation == "missing":
        target.unlink()
    elif mutation == "content":
        target.write_text("changed=True\n", encoding="utf-8")
    else:
        target.unlink()
        target.symlink_to("__init__.py")

    result = toolchain_api.verify_installed_module_payload(metadata)

    assert result.status == "UNKNOWN"


def test_builtin_payload_boots_after_marketplace_archive_discard(toolchain_api: Any, tmp_path: Path) -> None:
    metadata = _installed_payload(tmp_path / "installed")
    archive = tmp_path / "module.tar.gz"
    archive.write_bytes(b"discard me")
    archive.unlink()

    result = toolchain_api.install_builtin_payload(
        toolchain_api.verify_installed_module_payload(metadata), capsule_root=tmp_path / "capsule"
    )

    assert result.status == "PASS"
    assert result.archive_required is False


@pytest.mark.parametrize("field", ["loader_origin", "key_fingerprint", "signature", "checksum"])
def test_builtin_payload_rejects_untrusted_install_origin_or_key(
    toolchain_api: Any, tmp_path: Path, field: str
) -> None:
    metadata = _installed_payload(tmp_path / "installed")
    metadata[field] = "untrusted"

    assert toolchain_api.verify_installed_module_payload(metadata).status == "UNKNOWN"


def test_builtin_payload_derives_core_0_55_1_install_handoff(
    toolchain_api: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specfact_cli.registry import module_installer

    user_root = tmp_path / "user-modules"
    install_root = user_root / "nold-ai" / "specfact-code-review"
    discovered, registry_id, public_key = _core_0_55_1_discovered_install(install_root, user_modules_root=user_root)
    monkeypatch.setattr(module_installer, "verify_module_artifact", lambda *args, **kwargs: True)

    result = toolchain_api.derive_core_0_55_1_install_handoff(
        discovered,
        expected_registry_id=registry_id,
        user_modules_root=user_root,
        marketplace_modules_root=tmp_path / "marketplace-modules",
        public_key_path=public_key,
    )

    assert result.status == "PASS"
    assert result.identity.derivation_schema == "core-v0.55.1-installed-module-handoff-v1"
    assert result.identity.discovered_source == "user"
    assert result.identity.install_root_class == "user"
    assert result.identity.registry_id == registry_id
    assert result.identity.install_verified_checksum == discovered.metadata.integrity.checksum
    assert result.identity.artifact_verification_result is True
    assert not hasattr(result.identity, "loader_registration_digest")


def test_candidate_payload_identity_is_not_official_install(toolchain_api: Any) -> None:
    result = toolchain_api.verify_candidate_module_payload(
        {
            "repository": "nold-ai/specfact-cli-modules",
            "commit_sha": "1" * 40,
            "tree_sha": "2" * 40,
            "module_package_digest": _digest("3"),
            "payload_manifest_digest": _digest("4"),
            "workflow": "pr-orchestrator.yml",
            "workflow_ref": "refs/heads/dev",
            "run_id": "1234",
            "run_attempt": "1",
            "job": "exact-core-compatibility",
        }
    )

    assert result.status == "PASS"
    assert result.identity.schema == "verified-candidate-module-payload-v1"
    assert result.identity.allowed_use == "protected-pre-release-only"
    assert result.identity.official_install_provenance is False
    assert result.identity.pr_range_authority is False


def test_post_base_bootstrap_and_composite_identity_bind_copied_payload(toolchain_api: Any, tmp_path: Path) -> None:
    payload = toolchain_api.verify_installed_module_payload(_installed_payload(tmp_path / "installed"))

    result = toolchain_api.compose_post_base_capsule(
        payload,
        capsule_root=tmp_path / "capsule",
        immutable_base_root_digest=_digest("5"),
        analyzer_installed_set_digest=_digest("6"),
        native_launcher_digest=_digest("7"),
        project_runtime_identity="not-applicable",
    )

    assert result.status == "PASS"
    assert result.bootstrap_schema == "sealed-bootstrap-v2"
    assert result.composite_schema == "capsule-composite-identity-v1"
    assert result.immutable_base_root_digest == _digest("5")
    assert result.module_payload_manifest_digest == toolchain_api.canonical_json_digest(
        [{"digest": entry.digest, "path": entry.path} for entry in payload.manifest]
    )
    assert result.bootstrap_digest.startswith("sha256:")
    assert result.final_composite_root_manifest_digest.startswith("sha256:")
    bootstrap = tmp_path / "capsule/opt/specfact/bootstrap/sealed_bootstrap.py"
    assert bootstrap.is_file()
    bootstrap_source = bootstrap.read_text(encoding="utf-8")
    assert 'ANALYZER_ROOT = "/opt/specfact/analyzers"' in bootstrap_source
    assert 'BUILTIN_ROOT = "/opt/specfact/builtin"' in bootstrap_source


def _project_runtime_descriptor() -> dict[str, Any]:
    return {
        "schema": "project-runtime-layer-v1",
        "target": {
            "repository": "nold-ai/consumer",
            "commit_sha": "1" * 40,
            "tree_sha": "2" * 40,
        },
        "source_lock_paths": [{"path": "uv.lock", "blob_sha": "3" * 40, "content_sha256": _digest("c")}],
        "distributions": [
            {
                "name": "consumer-dependency",
                "version": "1.0",
                "payload_digest": _digest("a"),
                "dependencies": [],
                "entry_points": [],
            }
        ],
        "native_components": [],
        "oci": {
            "registry": "https://ghcr.io",
            "repository": "nold-ai/consumer-runtime",
            "manifest_digest": _digest("e"),
            "config_digest": _digest("f"),
            "layers": [{"digest": _digest("1"), "diff_id": _digest("2"), "size": 1024}],
        },
        "build": {
            "workflow": "build-runtime",
            "ref": "refs/heads/dev",
            "run_id": 42,
            "run_attempt": 1,
            "artifact_id": 43,
            "artifact_digest": _digest("d"),
        },
        "attestation": {
            "predicate_type": "https://slsa.dev/provenance/v1",
            "subject_digest": _digest("d"),
            "builder_identity": "https://github.com/nold-ai/consumer/.github/workflows/runtime.yml@refs/heads/dev",
            "signature": "signed-attestation",
        },
        "root_manifest": {
            "algorithm": "canonical-json-v1",
            "digest": _digest("9"),
            "python_abi": "cp312",
            "platform_tag": "linux-x86_64",
            "site_packages": "/opt/specfact/project-runtime/site-packages",
        },
    }


def test_project_runtime_layer_binds_target_tip_dependency_inputs(toolchain_api: Any) -> None:
    result = toolchain_api.validate_project_runtime_layer(_project_runtime_descriptor(), expected_target="1" * 40)

    assert result.status == "PASS"
    assert result.source_lock_digest.startswith("sha256:")
    assert result.target_commit == "1" * 40


@pytest.mark.parametrize("reserved", ["specfact_code_review", "pytest", "sitecustomize"])
def test_project_runtime_layer_cannot_shadow_reserved_runner_components(toolchain_api: Any, reserved: str) -> None:
    descriptor = _project_runtime_descriptor()
    descriptor["distributions"].append(
        {
            "name": reserved,
            "version": "1",
            "payload_digest": _digest("b"),
            "dependencies": [],
            "entry_points": [],
        }
    )

    result = toolchain_api.validate_project_runtime_layer(descriptor, expected_target="1" * 40)

    assert result.status == "UNKNOWN"
    assert result.reason == "reserved_import_collision"


def test_project_runtime_layer_is_identical_across_snapshots(toolchain_api: Any) -> None:
    layer = toolchain_api.validate_project_runtime_layer(_project_runtime_descriptor(), expected_target="1" * 40)

    result = toolchain_api.bind_project_runtime_to_snapshots(layer, snapshots=("merge_base", "head"))

    assert result["merge_base"].identity == result["head"].identity


@pytest.mark.parametrize("mutation", ["candidate-target", "missing-attestation", "host-path", "mutable-oci"])
def test_project_runtime_layer_rejects_untrusted_or_candidate_inputs(toolchain_api: Any, mutation: str) -> None:
    descriptor = _project_runtime_descriptor()
    if mutation == "candidate-target":
        descriptor["target"]["commit_sha"] = "9" * 40
    elif mutation == "missing-attestation":
        descriptor.pop("attestation")
    elif mutation == "host-path":
        descriptor["root_manifest"]["site_packages"] = "/usr/lib/python/site-packages"
    else:
        descriptor["oci"]["manifest_digest"] = "latest"

    assert toolchain_api.validate_project_runtime_layer(descriptor, expected_target="1" * 40).status == "UNKNOWN"


def test_candidate_project_dependency_input_change_is_governed_unknown(toolchain_api: Any) -> None:
    result = toolchain_api.validate_source_lock_transition(
        target_tip={"uv.lock": _digest("a")}, candidate={"uv.lock": _digest("b")}
    )

    assert result.status == "UNKNOWN"
    assert result.reason == "candidate_project_dependency_input_change"


def test_missing_project_runtime_is_unknown_not_not_applicable(toolchain_api: Any) -> None:
    result = toolchain_api.require_project_runtime(member="targeted-pytest-coverage", descriptor=None)

    assert result.status == "UNKNOWN"


def test_non_importing_member_cannot_mount_project_runtime_layer(toolchain_api: Any) -> None:
    result = toolchain_api.authorize_project_runtime_mount(member="ruff", descriptor=_project_runtime_descriptor())

    assert result.status == "UNKNOWN"


def test_non_reserved_snapshot_import_precedes_project_runtime(toolchain_api: Any) -> None:
    order = toolchain_api.import_search_order(
        member="targeted-pytest-coverage",
        snapshot_root="/opt/specfact/snapshot",
        project_root="/opt/specfact/project/site-packages",
    )

    assert order == ("capsule-reserved-finder", "/opt/specfact/snapshot", "/opt/specfact/project/site-packages")


def test_attested_pytest_plugin_identity_is_bound_by_project_runtime(toolchain_api: Any) -> None:
    descriptor = _project_runtime_descriptor()
    descriptor["distributions"].append(
        {
            "name": "fixture-plugin",
            "version": "1.0",
            "payload_digest": _digest("a"),
            "dependencies": [],
            "entry_points": ["pytest11:fixture_plugin"],
        }
    )
    descriptor["pytest_plugins"] = [
        {
            "distribution": "fixture-plugin",
            "version": "1.0",
            "payload_digest": _digest("a"),
            "dependencies": [],
            "pytest11_entry_point": "fixture_plugin",
            "parser_catalog_digest": _digest("b"),
            "hook_capability_digest": _digest("c"),
        }
    ]

    result = toolchain_api.validate_project_runtime_layer(descriptor, expected_target="1" * 40)

    assert result.status == "PASS"
    assert result.pytest_plugins[0].distribution == "fixture-plugin"


def test_attested_fixture_plugin_extends_frozen_pytest_catalog(toolchain_api: Any) -> None:
    descriptor = _project_runtime_descriptor()
    descriptor["distributions"].append(
        {
            "name": "fixture-plugin",
            "version": "1.0",
            "payload_digest": _digest("a"),
            "dependencies": [],
            "entry_points": ["pytest11:fixture_plugin"],
        }
    )
    descriptor["pytest_plugins"] = [
        {
            "distribution": "fixture-plugin",
            "version": "1.0",
            "payload_digest": _digest("a"),
            "dependencies": [],
            "pytest11_entry_point": "fixture_plugin",
            "options": ["--fixture-mode"],
            "ini_fields": ["fixture_mode"],
            "parser_catalog_digest": _digest("b"),
            "hook_capability_digest": _digest("c"),
        }
    ]

    catalog = toolchain_api.compose_pytest_catalog(descriptor)

    assert "--fixture-mode" in catalog.options
    assert "fixture_mode" in catalog.ini_fields
    assert catalog.digest.startswith("sha256:")


def test_unattested_pytest_plugin_is_unknown(toolchain_api: Any) -> None:
    descriptor = _project_runtime_descriptor()
    descriptor["pytest_plugins"] = [
        {
            "distribution": "unattested-plugin",
            "version": "1.0",
            "payload_digest": _digest("a"),
            "dependencies": [],
            "pytest11_entry_point": "unattested_plugin",
            "parser_catalog_digest": _digest("b"),
            "hook_capability_digest": _digest("c"),
        }
    ]

    result = toolchain_api.validate_project_runtime_layer(descriptor, expected_target="1" * 40)

    assert result.status == "UNKNOWN"


def test_module_package_does_not_install_analyzer_lock_into_host(toolchain_api: Any) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    manifest = yaml.safe_load(
        (repo_root / "packages/specfact-code-review/module-package.yaml").read_text(encoding="utf-8")
    )
    host_names = {toolchain_api.normalized_requirement_name(item) for item in manifest.get("pip_dependencies", [])}

    assert host_names.isdisjoint(set(ANALYZER_COMPONENTS))
