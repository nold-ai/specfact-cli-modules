from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "pr-orchestrator.yml").read_text(encoding="utf-8")


def _job_text(workflow: str, job_name: str) -> str:
    match = re.search(rf"(?ms)^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)", workflow)
    assert match is not None, f"missing workflow job: {job_name}"
    return match.group(0)


def test_pr_orchestrator_verify_has_core_verifier_flags() -> None:
    workflow = _workflow_text()
    assert "verify-module-signatures" in workflow
    assert "scripts/verify-modules-signature.py" in workflow
    assert "--payload-from-filesystem" in workflow
    assert "--enforce-version-bump" in workflow
    assert "github.event.pull_request.base.ref" in workflow
    assert "TARGET_BRANCH" in workflow
    assert "github.ref_name" in workflow
    assert "VERIFY_CMD" in workflow


def test_pr_orchestrator_pr_to_dev_verifier_omits_loose_integrity_mode() -> None:
    workflow = _workflow_text()
    assert "--metadata-only" not in workflow


def test_pr_orchestrator_push_uses_github_event_before_for_version_base() -> None:
    workflow = _workflow_text()
    assert 'BEFORE="${{ github.event.before }}"' in workflow
    assert 'VERIFY_CMD+=(--version-check-base "$BEFORE")' in workflow
    assert "0000000000000000000000000000000000000000" in workflow


def test_pr_orchestrator_installs_pinned_specfact_cli() -> None:
    workflow = _workflow_text()
    assert "actions/checkout@v4" in workflow
    assert "repository: nold-ai/specfact-cli" in workflow
    assert "id: core-ref" in workflow
    assert "git ls-remote --exit-code --heads https://github.com/nold-ai/specfact-cli.git" in workflow
    assert "FALLBACK_REF: ${{ github.base_ref || github.ref_name }}" in workflow
    assert 'echo "ref=$fallback" >> "$GITHUB_OUTPUT"' in workflow
    assert "ref: ${{ steps.core-ref.outputs.ref }}" in workflow
    assert "ref: dev" not in workflow
    assert "hatch run pip install -e ./specfact-cli" in workflow
    assert "hatch run python specfact-cli/scripts/runtime_discovery_smoke.py" in workflow


def test_pr_orchestrator_pins_exact_core_schema_smoke() -> None:
    """Preserve the frozen C14 selector; the pinned identity proves the minimum."""
    workflow = _workflow_text()

    assert "minimum-core-schema-compatibility" in workflow
    assert '["3.11", "3.12", "3.13"]' in workflow
    assert "refs/tags/v0.55.1" in workflow
    assert "b1e517e60e669eaba15a18ecfa83ef5a9df65276" in workflow
    assert "47984be5434d7ae65ed6908bf525a32053290337" in workflow
    assert ">=0.55.1" in workflow
    assert "test_core_0_55_1_runtime_loads_schema_1_6_consumer_matrix" in workflow
    assert "pip install" in workflow
    assert "--no-cache-dir" in workflow


def test_pr_orchestrator_rejects_pep440_local_core_alias() -> None:
    """Preserve the frozen C14 selector while superseding its exact-only rule."""
    workflow = _workflow_text()
    minimum_job = _job_text(workflow, "minimum-core-schema-compatibility")

    assert "0.55.0" in minimum_job
    assert "0.55.2" in minimum_job
    assert "1.0.0" in minimum_job
    assert "verify-minimum-core-compatibility-range" in minimum_job
    assert "===0.55.1" not in minimum_job
    assert "ref: dev" not in minimum_job
    assert "ref: main" not in minimum_job
    assert "FALLBACK_REF" not in minimum_job


def _assert_pinned_credentialed_prefetch(exact_job: str, prefetch_step: str) -> None:
    assert "packages: read" in exact_job
    assert "oras-project/setup-oras@22ce207df3b08e061f537244349aac6ae1d214f6" in exact_job
    assert "oras_1.3.3_linux_amd64.tar.gz" in exact_job
    assert "9ce999f8d2de03fc03968b29d743077a58783e545e5eaa53917ca177352d0e59" in exact_job
    assert "REGISTRY_TOKEN: ${{ github.token }}" in prefetch_step
    assert "REGISTRY_ACTOR: ${{ github.actor }}" in prefetch_step
    assert "oras cp --to-oci-layout" in prefetch_step
    assert 'rm -f "$registry_config"' in prefetch_step


def _assert_candidate_python_is_credential_free(capsule_step: str) -> None:
    assert "REGISTRY_TOKEN" not in capsule_step
    assert "REGISTRY_ACTOR" not in capsule_step
    assert "github.token" not in capsule_step
    assert "credential=" not in capsule_step
    assert "simulate_cache_hit=True" in capsule_step
    assert "PREFETCHED_OCI_CACHE" in capsule_step
    assert "sudo --preserve-env=MATRIX_PYTHON,PREFETCHED_OCI_CACHE,PYTHONPATH" in capsule_step


