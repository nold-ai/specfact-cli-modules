"""Orchestration helpers for structured code-review runs."""

from __future__ import annotations

import ast
import configparser
import fnmatch
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from contextlib import ExitStack, suppress
from dataclasses import dataclass, field
from functools import lru_cache, partial
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import normalize_path_variants, tool_error
from specfact_code_review.run import differential, scope, toolchain
from specfact_code_review.run.findings import (
    PR_RANGE_CONDITIONAL_ANALYZERS,
    PR_RANGE_REQUIRED_ANALYZERS,
    CleanupForecast,
    EvidenceRef,
    PreserveReasonEvidence,
    RemediationPacket,
    ReviewFinding,
    ReviewReport,
    SignalTraceEntry,
)
from specfact_code_review.run.forecast import build_cleanup_forecast
from specfact_code_review.run.sandbox import (
    BubblewrapIdentity,
    SnapshotInvocationContext,
    build_launch_plan,
    execute_launch_plan,
    preflight_reserved_imports,
)
from specfact_code_review.run.scorer import score_review
from specfact_code_review.tools.ai_bloat_runner import run_ai_bloat
from specfact_code_review.tools.ast_clean_code_runner import run_ast_clean_code
from specfact_code_review.tools.basedpyright_runner import run_basedpyright
from specfact_code_review.tools.contract_runner import run_contract_check
from specfact_code_review.tools.pylint_runner import run_pylint
from specfact_code_review.tools.radon_runner import run_radon
from specfact_code_review.tools.ruff_runner import run_ruff
from specfact_code_review.tools.semgrep_runner import run_semgrep, run_semgrep_bugs
from specfact_code_review.tools.tool_availability import skip_if_pytest_unavailable


_SOURCE_ROOT = Path("packages/specfact-code-review/src")
_PACKAGE_ROOT = _SOURCE_ROOT / "specfact_code_review"
_COVERAGE_THRESHOLD = 80.0
_SUPPRESSION_MARKERS = ("# noqa", "# type: ignore", "# pyright: ignore", "# pylint: disable")
_TEST_NOISE_RULES = {
    ("contract_runner", "MISSING_ICONTRACT"),
    ("basedpyright", "reportMissingImports"),
    ("basedpyright", "reportAttributeAccessIssue"),
    ("pylint", "W0212"),
}
_GLOBAL_NOISE_RULES = {
    ("pylint", "R0801"),
}
_PYLINT_CLI_WRAPPER_NOISE_RULES = {"R0914", "R0917"}
_NOISE_MESSAGE_PREFIXES = ("ValidationError: 1 validation error for LedgerState",)
_PR_MODE_ENV = "SPECFACT_CODE_REVIEW_PR_MODE"
_PR_CONTEXT_ENVS = (
    "SPECFACT_CODE_REVIEW_PR_TITLE",
    "SPECFACT_CODE_REVIEW_PR_BODY",
    "SPECFACT_CODE_REVIEW_PR_PROPOSAL",
)
_CLEAN_CODE_CONTEXT_HINTS = ("clean code", "naming", "kiss", "yagni", "dry", "solid", "complexity")
_TARGETED_TEST_TIMEOUT = int(os.environ.get("SPECFACT_CODE_REVIEW_TARGETED_TEST_TIMEOUT", "120"))
_PROJECT_RUNTIME_MEMBERS = frozenset(
    {"basedpyright", "contracts", "pylint", "targeted-pytest-coverage", "targeted-pytest-plugin-preflight"}
)
_GIT_LOCAL_ENV_VARS = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
        "GIT_WORK_TREE",
    }
)
ReviewFocus = Literal["simplify"]
ReviewEnforcementMode = Literal["full", "changed", "shadow"]
LocalAssuranceKind = Literal["worktree", "full", "explicit_files"]


@dataclass(frozen=True)
class ReviewOptions:
    """Optional controls for a governed review run."""

    no_tests: bool = False
    include_noise: bool = False
    progress_callback: Callable[[str], None] | None = None
    bug_hunt: bool = False
    review_level: Literal["error", "warning"] | None = None
    review_mode: ReviewEnforcementMode = "full"
    focus: ReviewFocus | None = None


@dataclass(frozen=True)
class RuntimePolicyResult:
    """Disposition of the initial non-adversarial runtime assumption."""

    status: Literal["PASS", "UNKNOWN"]
    assumption: Literal["non_adversarial_candidate_runtime"]


@dataclass(frozen=True)
class AnalyzerProfile:
    id: str
    required_ids: tuple[str, ...]
    conditional_ids: tuple[str, ...]

    @property
    def all_ids(self) -> tuple[str, ...]:
        return self.required_ids + self.conditional_ids


@dataclass(frozen=True)
class StatusResult:
    status: Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
    reason: str = ""
    disposition: str = ""
    execution_state: str = ""
    policy_source: str = ""


@dataclass(frozen=True)
class AnalyzerEvidence:
    id: str
    execution_state: str
    evidence_outcome: str
    version: str
    diagnostic: str = ""


@dataclass(frozen=True)
class ProfileEvidenceReport:
    analyzer_evidence: tuple[AnalyzerEvidence, ...]
    assurance_status: str
    overall_verdict: str
    has_unknown_required_evidence: bool


@dataclass(frozen=True)
class CapsuleRuntime:
    """Verified analyzer capsule identities reused across fresh sandboxes."""

    root: Path
    identity: str
    environment_id: str
    interpreter: str
    bootstrap: str
    bubblewrap: BubblewrapIdentity
    cleanup_root: Path | None = None


@dataclass(frozen=True)
class CapsuleSnapshotResult:
    """Per-member evidence produced from one immutable snapshot."""

    evidence: dict[str, dict[str, object]]
    findings_by_member: dict[str, list[ReviewFinding]]


@dataclass(frozen=True)
class SnapshotPolicyBindings:
    """Explicit per-member policy argv and their read-only mount roots."""

    config_roots: tuple[Path, ...]
    member_argv: dict[str, tuple[str, ...]]
    cleanup_roots: tuple[Path, ...]


@dataclass(frozen=True)
class CapsuleMemberExecutionRequest:
    """Complete controller-owned input for one fresh member sandbox."""

    runtime: CapsuleRuntime
    member: str
    invocation_id: str
    snapshot_root: Path
    files: list[Path]
    options: ReviewOptions
    config_roots: tuple[Path, ...] = ()
    adapter_argv: tuple[str, ...] = ()
    complete_pytest_inventory: bool = False
    project_runtime_root: Path | None = None


@dataclass(frozen=True)
class ImmutablePytestInventory:
    """Reconciled complete selector inventory for both immutable sides."""

    reconciliation: CandidateReconciliation
    base: tuple[str, ...] = ()
    head: tuple[str, ...] = ()


@dataclass(frozen=True)
class RangeDifferentialContext:
    """Immutable sources and rename/add/delete facts shared by all members."""

    base_sources: dict[str, bytes]
    head_sources: dict[str, bytes]
    rename_facts: dict[str, str]
    rename_ambiguities: dict[str, list[str]] | None
    added_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]


@dataclass(frozen=True)
class SelectedModulePayload:
    """Verified module bytes plus optional ownership of a staged source tree."""

    payload: object | None
    reason: str = ""
    staged_source: tempfile.TemporaryDirectory[str] | None = None


@dataclass(frozen=True)
class GeneratedInputIdentity:
    kind: str
    digest: str


@dataclass(frozen=True)
class SyntheticSnapshotContext:
    inputs: tuple[GeneratedInputIdentity, ...]
    invoked_inputs: tuple[GeneratedInputIdentity, ...]


@dataclass(frozen=True)
class InvocationManifestEvidence:
    id: str
    eligible_digest: str
    invoked_digest: str


@dataclass(frozen=True)
class InvocationManifestResult:
    status: str
    members: tuple[InvocationManifestEvidence, ...]


@dataclass(frozen=True)
class TargetPolicyResult:
    assurance_status: str
    reason: str


@dataclass(frozen=True)
class RangePolicySelection:
    source_baseline: str
    policy_commit: str
    applies_to: tuple[str, str]


@dataclass(frozen=True)
class PytestSuitePlan:
    selectors: tuple[str, ...]
    source_heuristics_used: bool
    status: str = "PASS"
    reason: str = ""


@dataclass(frozen=True)
class SnapshotApplicability:
    base: str
    head: str


@dataclass(frozen=True)
class PytestInputRole:
    kind: str
    inputs: tuple[str, ...]


@dataclass(frozen=True)
class CandidateReconciliation:
    status: str
    reason: str = ""
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoverageProjection:
    status: str
    values: dict[str, object]
    writable_paths: tuple[Path, ...] = ()
    reason: str = ""
    policy_source: str = "target_tip"


@dataclass(frozen=True)
class SnapshotMemberState:
    id: str
    status: str
    required: bool = True


@dataclass(frozen=True)
class SnapshotInputClassification:
    members: tuple[SnapshotMemberState, ...]

    def member(self, member_id: str) -> SnapshotMemberState:
        try:
            return next(member for member in self.members if member.id == member_id)
        except StopIteration as exc:
            raise KeyError(member_id) from exc


@dataclass(frozen=True)
class ContractComponents:
    static_scan: SnapshotMemberState
    crosshair: SnapshotMemberState
    parent: SnapshotMemberState


@dataclass(frozen=True)
class ContractActivation:
    active: bool
    contract: str


@dataclass(frozen=True)
class PytestHookCatalog:
    hooks: tuple[str, ...]
    unclassified_hooks: tuple[str, ...] = ()


@dataclass(frozen=True)
class PytestOptionCatalog:
    options: tuple[str, ...]
    unclassified_help_options: tuple[str, ...] = ()


@dataclass(frozen=True)
class PytestConfigurationCatalog:
    fields: tuple[str, ...]
    classifications: dict[str, str]
    unclassified_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class PytestCollectorCatalog:
    branches: tuple[str, ...]
    unclassified_branches: tuple[str, ...] = ()


@dataclass(frozen=True)
class PytestProjection:
    status: str
    values: dict[str, object]
    writable_paths: tuple[Path, ...]
    logical_policy_digest: str
    reason: str = ""


@dataclass(frozen=True)
class PytestObservedOutcome:
    kind: str


@dataclass(frozen=True)
class PytestOutcomeResult:
    status: str
    outcomes: tuple[PytestObservedOutcome, ...]


@dataclass(frozen=True)
class ImportOrderResult:
    status: str
    search_order: tuple[str, ...]


_C14_ANALYZER_VERSIONS = {
    "ai-bloat-ast": "module-release-bound",
    "ast-clean-code": "module-release-bound",
    "basedpyright": "1.39.10",
    "contracts": "crosshair-tool-0.0.109+icontract-2.7.1",
    "pylint": "4.0.7",
    "radon": "6.0.1",
    "ruff": "0.15.12",
    "semgrep-clean": "1.144.0",
    "semgrep-bugs": "1.144.0",
    "targeted-pytest-coverage": "pytest-9.0.3+pytest-cov-7.1.0+coverage-7.15.4",
}


def _canonical_json_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def default_pr_range_profile() -> AnalyzerProfile:
    return AnalyzerProfile(
        "pr-range-v1",
        PR_RANGE_REQUIRED_ANALYZERS,
        PR_RANGE_CONDITIONAL_ANALYZERS,
    )


def aggregate_profile_evidence(evidence: dict[str, dict[str, object]]) -> ProfileEvidenceReport:
    profile = default_pr_range_profile()
    members: list[AnalyzerEvidence] = []
    required_unknown = False
    known_fail = False
    for member_id in profile.all_ids:
        raw = evidence.get(member_id, {})
        execution = str(raw.get("execution_state", "error"))
        outcome = str(raw.get("evidence_outcome", "UNKNOWN"))
        version = str(raw.get("version", ""))
        has_member_unknown = _has_required_unknown_reasons(raw.get("required_unknown_reasons", []))
        if execution == "error" or version != _C14_ANALYZER_VERSIONS[member_id]:
            outcome = "UNKNOWN"
        required_unknown |= outcome == "UNKNOWN" or has_member_unknown
        known_fail |= outcome == "FAIL"
        members.append(AnalyzerEvidence(member_id, execution, outcome, version, str(raw.get("diagnostic", ""))))
    assurance = "FAIL" if known_fail else "UNKNOWN" if required_unknown else "PASS"
    return ProfileEvidenceReport(tuple(members), assurance, "PASS" if assurance == "PASS" else "FAIL", required_unknown)


def _has_required_unknown_reasons(raw_reasons: object) -> bool:
    """Treat malformed or non-empty required uncertainty as fail-closed evidence."""

    return (
        not isinstance(raw_reasons, list)
        or bool(raw_reasons)
        or any(not isinstance(reason, str) or not reason for reason in raw_reasons)
    )


def _capsule_environment_id() -> str:
    return f"linux-x86_64-cp{sys.version_info.major}{sys.version_info.minor}"


def _capsule_credential() -> str | None:
    actor = os.environ.get("GITHUB_ACTOR", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    return f"{actor}:{token}" if actor and token else None


def _official_installed_payload() -> tuple[object | None, str]:
    try:
        from specfact_cli.registry import module_discovery, module_installer

        discovered = next(
            (
                item
                for item in module_discovery.discover_all_modules_for_project_with_shadowed(Path.cwd())
                if item.metadata.name == "nold-ai/specfact-code-review" and item.source in {"user", "marketplace"}
            ),
            None,
        )
        if discovered is None:
            return None, "official_installed_module_missing"
        handoff = toolchain.derive_core_0_55_1_install_handoff(
            discovered,
            expected_registry_id="nold-ai/specfact-code-review",
            user_modules_root=module_discovery.USER_MODULES_ROOT,
            marketplace_modules_root=module_discovery.MARKETPLACE_MODULES_ROOT,
            public_key_path=module_installer._bundled_public_key_path(),  # pylint: disable=protected-access
        )
        payload = toolchain.verify_installed_module_payload(handoff)
    except (AttributeError, ImportError, OSError):
        return None, "core_installed_module_handoff_unavailable"
    if payload.status != "PASS":
        return None, payload.reason
    return payload, ""


def _candidate_git_environment() -> dict[str, str]:
    return {
        **{key: value for key, value in os.environ.items() if key not in _GIT_LOCAL_ENV_VARS},
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        env=_candidate_git_environment(),
    )
    return completed.stdout


def _stage_candidate_payload(repo_root: Path, commit_sha: str) -> tempfile.TemporaryDirectory[str]:
    package_prefix = "packages/specfact-code-review/src/"
    tree = _git_bytes(
        repo_root,
        "ls-tree",
        "-rz",
        "--full-tree",
        commit_sha,
        package_prefix + "specfact_code_review",
    )
    # Ownership is transferred to SelectedModulePayload and released after capsule composition.
    staged = tempfile.TemporaryDirectory(prefix="specfact-candidate-")  # pylint: disable=consider-using-with
    installed_root = Path(staged.name)
    try:
        entries = [entry for entry in tree.split(b"\0") if entry]
        if not entries:
            raise ValueError("candidate payload tree is empty")
        for entry in entries:
            descriptor, encoded_path = entry.split(b"\t", 1)
            mode, object_type, object_sha = descriptor.decode("ascii").split()
            path = encoded_path.decode("utf-8")
            if object_type != "blob" or mode not in {"100644", "100755"} or not path.startswith(package_prefix):
                raise ValueError("candidate payload contains an unsupported entry")
            relative = Path(path.removeprefix(package_prefix))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("candidate payload path escapes its staging root")
            target = installed_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_git_bytes(repo_root, "cat-file", "blob", object_sha))
            target.chmod(0o755 if mode == "100755" else 0o644)
    except Exception:
        staged.cleanup()
        raise
    return staged


def _candidate_module_version(module_package: bytes) -> str:
    match = re.search(rb"(?m)^version:\s*([^\s#]+)\s*$", module_package)
    if match is None:
        raise ValueError("candidate module version is missing")
    return match.group(1).decode("utf-8")


def _protected_candidate_payload() -> SelectedModulePayload:
    required = {
        "GITHUB_REPOSITORY": "repository",
        "GITHUB_WORKFLOW": "workflow",
        "GITHUB_WORKFLOW_REF": "workflow_ref",
        "GITHUB_RUN_ID": "run_id",
        "GITHUB_RUN_ATTEMPT": "run_attempt",
        "GITHUB_JOB": "job",
    }
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != "nold-ai/specfact-cli-modules"
        or os.environ.get("GITHUB_EVENT_NAME") not in {"pull_request", "merge_group"}
    ):
        return SelectedModulePayload(None, "untrusted_candidate_workflow_context")
    try:
        repo_root = Path(__file__).parents[5]
        if (
            Path(_git_bytes(repo_root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
            != repo_root.resolve()
        ):
            raise ValueError("candidate repository root mismatch")
        commit_sha = os.environ.get("GITHUB_SHA", "")
        if re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None:
            raise ValueError("candidate commit is invalid")
        if _git_bytes(repo_root, "rev-parse", "HEAD").decode().strip() != commit_sha:
            raise ValueError("candidate checkout does not match GITHUB_SHA")
        tree_sha = _git_bytes(repo_root, "rev-parse", f"{commit_sha}^{{tree}}").decode().strip()
        if re.fullmatch(r"[0-9a-f]{40}", tree_sha) is None:
            raise ValueError("candidate tree is invalid")
        dirty = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--quiet",
                commit_sha,
                "--",
                "packages/specfact-code-review/src/specfact_code_review",
                "packages/specfact-code-review/module-package.yaml",
            ],
            check=False,
            env=_candidate_git_environment(),
        )
        if dirty.returncode != 0:
            raise ValueError("candidate tracked payload differs from GITHUB_SHA")
        module_package = _git_bytes(
            repo_root,
            "show",
            f"{commit_sha}:packages/specfact-code-review/module-package.yaml",
        )
        staged = _stage_candidate_payload(repo_root, commit_sha)
        installed_root = Path(staged.name)
        metadata: dict[str, object] = {
            output_name: os.environ[input_name] for input_name, output_name in required.items()
        }
        metadata.update(
            {
                "commit_sha": commit_sha,
                "tree_sha": tree_sha,
                "module_package_digest": "sha256:" + hashlib.sha256(module_package).hexdigest(),
                "payload_manifest_digest": toolchain.candidate_source_manifest_digest(installed_root),
                "version": _candidate_module_version(module_package),
            }
        )
        payload = toolchain.verify_candidate_module_source(metadata, installed_root=installed_root)
        if payload.status != "PASS":
            staged.cleanup()
            return SelectedModulePayload(None, payload.reason)
        return SelectedModulePayload(payload, staged_source=staged)
    except (OSError, subprocess.SubprocessError, TypeError, UnicodeDecodeError, ValueError) as exc:
        return SelectedModulePayload(None, f"candidate_payload_unavailable:{exc}")


def _selected_module_payload() -> SelectedModulePayload:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return _protected_candidate_payload()
    payload, reason = _official_installed_payload()
    return SelectedModulePayload(payload, reason)


