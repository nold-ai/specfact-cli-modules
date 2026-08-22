"""Orchestration helpers for structured code-review runs."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from functools import lru_cache, partial
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import normalize_path_variants, tool_error
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
ReviewFocus = Literal["simplify"]
ReviewEnforcementMode = Literal["full", "changed", "shadow"]


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
        if execution == "error" or version != _C14_ANALYZER_VERSIONS[member_id]:
            outcome = "UNKNOWN"
        required_unknown |= outcome == "UNKNOWN"
        known_fail |= outcome == "FAIL"
        members.append(AnalyzerEvidence(member_id, execution, outcome, version, str(raw.get("diagnostic", ""))))
    assurance = "FAIL" if known_fail else "UNKNOWN" if required_unknown else "PASS"
    return ProfileEvidenceReport(tuple(members), assurance, "PASS" if assurance == "PASS" else "FAIL", required_unknown)


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
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)


def _test_selectors(
    path: Path,
    relative: str,
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> tuple[str, ...]:
    try:
        tree = ast.parse(path.read_bytes())
    except (OSError, SyntaxError):
        return ()
    selectors: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            fnmatch.fnmatch(node.name, pattern) for pattern in function_patterns
        ):
            selectors.append(f"{relative}::{node.name}")
        if isinstance(node, ast.ClassDef) and any(fnmatch.fnmatch(node.name, pattern) for pattern in class_patterns):
            selectors.extend(
                f"{relative}::{node.name}::{child.name}"
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and any(fnmatch.fnmatch(child.name, pattern) for pattern in function_patterns)
            )
    return tuple(selectors)


def _collect_pytest_selectors(
    snapshot_root: Path,
    roots: tuple[str, ...],
    file_patterns: tuple[str, ...],
    function_patterns: tuple[str, ...],
    class_patterns: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        selector
        for root in roots
        for path in sorted((snapshot_root / root).rglob("*.py"))
        if _matches_python_file(path, file_patterns)
        for selector in _test_selectors(
            path,
            path.relative_to(snapshot_root).as_posix(),
            function_patterns,
            class_patterns,
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
        if any(path == root or path.startswith(f"{root}/") for root in roots)
        and _matches_python_file(Path(path), file_patterns)
    }


def plan_complete_pytest_suite(
    snapshot_root: Path,
    policy: dict[str, object],
    *,
    changed_paths: tuple[str, ...],
    deleted_paths: tuple[str, ...] = (),
) -> PytestSuitePlan:
    del deleted_paths
    roots = tuple(str(value) for value in cast(list[object], policy.get("testpaths", ["tests"])))
    file_patterns = tuple(str(value) for value in cast(list[object], policy.get("python_files", ["test_*.py"])))
    class_patterns = tuple(str(value) for value in cast(list[object], policy.get("python_classes", ["Test*"])))
    function_patterns = tuple(str(value) for value in cast(list[object], policy.get("python_functions", ["test_*"])))
    selectors = _collect_pytest_selectors(
        snapshot_root,
        roots,
        file_patterns,
        function_patterns,
        class_patterns,
    )
    changed_candidates = _changed_pytest_candidates(changed_paths, roots, file_patterns)
    collected_paths = {selector.split("::", maxsplit=1)[0] for selector in selectors}
    if changed_candidates - collected_paths:
        return PytestSuitePlan(selectors, False, "UNKNOWN", "uncollected_changed_test")
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
    below_root = any(path == root or path.startswith(f"{root}/") for root in roots)
    matches_test_pattern = _matches_python_file(Path(path), patterns)
    if below_root:
        kind = "test_candidate" if matches_test_pattern else "test_support"
    else:
        kind = "test_candidate_outside_root" if matches_test_pattern else "test_support"
    return PytestInputRole(kind, ("path", "testpaths", "python_files", "pytest_version"))


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
        raw = cast(list[object], config.get(key, policy.get(key, [])))
        projected: list[str] = []
        for value in raw:
            relative = Path(str(value))
            if relative.is_absolute() or ".." in relative.parts:
                return PytestProjection("UNKNOWN", {}, (), logical_digest, "unbound_read_path")
            projected.append(str(snapshot_root / relative))
        if projected:
            values[key] = projected
    for key in ("cache_dir", "log_file"):
        if key not in config:
            continue
        destination = output_root / key.replace("_", "-")
        values[key] = str(destination)
        writable.append(destination)
    return PytestProjection("PASS", values, tuple(writable), logical_digest)


def reconcile_pytest_outcomes(
    *, observer: tuple[dict[str, object], ...], junit: tuple[dict[str, object], ...], process_exit: int
) -> PytestOutcomeResult:
    call_records = tuple(record for record in observer if record.get("phase") == "call")

    def observed_kind(record: dict[str, object]) -> str:
        if record.get("wasxfail"):
            return "XPASS" if record.get("passed") else "XFAIL"
        if record.get("skipped"):
            return "SKIPPED"
        return "PASS" if record.get("passed") else "FAILED"

    outcomes = tuple(PytestObservedOutcome(observed_kind(record)) for record in call_records)
    expected_junit = {"PASS": "passed", "XPASS": "passed", "FAILED": "failed", "XFAIL": "skipped", "SKIPPED": "skipped"}
    junit_by_node = {str(record.get("nodeid", "")): str(record.get("outcome", "")) for record in junit}
    signals_match = len(junit_by_node) == len(call_records) and all(
        junit_by_node.get(str(record.get("nodeid", ""))) == expected_junit[outcome.kind]
        for record, outcome in zip(call_records, outcomes, strict=True)
    )
    process_matches = (process_exit != 0) == any(outcome.kind == "FAILED" for outcome in outcomes)
    if not signals_match or not process_matches:
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
            if key in values:
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


def _run_pytest_with_coverage(test_files: list[Path]) -> tuple[subprocess.CompletedProcess[str], Path]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as coverage_file:
        coverage_path = Path(coverage_file.name)

    test_targets = _pytest_targets(test_files)
    source_root = str(_SOURCE_ROOT.resolve())
    repo_root = str(Path.cwd().resolve())
    command = [
        _pytest_python_executable(),
        "-c",
        (
            "import pathlib, sys, pytest; "
            f"sys.path[:0] = [{source_root!r}, {repo_root!r}]; "
            "import specfact_code_review; "
            "raise SystemExit(pytest.main(sys.argv[1:]))"
        ),
        "--import-mode=importlib",
        "--cov",
        str(_PACKAGE_ROOT),
        "--cov-fail-under=0",
        f"--cov-report=json:{coverage_path}",
        *(str(test_target) for test_target in test_targets),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=_TARGETED_TEST_TIMEOUT,
        env=_pytest_env(),
    )
    return result, coverage_path


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
    changed_lines = _changed_lines_from_git(files)
    blocking_changed = [
        finding
        for finding in report.findings
        if finding.is_blocking() and _finding_targets_changed_line(finding, changed_lines)
    ]
    if blocking_changed:
        summary = f"Changed enforcement blocks on {len(blocking_changed)} blocking finding(s) on changed lines."
        return report.model_copy(
            update={"ci_exit_code": 1, "enforcement_mode": "changed", "enforcement_summary": summary}
        )
    legacy_blocking = sum(finding.is_blocking() for finding in report.findings)
    summary = (
        "Changed enforcement found no blocking findings on changed lines."
        if legacy_blocking == 0
        else f"Changed enforcement found no blocking findings on changed lines; {legacy_blocking} legacy blocking finding(s) remain as evidence."
    )
    verdict = "PASS" if not report.findings else "PASS_WITH_ADVISORY"
    return report.model_copy(
        update={
            "overall_verdict": verdict,
            "ci_exit_code": 0,
            "enforcement_mode": "changed",
            "enforcement_summary": summary,
        }
    )


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
) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    findings: list[ReviewFinding] = []
    coverage_by_source: dict[str, float] = {}
    for source_file in source_files:
        percent_covered = _coverage_for_source(source_file, coverage_payload)
        if percent_covered is None:
            if source_file.name == "__init__.py" and _is_empty_init_file(source_file):
                continue  # Exempt empty __init__.py files
            if _is_coverage_omitted_init_by_project_policy(source_file):
                continue
            return [
                tool_error(
                    tool="pytest",
                    file_path=source_file,
                    message=f"Coverage data missing for {source_file}",
                )
            ], None
        coverage_by_source[str(source_file)] = percent_covered
        if percent_covered >= _COVERAGE_THRESHOLD:
            continue
        findings.append(
            ReviewFinding(
                category="testing",
                severity="warning",
                tool="pytest",
                rule="TEST_COVERAGE_LOW",
                file=str(source_file),
                line=1,
                message=(
                    f"Coverage for {source_file} is {percent_covered:.1f}%, below required {_COVERAGE_THRESHOLD:.1f}%."
                ),
                fixable=False,
            )
        )
    return findings, coverage_by_source


def _evaluate_tdd_gate(files: list[Path]) -> tuple[list[ReviewFinding], dict[str, float] | None]:
    """Validate tests and return findings plus per-source coverage when available."""
    source_files, test_files, findings = _collect_tdd_inputs(files)
    if not source_files:
        return [], None
    if findings:
        return findings, None

    pytest_skip = skip_if_pytest_unavailable(source_files[0])
    if pytest_skip:
        return pytest_skip, None

    try:
        test_result, coverage_path = _run_pytest_with_coverage(test_files)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return [
            tool_error(
                tool="pytest",
                file_path=source_files[0],
                message=f"Unable to execute targeted tests: {exc}",
            )
        ], None

    if test_result.returncode != 0:
        return [
            ReviewFinding(
                category="testing",
                severity="error",
                tool="pytest",
                rule="TEST_FAILURE",
                file=str(source_files[0]),
                line=1,
                message="Targeted tests failed for the reviewed source files.",
                fixable=False,
            )
        ], None

    try:
        coverage_payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            tool_error(
                tool="pytest",
                file_path=source_files[0],
                message=f"Unable to read coverage report: {exc}",
            )
        ], None
    finally:
        coverage_path.unlink(missing_ok=True)

    return _coverage_findings(source_files, coverage_payload)


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