def test_exact_core_smoke_does_not_expose_registry_token_to_candidate_python() -> None:
    exact_job = _job_text(_workflow_text(), "minimum-core-schema-compatibility")
    prefetch_name = "Prefetch signed analyzer capsule into credential-free cache"
    capsule_name = "Run signed analyzer capsule from prefetched cache and empty Bubblewrap smoke"
    prefetch_offset = exact_job.index(prefetch_name)
    capsule_offset = exact_job.index(capsule_name)
    candidate_execution_offset = exact_job.index("Install minimum core and candidate module package")
    prefetch_step = exact_job[prefetch_offset:candidate_execution_offset]
    capsule_step = exact_job[capsule_offset:]

    assert prefetch_offset < candidate_execution_offset < capsule_offset
    assert "github.workspace" not in prefetch_step
    assert "PYTHONPATH" not in prefetch_step
    _assert_pinned_credentialed_prefetch(exact_job, prefetch_step)
    _assert_candidate_python_is_credential_free(capsule_step)


def test_pr_orchestrator_runs_real_c14_capsule_smoke() -> None:
    workflow = _workflow_text()
    exact_job = _job_text(workflow, "minimum-core-schema-compatibility")
    capsule_step_name = "Run signed analyzer capsule from prefetched cache and empty Bubblewrap smoke"
    capsule_step_offset = exact_job.index(capsule_step_name)
    capsule_step = exact_job[capsule_step_offset:]
    elevated_python = (
        'sudo --preserve-env=MATRIX_PYTHON,PREFETCHED_OCI_CACHE,PYTHONPATH "$PWD/.exact-core-venv/bin/python" -'
    )
    required_fragments = (
        capsule_step_name,
        "import tempfile",
        'tempfile.mkdtemp(prefix=f"c14-capsule-{abi}-", dir="/tmp")',
        "C14_MANIFEST_DIAGNOSTIC",
        "diagnostic_manifest_verifier",
        "matching_subroot_orders",
        "permutations",
        "gzip",
        "c14-manifest-{abi}.json.gz",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "c14-manifest-${{ matrix.python-version }}.json.gz",
        "pr-range-v1-toolchain-lock.json",
        "Prefetch signed analyzer capsule into credential-free cache",
        "oras cp --to-oci-layout",
        "PREFETCHED_OCI_CACHE",
        "empty_cache=True",
        "empty_cache=False",
        'storage_root=runtime_root / "storage-a"',
        'storage_root=runtime_root / "storage-b"',
        "verified_cache",
        "bubblewrap-static",
        '"--unshare-all"',
        '"--cap-drop"',
        '"ALL"',
        '"--ro-bind"',
        '"--tmpfs"',
        "subprocess.run",
        "final_root_manifest_digest",
    )

    missing = tuple(fragment for fragment in required_fragments if fragment not in exact_job)
    assert not missing, f"missing protected C14 runtime workflow fragments: {missing}"
    assert elevated_python in capsule_step
    assert elevated_python not in exact_job[:capsule_step_offset]
    assert 'Path(os.environ["RUNNER_TEMP"])' not in capsule_step
    assert "caller_identity" not in capsule_step
    assert "bubblewrap_child_identity" not in capsule_step
    assert '"--uid"' not in capsule_step
    assert '"--gid"' not in capsule_step
    assert '"--unshare-net"' not in capsule_step


def test_exact_core_smoke_quotes_tree_revision_and_redacts_acquisition_urls() -> None:
    exact_job = _job_text(_workflow_text(), "minimum-core-schema-compatibility")

    assert "rev-parse 'HEAD^{tree}'" in exact_job
    assert "urlsplit" in exact_job
    assert "urlunsplit" in exact_job
    assert "parsed.hostname" in exact_job
    assert "parsed.netloc" not in exact_job
    assert '"acquisition_final_url": acquisition.final_url' not in exact_job
    assert '"redirects": [hop.url' not in exact_job


def test_pr_orchestrator_has_single_full_pytest_owner() -> None:
    workflow = _workflow_text()
    assert "hatch run contract-test-contracts" in workflow
    assert "hatch run smart-test-check" in workflow
    assert "hatch run test" in workflow
    assert "hatch run contract-test\n" not in workflow
    assert "hatch run smart-test\n" not in workflow
    full_suite_runs = re.findall(r"run:\s+hatch run (test|smart-test(?:-full)?|contract-test)(?!-)\b", workflow)
    assert full_suite_runs == ["test"]


def test_pr_orchestrator_verify_require_signature_on_main_paths() -> None:
    workflow = _workflow_text()
    main_pr_guard = 'if [ "$TARGET_BRANCH" = "main" ]; then'
    main_ref_guard = '[ "${{ github.ref_name }}" = "main" ]; then'
    require_append = "VERIFY_CMD+=(--require-signature)"
    assert main_pr_guard in workflow
    assert main_ref_guard in workflow
    assert require_append in workflow
    assert workflow.count(require_append) == 2
    push_require_block = (
        'if [ "${{ github.ref_name }}" = "main" ]; then\n              VERIFY_CMD+=(--require-signature)'
    )
    assert push_require_block in workflow
    assert "--require-signature" in workflow