def _prepare_capsule_runtime(*, project_runtime_identity: str = "not-applicable") -> tuple[CapsuleRuntime | None, str]:
    """Materialize and compose the signed runtime without host analyzer fallback."""

    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        return None, "unsupported_controller_platform"
    capsule_root: Path | None = None
    try:
        lock_path = Path(__file__).parents[1] / "resources/contracts/pr-range-v1-toolchain-lock.json"
        lock = cast(dict[str, object], json.loads(lock_path.read_text(encoding="utf-8")))
        environment_id = _capsule_environment_id()
        environments = cast(list[dict[str, object]], lock["environments"])
        environment = next(
            item for item in environments if str(item.get("environment_id") or item.get("id")) == environment_id
        )
        storage_root = Path(
            os.environ.get(
                "SPECFACT_CODE_REVIEW_CAPSULE_CACHE",
                str(Path.home() / ".cache/specfact/code-review/capsules"),
            )
        ).expanduser()
        storage_root.mkdir(parents=True, exist_ok=True)
        materialized = toolchain.materialize_capsule(
            lock,
            environment_id=environment_id,
            storage_root=storage_root,
            credential=_capsule_credential(),
        )
        if materialized.status != "PASS":
            _remove_invocation_capsule(cast(Path | None, getattr(materialized, "root", None)))
            return None, materialized.reason
        capsule_root = materialized.root
        selected_payload = _selected_module_payload()
        if selected_payload.payload is None:
            _remove_invocation_capsule(capsule_root)
            return None, selected_payload.reason
        try:
            native = next(
                item
                for item in cast(list[dict[str, object]], environment["native_tools"])
                if item.get("id") == "bubblewrap-static"
            )
            final_manifest = cast(dict[str, object], environment["final_root_manifest"])
            composition = toolchain.compose_post_base_capsule(
                cast(Any, selected_payload.payload),
                capsule_root=materialized.root,
                immutable_base_root_digest=str(final_manifest["manifest_digest"]),
                analyzer_installed_set_digest=toolchain.canonical_json_digest(materialized.installed_distributions),
                native_launcher_digest=str(native["executable_sha256"]),
                project_runtime_identity=project_runtime_identity,
            )
        finally:
            if selected_payload.staged_source is not None:
                selected_payload.staged_source.cleanup()
        if composition.status != "PASS":
            _remove_invocation_capsule(capsule_root)
            return None, composition.reason
        paths = cast(dict[str, object], environment["paths"])
        bubblewrap = BubblewrapIdentity(
            path=str(native["path"]),
            format=str(native["format"]),
            architecture=str(native["architecture"]),
            linkage=str(native["linkage_kind"]),
            interpreter=tuple(str(value) for value in cast(list[object], native["interpreter_set"])),
            needed=tuple(str(value) for value in cast(list[object], native["needed_library_set"])),
            sha256=str(native["executable_sha256"]),
            descriptor_digest=str(native["verified_descriptor_digest"]),
        )
        return (
            CapsuleRuntime(
                materialized.root,
                composition.composite_identity_digest,
                environment_id,
                str(paths["interpreter"]),
                "/opt/specfact/bootstrap/sealed_bootstrap.py",
                bubblewrap,
                capsule_root,
            ),
            "",
        )
    except (KeyError, OSError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
        _remove_invocation_capsule(capsule_root)
        return None, f"capsule_runtime_unavailable:{exc}"


def _remove_invocation_capsule(root: Path | None) -> None:
    if root is not None and root.parent.name == "invocations":
        shutil.rmtree(root, ignore_errors=True)


def _cleanup_capsule_runtime(runtime: CapsuleRuntime) -> None:
    cleanup_root = getattr(runtime, "cleanup_root", None)
    _remove_invocation_capsule(cleanup_root if isinstance(cleanup_root, Path) else None)


def _radon_member_findings(files: list[Path], *, adapter_argv: tuple[str, ...]) -> list[ReviewFinding]:
    if adapter_argv and adapter_argv != ("radon-full-result-v1",):
        raise ValueError("unsupported Radon adapter contract")
    return run_radon(files, full_result=bool(adapter_argv))


def _member_findings(
    member: str,
    files: list[Path],
    *,
    bug_hunt: bool,
    adapter_argv: tuple[str, ...] = (),
    complete_pytest_inventory: bool = False,
) -> list[ReviewFinding]:
    configured = _configured_member_findings(
        member,
        files,
        bug_hunt=bug_hunt,
        adapter_argv=adapter_argv,
        complete_pytest_inventory=complete_pytest_inventory,
    )
    if configured is not None:
        return configured
    runners: dict[str, Callable[[list[Path]], list[ReviewFinding]]] = {
        "radon": partial(_radon_member_findings, adapter_argv=adapter_argv),
        "ai-bloat-ast": run_ai_bloat,
        "ast-clean-code": run_ast_clean_code,
        "contracts": partial(run_contract_check, bug_hunt=bug_hunt),
    }
    try:
        runner = runners[member]
    except KeyError as exc:
        raise ValueError(f"unsupported capsule member: {member}") from exc
    return runner(files)


def _pytest_plugin_manifest(adapter_argv: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    if len(adapter_argv) != 1:
        raise ValueError("plugin manifest argv is invalid")
    manifest = json.loads(adapter_argv[0])
    if not isinstance(manifest, list) or not all(isinstance(item, dict) for item in manifest):
        raise ValueError("plugin manifest must be a list of objects")
    return tuple(cast(list[dict[str, object]], manifest))


def _pytest_plugin_manifest_string(raw: dict[str, object], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"plugin {field} is invalid")
    return value


def _pytest_plugin_manifest_strings(raw: dict[str, object], field: str) -> tuple[str, ...]:
    value = raw.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"plugin {field} catalog is invalid")
    return tuple(cast(list[str], value))


def _pytest_plugin_parser_catalog(manager: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    from _pytest.config.argparsing import Parser

    parser = cast(Any, Parser(_ispytest=True))
    manager.hook.pytest_addoption.call_historic(kwargs={"parser": parser, "pluginmanager": manager})
    groups = (parser._anonymous, *parser._groups)
    options = tuple(sorted({name for group in groups for option in group.options for name in option.names()}))
    return options, tuple(sorted(parser._inidict))


def _pytest_plugin_entry_point(raw: dict[str, object]) -> str:
    import importlib.metadata

    distribution_name = _pytest_plugin_manifest_string(raw, "distribution")
    version = _pytest_plugin_manifest_string(raw, "version")
    entry_point = _pytest_plugin_manifest_string(raw, "entry_point")
    distribution = importlib.metadata.distribution(distribution_name)
    if distribution.version != version:
        raise ValueError("plugin distribution version differs from its attested manifest")
    pytest_entry_points = tuple(item.value for item in distribution.entry_points if item.group == "pytest11")
    if entry_point not in pytest_entry_points:
        raise ValueError("plugin pytest11 entry point differs from its attested manifest")
    return entry_point


def _load_pytest_plugin(entry_point: str, *, runtime_root: Path) -> tuple[Any, object, set[str]]:
    from _pytest.config import PytestPluginManager

    manager = PytestPluginManager()
    initial_names = {name for name, _plugin in manager.list_name_plugin()}
    manager.import_plugin(entry_point)
    plugin = manager.get_plugin(entry_point)
    origin_value = getattr(plugin, "__file__", "")
    if plugin is None or not origin_value or not Path(str(origin_value)).resolve().is_relative_to(runtime_root):
        raise ValueError("plugin origin is outside the verified project runtime")
    return manager, plugin, initial_names


def _pytest_plugin_observed_hooks(raw: dict[str, object], *, manager: Any, plugin: object) -> tuple[str, ...]:
    hooks = tuple(sorted(caller.name for caller in manager.get_hookcallers(plugin) or []))
    if hooks != _pytest_plugin_manifest_strings(raw, "hooks"):
        raise ValueError("plugin hook registry differs from its attested manifest")
    if toolchain.pytest_hook_capability_digest(hooks) != raw.get("hook_capability_digest"):
        raise ValueError("plugin hook capability digest differs from observation")
    return hooks


def _validate_pytest_plugin_parser(raw: dict[str, object], *, manager: Any) -> None:
    options, ini_fields = _pytest_plugin_parser_catalog(manager)
    if options != _pytest_plugin_manifest_strings(raw, "options") or ini_fields != _pytest_plugin_manifest_strings(
        raw, "ini_fields"
    ):
        raise ValueError("plugin parser catalog differs from its attested manifest")
    if toolchain.pytest_parser_catalog_digest(options=options, ini_fields=ini_fields) != raw.get(
        "parser_catalog_digest"
    ):
        raise ValueError("plugin parser catalog digest differs from observation")


def _validate_pytest_plugin_registry(manager: Any, *, initial_names: set[str], entry_point: str) -> None:
    registered_names = {name for name, _plugin in manager.list_name_plugin()} - initial_names
    if registered_names != {entry_point}:
        raise ValueError("plugin registry differs from its attested manifest")


def _observe_pytest_plugin(raw: dict[str, object], *, runtime_root: Path) -> dict[str, object]:
    entry_point = _pytest_plugin_entry_point(raw)
    manager, plugin, initial_names = _load_pytest_plugin(entry_point, runtime_root=runtime_root)
    hooks = _pytest_plugin_observed_hooks(raw, manager=manager, plugin=plugin)
    _validate_pytest_plugin_parser(raw, manager=manager)
    _validate_pytest_plugin_registry(manager, initial_names=initial_names, entry_point=entry_point)
    return {"origin": "attested-project", "hooks": list(hooks)}


def _pytest_plugin_preflight_findings(adapter_argv: tuple[str, ...]) -> list[ReviewFinding]:
    anchor = Path("/opt/specfact/project-runtime")
    try:
        runtime_root = anchor / "site-packages"
        observed = tuple(
            _observe_pytest_plugin(raw, runtime_root=runtime_root) for raw in _pytest_plugin_manifest(adapter_argv)
        )
        validation = validate_pytest_plugins(observed)
        if validation.status != "PASS":
            raise ValueError(validation.reason)
    except (ImportError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [
            tool_error(tool="pytest", file_path=anchor, message=f"Pytest plugin capability preflight failed: {exc}")
        ]
    return []


def _configured_member_findings(
    member: str,
    files: list[Path],
    *,
    bug_hunt: bool,
    adapter_argv: tuple[str, ...],
    complete_pytest_inventory: bool,
) -> list[ReviewFinding] | None:
    if member == "targeted-pytest-plugin-preflight":
        return _pytest_plugin_preflight_findings(adapter_argv)
    if member == "targeted-pytest-coverage":
        findings, _coverage = (
            _evaluate_complete_tdd_gate(files, adapter_argv) if complete_pytest_inventory else _evaluate_tdd_gate(files)
        )
        return findings
    configurable = {"ruff": run_ruff, "basedpyright": run_basedpyright, "pylint": run_pylint}
    if member in configurable:
        runner = configurable[member]
        return runner(files, extra_args=adapter_argv) if adapter_argv else runner(files)
    semgrep_runners = {"semgrep-clean": run_semgrep, "semgrep-bugs": run_semgrep_bugs}
    if member in semgrep_runners:
        bundle_root = Path(adapter_argv[0]) if adapter_argv else None
        return semgrep_runners[member](files, bundle_root=bundle_root)
    if member == "contracts" and adapter_argv:
        return _sealed_contract_findings(files, bug_hunt=bug_hunt, adapter_argv=adapter_argv)
    return None


def _sealed_contract_findings(
    files: list[Path],
    *,
    bug_hunt: bool,
    adapter_argv: tuple[str, ...],
) -> list[ReviewFinding]:
    test_roots = _contract_test_roots(adapter_argv)
    crosshair_files = [
        path for path in files if path.suffix == ".py" and not _path_is_below_test_root(path, test_roots)
    ]
    return run_contract_check(files, bug_hunt=bug_hunt, crosshair_files=crosshair_files)


def _contract_test_roots(adapter_argv: tuple[str, ...]) -> tuple[Path, ...]:
    if not adapter_argv or adapter_argv[0] != "contract-inputs-v1" or len(adapter_argv[1:]) % 2:
        raise ValueError("unsupported contracts adapter contract")
    pairs = tuple(zip(adapter_argv[1::2], adapter_argv[2::2], strict=True))
    if not pairs or any(flag != "--test-root" for flag, _value in pairs):
        raise ValueError("contracts test-root manifest is invalid")
    roots = tuple(Path(value) for _flag, value in pairs)
    if any(root.is_absolute() or ".." in root.parts for root in roots):
        raise ValueError("contracts test root escapes snapshot")
    return roots


def _path_is_below_test_root(path: Path, roots: tuple[Path, ...]) -> bool:
    snapshot_root = Path("/opt/specfact/snapshot")
    relative = path.relative_to(snapshot_root) if path.is_absolute() and path.is_relative_to(snapshot_root) else path
    return any(relative == root or relative.is_relative_to(root) for root in roots)


def _validate_pytest_inventory(selectors: tuple[str, ...]) -> None:
    for selector in selectors:
        raw_path = selector.split("::", maxsplit=1)[0]
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("pytest selector escapes snapshot")


def _split_pytest_adapter_argv(adapter_argv: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        separator = adapter_argv.index("--")
    except ValueError as exc:
        raise ValueError("complete pytest inventory separator is missing") from exc
    return adapter_argv[:separator], adapter_argv[separator + 1 :]


def _projected_pytest_test_roots(policy_argv: tuple[str, ...]) -> tuple[Path, ...]:
    try:
        config_path = Path(policy_argv[policy_argv.index("-c") + 1])
    except (ValueError, IndexError) as exc:
        raise ValueError("sealed pytest configuration is missing") from exc
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with config_path.open(encoding="utf-8") as handle:
            parser.read_file(handle)
        roots = tuple(Path(value) for value in parser.get("pytest", "testpaths").split())
    except (OSError, configparser.Error, KeyError) as exc:
        raise ValueError("sealed pytest test roots are invalid") from exc
    snapshot_root = Path("/opt/specfact/snapshot")
    if not roots or any(not root.is_absolute() or not root.is_relative_to(snapshot_root) for root in roots):
        raise ValueError("sealed pytest test root escapes snapshot")
    return roots


def _is_below_any_root(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def _capsule_snapshot_files(request: dict[str, object], *, member: str) -> list[Path]:
    raw_paths = request["paths"]
    if (
        not isinstance(raw_paths, list)
        or (not raw_paths and member != "targeted-pytest-plugin-preflight")
        or not all(isinstance(path, str) for path in raw_paths)
    ):
        raise ValueError("capsule paths are invalid")
    relative_paths = [Path(cast(str, path)) for path in raw_paths]
    if any(path.is_absolute() or ".." in path.parts for path in relative_paths):
        raise ValueError("capsule path escapes snapshot")
    return [Path("/opt/specfact/snapshot") / path for path in relative_paths]


def _capsule_adapter_request(request: dict[str, object], *, member: str) -> tuple[tuple[str, ...], bool]:
    raw_adapter_argv = request.get("adapter_argv", [])
    if not isinstance(raw_adapter_argv, list) or not all(isinstance(value, str) for value in raw_adapter_argv):
        raise ValueError("capsule adapter argv is invalid")
    adapter_argv = tuple(cast(list[str], raw_adapter_argv))
    complete_pytest_inventory = request.get("complete_pytest_inventory", False)
    if not isinstance(complete_pytest_inventory, bool):
        raise ValueError("complete pytest inventory flag is invalid")
    if not complete_pytest_inventory:
        return adapter_argv, False
    if member != "targeted-pytest-coverage":
        raise ValueError("complete pytest inventory is invalid for this member")
    _policy_argv, selectors = _split_pytest_adapter_argv(adapter_argv)
    _validate_pytest_inventory(selectors)
    return adapter_argv, True


def _load_capsule_request(request_path: Path) -> tuple[str, list[Path], bool, tuple[str, ...], bool]:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("capsule request must be an object")
    member = str(request["member"])
    adapter_argv, complete_pytest_inventory = _capsule_adapter_request(request, member=member)
    return (
        member,
        _capsule_snapshot_files(request, member=member),
        bool(request.get("bug_hunt", False)),
        adapter_argv,
        complete_pytest_inventory,
    )


def _capsule_member_response(member: str, findings: list[ReviewFinding]) -> dict[str, object]:
    unknown = any(finding.category == "tool_error" for finding in findings)
    blocking = any(finding.is_blocking() for finding in findings)
    normalized = [
        finding.model_copy(
            update={"file": Path(finding.file).as_posix().removeprefix("/opt/specfact/snapshot/")}
        ).model_dump(mode="json")
        for finding in findings
    ]
    return {
        "member": member,
        "execution_state": "error" if unknown else "ran",
        "evidence_outcome": "UNKNOWN" if unknown else "FAIL" if blocking else "PASS",
        "findings": normalized,
        "diagnostic": "analyzer_reported_incomplete_execution" if unknown else "",
    }


def _capsule_process_request(request_path: Path) -> None:
    """Run exactly one analyzer member inside the sealed capsule process."""

    try:
        member, files, bug_hunt, adapter_argv, complete_pytest_inventory = _load_capsule_request(request_path)
        response = _capsule_member_response(
            member,
            _member_findings(
                member,
                files,
                bug_hunt=bug_hunt,
                adapter_argv=adapter_argv,
                complete_pytest_inventory=complete_pytest_inventory,
            ),
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        response = {
            "member": "unknown",
            "execution_state": "error",
            "evidence_outcome": "UNKNOWN",
            "findings": [],
            "diagnostic": f"capsule_request_failed:{exc}",
        }
    destination = Path("/opt/specfact/output/result.json")
    temporary = destination.with_name(".result.json.tmp")
    temporary.write_text(
        json.dumps(response, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, destination)


def _prepare_capsule_process_roots(process_root: Path) -> tuple[Path, Path, Path, Path]:
    roots = (
        process_root / "request",
        process_root / "output",
        process_root / "temporary",
        process_root / "control",
    )
    for root in roots:
        root.mkdir()
    for projected_root in ("coverage", "pytest"):
        (roots[2] / projected_root).mkdir()
    return roots


def _execute_capsule_member(request: CapsuleMemberExecutionRequest) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"specfact-{request.member}-") as temporary_directory:
        request_root, output_root, scratch_root, control_root = _prepare_capsule_process_roots(
            Path(temporary_directory)
        )
        resolved_snapshot = request.snapshot_root.resolve()
        relative_paths = tuple(path.resolve().relative_to(resolved_snapshot).as_posix() for path in request.files)
        request_path = request_root / "request.json"
        request_path.write_text(
            json.dumps(
                {
                    "adapter_argv": request.adapter_argv,
                    "bug_hunt": request.options.bug_hunt,
                    "complete_pytest_inventory": request.complete_pytest_inventory,
                    "member": request.member,
                    "paths": relative_paths,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        context = SnapshotInvocationContext(
            member=request.member,
            snapshot_root=resolved_snapshot,
            config_roots=(request_root, *request.config_roots),
            output_root=output_root,
            temporary_root=scratch_root,
            capsule_root=request.runtime.root,
            interpreter=request.runtime.interpreter,
            bootstrap=request.runtime.bootstrap,
            project_runtime_root=request.project_runtime_root,
            network="none",
            control_root=control_root,
            environment_id=request.runtime.environment_id,
        )
        preflight = preflight_reserved_imports(context)
        if preflight.status != "PASS":
            return {
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "findings": [],
                "diagnostic": preflight.reason,
            }
        execution = execute_launch_plan(
            build_launch_plan(context),
            request.runtime.bubblewrap,
            extra_argv=("specfact_code_review.run.runner", "/opt/specfact/config/0/request.json"),
        )
        response_path = output_root / "result.json"
        if execution.status != "PASS":
            return {
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "findings": [],
                "diagnostic": execution.reason,
            }
        try:
            output_paths = tuple(sorted(path.relative_to(output_root).as_posix() for path in output_root.rglob("*")))
            if output_paths != ("result.json",):
                raise ValueError("unexpected analyzer outputs")
            response = json.loads(response_path.read_text(encoding="utf-8"))
            if not isinstance(response, dict) or response.get("member") != request.member:
                raise ValueError("analyzer response identity mismatch")
            findings = response.get("findings")
            if not isinstance(findings, list):
                raise ValueError("analyzer findings are invalid")
            for finding in findings:
                ReviewFinding.model_validate(finding)
            return cast(dict[str, object], response)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return {
                "execution_state": "error",
                "evidence_outcome": "UNKNOWN",
                "findings": [],
                "diagnostic": "analyzer_output_invalid",
            }


def _not_applicable_member(reason: str) -> dict[str, object]:
    return {
        "execution_state": "not_applicable",
        "evidence_outcome": "NOT_APPLICABLE",
        "findings": [],
        "diagnostic": reason,
    }


def _dispatch_capsule_member(
    request: CapsuleMemberExecutionRequest,
    *,
    applicability: SnapshotInputClassification,
    sealed_bugs_policy: bool,
) -> dict[str, object]:
    if not request.files and not (
        request.member == "targeted-pytest-coverage"
        and request.complete_pytest_inventory
        and applicability.member(request.member).status != "NOT_APPLICABLE"
    ):
        return _not_applicable_member("empty_snapshot_input")
    if applicability.member(request.member).status == "NOT_APPLICABLE":
        return _not_applicable_member("member_input_not_applicable")
    if request.member == "semgrep-bugs" and not (request.options.bug_hunt or sealed_bugs_policy):
        return _not_applicable_member("conditional_member_not_activated")
    if request.member == "targeted-pytest-coverage" and request.options.no_tests:
        return _not_applicable_member("tests_explicitly_disabled_for_legacy_scope")
    return _execute_capsule_member(request)


def _run_capsule_snapshot(
    runtime: CapsuleRuntime,
    *,
    snapshot_root: Path,
    files: list[Path],
    options: ReviewOptions,
    config_roots: tuple[Path, ...] = (),
    member_argv: dict[str, tuple[str, ...]] | None = None,
    project_runtime_root: Path | None = None,
    scope_paths: tuple[str, ...] | None = None,
) -> CapsuleSnapshotResult:
    evidence: dict[str, dict[str, object]] = {}
    findings_by_member: dict[str, list[ReviewFinding]] = {}
    resolved_snapshot = snapshot_root.resolve()
    resolved_inputs = tuple(path.resolve() for path in files)
    relative_inputs = tuple(
        path.relative_to(resolved_snapshot).as_posix() if path.is_relative_to(resolved_snapshot) else path.as_posix()
        for path in resolved_inputs
    )
    applicability = classify_snapshot_input_kinds(relative_inputs if scope_paths is None else scope_paths)
    for member in default_pr_range_profile().all_ids:
        sealed_bugs_policy = member_argv is not None and "semgrep-bugs" in member_argv
        raw = _dispatch_capsule_member(
            CapsuleMemberExecutionRequest(
                runtime=runtime,
                member=member,
                invocation_id=str(uuid4()),
                snapshot_root=snapshot_root,
                files=files,
                options=options,
                config_roots=config_roots,
                adapter_argv=(member_argv or {}).get(member, ()),
                complete_pytest_inventory=(
                    member == "targeted-pytest-coverage" and member_argv is not None and member in member_argv
                ),
                project_runtime_root=(project_runtime_root if member in _PROJECT_RUNTIME_MEMBERS else None),
            ),
            applicability=applicability,
            sealed_bugs_policy=sealed_bugs_policy,
        )
        raw_findings = raw.get("findings", [])
        findings = [ReviewFinding.model_validate(value) for value in cast(list[object], raw_findings)]
        findings_by_member[member] = findings
        evidence[member] = {
            "execution_state": str(raw.get("execution_state", "error")),
            "evidence_outcome": str(raw.get("evidence_outcome", "UNKNOWN")),
            "version": _C14_ANALYZER_VERSIONS[member],
            "diagnostic": str(raw.get("diagnostic", "")),
            "sandbox_invocation": "fresh",
            "capsule_identity": runtime.identity,
        }
    return CapsuleSnapshotResult(evidence, findings_by_member)


def _mounted_config_path(index: int, path: Path) -> str:
    return str(Path("/opt/specfact/config") / str(index) / path.name)


def _pylint_projection_argv(policy: scope.PylintPolicy, *, config_path: str) -> tuple[str, ...]:
    if policy.status != "PASS":
        raise ValueError(policy.reason)

    def cli_value(value: object) -> str:
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, list | tuple):
            return ",".join(str(item) for item in value)
        return str(value)

    return (
        "--rcfile",
        config_path,
        *(f"--{key}={cli_value(value)}" for key, value in sorted(policy.projection.items())),
    )


@dataclass
class _PolicyBindingBuilder:
    config_roots: list[Path] = field(default_factory=list)
    cleanup_roots: list[Path] = field(default_factory=list)
    member_argv: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def register(self, path: Path) -> str:
        root = path.parent
        self.config_roots.append(root)
        self.cleanup_roots.append(root)
        return _mounted_config_path(len(self.config_roots), path)

    def result(self) -> SnapshotPolicyBindings:
        return SnapshotPolicyBindings(
            tuple(self.config_roots),
            self.member_argv,
            tuple(dict.fromkeys(self.cleanup_roots)),
        )


def _bind_ruff_policy(builder: _PolicyBindingBuilder, policy_root: Path) -> None:
    policy = scope.resolve_ruff_policy(policy_root, expected_version="0.15.12")
    if policy.bundle_root is not None:
        builder.cleanup_roots.append(policy.bundle_root)
    projection = scope.project_ruff_policy(policy, snapshot_root=Path("/opt/specfact/snapshot"))
    if projection.status != "PASS":
        raise ValueError(projection.reason)
    if projection.config_path is None:
        builder.member_argv["ruff"] = projection.argv
        return
    mounted = builder.register(projection.config_path)
    builder.member_argv["ruff"] = tuple(
        mounted if value == str(projection.config_path) else value for value in projection.argv
    )


def _bind_basedpyright_policy(
    builder: _PolicyBindingBuilder,
    policy_root: Path,
    *,
    relative_inputs: tuple[str, ...],
) -> None:
    policy = scope.resolve_basedpyright_policy(policy_root, expected_version="1.39.10")
    if policy.bundle_root is not None:
        builder.cleanup_roots.append(policy.bundle_root)
    projection = scope.project_basedpyright_policy(
        policy,
        snapshot_root=Path("/opt/specfact/snapshot"),
        eligible_inputs=relative_inputs,
    )
    if projection.status != "PASS" or projection.config_path is None:
        raise ValueError(projection.reason or "basedpyright_projection_missing")
    mounted = builder.register(projection.config_path)
    builder.member_argv["basedpyright"] = tuple(
        mounted if value == str(projection.config_path) else value for value in projection.argv
    )


def _bind_pylint_policy(builder: _PolicyBindingBuilder, policy_root: Path) -> None:
    policy = scope.resolve_pylint_policy(policy_root, expected_version="4.0.7")
    pylint_root = Path(tempfile.mkdtemp(prefix="specfact-pylint-projection-"))
    pylint_config = pylint_root / "pylintrc"
    pylint_config.write_text("[MAIN]\n", encoding="utf-8")
    pylint_config.chmod(0o444)
    mounted = builder.register(pylint_config)
    builder.member_argv["pylint"] = _pylint_projection_argv(policy, config_path=mounted)


def _bind_radon_policy(builder: _PolicyBindingBuilder) -> None:
    projection = scope.project_radon_policy(Path("/opt/specfact/snapshot"), expected_version="6.0.1")
    if projection.status != "PASS" or projection.contract != "radon-full-result-v1":
        raise ValueError(projection.reason or "radon_projection_missing")
    builder.member_argv["radon"] = (projection.contract,)


def _bind_semgrep_policy(builder: _PolicyBindingBuilder, policy_root: Path) -> None:
    if not (policy_root / ".semgrep").is_dir():
        return
    builder.config_roots.append(policy_root)
    mounted = str(Path("/opt/specfact/config") / str(len(builder.config_roots)))
    builder.member_argv["semgrep-clean"] = (mounted,)
    if (policy_root / ".semgrep/bugs.yaml").is_file():
        builder.member_argv["semgrep-bugs"] = (mounted,)


def _ini_projection_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list | tuple):
        return "\n    ".join(str(item) for item in value)
    if isinstance(value, str | int | float):
        return str(value)
    raise ValueError("policy_projection_value_unsupported")


def _serialize_pytest_projection(values: dict[str, object]) -> str:
    lines = ["[pytest]"]
    lines.extend(f"{key} = {_ini_projection_value(value)}" for key, value in sorted(values.items()))
    return "\n".join(lines) + "\n"


def _serialize_coverage_projection(values: dict[str, object]) -> str:
    sections: dict[str, dict[str, object]] = {}
    for qualified, value in values.items():
        if ":" not in qualified:
            raise ValueError("coverage_policy_projection_field_unsupported")
        section, key = qualified.split(":", maxsplit=1)
        sections.setdefault(section, {})[key] = value
    lines: list[str] = []
    for section, fields in sorted(sections.items()):
        lines.append(f"[{section}]")
        lines.extend(f"{key} = {_ini_projection_value(value)}" for key, value in sorted(fields.items()))
    return "\n".join(lines) + "\n"


def _write_policy_projection(builder: _PolicyBindingBuilder, *, name: str, payload: str) -> str:
    root = Path(tempfile.mkdtemp(prefix=f"specfact-{name}-projection-"))
    path = root / name
    path.write_text(payload, encoding="utf-8")
    path.chmod(0o444)
    return builder.register(path)


def _bind_pytest_coverage_policy(
    builder: _PolicyBindingBuilder,
    policy_bundle: object | None,
) -> None:
    pytest_policy = _pytest_policy_values(policy_bundle)
    selection = validate_pytest_selection_controls(pytest_policy)
    if selection.status != "PASS":
        raise ValueError(selection.reason)
    private_root = Path("/opt/specfact/tmp")
    pytest_projection = project_pytest_policy(
        pytest_policy,
        snapshot_root=Path("/opt/specfact/snapshot"),
        output_root=private_root / "pytest",
    )
    if pytest_projection.status != "PASS":
        raise ValueError(pytest_projection.reason)
    coverage_projection = project_coverage_policy(
        _coverage_policy_values(policy_bundle),
        snapshot_root=Path("/opt/specfact/snapshot"),
        output_root=private_root / "coverage",
    )
    if coverage_projection.status != "PASS":
        raise ValueError(coverage_projection.reason)
    pytest_config = _write_policy_projection(
        builder,
        name="pytest.ini",
        payload=_serialize_pytest_projection(pytest_projection.values),
    )
    coverage_config = _write_policy_projection(
        builder,
        name="coveragerc",
        payload=_serialize_coverage_projection(coverage_projection.values),
    )
    builder.member_argv["targeted-pytest-coverage"] = (
        "-c",
        pytest_config,
        "--rootdir",
        "/opt/specfact/snapshot",
        "--cov-config",
        coverage_config,
    )
    test_roots = tuple(str(value) for value in cast(list[object], pytest_policy["testpaths"]))
    builder.member_argv["contracts"] = (
        "contract-inputs-v1",
        *(value for root in test_roots for value in ("--test-root", root)),
    )


def _snapshot_policy_bindings(
    policy_bundle: object | None,
    *,
    snapshot_root: Path,
    files: list[Path],
) -> SnapshotPolicyBindings:
    builder = _PolicyBindingBuilder()
    _bind_pytest_coverage_policy(builder, policy_bundle)
    _bind_radon_policy(builder)
    if policy_bundle is None:
        return builder.result()
    policy_root = cast(Path, cast(Any, policy_bundle).root)
    relative_inputs = tuple(
        sorted(
            path.resolve().relative_to(snapshot_root.resolve()).as_posix()
            for path in files
            if path.resolve().is_relative_to(snapshot_root.resolve())
        )
    )
    _bind_ruff_policy(builder, policy_root)
    _bind_basedpyright_policy(builder, policy_root, relative_inputs=relative_inputs)
    _bind_pylint_policy(builder, policy_root)
    _bind_semgrep_policy(builder, policy_root)
    return builder.result()


def validate_invocation_manifests(context: SyntheticSnapshotContext) -> InvocationManifestResult:
    member_ids = default_pr_range_profile().all_ids
    members = tuple(
        InvocationManifestEvidence(
            member_id,
            context.inputs[index].digest if index < len(context.inputs) else "",
            context.invoked_inputs[index].digest if index < len(context.invoked_inputs) else "",
        )
        for index, member_id in enumerate(member_ids)
    )
    complete = len(context.inputs) == len(member_ids) == len(context.invoked_inputs)
    matching = complete and all(
        eligible == invoked for eligible, invoked in zip(context.inputs, context.invoked_inputs, strict=True)
    )
    return InvocationManifestResult("PASS" if matching else "UNKNOWN", members)


def apply_target_policy(
    *,
    target_policy: dict[str, object],
    candidate_policy: dict[str, object],
    base_findings: tuple[object, ...],
    head_findings: tuple[object, ...],
) -> TargetPolicyResult:
    del base_findings, head_findings
    if candidate_policy != target_policy:
        return TargetPolicyResult("UNKNOWN", "candidate_policy_change")
    return TargetPolicyResult("PASS", "target_policy_applied")


def select_range_policy(
    *, merge_base: str, target_tip: str, head: str, context_target_tip: str
) -> RangePolicySelection:
    if target_tip != context_target_tip or head == merge_base:
        raise ValueError("range policy identity mismatch")
    return RangePolicySelection(merge_base, target_tip, ("merge_base", "head"))


def _matches_python_file(path: Path, patterns: tuple[str, ...]) -> bool:
    match_path = path if path.is_absolute() else Path("/opt/specfact/snapshot") / path
    return any(pytest_path_matches_pattern(match_path, pattern, platform="linux") for pattern in patterns)


ImportedPytestDefinition = tuple[
    str,
    ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    tuple[set[str], set[str]],
    dict[str, ast.ClassDef],
    frozenset[str],
]


@dataclass(frozen=True)
class _PytestDiscoveryPolicy:
    function_patterns: tuple[str, ...]
    class_patterns: tuple[str, ...]
    import_roots: tuple[Path, ...]


@dataclass(frozen=True)
class _ModeledTestDecorators:
    pytest_prefixes: tuple[str, ...]
    unittest_names: frozenset[str]


@dataclass(frozen=True)
class _PytestSelectorContext:
    relative: str
    imported: tuple[ImportedPytestDefinition, ...]
    classes: dict[str, ast.ClassDef]
    unittest_aliases: tuple[set[str], set[str]]
    imported_unittest_cases: frozenset[str]
    function_patterns: tuple[str, ...]
    class_patterns: tuple[str, ...]


def _test_selectors(
    path: Path,
    relative: str,
    policy: _PytestDiscoveryPolicy,
    *,
    snapshot_root: Path,
) -> tuple[str, ...]:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return ()
    if _module_disables_pytest_collection(tree):
        return ()
    imported = _imported_pytest_definitions(
        tree,
        path=path,
        snapshot_root=snapshot_root,
        import_roots=policy.import_roots,
    )
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    for name, node, _aliases, module_classes, _unsupported_bases in imported:
        for class_name, class_node in module_classes.items():
            classes.setdefault(class_name, class_node)
        if isinstance(node, ast.ClassDef):
            classes.setdefault(name, node)
    imported_unittest_cases = {
        name
        for name, node, aliases, module_classes, _unsupported_bases in imported
        if isinstance(node, ast.ClassDef)
        and _is_unittest_case(
            node,
            module_classes,
            *aliases,
            direct_unittest_classes=frozenset(),
            visiting=frozenset(),
        )
    }
    context = _PytestSelectorContext(
        relative,
        imported,
        classes,
        _unittest_aliases(tree),
        frozenset(imported_unittest_cases),
        policy.function_patterns,
        policy.class_patterns,
    )
    return tuple(selector for node in tree.body for selector in _node_test_selectors(node, context))


def _node_test_selectors(node: ast.stmt, context: _PytestSelectorContext) -> tuple[str, ...]:
    if isinstance(node, ast.ImportFrom):
        return _imported_test_selectors(
            context.relative,
            context.imported,
            set(context.imported_unittest_cases),
            context.function_patterns,
            context.class_patterns,
            selected_names={alias.asname or alias.name for alias in node.names},
        )
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
        fnmatch.fnmatch(node.name, pattern) for pattern in context.function_patterns
    ):
        return (f"{context.relative}::{node.name}",)
    if not isinstance(node, ast.ClassDef):
        return ()
    methods = _pytest_class_test_methods(
        node,
        context.classes,
        context.unittest_aliases,
        context.function_patterns,
        context.class_patterns,
        direct_unittest_classes=context.imported_unittest_cases,
    )
    return tuple(f"{context.relative}::{node.name}::{method}" for method in methods)


def _imported_module_path(
    statement: ast.ImportFrom,
    *,
    path: Path,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> Path | None:
    search = _import_search(statement, path=path, snapshot_root=snapshot_root, import_roots=import_roots)
    if search is None:
        return None
    module_parts, search_roots = search
    return _module_path_from_parts(module_parts, search_roots)


def _module_path_from_parts(module_parts: tuple[str, ...], search_roots: tuple[Path, ...]) -> Path | None:
    module_parts = tuple(part for part in module_parts if part)
    candidates = tuple(
        candidate
        for root in search_roots
        for candidate in (
            root.joinpath(*module_parts).with_suffix(".py"),
            root.joinpath(*module_parts, "__init__.py"),
        )
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _import_search(
    statement: ast.ImportFrom,
    *,
    path: Path,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> tuple[tuple[str, ...], tuple[Path, ...]] | None:
    if not statement.level:
        return tuple((statement.module or "").split(".")), import_roots
    owning_root = next((root for root in import_roots if path.is_relative_to(root)), snapshot_root)
    relative_parent = path.relative_to(owning_root).parent
    if statement.level > len(relative_parent.parts) + 1:
        return None
    prefix = relative_parent.parts[: len(relative_parent.parts) - statement.level + 1]
    return (*prefix, *(statement.module or "").split(".")), (owning_root,)


def _imported_pytest_definitions(
    tree: ast.Module,
    *,
    path: Path,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> tuple[ImportedPytestDefinition, ...]:
    definitions: list[ImportedPytestDefinition] = []
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom) or any(alias.name == "*" for alias in statement.names):
            continue
        module_path = _imported_module_path(
            statement,
            path=path,
            snapshot_root=snapshot_root,
            import_roots=import_roots,
        )
        if module_path is None:
            continue
        for alias in statement.names:
            resolved = _resolve_imported_pytest_definition(
                module_path,
                alias.name,
                snapshot_root=snapshot_root,
                import_roots=import_roots,
                visiting=frozenset(),
            )
            if resolved is not None:
                definitions.append((alias.asname or alias.name, *resolved))
    return tuple(definitions)


def _resolve_imported_pytest_definition(
    module_path: Path,
    export_name: str,
    *,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
    visiting: frozenset[Path],
) -> (
    tuple[
        ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        tuple[set[str], set[str]],
        dict[str, ast.ClassDef],
        frozenset[str],
    ]
    | None
):
    resolved_path = module_path.resolve()
    if resolved_path in visiting:
        return None
    try:
        tree = ast.parse(module_path.read_bytes())
    except (OSError, SyntaxError):
        return None
    direct = _direct_pytest_definition(tree, export_name)
    if direct is not None:
        module_classes = _module_class_definitions(tree)
        return direct, _unittest_aliases(tree), module_classes, _unsupported_imported_bases(tree, module_classes)
    reexport = _pytest_reexport(tree, export_name)
    if reexport is None:
        return None
    statement, source_name = reexport
    nested_path = _imported_module_path(
        statement,
        path=module_path,
        snapshot_root=snapshot_root,
        import_roots=import_roots,
    )
    if nested_path is None:
        return None
    return _resolve_imported_pytest_definition(
        nested_path,
        source_name,
        snapshot_root=snapshot_root,
        import_roots=import_roots,
        visiting=visiting | {resolved_path},
    )


def _direct_pytest_definition(
    tree: ast.Module,
    export_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None:
    return next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == export_name
        ),
        None,
    )


def _module_class_definitions(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _unsupported_imported_bases(tree: ast.Module, module_classes: dict[str, ast.ClassDef]) -> frozenset[str]:
    imported_names = {
        alias.asname or alias.name
        for statement in tree.body
        if isinstance(statement, ast.ImportFrom) and statement.module != "unittest"
        for alias in statement.names
        if alias.name != "*"
    }
    return frozenset(
        base.id
        for node in module_classes.values()
        for base in node.bases
        if isinstance(base, ast.Name) and base.id in imported_names and base.id not in module_classes
    )


def _pytest_reexport(tree: ast.Module, export_name: str) -> tuple[ast.ImportFrom, str] | None:
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom):
            continue
        alias = next((item for item in statement.names if (item.asname or item.name) == export_name), None)
        if alias is not None and alias.name != "*":
            return statement, alias.name
    return None


def _imported_test_selectors(
    relative: str,
    imported: tuple[ImportedPytestDefinition, ...],
    imported_unittest_cases: set[str],
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
    *,
    selected_names: set[str],
) -> tuple[str, ...]:
    selectors: list[str] = []
    for name, node, _aliases, module_classes, _unsupported_bases in imported:
        if name not in selected_names:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            fnmatch.fnmatch(name, pattern) for pattern in function_patterns
        ):
            selectors.append(f"{relative}::{name}")
        elif isinstance(node, ast.ClassDef):
            is_unittest = name in imported_unittest_cases
            if not is_unittest and not any(fnmatch.fnmatch(name, pattern) for pattern in class_patterns):
                continue
            methods = _class_test_methods(
                node,
                module_classes,
                ("test*",) if is_unittest else function_patterns,
                visiting=frozenset(),
            )
            selectors.extend(f"{relative}::{name}::{method}" for method in methods)
    return tuple(selectors)


def _pytest_class_test_methods(
    node: ast.ClassDef,
    classes: dict[str, ast.ClassDef],
    unittest_aliases: tuple[set[str], set[str]],
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
    *,
    direct_unittest_classes: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    module_aliases, case_aliases = unittest_aliases
    is_unittest_case = _is_unittest_case(
        node,
        classes,
        module_aliases,
        case_aliases,
        direct_unittest_classes=direct_unittest_classes,
        visiting=frozenset(),
    )
    if not any(fnmatch.fnmatch(node.name, pattern) for pattern in class_patterns) and not is_unittest_case:
        return ()
    method_patterns = ("test*",) if is_unittest_case else function_patterns
    return _class_test_methods(node, classes, method_patterns, visiting=frozenset())


def _unittest_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    modules: set[str] = set()
    cases: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == "unittest")
        elif isinstance(node, ast.ImportFrom) and node.module == "unittest":
            cases.update(alias.asname or alias.name for alias in node.names if alias.name == "TestCase")
    return modules, cases


def _is_unittest_case(
    node: ast.ClassDef,
    classes: dict[str, ast.ClassDef],
    module_aliases: set[str],
    case_aliases: set[str],
    *,
    direct_unittest_classes: frozenset[str],
    visiting: frozenset[str],
) -> bool:
    if node.name in visiting:
        return False
    active = visiting | {node.name}
    for base in node.bases:
        if (
            isinstance(base, ast.Attribute)
            and base.attr == "TestCase"
            and isinstance(base.value, ast.Name)
            and base.value.id in module_aliases
        ):
            return True
        if isinstance(base, ast.Name) and base.id in case_aliases:
            return True
        if isinstance(base, ast.Name) and base.id in direct_unittest_classes:
            return True
        if (
            isinstance(base, ast.Name)
            and base.id in classes
            and _is_unittest_case(
                classes[base.id],
                classes,
                module_aliases,
                case_aliases,
                direct_unittest_classes=direct_unittest_classes,
                visiting=active,
            )
        ):
            return True
    return False


def _class_declared_names(node: ast.ClassDef) -> set[str]:
    names = {
        child.name for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    for child in node.body:
        if isinstance(child, (ast.Assign, ast.AnnAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def _class_test_methods(
    node: ast.ClassDef,
    classes: dict[str, ast.ClassDef],
    function_patterns: tuple[str, ...],
    *,
    visiting: frozenset[str],
) -> tuple[str, ...]:
    if node.name in visiting:
        return ()
    declared = _class_declared_names(node)
    methods = [
        child.name
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(fnmatch.fnmatch(child.name, pattern) for pattern in function_patterns)
    ]
    inherited = (
        method
        for base in node.bases
        if isinstance(base, ast.Name) and base.id in classes
        for method in _class_test_methods(
            classes[base.id],
            classes,
            function_patterns,
            visiting=visiting | {node.name},
        )
        if method not in declared
    )
    return tuple(dict.fromkeys((*methods, *inherited)))


def _module_disables_pytest_collection(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if node.value.value is False and any(
            isinstance(target, ast.Name) and target.id == "__test__" for target in node.targets
        ):
            return True
    return False


def _module_uses_wildcard_import(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False
    return any(
        isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names) for node in tree.body
    )


def _module_has_unsupported_imported_test_base(
    path: Path,
    *,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False
    return any(
        unsupported_bases
        for _name, _node, _aliases, _module_classes, unsupported_bases in _imported_pytest_definitions(
            tree,
            path=path,
            snapshot_root=snapshot_root,
            import_roots=import_roots,
        )
    )


def _module_imports_dynamic_test_export(
    path: Path,
    *,
    snapshot_root: Path,
    policy: _PytestDiscoveryPolicy,
) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom):
            continue
        exported = tuple(alias.asname or alias.name for alias in statement.names)
        if not any(_test_name_matches(name, (*policy.function_patterns, *policy.class_patterns)) for name in exported):
            continue
        module_path = _imported_module_path(
            statement,
            path=path,
            snapshot_root=snapshot_root,
            import_roots=policy.import_roots,
        )
        if module_path is not None and _module_has_dynamic_test_members(
            module_path,
            function_patterns=policy.function_patterns,
            class_patterns=policy.class_patterns,
        ):
            return True
    return False


def _module_has_dynamic_test_members(
    path: Path,
    *,
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False

    if _module_uses_dynamic_namespace(tree):
        return True
    if _module_has_control_flow_test_bindings(
        tree,
        function_patterns=function_patterns,
        class_patterns=class_patterns,
    ):
        return True
    if any(
        _class_has_control_flow_test_methods(node, function_patterns)
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    ):
        return True

    for node in ast.walk(tree):
        if (
            _class_uses_metaclass(node)
            or _assignment_sets_dynamic_test_member(
                node,
                function_patterns=function_patterns,
                class_patterns=class_patterns,
            )
            or _call_sets_dynamic_test_member(node, function_patterns=function_patterns)
        ):
            return True
    return False


def _test_name_matches(value: object, patterns: tuple[str, ...]) -> bool:
    return isinstance(value, str) and any(fnmatch.fnmatch(value, pattern) for pattern in patterns)


def _class_uses_metaclass(node: ast.AST) -> bool:
    return isinstance(node, ast.ClassDef) and any(keyword.arg == "metaclass" for keyword in node.keywords)


def _assignment_target_nodes(target: ast.expr) -> tuple[ast.Name | ast.Attribute, ...]:
    if isinstance(target, (ast.Name, ast.Attribute)):
        return (target,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(item for element in target.elts for item in _assignment_target_nodes(element))
    if isinstance(target, ast.Starred):
        return _assignment_target_nodes(target.value)
    return ()


def _assignment_targets(node: ast.AST) -> tuple[ast.expr, ...]:
    if isinstance(node, ast.Assign):
        return tuple(node.targets)
    if isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
        return (node.target,)
    return ()


def _assignment_sets_dynamic_test_member(
    node: ast.AST,
    *,
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> bool:
    if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
        return False
    targets = _assignment_targets(node)
    value = node.value
    destructured = any(isinstance(target, (ast.Tuple, ast.List, ast.Starred)) for target in targets)
    return any(
        (isinstance(target, ast.Attribute) and _test_name_matches(target.attr, function_patterns))
        or (
            isinstance(target, ast.Name)
            and (_test_name_matches(target.id, function_patterns) or _test_name_matches(target.id, class_patterns))
            and (
                destructured
                or isinstance(value, (ast.Name, ast.Attribute, ast.Lambda, ast.Call, ast.Subscript, ast.IfExp))
            )
        )
        for target in targets
        for target in _assignment_target_nodes(target)
    )


def _call_sets_dynamic_test_member(node: ast.AST, *, function_patterns: tuple[str, ...]) -> bool:
    return (
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "setattr")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "setattr")
        )
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and _test_name_matches(node.args[1].value, function_patterns)
    )


def _module_has_test_execution_override(
    path: Path,
    *,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False
    imported = _imported_pytest_definitions(
        tree,
        path=path,
        snapshot_root=snapshot_root,
        import_roots=import_roots,
    )
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    for name, node, _aliases, module_classes, _unsupported_bases in imported:
        for class_name, class_node in module_classes.items():
            classes.setdefault(class_name, class_node)
        if isinstance(node, ast.ClassDef):
            classes.setdefault(name, node)
    imported_cases = frozenset(
        name
        for name, node, aliases, module_classes, _unsupported_bases in imported
        if isinstance(node, ast.ClassDef)
        and _is_unittest_case(
            node,
            module_classes,
            *aliases,
            direct_unittest_classes=frozenset(),
            visiting=frozenset(),
        )
    )
    module_aliases, case_aliases = _unittest_aliases(tree)
    context = _PytestSelectorContext(
        path.relative_to(snapshot_root).as_posix(),
        imported,
        classes,
        (module_aliases, case_aliases),
        imported_cases,
        function_patterns,
        class_patterns,
    )
    return any(
        _class_has_test_execution_override(
            name,
            node,
            context,
        )
        for name, node in classes.items()
    )


def _definition_has_unsupported_decorator(
    definition: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    modeled: _ModeledTestDecorators,
) -> bool:
    return any(not _is_modeled_test_decorator(decorator, modeled) for decorator in definition.decorator_list)


def _class_has_unsupported_test_decorator(
    node: ast.ClassDef,
    classes: dict[str, ast.ClassDef],
    modeled: _ModeledTestDecorators,
    function_patterns: tuple[str, ...],
    *,
    visiting: frozenset[str],
) -> bool:
    if node.name in visiting:
        return False
    if _definition_has_unsupported_decorator(node, modeled):
        return True
    if any(
        _definition_has_unsupported_decorator(child, modeled)
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _test_name_matches(child.name, function_patterns)
    ):
        return True
    return any(
        _class_has_unsupported_test_decorator(
            classes[base.id],
            classes,
            modeled,
            function_patterns,
            visiting=visiting | {node.name},
        )
        for base in node.bases
        if isinstance(base, ast.Name) and base.id in classes
    )


def _module_has_unsupported_test_decorator(
    tree: ast.Module,
    *,
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> bool:
    modeled = _modeled_test_decorators(tree)
    classes = _module_class_definitions(tree)
    return any(
        _definition_has_unsupported_decorator(definition, modeled)
        for definition in _test_definitions(tree, function_patterns)
    ) or any(
        _class_has_unsupported_test_decorator(
            node,
            classes,
            modeled,
            function_patterns,
            visiting=frozenset(),
        )
        for node in classes.values()
        if _test_name_matches(node.name, class_patterns)
    )


def _control_flow_binding_targets(node: ast.AST) -> tuple[ast.expr, ...]:
    if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
        return (node.target,)
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return tuple(item.optional_vars for item in node.items if item.optional_vars is not None)
    return ()


def _setter_target_binding_name(node: ast.AST) -> str:
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
        and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr) == "setattr"
        and node.args
    ):
        return ""
    return _decorator_full_name(node.args[0]).partition(".")[0]


def _module_nonimport_binding_names(tree: ast.Module) -> frozenset[str]:
    nodes = _module_execution_nodes(tree)
    target_names = {
        _decorator_full_name(target).partition(".")[0]
        for node in nodes
        for binding_target in (*_assignment_targets(node), *_control_flow_binding_targets(node))
        for target in _assignment_target_nodes(binding_target)
        if isinstance(target, (ast.Name, ast.Attribute))
    }
    definition_names = {
        node.name for node in nodes if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    exception_names = {node.name for node in nodes if isinstance(node, ast.ExceptHandler) and node.name is not None}
    setter_target_names = {target for node in nodes if (target := _setter_target_binding_name(node))}
    return frozenset(target_names | definition_names | exception_names | setter_target_names)


def _import_binding_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.asname or alias.name.split(".", maxsplit=1)[0] for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return tuple(alias.asname or alias.name for alias in node.names)
    return ()


def _stable_modeled_import_aliases(tree: ast.Module, aliases: set[str]) -> set[str]:
    rebound = _module_nonimport_binding_names(tree)
    imported = tuple(name for node in _module_execution_nodes(tree) for name in _import_binding_names(node))
    return {alias for alias in aliases if alias not in rebound and imported.count(alias) == 1}


def _modeled_test_decorators(tree: ast.Module) -> _ModeledTestDecorators:
    pytest_modules = _stable_modeled_import_aliases(tree, _imported_module_aliases(tree, "pytest"))
    pytest_marks = _stable_modeled_import_aliases(tree, _imported_member_aliases(tree, "pytest", frozenset({"mark"})))
    unittest_members = frozenset({"expectedFailure", "skip", "skipIf", "skipUnless"})
    unittest_modules = _stable_modeled_import_aliases(tree, _imported_module_aliases(tree, "unittest"))
    unittest_decorators = _stable_modeled_import_aliases(
        tree, _imported_member_aliases(tree, "unittest", unittest_members)
    )
    pytest_prefixes = tuple(f"{module}.mark." for module in pytest_modules) + tuple(f"{mark}." for mark in pytest_marks)
    unittest_names = {
        *(f"{module}.{member}" for module in unittest_modules for member in unittest_members),
        *unittest_decorators,
    }
    return _ModeledTestDecorators(pytest_prefixes, frozenset(unittest_names))


def _imported_module_aliases(tree: ast.Module, module: str) -> set[str]:
    return {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == module
    }


def _imported_member_aliases(tree: ast.Module, module: str, members: frozenset[str]) -> set[str]:
    return {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
        if alias.name in members
    }


def _test_definitions(
    tree: ast.Module,
    function_patterns: tuple[str, ...],
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    return tuple(
        node
        for parent in tree.body
        for node in ((parent,) if not isinstance(parent, ast.ClassDef) else tuple(parent.body))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(fnmatch.fnmatch(node.name, pattern) for pattern in function_patterns)
    )


def _path_has_unsupported_test_decorator(
    path: Path,
    *,
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False
    return _module_has_unsupported_test_decorator(
        tree,
        function_patterns=function_patterns,
        class_patterns=class_patterns,
    )


def _resolved_import_has_unsupported_test_decorator(
    module_path: Path,
    export_name: str,
    *,
    snapshot_root: Path,
    policy: _PytestDiscoveryPolicy,
    visiting: frozenset[Path],
) -> bool:
    resolved_path = module_path.resolve()
    if resolved_path in visiting:
        return False
    try:
        tree = ast.parse(module_path.read_bytes())
    except (OSError, SyntaxError):
        return False
    direct = _direct_pytest_definition(tree, export_name)
    if isinstance(direct, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _definition_has_unsupported_decorator(direct, _modeled_test_decorators(tree))
    if isinstance(direct, ast.ClassDef):
        return _class_has_unsupported_test_decorator(
            direct,
            _module_class_definitions(tree),
            _modeled_test_decorators(tree),
            policy.function_patterns,
            visiting=frozenset(),
        )
    reexport = _pytest_reexport(tree, export_name)
    if reexport is None:
        return False
    statement, source_name = reexport
    nested_path = _imported_module_path(
        statement,
        path=module_path,
        snapshot_root=snapshot_root,
        import_roots=policy.import_roots,
    )
    return nested_path is not None and _resolved_import_has_unsupported_test_decorator(
        nested_path,
        source_name,
        snapshot_root=snapshot_root,
        policy=policy,
        visiting=visiting | {resolved_path},
    )


def _path_has_unsupported_imported_test_decorator(
    path: Path,
    *,
    snapshot_root: Path,
    policy: _PytestDiscoveryPolicy,
) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom) or any(alias.name == "*" for alias in statement.names):
            continue
        module_path = _imported_module_path(
            statement,
            path=path,
            snapshot_root=snapshot_root,
            import_roots=policy.import_roots,
        )
        if module_path is None:
            continue
        for alias in statement.names:
            bound_name = alias.asname or alias.name
            if not _test_name_matches(bound_name, (*policy.function_patterns, *policy.class_patterns)):
                continue
            if _resolved_import_has_unsupported_test_decorator(
                module_path,
                alias.name,
                snapshot_root=snapshot_root,
                policy=policy,
                visiting=frozenset(),
            ):
                return True
    return False


def _path_declares_unsupported_pytest_fixture(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return False
    return _module_declares_autouse_fixture(tree) or _module_declares_execution_shaping_fixture(tree)


def _has_unsupported_test_decorator(
    paths: tuple[Path, ...],
    *,
    snapshot_root: Path,
    policy: _PytestDiscoveryPolicy,
) -> bool:
    return any(
        _path_has_unsupported_test_decorator(
            path,
            function_patterns=policy.function_patterns,
            class_patterns=policy.class_patterns,
        )
        or _path_has_unsupported_imported_test_decorator(
            path,
            snapshot_root=snapshot_root,
            policy=policy,
        )
        for path in paths
    )


def _is_modeled_test_decorator(
    decorator: ast.expr,
    modeled: _ModeledTestDecorators,
) -> bool:
    name = _decorator_full_name(decorator.func if isinstance(decorator, ast.Call) else decorator)
    return name.startswith(modeled.pytest_prefixes) or name in modeled.unittest_names


def _class_has_test_execution_override(
    name: str,
    node: ast.ClassDef,
    context: _PytestSelectorContext,
) -> bool:
    declared = _class_declared_names(node)
    module_aliases, case_aliases = context.unittest_aliases
    is_unittest = name in context.imported_unittest_cases or _is_unittest_case(
        node,
        context.classes,
        module_aliases,
        case_aliases,
        direct_unittest_classes=context.imported_unittest_cases,
        visiting=frozenset(),
    )
    if is_unittest:
        return bool({"run", "__call__", "_callTestMethod", "__getattribute__", "__getattr__"} & declared)
    if not {"__getattribute__", "__getattr__"} & declared:
        return False
    return bool(
        _pytest_class_test_methods(
            node,
            context.classes,
            context.unittest_aliases,
            context.function_patterns,
            context.class_patterns,
            direct_unittest_classes=context.imported_unittest_cases,
        )
    )


def _loaded_conftest_paths(snapshot_root: Path, roots: tuple[str, ...]) -> tuple[Path, ...]:
    paths = {snapshot_root / "conftest.py"}
    for root in roots:
        root_path = snapshot_root / root
        current = root_path
        while current != snapshot_root:
            paths.add(current / "conftest.py")
            current = current.parent
        if root_path.is_dir():
            paths.update(root_path.rglob("conftest.py"))
    return tuple(sorted(path for path in paths if path.is_file()))


def _decorated_pytest_hook_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        keyword.value.value
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        for keyword in decorator.keywords
        if keyword.arg == "specname"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
        and keyword.value.value.startswith("pytest_")
    }


def _imported_pytest_hook_names(tree: ast.Module) -> set[str]:
    return {
        alias.asname or alias.name
        for node in _module_execution_nodes(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if (alias.asname or alias.name).startswith("pytest_")
    }


def _module_execution_nodes(tree: ast.Module) -> tuple[ast.AST, ...]:
    pending: list[ast.AST] = list(reversed(tree.body))
    nodes: list[ast.AST] = []
    while pending:
        node = pending.pop()
        nodes.append(node)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            pending.extend(reversed(tuple(ast.iter_child_nodes(node))))
    return tuple(nodes)


def _module_has_control_flow_test_bindings(
    tree: ast.Module,
    *,
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> bool:
    direct_statements = {id(node) for node in tree.body}
    for node in _module_execution_nodes(tree):
        if id(node) in direct_statements:
            continue
        if isinstance(node, ast.ImportFrom) and any(
            _test_name_matches(alias.asname or alias.name, (*function_patterns, *class_patterns))
            for alias in node.names
        ):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _test_name_matches(
            node.name, function_patterns
        ):
            return True
        if isinstance(node, ast.ClassDef) and _test_name_matches(node.name, class_patterns):
            return True
    return False


def _class_has_control_flow_test_methods(node: ast.ClassDef, function_patterns: tuple[str, ...]) -> bool:
    direct_statements = {id(child) for child in node.body}
    pending: list[ast.AST] = list(reversed(node.body))
    while pending:
        child = pending.pop()
        if (
            id(child) not in direct_statements
            and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _test_name_matches(child.name, function_patterns)
        ):
            return True
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            pending.extend(reversed(tuple(ast.iter_child_nodes(child))))
    return False


def _assigned_pytest_hook_names(tree: ast.Module) -> set[str]:
    return {
        target.id
        for node in _module_execution_nodes(tree)
        for assignment_target in _assignment_targets(node)
        for target in _assignment_target_nodes(assignment_target)
        if isinstance(target, ast.Name) and target.id.startswith("pytest_")
    }


def _is_module_namespace_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"globals", "locals", "vars"}
        and not node.args
        and not node.keywords
    )


def _module_uses_dynamic_namespace(tree: ast.Module) -> bool:
    execution_nodes = _module_execution_nodes(tree)
    return (
        any(_is_module_namespace_call(node) for node in execution_nodes)
        or any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}
            for node in execution_nodes
        )
        or any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {"__dir__", "__getattr__"}
            for node in tree.body
        )
    )


def _pytest_fixture_names(tree: ast.Module) -> set[str]:
    return {
        *(f"{module}.fixture" for module in _imported_module_aliases(tree, "pytest")),
        *_imported_member_aliases(tree, "pytest", frozenset({"fixture"})),
    }


def _pytest_fixture_definitions(
    tree: ast.Module,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    fixture_names = _pytest_fixture_names(tree)
    return tuple(
        node
        for node in _module_execution_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            _decorator_full_name(decorator.func if isinstance(decorator, ast.Call) else decorator) in fixture_names
            for decorator in node.decorator_list
        )
    )


def _module_declares_autouse_fixture(tree: ast.Module) -> bool:
    fixture_names = {
        *(f"{module}.fixture" for module in _imported_module_aliases(tree, "pytest")),
        *_imported_member_aliases(tree, "pytest", frozenset({"fixture"})),
    }
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(decorator, ast.Call)
            and _decorator_full_name(decorator.func) in fixture_names
            and any(
                keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                for keyword in decorator.keywords
            )
            for decorator in node.decorator_list
        )
        for node in _module_execution_nodes(tree)
    )


def _is_pytest_node(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "node"


def _assignment_name_targets(node: ast.AST) -> frozenset[str]:
    return frozenset(
        target.id
        for assignment_target in _assignment_targets(node)
        for target in _assignment_target_nodes(assignment_target)
        if isinstance(target, ast.Name)
    )


def _is_pytest_node_alias_assignment(
    assignment: ast.Assign | ast.AnnAssign | ast.NamedExpr, aliases: frozenset[str]
) -> bool:
    value = assignment.value
    return value is not None and (_is_pytest_node(value) or (isinstance(value, ast.Name) and value.id in aliases))


def _fixture_pytest_node_aliases(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    aliases = frozenset[str]()
    assignments = tuple(
        child for child in ast.walk(node) if isinstance(child, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
    )
    while True:
        expanded = aliases.union(
            *(
                _assignment_name_targets(assignment)
                for assignment in assignments
                if _is_pytest_node_alias_assignment(assignment, aliases)
            )
        )
        if expanded == aliases:
            return aliases
        aliases = expanded


def _fixture_pytest_request_aliases(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    parameters = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    aliases = frozenset(parameter.arg for parameter in parameters if parameter.arg == "request")
    assignments = tuple(
        child for child in ast.walk(node) if isinstance(child, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
    )
    while True:
        expanded = aliases.union(
            *(
                _assignment_name_targets(assignment)
                for assignment in assignments
                if _expression_uses_pytest_request(assignment.value, aliases)
            )
        )
        if expanded == aliases:
            return aliases
        aliases = expanded


def _is_pytest_request_reference(node: ast.AST | None, aliases: frozenset[str]) -> bool:
    while isinstance(node, ast.Attribute):
        node = node.value
    return isinstance(node, ast.Name) and node.id in aliases


def _expression_uses_pytest_request(node: ast.AST | None, aliases: frozenset[str]) -> bool:
    return node is not None and any(_is_pytest_request_reference(child, aliases) for child in ast.walk(node))


def _is_pytest_config(node: ast.AST, request_aliases: frozenset[str]) -> bool:
    if not isinstance(node, ast.Attribute) or node.attr != "config":
        return False
    return _is_pytest_request_reference(node.value, request_aliases)


def _fixture_pytest_config_aliases(
    node: ast.FunctionDef | ast.AsyncFunctionDef, request_aliases: frozenset[str]
) -> frozenset[str]:
    parameters = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    aliases = frozenset(parameter.arg for parameter in parameters if parameter.arg == "pytestconfig")
    assignments = tuple(
        child for child in ast.walk(node) if isinstance(child, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
    )
    while True:
        expanded = aliases.union(
            *(
                _assignment_name_targets(assignment)
                for assignment in assignments
                if assignment.value is not None
                and (
                    _is_pytest_config(assignment.value, request_aliases)
                    or (isinstance(assignment.value, ast.Name) and assignment.value.id in aliases)
                )
            )
        )
        if expanded == aliases:
            return aliases
        aliases = expanded


def _fixture_accesses_pytest_plugin_manager(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    request_aliases = _fixture_pytest_request_aliases(node)
    config_aliases = _fixture_pytest_config_aliases(node, request_aliases)
    return any(
        isinstance(child, ast.Attribute)
        and child.attr == "pluginmanager"
        and (
            _is_pytest_config(child.value, request_aliases)
            or (isinstance(child.value, ast.Name) and child.value.id in config_aliases)
        )
        for child in ast.walk(node)
    )


def _call_exposes_pytest_request(node: ast.AST, aliases: frozenset[str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    expressions = (*node.args, *(keyword.value for keyword in node.keywords))
    return any(_expression_uses_pytest_request(expression, aliases) for expression in expressions)


def _is_ref(node: ast.AST, refs: frozenset[str]) -> bool:
    return _is_pytest_node(node) or (isinstance(node, ast.Name) and node.id in refs)


def _is_pytest_collected_callable(node: ast.AST, refs: frozenset[str]) -> bool:
    return isinstance(node, ast.Attribute) and node.attr in ("_obj", "obj") and _is_ref(node.value, refs)


def _is_pytest_dispatch_owner(node: ast.AST, refs: frozenset[str]) -> bool:
    return _is_ref(node, refs) or (
        isinstance(node, ast.Attribute) and node.attr == "__class__" and _is_ref(node.value, refs)
    )


def _is_pytest_dispatch_target(node: ast.AST, refs: frozenset[str]) -> bool:
    return (
        (
            isinstance(node, ast.Attribute)
            and node.attr in ("_obj", "obj", "runtest")
            and _is_pytest_dispatch_owner(node.value, refs)
        )
        or (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "__dict__"
            and _is_pytest_dispatch_owner(node.value.value, refs)
        )
        or (
            isinstance(node, (ast.Attribute, ast.Subscript))
            and any(_is_pytest_collected_callable(child, refs) for child in ast.walk(node))
        )
    )


def _pytest_dispatch_setter_arguments(node: ast.AST, refs: frozenset[str]) -> tuple[ast.AST, ast.AST] | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, (ast.Name, ast.Attribute)):
        return None
    setter_name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
    if setter_name == "setattr":
        return (node.args[0], node.args[1]) if len(node.args) >= 2 else None
    if setter_name != "__setattr__":
        return None
    if isinstance(node.func, ast.Attribute) and (
        _is_ref(node.func.value, refs) or _is_pytest_collected_callable(node.func.value, refs)
    ):
        return (node.func.value, node.args[0]) if node.args else None
    return (node.args[0], node.args[1]) if len(node.args) >= 2 else None


def _call_shapes_pytest_dispatch(node: ast.AST, refs: frozenset[str]) -> bool:
    arguments = _pytest_dispatch_setter_arguments(node, refs)
    if arguments is None:
        return False
    target, attribute = arguments
    return (
        isinstance(attribute, ast.Constant)
        and attribute.value in ("_obj", "obj", "runtest")
        and _is_pytest_dispatch_owner(target, refs)
    ) or _is_pytest_collected_callable(target, refs)


def _assignment_exposes_pytest_node_namespace(node: ast.AST, refs: frozenset[str]) -> bool:
    if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) or node.value is None:
        return False
    return any(
        isinstance(child, ast.Attribute) and child.attr == "__dict__" and _is_ref(child.value, refs)
        for child in ast.walk(node.value)
    )


def _call_exposes_pytest_node(node: ast.AST, refs: frozenset[str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    expressions = (*node.args, *(keyword.value for keyword in node.keywords))
    return any(_is_ref(child, refs) for expression in expressions for child in ast.walk(expression)) or (
        isinstance(node.func, ast.Attribute) and any(_is_ref(child, refs) for child in ast.walk(node.func.value))
    )


def _fixture_shapes_test_execution(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    node_aliases = _fixture_pytest_node_aliases(node)
    request_aliases = _fixture_pytest_request_aliases(node)
    return _fixture_accesses_pytest_plugin_manager(node) or any(
        any(_is_pytest_dispatch_target(target, node_aliases) for target in _assignment_targets(child))
        or _call_shapes_pytest_dispatch(child, node_aliases)
        or _assignment_exposes_pytest_node_namespace(child, node_aliases)
        or _call_exposes_pytest_node(child, node_aliases)
        or _call_exposes_pytest_request(child, request_aliases)
        for child in ast.walk(node)
    )


def _module_declares_execution_shaping_fixture(tree: ast.Module) -> bool:
    return any(_fixture_shapes_test_execution(node) for node in _pytest_fixture_definitions(tree))


def _selected_fixture_shapes_execution(tree: ast.Module, exported_names: frozenset[str]) -> bool:
    selected = None if "*" in exported_names else exported_names
    return any(
        (selected is None or node.name in selected) and _fixture_shapes_test_execution(node)
        for node in _pytest_fixture_definitions(tree)
    )


def _forwarded_fixture_import(
    statement: ast.AST,
    *,
    selected: frozenset[str] | None,
    path: Path,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> tuple[Path, frozenset[str]] | None:
    if not isinstance(statement, ast.ImportFrom):
        return None
    forwarded = frozenset(
        alias.name for alias in statement.names if selected is None or (alias.asname or alias.name) in selected
    )
    module_path = _imported_module_path(
        statement,
        path=path,
        snapshot_root=snapshot_root,
        import_roots=import_roots,
    )
    return (module_path, forwarded) if forwarded and module_path is not None else None


def _imported_fixture_module_bindings(
    tree: ast.Module,
    *,
    path: Path,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> tuple[tuple[str, Path], ...]:
    bindings: list[tuple[str, Path]] = []
    for statement in _module_execution_nodes(tree):
        if (
            not isinstance(statement, ast.ImportFrom)
            or (search := _import_search(statement, path=path, snapshot_root=snapshot_root, import_roots=import_roots))
            is None
        ):
            continue
        module_parts, search_roots = search
        for alias in statement.names:
            module_path = _module_path_from_parts((*module_parts, *alias.name.split(".")), search_roots)
            if module_path is not None:
                bindings.append((alias.asname or alias.name, module_path))
    return tuple(bindings)


def _assigned_fixture_imports(
    tree: ast.Module,
    *,
    selected: frozenset[str] | None,
    path: Path,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> tuple[tuple[Path, frozenset[str]], ...]:
    bindings = _imported_fixture_module_bindings(
        tree, path=path, snapshot_root=snapshot_root, import_roots=import_roots
    )
    return tuple(
        (module_path, frozenset({statement.value.attr}))
        for statement in _module_execution_nodes(tree)
        if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
        and statement.value is not None
        and isinstance(statement.value, ast.Attribute)
        and isinstance(statement.value.value, ast.Name)
        for alias, module_path in bindings
        if statement.value.value.id == alias
        and any(selected is None or target in selected for target in _assignment_name_targets(statement))
    )


def _fixture_imports(
    tree: ast.Module,
    *,
    selected: frozenset[str] | None,
    path: Path,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> tuple[tuple[Path, frozenset[str]], ...]:
    direct = (
        forwarded
        for statement in _module_execution_nodes(tree)
        if (
            forwarded := _forwarded_fixture_import(
                statement,
                selected=selected,
                path=path,
                snapshot_root=snapshot_root,
                import_roots=import_roots,
            )
        )
        is not None
    )
    assigned = _assigned_fixture_imports(
        tree,
        selected=selected,
        path=path,
        snapshot_root=snapshot_root,
        import_roots=import_roots,
    )
    return (*direct, *assigned)


def _module_exports_execution_shaping_fixture(
    path: Path,
    exported_names: frozenset[str],
    *,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
    visiting: frozenset[Path],
) -> bool:
    if path in visiting:
        return False
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return True
    if _module_uses_dynamic_namespace(tree):
        return True
    selected = None if "*" in exported_names else exported_names
    if _selected_fixture_shapes_execution(tree, exported_names):
        return True
    forwarded_imports = _fixture_imports(
        tree,
        selected=selected,
        path=path,
        snapshot_root=snapshot_root,
        import_roots=import_roots,
    )
    return any(
        _module_exports_execution_shaping_fixture(
            module_path,
            forwarded,
            snapshot_root=snapshot_root,
            import_roots=import_roots,
            visiting=visiting | {path},
        )
        for module_path, forwarded in forwarded_imports
    )


def _module_imports_execution_shaping_fixture(
    path: Path,
    tree: ast.Module,
    *,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> bool:
    imported = _fixture_imports(
        tree,
        selected=None,
        path=path,
        snapshot_root=snapshot_root,
        import_roots=import_roots,
    )
    return any(
        _module_exports_execution_shaping_fixture(
            module_path,
            exported_names,
            snapshot_root=snapshot_root,
            import_roots=import_roots,
            visiting=frozenset({path}),
        )
        for module_path, exported_names in imported
    )


def _conftest_hook_names(tree: ast.Module) -> set[str]:
    functions = tuple(
        node for node in _module_execution_nodes(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    hooks = {node.name for node in functions if node.name.startswith("pytest_")}
    hooks.update(_imported_pytest_hook_names(tree))
    hooks.update(_assigned_pytest_hook_names(tree))
    for function in functions:
        hooks.update(_decorated_pytest_hook_names(function))
    return hooks


def _conftest_declares_plugins(tree: ast.Module) -> bool:
    return any(
        isinstance(target, ast.Name) and target.id == "pytest_plugins"
        for node in _module_execution_nodes(tree)
        for assignment_target in _assignment_targets(node)
        for target in _assignment_target_nodes(assignment_target)
    )


def _repository_pytest_hook_validation(
    snapshot_root: Path,
    roots: tuple[str, ...],
    import_roots: tuple[Path, ...],
) -> CandidateReconciliation:
    plugins: list[dict[str, object]] = []
    for path in _loaded_conftest_paths(snapshot_root, roots):
        try:
            tree = ast.parse(path.read_bytes())
        except (OSError, SyntaxError):
            return CandidateReconciliation("UNKNOWN", "pytest_plugin_inventory_ambiguous")
        if (
            _conftest_declares_plugins(tree)
            or _module_uses_dynamic_namespace(tree)
            or _module_declares_autouse_fixture(tree)
            or _module_declares_execution_shaping_fixture(tree)
            or _module_imports_execution_shaping_fixture(
                path,
                tree,
                snapshot_root=snapshot_root,
                import_roots=import_roots,
            )
        ):
            return CandidateReconciliation("UNKNOWN", "pytest_plugin_capability_unsupported")
        plugins.append({"origin": "repository", "hooks": sorted(_conftest_hook_names(tree)), "path": str(path)})
    return validate_pytest_plugins(tuple(plugins))


def _collect_pytest_selectors(
    snapshot_root: Path,
    roots: tuple[str, ...],
    file_patterns: tuple[str, ...],
    policy: _PytestDiscoveryPolicy,
) -> tuple[str, ...]:
    return tuple(
        selector
        for root in roots
        for path in sorted((snapshot_root / root).rglob("*.py"))
        if _matches_python_file(path, file_patterns)
        for selector in _test_selectors(
            path,
            path.relative_to(snapshot_root).as_posix(),
            policy,
            snapshot_root=snapshot_root,
        )
    )


def _changed_pytest_candidates(
    changed_paths: tuple[str, ...],
    roots: tuple[str, ...],
    file_patterns: tuple[str, ...],
) -> set[str]:
    return {
        path
        for path in changed_paths
        if any(_logical_test_root_contains(path, root) for root in roots)
        and _matches_python_file(Path(path), file_patterns)
    }


def _pytest_candidates(
    snapshot_root: Path,
    roots: tuple[str, ...],
    file_patterns: tuple[str, ...],
) -> set[str]:
    return {
        path.relative_to(snapshot_root).as_posix()
        for root in roots
        for path in (snapshot_root / root).rglob("*.py")
        if _matches_python_file(path, file_patterns)
    }


def _has_unsupported_imported_test_base(
    paths: tuple[Path, ...],
    *,
    snapshot_root: Path,
    import_roots: tuple[Path, ...],
) -> bool:
    return any(
        _module_has_unsupported_imported_test_base(
            path,
            snapshot_root=snapshot_root,
            import_roots=import_roots,
        )
        for path in paths
    )


def _imported_test_rejection_reason(
    paths: tuple[Path, ...], *, snapshot_root: Path, policy: _PytestDiscoveryPolicy
) -> str:
    if _has_unsupported_imported_test_base(
        paths,
        snapshot_root=snapshot_root,
        import_roots=policy.import_roots,
    ):
        return "imported_test_base_unsupported"
    if any(_module_imports_dynamic_test_export(path, snapshot_root=snapshot_root, policy=policy) for path in paths):
        return "dynamic_imported_test_export_unsupported"
    return ""


def _pytest_candidate_rejection_reason(
    snapshot_root: Path,
    candidates: set[str],
    *,
    policy: _PytestDiscoveryPolicy,
) -> str:
    paths = tuple(snapshot_root / candidate for candidate in candidates)
    if any(_module_uses_wildcard_import(path) for path in paths):
        return "wildcard_import_unsupported"
    imported_reason = _imported_test_rejection_reason(paths, snapshot_root=snapshot_root, policy=policy)
    if imported_reason:
        return imported_reason
    if any(
        _module_has_dynamic_test_members(
            path,
            function_patterns=policy.function_patterns,
            class_patterns=policy.class_patterns,
        )
        for path in paths
    ):
        return "dynamic_test_assignment_unsupported"
    if _has_unsupported_test_decorator(paths, snapshot_root=snapshot_root, policy=policy):
        return "test_execution_decorator_unsupported"
    if any(_path_declares_unsupported_pytest_fixture(path) for path in paths):
        return "pytest_plugin_capability_unsupported"
    if any(
        _module_has_test_execution_override(
            path,
            snapshot_root=snapshot_root,
            import_roots=policy.import_roots,
            function_patterns=policy.function_patterns,
            class_patterns=policy.class_patterns,
        )
        for path in paths
    ):
        return "unittest_execution_override"
    return ""


def _projected_pytest_import_roots(
    policy: dict[str, object],
    *,
    snapshot_root: Path,
) -> tuple[tuple[Path, ...], str]:
    projection = project_pytest_policy(
        policy,
        snapshot_root=snapshot_root,
        output_root=snapshot_root / ".specfact-pytest-output",
    )
    if projection.status != "PASS":
        return (), projection.reason
    raw = projection.values.get("pythonpath", [])
    values = raw.split() if isinstance(raw, str) else cast(list[object], raw)
    return tuple(Path(str(value)) for value in values), ""


def plan_complete_pytest_suite(
    snapshot_root: Path,
    policy: dict[str, object],
    *,
    changed_paths: tuple[str, ...],
    deleted_paths: tuple[str, ...] = (),
    project_runtime_root: Path | None = None,
) -> PytestSuitePlan:
    del deleted_paths
    roots = tuple(str(value) for value in cast(list[object], policy.get("testpaths", ["."])))
    file_patterns = tuple(str(value) for value in cast(list[object], policy.get("python_files", ["test_*.py"])))
    class_patterns = tuple(str(value) for value in cast(list[object], policy.get("python_classes", ["Test*"])))
    function_patterns = tuple(str(value) for value in cast(list[object], policy.get("python_functions", ["test_*"])))
    projected_roots, projection_reason = _projected_pytest_import_roots(policy, snapshot_root=snapshot_root)
    if projection_reason:
        return PytestSuitePlan((), False, "UNKNOWN", projection_reason)
    runtime_roots = () if project_runtime_root is None else (project_runtime_root / "site-packages",)
    import_roots = tuple(dict.fromkeys((*projected_roots, snapshot_root, *runtime_roots)))
    discovery_policy = _PytestDiscoveryPolicy(function_patterns, class_patterns, import_roots)
    plugin_validation = _repository_pytest_hook_validation(snapshot_root, roots, import_roots)
    if plugin_validation.status != "PASS":
        return PytestSuitePlan((), False, "UNKNOWN", plugin_validation.reason)
    selectors = _collect_pytest_selectors(
        snapshot_root,
        roots,
        file_patterns,
        discovery_policy,
    )
    changed_candidates = _changed_pytest_candidates(changed_paths, roots, file_patterns)
    candidates = _pytest_candidates(snapshot_root, roots, file_patterns)
    rejection_reason = _pytest_candidate_rejection_reason(
        snapshot_root,
        candidates,
        policy=discovery_policy,
    )
    if rejection_reason:
        return PytestSuitePlan(selectors, False, "UNKNOWN", rejection_reason)
    collected_paths = {selector.split("::", maxsplit=1)[0] for selector in selectors}
    uncollected = candidates - collected_paths
    if uncollected:
        reason = "uncollected_changed_test" if uncollected & changed_candidates else "uncollected_test_candidate"
        return PytestSuitePlan(selectors, False, "UNKNOWN", reason)
    return PytestSuitePlan(selectors, False)


def classify_snapshot_applicability(
    *, base_inputs: tuple[str, ...], head_inputs: tuple[str, ...]
) -> SnapshotApplicability:
    return SnapshotApplicability(
        "PASS" if base_inputs else "NOT_APPLICABLE",
        "PASS" if head_inputs else "NOT_APPLICABLE",
    )


def classify_pytest_input_role(path: str, *, policy: dict[str, object]) -> PytestInputRole:
    roots = tuple(str(value).rstrip("/") for value in cast(list[object], policy["testpaths"]))
    patterns = tuple(str(value) for value in cast(list[object], policy["python_files"]))
    below_root = any(_logical_test_root_contains(path, root) for root in roots)
    matches_test_pattern = _matches_python_file(Path(path), patterns)
    if below_root:
        kind = "test_candidate" if matches_test_pattern else "test_support"
    else:
        kind = "test_candidate_outside_root" if matches_test_pattern else "test_support"
    return PytestInputRole(kind, ("path", "testpaths", "python_files", "pytest_version"))


def _logical_test_root_contains(path: str, root: str) -> bool:
    normalized = root.rstrip("/")
    return normalized in {"", "."} or path == normalized or path.startswith(f"{normalized}/")


def pytest_path_matches_pattern(path: Path, pattern: str, *, platform: str) -> bool:
    """Reproduce pinned pytest 9.0.3 ``fnmatch_ex`` path handling."""

    del platform
    if "/" not in pattern:
        return fnmatch.fnmatch(path.name, pattern)
    effective = pattern if pattern.startswith("/") else f"*/{pattern}"
    return fnmatch.fnmatch(path.as_posix(), effective)


def reconcile_test_candidate(
    *, role: str, base_selectors: tuple[str, ...], head_selectors: tuple[str, ...]
) -> CandidateReconciliation:
    del base_selectors
    if role == "test_candidate" and not head_selectors:
        return CandidateReconciliation("UNKNOWN", "uncollected_test_candidate")
    return CandidateReconciliation("PASS")


def validate_pytest_item_controls(
    *, candidate_path: str, namespace: dict[str, object], collected: tuple[str, ...]
) -> CandidateReconciliation:
    del candidate_path, collected
    if namespace.get("__test__") is False:
        return CandidateReconciliation("UNKNOWN", "pytest_item_control_unsupported")
    return CandidateReconciliation("PASS")


def reconcile_test_roles(
    *, base: dict[str, str], head: dict[str, str], rename_facts: dict[str, str]
) -> CandidateReconciliation:
    for old, new in rename_facts.items():
        if base.get(old) == "test_candidate" and head.get(new) != "test_candidate":
            return CandidateReconciliation("UNKNOWN", "uncollected_changed_test")
    return CandidateReconciliation("PASS")


def validate_pytest_selection_controls(policy: dict[str, object]) -> CandidateReconciliation:
    rejected = {
        "--cache-clear",
        "--co",
        "--collect-only",
        "--confcutdir",
        "--cov",
        "--cov-config",
        "--cov-fail-under",
        "--cov-report",
        "--deselect",
        "--doctest-modules",
        "--exitfirst",
        "--ff",
        "--ignore",
        "--ignore-glob",
        "--lf",
        "--last-failed",
        "--maxfail",
        "--new-first",
        "--no-cov",
        "--noconftest",
        "--override-ini",
        "--pyargs",
        "--rootdir",
        "--stepwise",
        "--stepwise-skip",
        "-c",
        "-k",
        "-m",
        "-p",
        "-x",
    }
    raw_addopts = [str(value) for value in cast(list[object], policy.get("addopts", []))]
    addopts = {value.split("=", maxsplit=1)[0] for value in raw_addopts}
    short_cluster_rejected = any(
        value.startswith("-")
        and not value.startswith("--")
        and len(value) > 2
        and any(flag in value[1:] for flag in ("k", "m", "x", "c", "p"))
        for value in raw_addopts
    )
    config = cast(dict[str, object], policy.get("config", {}))
    if rejected & addopts or short_cluster_rejected or config.get("norecursedirs"):
        return CandidateReconciliation("UNKNOWN", "pytest_selection_policy_unsupported")
    return CandidateReconciliation("PASS")


def validate_native_pytest_namespace(controls: dict[str, dict[str, object]]) -> CandidateReconciliation:
    return CandidateReconciliation("UNKNOWN" if any(values for values in controls.values()) else "PASS")


def validate_unittest_controls(controls: dict[str, dict[str, object]]) -> CandidateReconciliation:
    return CandidateReconciliation("UNKNOWN" if any(values for values in controls.values()) else "PASS")


def validate_pytest_plugins(plugins: tuple[dict[str, object], ...]) -> CandidateReconciliation:
    forbidden = {
        "pytest_addhooks",
        "pytest_addoption",
        "pytest_cmdline_main",
        "pytest_cmdline_parse",
        "pytest_collect_directory",
        "pytest_collect_file",
        "pytest_collection",
        "pytest_collection_finish",
        "pytest_collection_modifyitems",
        "pytest_collectreport",
        "pytest_collectstart",
        "pytest_configure",
        "pytest_deselected",
        "pytest_generate_tests",
        "pytest_ignore_collect",
        "pytest_itemcollected",
        "pytest_load_initial_conftests",
        "pytest_make_collect_report",
        "pytest_make_parametrize_id",
        "pytest_markeval_namespace",
        "pytest_plugin_registered",
        "pytest_pycollect_makeitem",
        "pytest_pycollect_makemodule",
        "pytest_pyfunc_call",
        "pytest_runtest_call",
        "pytest_runtest_makereport",
        "pytest_runtest_protocol",
        "pytest_runtest_setup",
        "pytest_runtest_teardown",
        "pytest_runtestloop",
        "pytest_sessionfinish",
        "pytest_sessionstart",
        "pytest_unconfigure",
    }
    if any(forbidden & set(cast(list[str], plugin.get("hooks", []))) for plugin in plugins):
        return CandidateReconciliation("UNKNOWN", "pytest_plugin_capability_unsupported")
    return CandidateReconciliation("PASS")


def pytest_hook_disposition_catalog(*, version: str) -> PytestHookCatalog:
    if version != "9.0.3":
        return PytestHookCatalog((), ("version_drift",))
    return PytestHookCatalog(
        (
            "pytest_addhooks",
            "pytest_addoption",
            "pytest_assertion_pass",
            "pytest_assertrepr_compare",
            "pytest_cmdline_main",
            "pytest_cmdline_parse",
            "pytest_collect_directory",
            "pytest_collect_file",
            "pytest_collection",
            "pytest_collection_finish",
            "pytest_collection_modifyitems",
            "pytest_collectreport",
            "pytest_collectstart",
            "pytest_configure",
            "pytest_deselected",
            "pytest_enter_pdb",
            "pytest_exception_interact",
            "pytest_fixture_post_finalizer",
            "pytest_fixture_setup",
            "pytest_generate_tests",
            "pytest_ignore_collect",
            "pytest_internalerror",
            "pytest_itemcollected",
            "pytest_keyboard_interrupt",
            "pytest_leave_pdb",
            "pytest_load_initial_conftests",
            "pytest_make_collect_report",
            "pytest_make_parametrize_id",
            "pytest_markeval_namespace",
            "pytest_plugin_registered",
            "pytest_pycollect_makeitem",
            "pytest_pycollect_makemodule",
            "pytest_pyfunc_call",
            "pytest_report_collectionfinish",
            "pytest_report_from_serializable",
            "pytest_report_header",
            "pytest_report_teststatus",
            "pytest_report_to_serializable",
            "pytest_runtest_call",
            "pytest_runtest_logfinish",
            "pytest_runtest_logreport",
            "pytest_runtest_logstart",
            "pytest_runtest_makereport",
            "pytest_runtest_protocol",
            "pytest_runtest_setup",
            "pytest_runtest_teardown",
            "pytest_runtestloop",
            "pytest_sessionfinish",
            "pytest_sessionstart",
            "pytest_terminal_summary",
            "pytest_unconfigure",
            "pytest_warning_recorded",
        )
    )


def pytest_selection_option_catalog(*, version: str, pytest_cov_version: str) -> PytestOptionCatalog:
    if (version, pytest_cov_version) != ("9.0.3", "7.1.0"):
        return PytestOptionCatalog((), ("version_drift",))
    return PytestOptionCatalog(
        (
            "--cache-clear",
            "--collect-only",
            "--confcutdir",
            "--cov",
            "--cov-config",
            "--cov-fail-under",
            "--cov-report",
            "--deselect",
            "--doctest-modules",
            "--exitfirst",
            "--ff",
            "--ignore",
            "--ignore-glob",
            "--lf",
            "--last-failed",
            "--maxfail",
            "--new-first",
            "--no-cov",
            "--noconftest",
            "--override-ini",
            "--pyargs",
            "--rootdir",
            "--stepwise",
            "--stepwise-skip",
            "-c",
            "-k",
            "-m",
            "-p",
            "-x",
        )
    )


def pytest_configuration_catalog(*, version: str, pytest_cov_version: str) -> PytestConfigurationCatalog:
    if (version, pytest_cov_version) != ("9.0.3", "7.1.0"):
        return PytestConfigurationCatalog((), {}, ("version_drift",))
    fields = (
        "testpaths",
        "python_files",
        "python_classes",
        "python_functions",
        "pythonpath",
        "cache_dir",
        "log_file",
        "norecursedirs",
    )
    classifications = {
        field: (
            "read_source"
            if field in {"testpaths", "pythonpath"}
            else "write_output"
            if field in {"cache_dir", "log_file"}
            else "selection_filter"
            if field == "norecursedirs"
            else "non_selecting"
        )
        for field in fields
    }
    return PytestConfigurationCatalog(fields, classifications)


def pytest_builtin_collector_decision_catalog(*, version: str) -> PytestCollectorCatalog:
    if version != "9.0.3":
        return PytestCollectorCatalog((), ("version_drift",))
    return PytestCollectorCatalog(("PyCollector.collect", "istestclass", "istestfunction", "UnitTestCase.collect"))


def project_pytest_policy(policy: dict[str, object], *, snapshot_root: Path, output_root: Path) -> PytestProjection:
    logical_digest = _canonical_json_digest(policy)
    config = dict(cast(dict[str, object], policy.get("config", {})))
    values = dict(config)
    writable: list[Path] = []
    for key in ("pythonpath", "testpaths"):
        raw_value = policy.get(key, config.get(key, []))
        raw = raw_value.split() if isinstance(raw_value, str) else cast(list[object], raw_value)
        projected: list[str] = []
        for value in raw:
            relative = Path(str(value))
            if relative.is_absolute() or ".." in relative.parts:
                return PytestProjection("UNKNOWN", {}, (), logical_digest, "unbound_read_path")
            projected.append(str(snapshot_root / relative))
        if projected:
            values[key] = projected
    for key in ("python_files", "python_classes", "python_functions"):
        raw = policy.get(key)
        if raw is not None:
            values[key] = raw
    if policy.get("addopts"):
        values["addopts"] = policy["addopts"]
    for key in ("cache_dir", "log_file"):
        if key == "log_file" and key not in config:
            continue
        destination = output_root / key.replace("_", "-")
        values[key] = str(destination)
        writable.append(destination)
    return PytestProjection("PASS", values, tuple(writable), logical_digest)


def _pytest_call_outcome(call_record: dict[str, object], records: list[dict[str, object]]) -> str:
    if call_record.get("wasxfail"):
        return "XPASS" if call_record.get("passed") else "XFAIL"
    if call_record.get("skipped"):
        return "SKIPPED"
    if not call_record.get("passed"):
        return "FAILED"
    return "FAILED" if any(not record.get("passed") and not record.get("skipped") for record in records) else "PASS"


def _pytest_no_call_outcome(records: list[dict[str, object]]) -> str:
    skipped_record = next((record for record in records if record.get("skipped")), None)
    if skipped_record is not None:
        return "XFAIL" if skipped_record.get("wasxfail") else "SKIPPED"
    return "FAILED" if any(not record.get("passed") for record in records) else "UNKNOWN"


def _pytest_observed_outcome(records: list[dict[str, object]]) -> str:
    call_record = next((record for record in records if record.get("phase") == "call"), None)
    return _pytest_call_outcome(call_record, records) if call_record is not None else _pytest_no_call_outcome(records)


def _pytest_planned_nodes_match(*, planned: tuple[str, ...], observed: tuple[str, ...]) -> bool:
    if not planned:
        return True
    if len(set(planned)) != len(planned):
        return False
    matched: list[str] = []
    for nodeid in observed:
        candidates = tuple(selector for selector in planned if nodeid == selector or nodeid.startswith(f"{selector}["))
        if len(candidates) != 1:
            return False
        matched.append(candidates[0])
    return set(matched) == set(planned)


def reconcile_pytest_outcomes(
    *,
    observer: tuple[dict[str, object], ...],
    junit: tuple[dict[str, object], ...],
    process_exit: int,
    planned: tuple[str, ...] = (),
) -> PytestOutcomeResult:
    records_by_node: dict[str, list[dict[str, object]]] = {}
    for record in observer:
        records_by_node.setdefault(str(record.get("nodeid", "")), []).append(record)

    observed_nodes = tuple(records_by_node)
    outcomes = tuple(
        PytestObservedOutcome(_pytest_observed_outcome(records_by_node[nodeid])) for nodeid in observed_nodes
    )
    expected_junit = {"PASS": "passed", "XPASS": "passed", "FAILED": "failed", "XFAIL": "skipped", "SKIPPED": "skipped"}
    junit_by_node = {str(record.get("nodeid", "")): str(record.get("outcome", "")) for record in junit}
    signals_match = len(junit_by_node) == len(observed_nodes) and all(
        outcome.kind in expected_junit and junit_by_node.get(nodeid) == expected_junit[outcome.kind]
        for nodeid, outcome in zip(observed_nodes, outcomes, strict=True)
    )
    process_matches = (process_exit != 0) == any(outcome.kind == "FAILED" for outcome in outcomes)
    if (
        not signals_match
        or not process_matches
        or not _pytest_planned_nodes_match(planned=planned, observed=observed_nodes)
    ):
        return PytestOutcomeResult("UNKNOWN", outcomes)
    return PytestOutcomeResult(
        "FAIL" if any(outcome.kind != "PASS" for outcome in outcomes) else "PASS",
        outcomes,
    )


def classify_targeted_pytest(*, base_outcome: str, head_outcome: str) -> StatusResult:
    if base_outcome == "fail" and head_outcome == "pass":
        return StatusResult("PASS", disposition="fixed")
    if head_outcome in {"skip", "xfail", "xpass", "assertion-fail"}:
        return StatusResult("FAIL")
    if head_outcome in {"deselected", "timeout", "collection-error"}:
        return StatusResult("UNKNOWN")
    return StatusResult("PASS")


def build_pytest_import_order(*, snapshot_root: str, project_runtime: str, attested: bool) -> ImportOrderResult:
    if not attested:
        return ImportOrderResult("UNKNOWN", ())
    return ImportOrderResult("PASS", (snapshot_root, project_runtime))


def reconcile_pytest_inventories(
    *, base: tuple[str, ...], head: tuple[str, ...], rename_facts: dict[str, str]
) -> CandidateReconciliation:
    del rename_facts
    if set(base) - set(head):
        return CandidateReconciliation("UNKNOWN", "removed_selector")
    return CandidateReconciliation("PASS")


def reconcile_test_candidates(
    *, candidates: tuple[str, ...], collected_paths: tuple[str, ...]
) -> CandidateReconciliation:
    missing = tuple(sorted(set(candidates) - set(collected_paths)))
    return CandidateReconciliation("UNKNOWN" if missing else "PASS", missing=missing)


def project_coverage_policy(
    policy: dict[str, object], *, snapshot_root: Path | None = None, output_root: Path | None = None
) -> CoverageProjection:
    del snapshot_root
    unsupported = ("report:exclude_lines", "report:exclude_also", "report:partial_branches", "report:partial_also")
    if any(policy.get(key) for key in unsupported) or policy.get("run:plugins"):
        return CoverageProjection("UNKNOWN", {}, reason="coverage_policy_unsupported")
    values = dict(policy)
    values.update(
        {
            "report:exclude_lines": [],
            "report:exclude_also": [],
            "report:partial_branches": [],
            "report:partial_also": [],
        }
    )
    writable: list[Path] = []
    if output_root is not None:
        for key in ("run:data_file", "html:directory", "xml:output", "json:output", "lcov:output"):
            if key == "run:data_file" or key in values:
                destination = output_root / key.replace(":", "-")
                values[key] = str(destination)
                writable.append(destination)
    return CoverageProjection("PASS", values, tuple(writable))


def select_coverage_policy(*, target: dict[str, object], candidate: dict[str, object]) -> CoverageProjection:
    if candidate != target:
        return CoverageProjection("UNKNOWN", target, reason="candidate_policy_change")
    return CoverageProjection("PASS", target)


def classify_coverage(*, base: float, head: float, threshold: float) -> StatusResult:
    if head < threshold:
        return StatusResult("FAIL", execution_state="ran")
    if base < threshold <= head:
        return StatusResult("PASS", disposition="fixed", execution_state="ran")
    return StatusResult("PASS", execution_state="ran")


def reconcile_coverage_manifest(*, required: tuple[str, ...], observed: tuple[str, ...]) -> CandidateReconciliation:
    if tuple(sorted(required)) != tuple(sorted(observed)):
        return CandidateReconciliation("UNKNOWN", "coverage_input_manifest_mismatch")
    return CandidateReconciliation("PASS")


def classify_analyzer_input_kinds(inputs: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    static = tuple(sorted(path for path in inputs if path.endswith((".py", ".pyi"))))
    runtime = tuple(path for path in static if path.endswith(".py"))
    return {
        "targeted-pytest-coverage": runtime,
        "ruff": static,
        "basedpyright": static,
        "pylint": static,
        "contracts.icontract-static-scan": static,
        "contracts.crosshair": runtime,
    }


def classify_snapshot_input_kinds(inputs: tuple[str, ...]) -> SnapshotInputClassification:
    profile_ids = (*default_pr_range_profile().all_ids, "contracts.crosshair", "contracts.icontract-static-scan")
    if not inputs:
        return SnapshotInputClassification(
            tuple(SnapshotMemberState(member_id, "NOT_APPLICABLE") for member_id in profile_ids)
        )
    stub_only = all(path.endswith(".pyi") for path in inputs)
    return SnapshotInputClassification(
        tuple(
            SnapshotMemberState(
                member_id,
                "NOT_APPLICABLE"
                if stub_only and member_id in {"targeted-pytest-coverage", "contracts.crosshair"}
                else "PASS",
            )
            for member_id in profile_ids
        )
    )


def classify_contract_components(inputs: tuple[str, ...], *, icontract_usage: bool) -> ContractComponents:
    static_status = "PASS" if inputs and icontract_usage else "NOT_APPLICABLE"
    crosshair_status = "PASS" if any(path.endswith(".py") for path in inputs) else "NOT_APPLICABLE"
    parent_status = "PASS" if "PASS" in {static_status, crosshair_status} else "NOT_APPLICABLE"
    return ContractComponents(
        SnapshotMemberState("contracts.icontract-static-scan", static_status),
        SnapshotMemberState("contracts.crosshair", crosshair_status),
        SnapshotMemberState("contracts", parent_status),
    )


def icontract_static_activation(payload: bytes) -> ContractActivation:
    return ContractActivation(b"icontract" in payload, "icontract-static-activation-v1")


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def evaluate_runtime_policy(*, candidate_python_executes: bool, hostile_candidate_claim: bool) -> RuntimePolicyResult:
    """Fail closed when executable candidate code is claimed to be adversarial."""

    status: Literal["PASS", "UNKNOWN"] = "UNKNOWN" if candidate_python_executes and hostile_candidate_claim else "PASS"
    return RuntimePolicyResult(status, "non_adversarial_candidate_runtime")


def _source_relative_path(source_file: Path) -> Path | None:
    source_root_candidates = [_SOURCE_ROOT, *_resolved_path_variants(_SOURCE_ROOT)]
    source_file_candidates = [source_file, *_resolved_path_variants(source_file)]
    return next(
        (
            relative_path
            for candidate in source_file_candidates
            for source_root in source_root_candidates
            if (relative_path := _relative_to(candidate, source_root)) is not None
        ),
        None,
    )


def _resolved_path_variants(path: Path) -> list[Path]:
    try:
        return [path.resolve()]
    except OSError:
        return []


def _relative_to(candidate: Path, source_root: Path) -> Path | None:
    with suppress(ValueError):
        return candidate.relative_to(source_root)
    return None


def _expected_test_path(source_file: Path) -> Path | None:
    relative_path = _source_relative_path(source_file)
    return None if relative_path is None else Path("tests/unit") / relative_path.parent / f"test_{relative_path.name}"


def _coverage_for_source(source_file: Path, payload: dict[str, object]) -> float | None:
    files_payload = payload.get("files")
    if not isinstance(files_payload, dict):
        return None
    allowed_paths = normalize_path_variants(source_file)
    for filename, file_payload in files_payload.items():
        if not isinstance(filename, str):
            continue
        if normalize_path_variants(filename).isdisjoint(allowed_paths):
            continue
        if not isinstance(file_payload, dict):
            return None
        summary = file_payload.get("summary")
        if not isinstance(summary, dict):
            return None
        percent_covered = summary.get("percent_covered")
        if isinstance(percent_covered, int | float):
            return float(percent_covered)
    return None


def _pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_entries: list[str] = [str(_SOURCE_ROOT.resolve()), str(Path.cwd().resolve())]
    _extend_unique_entries(pythonpath_entries, env.get("PYTHONPATH", ""), split_by=os.pathsep)
    _extend_unique_entries(
        pythonpath_entries,
        (str(Path(entry).resolve()) for entry in sys.path if entry and Path(entry).exists()),
    )
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def _extend_unique_entries(
    entries: list[str],
    values: Iterable[str] | str,
    *,
    split_by: str | None = None,
) -> None:
    for entry in _iter_unique_entries(values, split_by=split_by):
        if entry and entry not in entries:
            entries.append(entry)


def _iter_unique_entries(
    values: Iterable[str] | str,
    *,
    split_by: str | None = None,
) -> Iterable[str]:
    if isinstance(values, str):
        yield from values.split(split_by) if split_by is not None else [values]
        return
    yield from values


def _pytest_targets(test_files: list[Path]) -> list[Path]:
    if len(test_files) <= 1:
        return test_files
    common_root = Path(os.path.commonpath([str(test_file) for test_file in test_files]))
    if common_root.is_dir() and common_root.parts[:2] == ("tests", "unit") and len(common_root.parts) > 3:
        return [common_root]
    return test_files


def _pytest_python_executable() -> str:
    return sys.executable


def _pytest_observer_script() -> str:
    source_root = str(_SOURCE_ROOT.resolve())
    repo_root = str(Path.cwd().resolve())
    return (
        "import json, pathlib, sys, pytest, pytest_cov.plugin as pytest_cov_plugin\n"
        "class Observer:\n"
        "    def __init__(self, path):\n"
        "        self.path = pathlib.Path(path)\n"
        "        self.records = []\n"
        "    def pytest_itemcollected(self, item):\n"
        "        self.records.append({\n"
        "            'nodeid': item.nodeid,\n"
        "            'phase': 'collection',\n"
        "            'passed': True,\n"
        "            'skipped': False,\n"
        "            'wasxfail': '',\n"
        "        })\n"
        "    def pytest_runtest_logreport(self, report):\n"
        "        self.records.append({\n"
        "            'nodeid': report.nodeid,\n"
        "            'phase': report.when,\n"
        "            'passed': report.passed,\n"
        "            'skipped': report.skipped,\n"
        "            'wasxfail': getattr(report, 'wasxfail', ''),\n"
        "        })\n"
        "    def pytest_sessionfinish(self, session, exitstatus):\n"
        "        self.path.write_text(json.dumps(self.records), encoding='utf-8')\n"
        "observer_path = sys.argv.pop(1)\n"
        f"sys.path[:0] = [{source_root!r}, {repo_root!r}]\n"
        "import specfact_code_review\n"
        "raise SystemExit(pytest.main(sys.argv[1:], plugins=[pytest_cov_plugin, Observer(observer_path)]))\n"
    )


def _temporary_pytest_evidence_path(suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as evidence_file:
        return Path(evidence_file.name)


def _temporary_pytest_evidence_paths() -> tuple[Path, Path, Path]:
    coverage_path = _temporary_pytest_evidence_path(".json")
    observer_path = _temporary_pytest_evidence_path(".json")
    junit_path = _temporary_pytest_evidence_path(".xml")
    observer_path.unlink(missing_ok=True)
    junit_path.unlink(missing_ok=True)
    return coverage_path, observer_path, junit_path


def _run_pytest_selection_with_coverage(
    selectors: tuple[str, ...],
    *,
    coverage_source: Path,
    policy_argv: tuple[str, ...] = (),
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    coverage_path, observer_path, junit_path = _temporary_pytest_evidence_paths()
    command = [
        _pytest_python_executable(),
        "-c",
        _pytest_observer_script(),
        str(observer_path),
        *policy_argv,
        "--import-mode=importlib",
        "--cov",
        str(coverage_source),
        "--cov-fail-under=0",
        f"--cov-report=json:{coverage_path}",
        f"--junitxml={junit_path}",
        *selectors,
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=_TARGETED_TEST_TIMEOUT,
        env=_pytest_env(),
    )
    return result, coverage_path, observer_path, junit_path


def _run_pytest_with_coverage(test_files: list[Path]) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    test_targets = tuple(str(test_target) for test_target in _pytest_targets(test_files))
    return _run_pytest_selection_with_coverage(test_targets, coverage_source=_PACKAGE_ROOT)


def _run_pytest_inventory_with_coverage(
    selectors: tuple[str, ...],
    *,
    policy_argv: tuple[str, ...] = (),
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    return _run_pytest_selection_with_coverage(
        selectors,
        coverage_source=Path("/opt/specfact/snapshot"),
        policy_argv=policy_argv,
    )


def _summary_for_findings(findings: list[ReviewFinding]) -> str:
    if not findings:
        return "Review completed with no findings."
    blocking_count = sum(finding.is_blocking() for finding in findings)
    return f"Review completed with {len(findings)} findings ({blocking_count} blocking)."


def _is_test_file(file_path: str | Path) -> bool:
    return "tests" in Path(file_path).parts


def _normalize_report_path(raw_path: str | Path) -> str:
    path = Path(raw_path)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def _parse_added_lines_from_diff(diff_text: str) -> dict[str, set[int]]:
    """Return added new-file line numbers from a zero-context git diff."""
    changed_lines: dict[str, set[int]] = {}
    current_file: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            destination = line[4:].strip()
            current_file = None if destination == "/dev/null" else destination.removeprefix("b/")
            if current_file is not None:
                changed_lines.setdefault(current_file, set())
            continue
        if current_file is None or not line.startswith("@@ "):
            continue
        match = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if match is None:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count > 0:
            changed_lines[current_file].update(range(start, start + count))
    return changed_lines


def _changed_lines_from_git(files: list[Path]) -> dict[str, set[int]]:
    """Collect changed line numbers for changed enforcement evidence."""
    diff_mode = os.environ.get("SPECFACT_CODE_REVIEW_CHANGED_DIFF", "worktree").strip().lower()
    command = ["git", "diff", "--unified=0", "--no-ext-diff"]
    if diff_mode == "cached":
        command.append("--cached")
    else:
        command.append("HEAD")
    if files:
        command.extend(["--", *(str(file_path) for file_path in files)])
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    if result.returncode != 0:
        return {}
    changed_lines = _parse_added_lines_from_diff(result.stdout)
    for file_path in files:
        if not file_path.exists():
            continue
        relative = _normalize_report_path(file_path)
        if relative in changed_lines:
            continue
        try:
            listed = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", "--", str(file_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except subprocess.SubprocessError:
            continue
        if listed.returncode == 0 and listed.stdout.strip():
            try:
                line_count = len(file_path.read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeDecodeError):
                continue
            changed_lines[relative] = set(range(1, line_count + 1))
    return changed_lines


def _finding_targets_changed_line(finding: ReviewFinding, changed_lines: dict[str, set[int]]) -> bool:
    """Return whether a finding points at a changed line."""
    line_numbers = changed_lines.get(_normalize_report_path(finding.file))
    if not line_numbers:
        return False
    return finding.line in line_numbers


def _with_changed_enforcement(report: ReviewReport, files: list[Path]) -> ReviewReport:
    """Apply changed-line policy without discarding findings or uncertainty."""
    if report.assurance_status == "UNKNOWN" or report.has_unknown_required_evidence:
        return report.model_copy(
            update={
                "enforcement_mode": "changed",
                "enforcement_summary": "Changed enforcement cannot pass while required evidence is UNKNOWN.",
            }
        )
    changed_lines = _changed_lines_from_git(files)
    blocking_changed = [
        finding
        for finding in report.findings
        if finding.is_blocking() and _finding_targets_changed_line(finding, changed_lines)
    ]
    if blocking_changed:
        summary = f"Changed enforcement blocks on {len(blocking_changed)} blocking finding(s) on changed lines."
        return report.model_copy(
            update={
                "assurance_status": "FAIL" if report.assurance_status is not None else None,
                "overall_verdict": "FAIL",
                "ci_exit_code": 1,
                "enforcement_mode": "changed",
                "enforcement_summary": summary,
            }
        )
    legacy_blocking = sum(finding.is_blocking() for finding in report.findings)
    summary = (
        "Changed enforcement found no blocking findings on changed lines."
        if legacy_blocking == 0
        else (
            "Changed enforcement found no blocking findings on changed lines; "
            f"{legacy_blocking} legacy blocking finding(s) remain as evidence."
        )
    )
    verdict = "PASS" if not report.findings else "PASS_WITH_ADVISORY"
    return report.model_copy(
        update={
            "assurance_status": "PASS" if report.assurance_status is not None else None,
            "overall_verdict": verdict,
            "ci_exit_code": 0,
            "enforcement_mode": "changed",
            "enforcement_summary": summary,
        }
    )


def _with_enforcement(report: ReviewReport, *, mode: ReviewEnforcementMode, files: list[Path]) -> ReviewReport:
    """Apply enforcement mode to report exit code while preserving all findings as evidence."""
    if mode == "full":
        return report.model_copy(
            update={
                "enforcement_mode": "full",
                "enforcement_summary": "Full enforcement blocks on any blocking finding in the reviewed files.",
            }
        )
    if mode == "shadow":
        return report.model_copy(
            update={
                "ci_exit_code": 0,
                "enforcement_mode": "shadow",
                "enforcement_summary": "Shadow enforcement records findings as evidence and never blocks CI.",
            }
        )
    return _with_changed_enforcement(report, files)


def _suppress_known_noise(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    filtered: list[ReviewFinding] = []
    for finding in findings:
        if (finding.tool, finding.rule) in _GLOBAL_NOISE_RULES:
            continue
        if _is_pylint_structural_noise(finding):
            continue
        if finding.tool == "crosshair" and finding.message.startswith(_NOISE_MESSAGE_PREFIXES):
            continue
        if _is_test_file(finding.file) and (finding.tool, finding.rule) in _TEST_NOISE_RULES:
            continue
        filtered.append(finding)
    return filtered


def _is_pylint_structural_noise(finding: ReviewFinding) -> bool:
    if finding.tool != "pylint":
        return False
    if finding.rule in _PYLINT_CLI_WRAPPER_NOISE_RULES and _path_name(finding.file) == "commands.py":
        return "argument" in finding.message or "local variable" in finding.message
    return (
        finding.rule == "R0902"
        and "Too many instance attributes" in finding.message
        and _line_targets_dataclass(finding.file, finding.line)
    )


def _path_name(file_path: str) -> str:
    return Path(file_path.replace("\\", "/")).name


def _line_targets_dataclass(file_path: str, line: int) -> bool:
    try:
        module = ast.parse(Path(file_path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    return any(
        isinstance(node, ast.ClassDef)
        and (node.lineno == line or any(decorator.lineno == line for decorator in node.decorator_list))
        and any(_is_dataclass_decorator(decorator) for decorator in node.decorator_list)
        for node in ast.walk(module)
    )


def _is_dataclass_decorator(decorator: ast.expr) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Name):
        return target.id == "dataclass"
    return isinstance(target, ast.Attribute) and target.attr == "dataclass"


def _is_truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _checklist_findings() -> list[ReviewFinding]:
    if not _is_truthy_env(_PR_MODE_ENV):
        return []

    context = "\n".join(
        os.environ.get(name, "").strip() for name in _PR_CONTEXT_ENVS if os.environ.get(name, "").strip()
    )
    if any(re.search(rf"\b{re.escape(hint)}\b", context, flags=re.IGNORECASE) for hint in _CLEAN_CODE_CONTEXT_HINTS):
        return []

    return [
        ReviewFinding(
            category="clean_code",
            severity="info",
            tool="checklist",
            rule="clean-code.pr-checklist-missing-rationale",
            file="PR_CONTEXT",
            line=1,
            message=(
                "PR context is missing explicit clean-code reasoning. "
                "Call out the naming, KISS, YAGNI, DRY, or SOLID impact in the proposal or PR body."
            ),
            fixable=False,
        )
    ]


def _tool_steps(*, bug_hunt: bool) -> list[tuple[str, Callable[[list[Path]], list[ReviewFinding]]]]:
    return [
        ("Running Ruff checks...", run_ruff),
        ("Running Radon complexity checks...", run_radon),
        ("Running Semgrep rules...", run_semgrep),
        ("Running Semgrep bug rules...", run_semgrep_bugs),
        ("Running AI-bloat AST checks...", run_ai_bloat),
        ("Running AST clean-code checks...", run_ast_clean_code),
        ("Running basedpyright type checks...", run_basedpyright),
        ("Running pylint checks...", run_pylint),
        ("Running contract checks...", partial(run_contract_check, bug_hunt=bug_hunt)),
    ]


def _filter_findings_by_review_level(
    findings: list[ReviewFinding],
    level: Literal["error", "warning"] | None,
) -> list[ReviewFinding]:
    if level is None:
        return findings
    if level == "error":
        return [finding for finding in findings if finding.severity == "error"]
    return [finding for finding in findings if finding.severity in {"error", "warning"}]


def _belongs_to_simplification_queue(finding: ReviewFinding) -> bool:
    if finding.category == "tool_error":
        return True
    if finding.category == "ai_bloat":
        return True
    return (
        finding.category in {"dry", "kiss"}
        and finding.confidence == "high"
        and finding.simplification_metadata_is_deterministic()
    )


def _filter_findings_by_focus(findings: list[ReviewFinding], focus: ReviewFocus | None) -> list[ReviewFinding]:
    if focus is None:
        return findings
    if focus == "simplify":
        return [finding for finding in findings if _belongs_to_simplification_queue(finding)]
    raise ValueError(f"Unsupported review focus: {focus}")


def _enrich_cleanup_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    return [_enriched_cleanup_finding(finding) for finding in findings]


def _enriched_cleanup_finding(finding: ReviewFinding) -> ReviewFinding:
    if finding.guidance_kind is None:
        return finding
    preserve_reasons = list(finding.preserve_reasons or [])
    preserve_reasons.extend(
        reason
        for reason in _preserve_reasons_for_finding(finding, load_bearing=False)
        if reason not in preserve_reasons
    )
    updates: dict[str, object] = {
        "signal_trace": _signal_trace_for_finding(finding),
    }
    if preserve_reasons:
        updates.update(
            {
                "guidance_kind": "preserve",
                "recommended_action": "keep",
                "estimated_deletion_lines": 0,
                "action_status": "kept",
                "preserve_reason": "; ".join(reason.explanation for reason in preserve_reasons),
                "preserve_reasons": preserve_reasons,
            }
        )
    candidate = finding.model_copy(update=updates)
    return candidate.model_copy(update={"remediation_packet": _remediation_packet_for_finding(candidate)})


def _signal_trace_for_finding(finding: ReviewFinding) -> list[SignalTraceEntry]:
    existing = list(finding.signal_trace or [])
    if existing:
        return existing
    return [
        SignalTraceEntry(
            tool=finding.tool,
            source=finding.rule,
            fired=True,
            score=1.0 if finding.confidence == "high" else None,
            value=finding.canonical_pattern,
            evidence_refs=[EvidenceRef(path=finding.file, start_line=finding.line)],
            explanation=f"{finding.tool} emitted {finding.rule}.",
        )
    ]


def _remediation_packet_for_finding(finding: ReviewFinding) -> RemediationPacket:
    possible_keep_reason = finding.preserve_reason
    if possible_keep_reason is None and finding.guidance_kind in {"design_judgment", "needs_tests"}:
        possible_keep_reason = "Keep the current shape if tests, API compatibility, or domain readability need it."
    return RemediationPacket(
        issue=finding.message,
        recommended_action=finding.recommended_action or "inspect",
        possible_keep_reason=possible_keep_reason,
        safety_checks=finding.safety_checks or ["inspect the surrounding behavior before editing"],
        validation_plan=["run targeted tests for the touched file", "rerun specfact code review with --focus simplify"],
        safe_to_autofix=finding.is_safe_mechanical_simplification() and finding.fixable,
    )


def _preserve_reasons_for_finding(finding: ReviewFinding, *, load_bearing: bool) -> list[PreserveReasonEvidence]:
    reasons: list[PreserveReasonEvidence] = []
    evidence_ref = EvidenceRef(path=finding.file, start_line=finding.line)
    if load_bearing:
        reasons.append(
            PreserveReasonEvidence(
                reason="load_bearing",
                evidence_refs=[evidence_ref],
                explanation="Mutation proof indicates this code is load-bearing.",
            )
        )
    parsed = _get_parsed_source(finding.file)
    if parsed is None:
        return reasons
    tree, lines = parsed
    function_node = _function_containing_line(tree, finding.line)
    class_node = _class_containing_line(tree, finding.line)
    public_names = _module_all_names(tree)
    if function_node is not None:
        if _has_contract_decorator(function_node):
            reasons.append(
                PreserveReasonEvidence(
                    reason="contract_lambda",
                    evidence_refs=[evidence_ref],
                    explanation="Function is protected by an icontract-style contract decorator.",
                )
            )
        if function_node.name in public_names:
            reasons.append(
                PreserveReasonEvidence(
                    reason="public_api",
                    evidence_refs=[evidence_ref],
                    explanation="Function is exported through __all__ and is public API.",
                )
            )
        if _has_cli_decorator(function_node):
            reasons.append(
                PreserveReasonEvidence(
                    reason="cli_callback",
                    evidence_refs=[evidence_ref],
                    explanation="Function is registered as a Typer or Click callback.",
                )
            )
        if _has_preserve_marker(lines, function_node.lineno):
            reasons.append(
                PreserveReasonEvidence(
                    reason="compat_shim",
                    evidence_refs=[evidence_ref],
                    explanation="Function has an explicit specfact preserve compatibility marker.",
                )
            )
        if _has_spec_marker(lines, function_node.lineno):
            reasons.append(
                PreserveReasonEvidence(
                    reason="spec_linked",
                    evidence_refs=[evidence_ref],
                    explanation="Function has an explicit spec requirement marker.",
                )
            )
    if class_node is not None and _is_protocol_or_abstract_member(class_node, function_node):
        reasons.append(
            PreserveReasonEvidence(
                reason="protocol_member",
                evidence_refs=[evidence_ref],
                explanation="Finding is inside an abstract Protocol or ABC member contract.",
            )
        )
    return _dedupe_preserve_reasons(reasons)


def _get_parsed_source(file_path: str) -> tuple[ast.Module, list[str]] | None:
    try:
        source = Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _parse_source(file_path, source)


@lru_cache(maxsize=256)
def _parse_source(file_path: str, source: str) -> tuple[ast.Module, list[str]] | None:
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return None
    return tree, source.splitlines()


def _dedupe_preserve_reasons(reasons: list[PreserveReasonEvidence]) -> list[PreserveReasonEvidence]:
    deduped: list[PreserveReasonEvidence] = []
    seen: set[str] = set()
    for reason in reasons:
        if reason.reason in seen:
            continue
        seen.add(reason.reason)
        deduped.append(reason)
    return deduped


def _function_containing_line(tree: ast.AST, line: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    return max(functions, key=lambda node: node.lineno, default=None)


def _class_containing_line(tree: ast.AST, line: int) -> ast.ClassDef | None:
    classes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    return max(classes, key=lambda node: node.lineno, default=None)


def _module_all_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        exported_values = _module_all_assignment_values(node)
        if exported_values is None:
            continue
        for item in exported_values:
            item_name = _string_constant_value(item)
            if item_name is not None:
                names.add(item_name)
    return names


def _module_all_assignment_values(node: ast.stmt) -> list[ast.expr] | None:
    if not isinstance(node, ast.Assign):
        return None
    if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
        return None
    if isinstance(node.value, ast.List | ast.Tuple | ast.Set):
        return list(node.value.elts)
    return None


def _string_constant_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Str) and isinstance(node.s, str):
        return node.s
    return None


def _decorator_full_name(node: ast.AST) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        prefix = _decorator_full_name(target.value)
        return f"{prefix}.{target.attr}" if prefix else target.attr
    return ""


def _has_contract_decorator(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    contract_names = {"require", "ensure", "invariant", "icontract.require", "icontract.ensure", "icontract.invariant"}
    return any(_decorator_full_name(decorator) in contract_names for decorator in function_node.decorator_list)


def _has_cli_decorator(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        _decorator_full_name(decorator).split(".")[-1] in {"command", "callback"}
        for decorator in function_node.decorator_list
    )


def _has_abstractmethod(function_node: ast.FunctionDef | ast.AsyncFunctionDef | None) -> bool:
    if function_node is None:
        return False
    return any(
        _decorator_full_name(decorator).split(".")[-1] == "abstractmethod" for decorator in function_node.decorator_list
    )


def _is_protocol_or_abstract_member(
    class_node: ast.ClassDef,
    function_node: ast.FunctionDef | ast.AsyncFunctionDef | None,
) -> bool:
    if function_node is None:
        return False
    if _has_abstractmethod(function_node):
        return True
    return _has_base_named(class_node, {"Protocol"}) and _is_stub_function(function_node)


def _is_stub_function(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [statement for statement in function_node.body if not _is_docstring_statement(statement)]
    return all(_is_stub_statement(statement) for statement in body)


def _is_docstring_statement(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _is_stub_statement(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Pass):
        return True
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and statement.value.value is Ellipsis
    )


def _has_base_named(class_node: ast.ClassDef, names: set[str]) -> bool:
    return any(_base_name(base).rsplit(".", maxsplit=1)[-1] in names for base in class_node.bases)


def _base_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _base_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return ""


def _has_preserve_marker(lines: list[str], line: int) -> bool:
    context = "\n".join(lines[max(0, line - 3) : line])
    return "specfact: preserve(" in context


def _has_spec_marker(lines: list[str], line: int) -> bool:
    context = "\n".join(lines[max(0, line - 3) : line])
    return "# spec:" in context or "# specfact: requirement(" in context


def _collect_tdd_inputs(files: list[Path]) -> tuple[list[Path], list[Path], list[ReviewFinding]]:
    source_files = [file_path for file_path in files if _expected_test_path(file_path) is not None]
    findings: list[ReviewFinding] = []
    test_files: list[Path] = []
    for source_file in source_files:
        expected_test = _expected_test_path(source_file)
        if expected_test is None:
            continue
        if expected_test.exists():
            test_files.append(expected_test)
            continue
        findings.append(
            ReviewFinding(
                category="testing",
                severity="error",
                tool="pytest",
                rule="TEST_FILE_MISSING",
                file=str(source_file),
                line=1,
                message=f"Missing corresponding test file: {expected_test}",
                fixable=False,
            )
        )
    return source_files, test_files, findings


def _is_empty_init_file(source_file: Path) -> bool:
    """Check if __init__.py is a marker/empty module with no executable statements."""
    if source_file.name != "__init__.py":
        return False

    try:
        content = source_file.read_text(encoding="utf-8")
    except OSError:
        return False

    # Strip whitespace, comments, and docstrings
    stripped_content = re.sub(r'"""[^"""]*"""', "", content, flags=re.DOTALL)
    stripped_content = re.sub(r"'''[^']*'''", "", stripped_content, flags=re.DOTALL)
    stripped_content = re.sub(r"#.*$", "", stripped_content, flags=re.MULTILINE)
    stripped_content = stripped_content.strip()

    # Consider empty if only contains 'pass' or is completely empty
    return stripped_content in ("", "pass")


def _is_coverage_omitted_init_by_project_policy(source_file: Path) -> bool:
    """True when repo coverage omits this file (``pyproject.toml`` ``[tool.coverage.run]`` ``omit``).

    ``src/**/__init__.py`` and ``packages/**/__init__.py`` are omitted from coverage; the pytest-cov
    JSON report therefore has no ``percent_covered`` for them — not a TDD gap.
    """
    try:
        path = source_file if source_file.is_absolute() else (Path.cwd() / source_file).resolve()
        rel = path.relative_to(Path.cwd().resolve())
    except (ValueError, OSError):
        rel = source_file
    if rel.name != "__init__.py":
        return False
    parts = rel.parts
    return len(parts) >= 2 and parts[0] in ("src", "packages")


def _coverage_findings(
    source_files: list[Path],
    coverage_payload: dict[str, object],
    *,
    allow_project_omitted_initializers: bool = True,
    threshold: float = _COVERAGE_THRESHOLD,
    blocking_low_coverage: bool = False,
) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    findings: list[ReviewFinding] = []
    coverage_by_source: dict[str, float] = {}
    for source_file in source_files:
        percent_covered = _coverage_for_source(source_file, coverage_payload)
        if percent_covered is None:
            if source_file.name == "__init__.py" and _is_empty_init_file(source_file):
                continue  # Exempt empty __init__.py files
            if allow_project_omitted_initializers and _is_coverage_omitted_init_by_project_policy(source_file):
                continue
            return [
                tool_error(
                    tool="pytest",
                    file_path=source_file,
                    message=f"Coverage data missing for {source_file}",
                )
            ], None
        coverage_by_source[str(source_file)] = percent_covered
        if percent_covered >= threshold:
            continue
        findings.append(
            ReviewFinding(
                category="testing",
                severity="error" if blocking_low_coverage else "warning",
                tool="pytest",
                rule="TEST_COVERAGE_LOW",
                file=str(source_file),
                line=1,
                message=(f"Coverage for {source_file} is {percent_covered:.1f}%, below required {threshold:.1f}%."),
                fixable=False,
            )
        )
    return findings, coverage_by_source


def _pytest_junit_identities(observer: tuple[dict[str, object], ...]) -> dict[tuple[str, str], list[str]]:
    observed_nodes = tuple(dict.fromkeys(str(record.get("nodeid", "")) for record in observer))
    junit_identities: dict[tuple[str, str], list[str]] = {}
    for nodeid in observed_nodes:
        path, *qualifiers = nodeid.split("::")
        if not qualifiers or not path.endswith(".py"):
            continue
        classname_parts = [path[:-3].replace("/", "."), *qualifiers[:-1]]
        identity = (".".join(classname_parts), qualifiers[-1])
        junit_identities.setdefault(identity, []).append(nodeid)
    return junit_identities


def _pytest_junit_outcome(case: ET.Element) -> str:
    child_tags = {child.tag.rsplit("}", maxsplit=1)[-1] for child in case}
    if child_tags & {"error", "failure"}:
        return "failed"
    return "skipped" if "skipped" in child_tags else "passed"


def _pytest_junit_records(
    root: ET.Element,
    identities: dict[tuple[str, str], list[str]],
) -> tuple[dict[str, object], ...]:
    cases = tuple(element for element in root.iter() if element.tag.rsplit("}", maxsplit=1)[-1] == "testcase")
    junit: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        candidates = identities.get((case.get("classname", ""), case.get("name", "")), [])
        nodeid = candidates[0] if len(candidates) == 1 else f"__unmatched_junit_{index}"
        junit.append({"nodeid": nodeid, "outcome": _pytest_junit_outcome(case)})
    return tuple(junit)


def _load_pytest_outcome_evidence(
    observer_path: Path,
    junit_path: Path,
) -> tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...]]:
    observer_payload = json.loads(observer_path.read_text(encoding="utf-8"))
    if not isinstance(observer_payload, list) or not all(isinstance(record, dict) for record in observer_payload):
        raise ValueError("pytest observer artifact must be a list of objects")
    observer = tuple(cast(list[dict[str, object]], observer_payload))
    junit_root = ET.parse(junit_path).getroot()
    return observer, _pytest_junit_records(junit_root, _pytest_junit_identities(observer))


def _pytest_outcome_finding(anchor: Path, *, status: str) -> ReviewFinding:
    if status == "FAIL":
        return ReviewFinding(
            category="testing",
            severity="error",
            tool="pytest",
            rule="TEST_OUTCOME_NOT_PASS",
            file=str(anchor),
            line=1,
            message="At least one targeted pytest selector skipped, xfailed, xpassed, or failed.",
            fixable=False,
        )
    return tool_error(
        tool="pytest",
        file_path=anchor,
        message="Targeted pytest observer, JUnit, and process outcomes could not be reconciled.",
    )


def _evaluate_pytest_execution(
    source_files: list[Path],
    execute: Callable[[], tuple[subprocess.CompletedProcess[str], Path, Path, Path]],
    *,
    planned: tuple[str, ...] = (),
    allow_project_omitted_initializers: bool = True,
    coverage_threshold: float = _COVERAGE_THRESHOLD,
    blocking_low_coverage: bool = False,
) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    anchor = source_files[0] if source_files else Path("/opt/specfact/snapshot")
    pytest_skip = skip_if_pytest_unavailable(anchor)
    if pytest_skip:
        return pytest_skip, None

    try:
        test_result, coverage_path, observer_path, junit_path = execute()
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return [
            tool_error(
                tool="pytest",
                file_path=anchor,
                message=f"Unable to execute targeted tests: {exc}",
            )
        ], None

    try:
        observer, junit = _load_pytest_outcome_evidence(observer_path, junit_path)
        outcome = reconcile_pytest_outcomes(
            observer=observer,
            junit=junit,
            process_exit=test_result.returncode,
            planned=planned,
        )
        if outcome.status != "PASS":
            return [_pytest_outcome_finding(anchor, status=outcome.status)], None
        coverage_payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
        return [
            tool_error(
                tool="pytest",
                file_path=anchor,
                message=f"Unable to read targeted pytest evidence: {exc}",
            )
        ], None
    finally:
        coverage_path.unlink(missing_ok=True)
        observer_path.unlink(missing_ok=True)
        junit_path.unlink(missing_ok=True)

    return _coverage_findings(
        source_files,
        coverage_payload,
        allow_project_omitted_initializers=allow_project_omitted_initializers,
        threshold=coverage_threshold,
        blocking_low_coverage=blocking_low_coverage,
    )


def _coverage_threshold_from_policy_argv(policy_argv: tuple[str, ...]) -> float:
    try:
        config_path = Path(policy_argv[policy_argv.index("--cov-config") + 1])
    except (ValueError, IndexError) as exc:
        raise ValueError("sealed coverage configuration is missing") from exc
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with config_path.open(encoding="utf-8") as handle:
            parser.read_file(handle)
        configured = parser.getfloat("report", "fail_under", fallback=_COVERAGE_THRESHOLD)
    except (OSError, configparser.Error, ValueError) as exc:
        raise ValueError("sealed coverage threshold is invalid") from exc
    if not 0.0 <= configured <= 100.0:
        raise ValueError("sealed coverage threshold is invalid")
    return max(_COVERAGE_THRESHOLD, configured)


def _complete_pytest_coverage_roots(
    test_roots: tuple[Path, ...], selected_test_files: set[Path], *, snapshot_root: Path
) -> tuple[Path, ...]:
    selected_support_roots = {
        path.parent
        for path in selected_test_files
        if path.parent != snapshot_root and _is_test_file(path.relative_to(snapshot_root))
    }
    return tuple(sorted({root for root in test_roots if root != snapshot_root} | selected_support_roots))


def _evaluate_complete_tdd_gate(
    files: list[Path], adapter_argv: tuple[str, ...]
) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    """Execute the controller-supplied complete immutable pytest inventory."""
    policy_argv, selectors = _split_pytest_adapter_argv(adapter_argv)
    test_roots = _projected_pytest_test_roots(policy_argv)
    snapshot_root = Path("/opt/specfact/snapshot")
    selected_test_files = {snapshot_root / selector.split("::", maxsplit=1)[0] for selector in selectors}
    coverage_test_roots = _complete_pytest_coverage_roots(test_roots, selected_test_files, snapshot_root=snapshot_root)
    source_files = [
        file_path
        for file_path in files
        if file_path.suffix == ".py"
        and file_path not in selected_test_files
        and file_path.name != "conftest.py"
        and not _is_below_any_root(file_path, coverage_test_roots)
    ]
    if not selectors:
        anchor = source_files[0] if source_files else Path("/opt/specfact/snapshot")
        return [
            tool_error(
                tool="pytest",
                file_path=anchor,
                message="Complete pytest inventory contains no collected selectors.",
            )
        ], None
    return _evaluate_pytest_execution(
        source_files,
        lambda: _run_pytest_inventory_with_coverage(selectors, policy_argv=policy_argv),
        planned=selectors,
        allow_project_omitted_initializers=False,
        coverage_threshold=_coverage_threshold_from_policy_argv(policy_argv),
        blocking_low_coverage=True,
    )


def _evaluate_tdd_gate(files: list[Path]) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    """Validate tests and return findings plus per-source coverage when available."""
    source_files, test_files, findings = _collect_tdd_inputs(files)
    if not source_files:
        return [], None
    if findings:
        return findings, None
    return _evaluate_pytest_execution(
        source_files,
        lambda: _run_pytest_with_coverage(test_files),
    )


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_tdd_gate(files: list[Path]) -> list[ReviewFinding]:
    """Validate test-file presence and targeted test coverage for bundle source files."""
    findings, _coverage_by_source = _evaluate_tdd_gate(files)
    return findings


def _has_no_suppressions(files: list[Path]) -> bool:
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            return False
        if any(marker in content for marker in _SUPPRESSION_MARKERS):
            return False
    return True


def _review_options_from_kwargs(options: ReviewOptions | None, overrides: dict[str, object]) -> ReviewOptions:
    if options is not None and overrides:
        raise TypeError("pass either options or keyword review overrides, not both")
    if options is not None:
        return options
    allowed_keys = {
        "no_tests",
        "include_noise",
        "progress_callback",
        "bug_hunt",
        "review_level",
        "review_mode",
        "focus",
    }
    unknown_keys = set(overrides) - allowed_keys
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise TypeError(f"unknown review option override: {unknown}")
    for key in ("no_tests", "include_noise", "bug_hunt"):
        value = overrides.get(key, False)
        if not isinstance(value, bool):
            raise TypeError(f"{key} must be bool")
    no_tests = cast(bool, overrides.get("no_tests", False))
    include_noise = cast(bool, overrides.get("include_noise", False))
    bug_hunt = cast(bool, overrides.get("bug_hunt", False))
    progress_callback = overrides.get("progress_callback")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable or None")
    review_level = overrides.get("review_level")
    if review_level not in {"error", "warning", None}:
        raise TypeError("review_level must be one of error, warning, or None")
    review_mode = overrides.get("review_mode", "full")
    if review_mode not in {"full", "changed", "shadow", "enforce"}:
        raise TypeError("review_mode must be one of full, changed, shadow, or enforce")
    if review_mode == "enforce":
        review_mode = "full"
    focus = overrides.get("focus")
    if focus not in {"simplify", None}:
        raise TypeError("focus must be simplify or None")
    return ReviewOptions(
        no_tests=no_tests,
        include_noise=include_noise,
        progress_callback=cast(Callable[[str], None] | None, progress_callback),
        bug_hunt=bug_hunt,
        review_level=cast(Literal["error", "warning"] | None, review_level),
        review_mode=cast(ReviewEnforcementMode, review_mode),
        focus=cast(ReviewFocus | None, focus),
    )


def _capsule_evidence_list(evidence: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    return [{"id": member, **evidence[member]} for member in default_pr_range_profile().all_ids]


def _activated_capsule_report_evidence(
    evidence: dict[str, dict[str, object]],
) -> tuple[differential.CatalogActivation, dict[str, dict[str, object]]]:
    activation = differential.activate_packaged_suppression_catalog()
    if activation.status == "PASS" and activation.profile_activated and activation.digest is not None:
        return activation, evidence
    return activation, {
        member: {
            **evidence.get(member, {}),
            "execution_state": "error",
            "evidence_outcome": "UNKNOWN",
            "version": _C14_ANALYZER_VERSIONS[member],
            "diagnostic": activation.reason or "suppression_catalog_activation_failed",
        }
        for member in default_pr_range_profile().all_ids
    }


def _capsule_report(
    evidence: dict[str, dict[str, object]],
    findings_by_member: dict[str, list[ReviewFinding]],
    *,
    options: ReviewOptions,
    scope_evidence: dict[str, object],
) -> ReviewReport:
    activation, report_evidence = _activated_capsule_report_evidence(evidence)
    profile = aggregate_profile_evidence(report_evidence)
    findings = [
        finding for member in default_pr_range_profile().all_ids for finding in findings_by_member.get(member, [])
    ]
    if not options.include_noise:
        findings = _suppress_known_noise(findings)
    findings = _filter_findings_by_review_level(findings, options.review_level)
    findings = _filter_findings_by_focus(findings, options.focus)
    score = 100 if profile.assurance_status == "PASS" and not any(finding.is_blocking() for finding in findings) else 0
    return ReviewReport(
        schema_version="1.6",
        run_id=f"review-capsule-{uuid4()}",
        score=score,
        findings=findings,
        summary=(
            _summary_for_findings(findings)
            if profile.assurance_status != "UNKNOWN"
            else "Analyzer capsule execution is incomplete; assurance is UNKNOWN."
        ),
        assurance_status=cast(Any, profile.assurance_status),
        has_unknown_required_evidence=profile.has_unknown_required_evidence,
        scope_evidence=scope_evidence,
        analyzer_evidence=_capsule_evidence_list(report_evidence),
        suppression_catalog_digest=(
            activation.digest if activation.status == "PASS" and activation.profile_activated else None
        ),
        enforcement_mode=options.review_mode,
    )


def _unknown_capsule_report(reason: str, *, options: ReviewOptions, scope_evidence: dict[str, object]) -> ReviewReport:
    evidence: dict[str, dict[str, object]] = {
        member: {
            "execution_state": "error",
            "evidence_outcome": "UNKNOWN",
            "version": _C14_ANALYZER_VERSIONS[member],
            "diagnostic": reason,
        }
        for member in default_pr_range_profile().all_ids
    }
    return _capsule_report(evidence, {}, options=options, scope_evidence=scope_evidence)


def _is_development_source_checkout() -> bool:
    repository = Path.cwd().resolve()
    source = Path(__file__).resolve()
    return (
        (repository / ".git").exists()
        and (repository / "openspec/changes/code-review-14-scope-truth-and-differential-enforcement").is_dir()
        and source.is_relative_to(repository)
    )


def _allows_development_host_compatibility(reason: str) -> bool:
    if not _is_development_source_checkout():
        return False
    if reason == "unsupported_controller_platform":
        return True
    return (
        reason == "oci_acquisition_failed:verified cache entry is missing"
        and os.environ.get("SPECFACT_CODE_REVIEW_DEV_HOST_COMPAT") == "1"
    )


def _with_capsule_enforcement(report: ReviewReport, options: ReviewOptions, files: list[Path]) -> ReviewReport:
    """Finalize one capsule report under the requested local enforcement policy."""
    return _with_enforcement(report, mode=options.review_mode, files=files)


def run_capsule_review(
    files: list[Path],
    options: ReviewOptions | None = None,
    *,
    assurance_kind: LocalAssuranceKind = "explicit_files",
    **overrides: object,
) -> ReviewReport:
    """Run legacy/local review scopes only through the signed analyzer capsule."""

    review_options = _review_options_from_kwargs(options, overrides)
    runtime, reason = _prepare_capsule_runtime()
    scope_evidence: dict[str, object] = {"assurance_kind": assurance_kind, "capsule_execution": "required"}
    if runtime is None:
        if _allows_development_host_compatibility(reason):
            return run_review(files, review_options).model_copy(update={"scope_evidence": scope_evidence})
        return _with_capsule_enforcement(
            _unknown_capsule_report(reason, options=review_options, scope_evidence=scope_evidence),
            review_options,
            files=files,
        )
    try:
        snapshot = _run_capsule_snapshot(
            runtime,
            snapshot_root=Path.cwd(),
            files=files,
            options=review_options,
        )
        return _with_capsule_enforcement(
            _capsule_report(
                snapshot.evidence,
                snapshot.findings_by_member,
                options=review_options,
                scope_evidence=scope_evidence,
            ),
            review_options,
            files=files,
        )
    finally:
        _cleanup_capsule_runtime(runtime)


def _snapshot_python_files(snapshot: object, resolution: object) -> list[Path]:
    root = cast(Path, snapshot.root)
    contents = cast(dict[str, bytes], snapshot.contents)
    selected_paths = getattr(resolution, "selected_paths", None)
    if not isinstance(selected_paths, tuple) or not all(isinstance(path, str) for path in selected_paths):
        raise ValueError("selected_paths_missing")
    return [root / path for path in sorted(selected_paths) if path in contents and Path(path).suffix in {".py", ".pyi"}]


def _differential_finding_projection(finding: ReviewFinding) -> dict[str, object]:
    return {
        "analyzer": finding.tool,
        "blocking": finding.is_blocking(),
        "line": finding.line,
        "message": finding.message,
        "path": finding.file,
        "rule": finding.rule,
        "severity": finding.severity,
    }


def _differential_finding_key(finding: object) -> tuple[str, str, str, int, str, str, bool]:
    return (
        str(getattr(finding, "analyzer", getattr(finding, "tool", ""))),
        str(getattr(finding, "rule", "")),
        str(getattr(finding, "path", getattr(finding, "file", ""))),
        int(getattr(finding, "line", 1)),
        " ".join(str(getattr(finding, "message", "")).split()),
        str(getattr(finding, "severity", "")),
        bool(getattr(finding, "blocking", False)),
    )


def _classified_findings(
    classification: differential.DifferentialClassification,
    *,
    base: list[ReviewFinding],
    head: list[ReviewFinding],
) -> list[ReviewFinding]:
    base_by_key: dict[tuple[str, str, str, int, str, str, bool], list[ReviewFinding]] = {}
    head_by_key: dict[tuple[str, str, str, int, str, str, bool], list[ReviewFinding]] = {}
    for source, destination in ((base, base_by_key), (head, head_by_key)):
        for finding in source:
            destination.setdefault(_differential_finding_key(finding), []).append(finding)
    result: list[ReviewFinding] = []
    for state in ("introduced", "unchanged", "fixed", "unknown"):
        for finding in cast(tuple[object, ...], getattr(classification, state)):
            key = _differential_finding_key(finding)
            preferred = base_by_key if state == "fixed" else head_by_key
            fallback = head_by_key if state == "fixed" else base_by_key
            candidates = preferred.get(key) or fallback.get(key)
            if not candidates:
                raise ValueError("differential finding cannot be mapped to analyzer evidence")
            original = candidates.pop(0)
            updates: dict[str, object] = {"differential_state": state}
            if state == "fixed":
                updates.update({"blocking": False, "status": "fixed"})
            result.append(ReviewFinding.model_validate({**original.model_dump(), **updates}))
    return result


def _member_snapshot_is_consistent(evidence: dict[str, object], findings: list[ReviewFinding]) -> bool:
    outcome = str(evidence.get("evidence_outcome", "UNKNOWN"))
    if outcome == "UNKNOWN":
        return False
    if outcome == "NOT_APPLICABLE":
        return not findings
    expected = "FAIL" if any(finding.is_blocking() for finding in findings) else "PASS"
    return outcome == expected


def _unknown_range_member(
    member: str,
    *,
    reason: str,
    base: dict[str, object],
    head: dict[str, object],
) -> dict[str, object]:
    return {
        "execution_state": "error",
        "evidence_outcome": "UNKNOWN",
        "version": _C14_ANALYZER_VERSIONS[member],
        "diagnostic": reason,
        "disposition": "unknown",
        "base": base,
        "head": head,
    }


def _range_differential_context(resolution: object) -> RangeDifferentialContext:
    exact_renames = tuple(getattr(resolution, "exact_renames", ()))
    rename_ambiguities: dict[str, list[str]] = {
        item.old_path: [item.new_path] for item in exact_renames if item.disposition == "ambiguous"
    }
    path_statuses = cast(dict[str, str], getattr(resolution, "path_statuses", {}))
    return RangeDifferentialContext(
        cast(dict[str, bytes], resolution.base_snapshot.contents),
        cast(dict[str, bytes], resolution.head_snapshot.contents),
        {item.old_path: item.new_path for item in exact_renames if item.disposition == "exact_rename"},
        rename_ambiguities or None,
        tuple(sorted(path for path, status in path_statuses.items() if status == "A")),
        tuple(sorted(path for path, status in path_statuses.items() if status == "D")),
    )


def _not_applicable_range_member(
    member: str,
    *,
    base: dict[str, object],
    head: dict[str, object],
) -> dict[str, object]:
    return {
        "execution_state": "not_applicable",
        "evidence_outcome": "NOT_APPLICABLE",
        "version": _C14_ANALYZER_VERSIONS[member],
        "diagnostic": "",
        "disposition": "not_applicable",
        "base": base,
        "head": head,
    }


def _classify_range_member(
    member: str,
    context: RangeDifferentialContext,
    *,
    base_evidence: dict[str, object],
    head_evidence: dict[str, object],
    base_findings: list[ReviewFinding],
    head_findings: list[ReviewFinding],
) -> tuple[dict[str, object], list[ReviewFinding]]:
    outcomes = {
        str(base_evidence.get("evidence_outcome", "UNKNOWN")),
        str(head_evidence.get("evidence_outcome", "UNKNOWN")),
    }
    if outcomes == {"NOT_APPLICABLE"}:
        return _not_applicable_range_member(member, base=base_evidence, head=head_evidence), []
    if not _member_snapshot_is_consistent(base_evidence, base_findings) or not _member_snapshot_is_consistent(
        head_evidence, head_findings
    ):
        unknown_findings = [
            finding.model_copy(update={"differential_state": "unknown"}) for finding in (head_findings or base_findings)
        ]
        return (
            _unknown_range_member(
                member,
                reason="snapshot_member_incomplete",
                base=base_evidence,
                head=head_evidence,
            ),
            unknown_findings,
        )
    classification = differential.classify_findings(
        differential.FindingClassificationRequest(
            base_findings=[_differential_finding_projection(finding) for finding in base_findings],
            head_findings=[_differential_finding_projection(finding) for finding in head_findings],
            base_sources=context.base_sources,
            head_sources=context.head_sources,
            rename_facts=context.rename_facts,
            rename_ambiguities=context.rename_ambiguities,
            deleted_paths=context.deleted_paths,
            added_paths=context.added_paths,
        )
    )
    try:
        classified = _classified_findings(classification, base=base_findings, head=head_findings)
    except ValueError:
        return (
            _unknown_range_member(
                member,
                reason="differential_finding_mapping_failed",
                base=base_evidence,
                head=head_evidence,
            ),
            [],
        )
    counts = {state: len(getattr(classification, state)) for state in ("fixed", "introduced", "unchanged", "unknown")}
    return (
        {
            "execution_state": "ran",
            "evidence_outcome": classification.status,
            "version": _C14_ANALYZER_VERSIONS[member],
            "diagnostic": classification.reason,
            "disposition": "differential_complete" if classification.status != "UNKNOWN" else "unknown",
            "differential_counts": counts,
            "differential_evidence_digest": classification.evidence_digest,
            "base": base_evidence,
            "head": head_evidence,
        },
        classified,
    )


def _classify_range_findings(
    resolution: object,
    base: CapsuleSnapshotResult,
    head: CapsuleSnapshotResult,
) -> tuple[dict[str, dict[str, object]], dict[str, list[ReviewFinding]]]:
    """Classify each member's base/head findings with the canonical C14 differential."""

    context = _range_differential_context(resolution)
    combined: dict[str, dict[str, object]] = {}
    classified_by_member: dict[str, list[ReviewFinding]] = {}
    for member in default_pr_range_profile().all_ids:
        combined[member], classified_by_member[member] = _classify_range_member(
            member,
            context,
            base_evidence=base.evidence[member],
            head_evidence=head.evidence[member],
            base_findings=base.findings_by_member.get(member, []),
            head_findings=head.findings_by_member.get(member, []),
        )
    suppression = differential.classify_suppression_delta(
        base_sources=context.base_sources,
        head_sources=context.head_sources,
        rename_facts=context.rename_facts,
        missing_base_findings=[
            _differential_finding_projection(finding)
            for findings in base.findings_by_member.values()
            for finding in findings
        ],
    )
    _apply_suppression_delta(suppression, combined=combined, findings_by_member=classified_by_member)
    return combined, classified_by_member


def _suppression_finding_category(member: str) -> str:
    return {
        "basedpyright": "type_safety",
        "contracts": "contracts",
        "pylint": "clean_code",
        "ruff": "style",
        "semgrep": "security",
        "semgrep-bugs": "security",
        "targeted-pytest-coverage": "testing",
    }[member]


def _suppression_review_finding(
    finding: differential.SuppressionFinding,
    *,
    member: str,
) -> ReviewFinding:
    state = "unknown" if finding.kind == "unchanged_suppression_on_changed_file" else "introduced"
    return ReviewFinding(
        category=cast(Any, _suppression_finding_category(member)),
        severity="error",
        tool=member,
        rule=finding.kind,
        file=finding.path,
        line=finding.line,
        message=f"C14 suppression control requires {state} disposition for {member}.",
        fixable=False,
        differential_state=cast(Any, state),
        blocking=finding.blocking,
        evidence_refs=_suppression_evidence_refs(finding),
    )


def _suppression_evidence_refs(finding: differential.SuppressionFinding) -> list[EvidenceRef]:
    evidence = finding.evidence
    transition = evidence.transition
    refs = [
        EvidenceRef(
            path=finding.path,
            start_line=finding.line,
            end_line=finding.line,
            artifact_id=evidence.occurrence_digest,
            description=(
                f"{evidence.family}; base={evidence.base_blob_digest or 'absent'}; "
                f"head={evidence.head_blob_digest or 'absent'}; change={evidence.changed_hunk_digest}"
            ),
        )
    ]
    if transition.base_occurrence_digest:
        refs.append(
            EvidenceRef(
                path=transition.base_path,
                start_line=transition.base_line,
                end_line=transition.base_line,
                artifact_id=transition.base_occurrence_digest,
                description="Baseline suppression occurrence matched to the head transition.",
            )
        )
    if transition.correspondence_digest:
        refs.append(
            EvidenceRef(
                artifact_id=transition.correspondence_digest,
                description=json.dumps(transition.correspondence_evidence, sort_keys=True, separators=(",", ":")),
            )
        )
    return refs


def _apply_suppression_delta(
    suppression: differential.SuppressionClassification,
    *,
    combined: dict[str, dict[str, object]],
    findings_by_member: dict[str, list[ReviewFinding]],
) -> None:
    if suppression.status == "UNKNOWN" and not suppression.findings:
        for member in default_pr_range_profile().all_ids:
            combined[member] = _merge_member_outcome(
                combined[member],
                outcome="UNKNOWN",
                reason=suppression.reason or "suppression_manifest_unknown",
            )
        return
    for finding in suppression.findings:
        for member in finding.evidence.analyzers:
            if member not in combined or combined[member].get("evidence_outcome") == "NOT_APPLICABLE":
                continue
            state = "UNKNOWN" if finding.kind == "unchanged_suppression_on_changed_file" else "FAIL"
            findings_by_member.setdefault(member, []).append(_suppression_review_finding(finding, member=member))
            combined[member] = _merge_member_outcome(combined[member], outcome=state, reason=finding.kind)
            if suppression.missing_base_disposition == "unknown":
                findings_by_member[member] = _reclassify_missing_base_findings(
                    findings_by_member[member],
                    path=finding.path,
                )


def _reclassify_missing_base_findings(findings: list[ReviewFinding], *, path: str) -> list[ReviewFinding]:
    return [
        ReviewFinding.model_validate(
            {
                **item.model_dump(exclude={"blocking"}),
                "differential_state": "unknown",
                "status": "open",
            }
        )
        if item.file == path and item.differential_state == "fixed"
        else item
        for item in findings
    ]


def _merge_member_outcome(
    evidence: dict[str, object],
    *,
    outcome: Literal["FAIL", "UNKNOWN"],
    reason: str,
) -> dict[str, object]:
    """Merge one fail-closed fact without losing a blocker or uncertainty."""

    existing_outcome = str(evidence.get("evidence_outcome", "UNKNOWN"))
    existing_diagnostic = str(evidence.get("diagnostic", ""))
    diagnostics = {value for value in (existing_diagnostic, reason) if value}
    unknown_reasons = _normalized_unknown_reasons(evidence.get("required_unknown_reasons", []))
    existing_unknown_reason = _preexisting_unknown_reason(existing_outcome, existing_diagnostic)
    if existing_unknown_reason:
        unknown_reasons.add(existing_unknown_reason)
    if outcome == "UNKNOWN":
        unknown_reasons.add(reason)
    merged_outcome = "FAIL" if "FAIL" in {existing_outcome, outcome} else "UNKNOWN"
    merged = {
        **evidence,
        "evidence_outcome": merged_outcome,
        "diagnostic": ";".join(sorted(diagnostics)),
        "disposition": "introduced" if merged_outcome == "FAIL" else "unknown",
    }
    if unknown_reasons:
        merged["required_unknown_reasons"] = sorted(unknown_reasons)
    return merged


def _normalized_unknown_reasons(raw_reasons: object) -> set[str]:
    if not isinstance(raw_reasons, list):
        return {"invalid_required_unknown_reasons"}
    return {value for value in raw_reasons if isinstance(value, str) and value}


def _preexisting_unknown_reason(outcome: str, diagnostic: str) -> str:
    if outcome == "UNKNOWN":
        return diagnostic or "preexisting_member_unknown"
    if outcome not in {"PASS", "FAIL", "NOT_APPLICABLE"}:
        return "untrusted_preexisting_member_outcome"
    return ""


def _pytest_toml_values(path: Path, payload: bytes) -> dict[str, object]:
    document = tomllib.loads(payload.decode("utf-8"))
    if path.name != "pyproject.toml":
        raw = document.get("pytest", {})
        return cast(dict[str, object], raw if isinstance(raw, dict) else {})
    tool = cast(dict[str, object], document.get("tool", {}))
    raw = tool.get("pytest", {})
    if isinstance(raw, dict) and isinstance(raw.get("ini_options"), dict):
        raw = raw["ini_options"]
    return cast(dict[str, object], raw if isinstance(raw, dict) else {})


def _pytest_ini_values(path: Path, payload: bytes, *, section: str) -> dict[str, object]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(payload.decode("utf-8"))
    selected_section = "pytest" if path.name in {"pytest.ini", ".pytest.ini"} else section
    return dict(parser[selected_section]) if selected_section and parser.has_section(selected_section) else {}


def _pytest_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return cast(list[str], value)
    raise ValueError("pytest_config_ambiguous")


def _pytest_policy_values(policy_bundle: object | None) -> dict[str, object]:
    defaults: dict[str, object] = {
        "version": "9.0.3",
        "testpaths": ["."],
        "python_files": ["test_*.py"],
        "python_classes": ["Test*"],
        "python_functions": ["test_*"],
        "addopts": [],
        "config": {},
    }
    if policy_bundle is None:
        return defaults
    root = cast(Path, cast(Any, policy_bundle).root)
    located = scope.resolve_pytest_policy(root, expected_version="9.0.3")
    if located.status != "PASS":
        raise ValueError(located.reason)
    if not located.selected_path:
        return defaults
    path = root / located.selected_path
    payload = path.read_bytes()
    values = (
        _pytest_toml_values(path, payload)
        if path.suffix == ".toml"
        else _pytest_ini_values(path, payload, section=located.selected_section)
    )
    result = dict(defaults)
    for key in ("testpaths", "python_files", "python_classes", "python_functions"):
        raw_value = values.get(key)
        if raw_value is not None:
            result[key] = _pytest_string_list(raw_value)
    addopts = values.get("addopts")
    if addopts is not None:
        result["addopts"] = _pytest_string_list(addopts)
    result["config"] = values
    return result


def _flatten_coverage_sections(document: dict[str, object]) -> dict[str, object]:
    return {
        f"{section}:{key}": value
        for section, raw_fields in document.items()
        if isinstance(section, str) and isinstance(raw_fields, dict)
        for key, value in cast(dict[str, object], raw_fields).items()
    }


def _coverage_policy_values(policy_bundle: object | None) -> dict[str, object]:
    if policy_bundle is None:
        return {}
    root = cast(Path, cast(Any, policy_bundle).root)
    located = scope.resolve_coverage_policy(root, expected_version="7.15.4")
    if located.status != "PASS":
        raise ValueError(located.reason)
    if not located.selected_path:
        return {}
    path = root / located.selected_path
    payload = path.read_bytes()
    if path.suffix == ".toml" or path.name == "pyproject.toml":
        document = tomllib.loads(payload.decode("utf-8"))
        if path.name == "pyproject.toml":
            tool = cast(dict[str, object], document.get("tool", {}))
            document = cast(dict[str, object], tool.get("coverage", {}))
        return _flatten_coverage_sections(document)
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(payload.decode("utf-8"))
    values: dict[str, object] = {}
    for raw_section in parser.sections():
        section = raw_section.removeprefix("coverage:")
        values.update({f"{section}:{key}": value for key, value in parser[raw_section].items()})
    return values


def _reconcile_immutable_pytest_inventory(
    resolution: object,
    *,
    options: ReviewOptions,
    project_runtime_root: Path | None = None,
) -> ImmutablePytestInventory:
    if options.no_tests:
        return ImmutablePytestInventory(CandidateReconciliation("PASS"))
    base_snapshot = cast(Any, resolution).base_snapshot
    head_snapshot = cast(Any, resolution).head_snapshot
    policy = _pytest_policy_values(_trusted_policy_bundle(resolution))
    changed_paths = tuple(sorted(cast(dict[str, str], getattr(resolution, "path_statuses", {}))))
    base_plan, head_plan = (
        plan_complete_pytest_suite(
            snapshot.root,
            policy,
            changed_paths=changed_paths,
            project_runtime_root=project_runtime_root,
        )
        for snapshot in (base_snapshot, head_snapshot)
    )
    if base_plan.status != "PASS":
        return ImmutablePytestInventory(CandidateReconciliation("UNKNOWN", base_plan.reason))
    if head_plan.status != "PASS":
        return ImmutablePytestInventory(CandidateReconciliation("UNKNOWN", head_plan.reason))
    rename_facts: dict[str, str] = {
        item.old_path: item.new_path
        for item in tuple(getattr(resolution, "exact_renames", ()))
        if getattr(item, "disposition", "") == "exact_rename"
    }
    return ImmutablePytestInventory(
        reconcile_pytest_inventories(
            base=base_plan.selectors,
            head=head_plan.selectors,
            rename_facts=rename_facts,
        ),
        base_plan.selectors,
        head_plan.selectors,
    )


def _with_pytest_inventory(
    bindings: SnapshotPolicyBindings,
    selectors: tuple[str, ...],
    *,
    pytest_plugins: tuple[toolchain.PytestPluginIdentity, ...] = (),
) -> SnapshotPolicyBindings:
    member_argv = dict(bindings.member_argv)
    member_argv["targeted-pytest-coverage"] = (
        *member_argv.get("targeted-pytest-coverage", ()),
        *(value for plugin in pytest_plugins for value in ("-p", plugin.entry_point)),
        "--",
        *selectors,
    )
    return SnapshotPolicyBindings(bindings.config_roots, member_argv, bindings.cleanup_roots)


def _materialize_claimed_project_runtime(
    resolution: object,
) -> tuple[
    toolchain.ProjectRuntimeMaterialization | None,
    tuple[toolchain.PytestPluginIdentity, ...],
    str,
]:
    context = getattr(resolution, "claimed_context", None)
    if not isinstance(context, dict):
        return None, (), ""
    descriptor = context.get("project_runtime")
    if not isinstance(descriptor, dict) or descriptor.get("schema") != "project-runtime-layer-v1":
        return None, (), ""
    layer = toolchain.validate_project_runtime_layer(
        cast(dict[str, object], descriptor),
        expected_target=str(getattr(resolution, "resolved_target_commit", "")),
        expected_tree=str(getattr(resolution, "resolved_target_tree", "")),
        expected_source_locks=cast(
            tuple[toolchain.SourceLockIdentity, ...],
            getattr(resolution, "project_runtime_source_locks", ()),
        ),
    )
    if layer.status != "PASS":
        return None, (), layer.reason
    storage_root = Path(
        os.environ.get(
            "SPECFACT_CODE_REVIEW_PROJECT_RUNTIME_CACHE",
            str(Path.home() / ".cache/specfact/code-review/project-runtimes"),
        )
    ).expanduser()
    materialized = toolchain.materialize_project_runtime(
        cast(dict[str, object], descriptor),
        expected_target=str(getattr(resolution, "resolved_target_commit", "")),
        expected_tree=str(getattr(resolution, "resolved_target_tree", "")),
        expected_source_locks=cast(
            tuple[toolchain.SourceLockIdentity, ...],
            getattr(resolution, "project_runtime_source_locks", ()),
        ),
        storage_root=storage_root,
        credential=_capsule_credential(),
    )
    return (
        (materialized, layer.pytest_plugins, "") if materialized.status == "PASS" else (None, (), materialized.reason)
    )


def _pytest_plugin_preflight_manifest(plugins: tuple[toolchain.PytestPluginIdentity, ...]) -> str:
    return json.dumps(
        [
            {
                "distribution": plugin.distribution,
                "version": plugin.version,
                "entry_point": plugin.entry_point,
                "options": list(plugin.options),
                "ini_fields": list(plugin.ini_fields),
                "hooks": list(plugin.hooks),
                "parser_catalog_digest": plugin.parser_catalog_digest,
                "hook_capability_digest": plugin.hook_capability_digest,
            }
            for plugin in plugins
        ],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _preflight_project_runtime_pytest_plugins(
    runtime: CapsuleRuntime,
    project_runtime: toolchain.ProjectRuntimeMaterialization | None,
    plugins: tuple[toolchain.PytestPluginIdentity, ...],
) -> CandidateReconciliation:
    if not plugins:
        return CandidateReconciliation("PASS")
    if project_runtime is None:
        return CandidateReconciliation("UNKNOWN", "project_runtime_required")
    with tempfile.TemporaryDirectory(prefix="specfact-pytest-plugin-preflight-") as root:
        raw = _execute_capsule_member(
            CapsuleMemberExecutionRequest(
                runtime=runtime,
                member="targeted-pytest-plugin-preflight",
                invocation_id=str(uuid4()),
                snapshot_root=Path(root),
                files=[],
                options=ReviewOptions(no_tests=False),
                adapter_argv=(_pytest_plugin_preflight_manifest(plugins),),
                project_runtime_root=project_runtime.root,
            )
        )
    if raw.get("evidence_outcome") != "PASS":
        return CandidateReconciliation("UNKNOWN", "pytest_plugin_capability_mismatch")
    return CandidateReconciliation("PASS")


def _trusted_policy_bundle(resolution: object) -> object | None:
    policy_bundle = getattr(resolution, "policy_bundle", None)
    if policy_bundle is not None or getattr(resolution, "assurance_kind", "") != "index":
        return policy_bundle
    base_snapshot = getattr(resolution, "base_snapshot", None)
    return None if base_snapshot is None else base_snapshot


def _prepare_immutable_pytest_inventory(
    resolution: object,
    options: ReviewOptions,
    runtime: CapsuleRuntime,
    project_runtime: toolchain.ProjectRuntimeMaterialization | None,
    pytest_plugins: tuple[toolchain.PytestPluginIdentity, ...],
) -> tuple[ImmutablePytestInventory | None, str]:
    plugin_preflight = _preflight_project_runtime_pytest_plugins(runtime, project_runtime, pytest_plugins)
    if plugin_preflight.status != "PASS":
        return None, plugin_preflight.reason
    try:
        inventory = _reconcile_immutable_pytest_inventory(
            resolution,
            options=options,
            project_runtime_root=cast(Path | None, getattr(project_runtime, "root", None)),
        )
    except (OSError, TypeError, ValueError, configparser.Error, tomllib.TOMLDecodeError) as exc:
        return None, f"pytest_config_ambiguous:{exc}"
    if inventory.reconciliation.status != "PASS":
        return None, inventory.reconciliation.reason
    return inventory, ""


@dataclass(frozen=True)
class _BoundSnapshotRun:
    root: Path
    files: list[Path]
    bindings: SnapshotPolicyBindings


def _run_bound_snapshot_pair(
    runtime: CapsuleRuntime,
    options: ReviewOptions,
    project_runtime_root: Path | None,
    base: _BoundSnapshotRun,
    head: _BoundSnapshotRun,
    *,
    scope_paths: tuple[str, ...],
) -> tuple[CapsuleSnapshotResult, CapsuleSnapshotResult]:
    with ExitStack() as cleanup:
        for root in (*base.bindings.cleanup_roots, *head.bindings.cleanup_roots):
            cleanup.callback(shutil.rmtree, root, ignore_errors=True)
        base_result, head_result = tuple(
            _run_capsule_snapshot(
                runtime,
                snapshot_root=side.root,
                files=side.files,
                options=options,
                config_roots=side.bindings.config_roots,
                member_argv=side.bindings.member_argv,
                project_runtime_root=project_runtime_root,
                scope_paths=scope_paths,
            )
            for side in (base, head)
        )
    return base_result, head_result


def run_immutable_scope_review(
    resolution: object,
    *,
    options: ReviewOptions,
    scope_evidence: dict[str, object],
) -> ReviewReport:
    """Execute both materialized sides through fresh member sandboxes."""

    project_runtime, pytest_plugins, reason = _materialize_claimed_project_runtime(resolution)
    if reason:
        return _unknown_capsule_report(reason, options=options, scope_evidence=scope_evidence)
    runtime_kwargs = {} if project_runtime is None else {"project_runtime_identity": project_runtime.identity}
    runtime, reason = _prepare_capsule_runtime(**runtime_kwargs)
    if runtime is None:
        return _unknown_capsule_report(reason, options=options, scope_evidence=scope_evidence)
    try:
        return _run_immutable_scope_review_with_runtime(
            resolution,
            options=options,
            scope_evidence=scope_evidence,
            runtime=runtime,
            project_runtime=project_runtime,
            pytest_plugins=pytest_plugins,
        )
    finally:
        _cleanup_capsule_runtime(runtime)


def _run_immutable_scope_review_with_runtime(
    resolution: object,
    *,
    options: ReviewOptions,
    scope_evidence: dict[str, object],
    runtime: CapsuleRuntime,
    project_runtime: toolchain.ProjectRuntimeMaterialization | None,
    pytest_plugins: tuple[toolchain.PytestPluginIdentity, ...],
) -> ReviewReport:
    base_snapshot = getattr(resolution, "base_snapshot", None)
    head_snapshot = getattr(resolution, "head_snapshot", None)
    if base_snapshot is None or head_snapshot is None:
        return _unknown_capsule_report(
            "immutable_snapshot_missing",
            options=options,
            scope_evidence=scope_evidence,
        )
    pytest_inventory, reason = _prepare_immutable_pytest_inventory(
        resolution,
        options,
        runtime,
        project_runtime,
        pytest_plugins,
    )
    if pytest_inventory is None:
        return _unknown_capsule_report(
            reason,
            options=options,
            scope_evidence=scope_evidence,
        )
    policy_bundle = _trusted_policy_bundle(resolution)
    try:
        base_files = _snapshot_python_files(base_snapshot, resolution)
        head_files = _snapshot_python_files(head_snapshot, resolution)
        base_bindings = _with_pytest_inventory(
            _snapshot_policy_bindings(
                policy_bundle,
                snapshot_root=base_snapshot.root,
                files=base_files,
            ),
            pytest_inventory.base,
            pytest_plugins=pytest_plugins,
        )
        head_bindings = _with_pytest_inventory(
            _snapshot_policy_bindings(
                policy_bundle,
                snapshot_root=head_snapshot.root,
                files=head_files,
            ),
            pytest_inventory.head,
            pytest_plugins=pytest_plugins,
        )
    except (OSError, TypeError, ValueError) as exc:
        return _unknown_capsule_report(
            f"target_policy_projection_failed:{exc}",
            options=options,
            scope_evidence=scope_evidence,
        )
    base, head = _run_bound_snapshot_pair(
        runtime,
        options,
        cast(Path | None, getattr(project_runtime, "root", None)),
        _BoundSnapshotRun(base_snapshot.root, base_files, base_bindings),
        _BoundSnapshotRun(head_snapshot.root, head_files, head_bindings),
        scope_paths=cast(tuple[str, ...], resolution.selected_paths),
    )
    combined, classified_findings = _classify_range_findings(resolution, base, head)
    return _capsule_report(
        combined,
        classified_findings,
        options=options,
        scope_evidence=scope_evidence,
    )


def _collect_tool_findings(
    files: list[Path],
    *,
    bug_hunt: bool,
    progress_callback: Callable[[str], None] | None,
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for description, runner in _tool_steps(bug_hunt=bug_hunt):
        if progress_callback is not None:
            progress_callback(description)
        findings.extend(runner(files))
    return findings


def _collect_tdd_findings(
    files: list[Path],
    *,
    no_tests: bool,
    progress_callback: Callable[[str], None] | None,
) -> tuple[list[ReviewFinding], bool]:
    if no_tests:
        return [], False
    if progress_callback is not None:
        progress_callback("Running targeted tests and coverage...")
    findings, coverage_by_source = _evaluate_tdd_gate(files)
    coverage_90_plus = bool(coverage_by_source) and all(percent >= 90.0 for percent in coverage_by_source.values())
    return findings, coverage_90_plus


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, ReviewReport), "result must be a ReviewReport")
def run_review(
    files: list[Path],
    options: ReviewOptions | None = None,
    **overrides: object,
) -> ReviewReport:
    """Run all configured review runners and build the governed report."""
    review_options = _review_options_from_kwargs(options, overrides)
    findings = _collect_tool_findings(
        files,
        bug_hunt=review_options.bug_hunt,
        progress_callback=review_options.progress_callback,
    )
    tdd_findings, coverage_90_plus = _collect_tdd_findings(
        files,
        no_tests=review_options.no_tests,
        progress_callback=review_options.progress_callback,
    )
    findings.extend(tdd_findings)

    findings.extend(_checklist_findings())

    if not review_options.include_noise:
        findings = _suppress_known_noise(findings)

    findings = _filter_findings_by_review_level(findings, review_options.review_level)
    findings = _filter_findings_by_focus(findings, review_options.focus)
    cleanup_forecast: CleanupForecast | None = None
    if review_options.focus == "simplify":
        findings = _enrich_cleanup_findings(findings)
        cleanup_forecast = build_cleanup_forecast(findings, files)

    score = score_review(
        findings=findings,
        zero_loc_violations=not any(finding.tool == "ruff" and finding.rule == "E501" for finding in findings),
        zero_complexity_violations=not any(finding.tool == "radon" for finding in findings),
        all_apis_have_icontract=not any(finding.rule == "MISSING_ICONTRACT" for finding in findings),
        coverage_90_plus=coverage_90_plus,
        no_new_suppressions=_has_no_suppressions(files),
        simplification_score_neutral=review_options.focus == "simplify",
    )
    report = ReviewReport(
        run_id=f"review-{uuid4()}",
        score=score.score,
        findings=findings,
        summary=_summary_for_findings(findings),
        cleanup_forecast=cleanup_forecast,
    )
    report = _with_enforcement(report, mode=review_options.review_mode, files=files)
    if (
        review_options.focus == "simplify"
        and review_options.review_mode == "full"
        and report.simplification_summary is not None
        and report.simplification_summary.blocking_simplification_count > 0
    ):
        return report.model_copy(update={"overall_verdict": "FAIL", "ci_exit_code": 1})
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("capsule runner requires one sealed request path")
    _capsule_process_request(Path(sys.argv[1]))
