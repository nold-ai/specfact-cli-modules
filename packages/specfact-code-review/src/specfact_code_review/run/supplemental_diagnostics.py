"""Bounded, opt-in observations for one immutable public diagnostic experiment."""

from __future__ import annotations

import ast
import contextlib
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from specfact_code_review.run.findings import ReviewFinding, ReviewReport


OUTPUT_ENV = "SPECFACT_SUPPLEMENTAL_DIAGNOSTIC_OUTPUT"
MAX_RECORDS = 80
MAX_BYTES = 65536
MAX_SOURCE_BYTES = 1 << 20
EXPECTED_TREES = ("0ef24f43e4cf4fe13d7b3d95e62165a4d2bbafc6", "acea0127e0ed3472c3439a6aa87cc4353eaa18c5")
EXPECTED_COMMITS = ("593656f675eaf4954b609aca51aa6504367dc02e", "5b451ec066e0ea5cbd8a97ef3b59d915ae54fe5b")
MEMBERS = (
    "ruff",
    "radon",
    "semgrep-clean",
    "ai-bloat-ast",
    "ast-clean-code",
    "basedpyright",
    "pylint",
    "contracts",
    "semgrep-bugs",
    "targeted-pytest-coverage",
)
OUTCOMES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}
REASONS = {
    "snapshot_member_incomplete",
    "differential_finding_mapping_failed",
    "analyzer_reported_incomplete_execution",
    "finding_correspondence_ambiguous",
    "source_correspondence_unknown",
    "project_range_runtime_identity_mismatch",
}
MEMBER_TOOLS = {
    "ruff": {"ruff"},
    "radon": {"radon", "radon-kiss"},
    "semgrep-clean": {"semgrep"},
    "ai-bloat-ast": {"ast"},
    "ast-clean-code": {"ast"},
    "basedpyright": {"basedpyright"},
    "pylint": {"pylint"},
    "contracts": {"crosshair", "contract_runner"},
    "semgrep-bugs": {"semgrep"},
    "targeted-pytest-coverage": {"pytest"},
}
ERROR_RULES = {
    "crosshair": {"tool_error", "CROSSHAIR_INCOMPLETE_EVIDENCE"},
    "pytest": {"tool_error", "TEST_OUTCOME_NOT_PASS", "TEST_COVERAGE_POLICY_FAILED"},
}
PYTEST_CODES = {
    "project_pytest_collection_failed",
    "project_pytest_collection_error",
    "project_pytest_execution_incomplete",
    "project_pytest_unexecuted",
    "project_pytest_coverage_missing",
    "project_pytest_internal_error",
    "project_pytest_configuration_or_collection_failed",
    "project_pytest_failure_without_observed_test",
    "project_pytest_coverage_evidence_unavailable",
    "project_pytest_coverage_controller_observation_missing",
}


def _catalog_rules() -> set[str]:
    catalog = Path(__file__).resolve().parents[1] / ".semgrep/bugs.yaml"
    payload = catalog.read_bytes()
    if len(payload) > 65536:
        return set()
    data = yaml.safe_load(payload)
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list) or len(rules) > 256:
        return set()
    return {
        rule["id"]
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("id"), str) and re.fullmatch(r"[a-z0-9-]{1,100}", rule["id"])
    }


def _function(source: bytes, line: int) -> str:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return "UNAVAILABLE"
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.lineno <= line <= (node.end_lineno or node.lineno)
        and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,79}", node.name)
    ]
    return max(matches, key=lambda node: node.lineno).name if matches else "UNAVAILABLE"


def _location(finding: ReviewFinding, snapshot: Any) -> dict[str, object] | None:
    path = finding.file
    if not re.fullmatch(r"[A-Za-z0-9_./-]{1,240}", path) or ".." in PurePosixPath(path).parts or path.startswith("/"):
        return None
    source = snapshot.contents.get(path)
    entry = snapshot.entries.get(path)
    if (
        not isinstance(source, bytes)
        or len(source) > MAX_SOURCE_BYTES
        or entry is None
        or entry.object_type != "blob"
        or entry.git_mode not in {"100644", "100755"}
    ):
        return None
    blob = b"blob " + str(len(source)).encode() + b"\0" + source
    if hashlib.sha1(blob, usedforsecurity=False).hexdigest() != entry.object_id:
        return None
    if not 1 <= finding.line <= len(source.splitlines()):
        return None
    return {
        "file": path,
        "line": finding.line,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "function": _function(source, finding.line),
    }


def _diagnostic(finding: ReviewFinding) -> str:
    message = finding.message
    if finding.tool == "crosshair" and message.startswith("Unrecognized CrossHair output:"):
        return "crosshair_unrecognized_output"
    if finding.tool == "pylint" and message.startswith("Unable to parse pylint output:") and "timed out" in message:
        return "pylint_timeout_observed"
    if finding.tool == "pytest":
        prefix = message.split(":", 1)[0].split(";", 1)[0]
        if prefix in PYTEST_CODES:
            return prefix
    return "UNAVAILABLE"


def _member_records(report: ReviewReport) -> list[dict[str, str]]:
    evidence = report.analyzer_evidence
    if not isinstance(evidence, list) or len(evidence) > len(MEMBERS):
        return []
    records = []
    seen = set()
    for node in evidence:
        if not isinstance(node, dict) or node.get("id") not in MEMBERS or node["id"] in seen:
            return []
        seen.add(node["id"])
        for side, value in (("combined", node), ("base", node.get("base")), ("head", node.get("head"))):
            if not isinstance(value, dict):
                continue
            outcome = value.get("evidence_outcome")
            reason = value.get("diagnostic")
            records.append(
                {
                    "member": node["id"],
                    "side": side,
                    "outcome": outcome if isinstance(outcome, str) and outcome in OUTCOMES else "UNAVAILABLE",
                    "diagnostic": reason if isinstance(reason, str) and reason in REASONS else "UNAVAILABLE",
                }
            )
    return records


def _finding_key(finding: ReviewFinding) -> tuple[str, str, str, int, str, str, bool]:
    return (
        finding.tool,
        finding.rule,
        finding.file,
        finding.line,
        " ".join(finding.message.split()),
        finding.severity,
        bool(finding.blocking),
    )


def _selected_findings(report: ReviewReport, results: Any) -> list[tuple[str, str, ReviewFinding, str]]:
    introduced = Counter(
        _finding_key(finding)
        for finding in report.findings
        if finding.tool == "semgrep" and finding.differential_state == "introduced"
    )
    selected = []
    for side, result in zip(("base", "head"), results, strict=True):
        for member in MEMBERS:
            for finding in result.findings_by_member.get(member, []):
                key = _finding_key(finding)
                state = "UNAVAILABLE"
                if side == "head" and member == "semgrep-bugs" and introduced[key] > 0:
                    state = "introduced"
                    introduced[key] -= 1
                if finding.category == "tool_error" or finding.tool == "pytest" or state == "introduced":
                    selected.append((side, member, finding, state))
    return selected


def _valid_identity(member: str, finding: ReviewFinding, catalog: set[str]) -> bool:
    if finding.tool not in MEMBER_TOOLS[member]:
        return False
    if member == "semgrep-bugs" and finding.tool == "semgrep" and finding.rule in catalog:
        return True
    return finding.rule in ERROR_RULES.get(finding.tool, {"tool_error"})


def _project_findings(report: ReviewReport, resolution: Any, results: Any) -> tuple[list[dict[str, object]], int]:
    rules = _catalog_rules()
    selected = _selected_findings(report, results)
    records: list[dict[str, object]] = []
    seen = set()
    snapshots = {"base": resolution.base_snapshot, "head": resolution.head_snapshot}
    for side, member, finding, state in selected[:MAX_RECORDS]:
        identity = (side, member, *_finding_key(finding))
        location = _location(finding, snapshots[side])
        if location is None or identity in seen or not _valid_identity(member, finding, rules):
            continue
        seen.add(identity)
        records.append(
            {
                "side": side,
                "member": member,
                "rule": finding.rule,
                "differential_state": state,
                "diagnostic": _diagnostic(finding),
                "location_is_cause": False,
                **location,
            }
        )
    return records, len(selected) - len(records)


def build_sidecar(report: ReviewReport, resolution: Any, results: Any) -> dict[str, Any]:
    """Project existing results without granting them required-gate authority."""
    payload: dict[str, Any] = {
        "schema": "supplemental-diagnostic-v1",
        "purpose": "SUPPLEMENTARY_DIAGNOSTIC_ONLY",
        "status": "UNAVAILABLE",
        "complete": False,
        "findings": [],
        "members": [],
        "omitted_findings": 0,
        "actual_loaded_adapter": "UNAVAILABLE",
        "effective_deadline": "UNAVAILABLE",
        "original_exit_code": report.ci_exit_code,
        "original_assurance": report.assurance_status,
    }
    snapshots = (resolution.base_snapshot, resolution.head_snapshot)
    if tuple(snapshot.tree for snapshot in snapshots) != EXPECTED_TREES or len(results) != 2:
        return payload
    if len(report.findings) > 10000 or any(
        sum(len(items) for items in result.findings_by_member.values()) > 10000 for result in results
    ):
        return payload
    records, omitted = _project_findings(report, resolution, results)
    payload.update(
        status="OBSERVED",
        findings=records,
        omitted_findings=omitted,
        members=_member_records(report),
        base_commit=EXPECTED_COMMITS[0],
        head_commit=EXPECTED_COMMITS[1],
        base_tree=EXPECTED_TREES[0],
        head_tree=EXPECTED_TREES[1],
    )
    # Unclassified private diagnostics intentionally remain incomplete.
    payload["complete"] = (
        omitted == 0
        and len(payload["members"]) == 30
        and all(record["diagnostic"] != "UNAVAILABLE" for record in records)
        and all(
            member["diagnostic"] != "UNAVAILABLE" and member["outcome"] in OUTCOMES for member in payload["members"]
        )
        and all(record["function"] != "UNAVAILABLE" for record in records)
    )
    if len(json.dumps(payload).encode()) > MAX_BYTES:
        payload.update(
            status="UNAVAILABLE", findings=[], members=[], complete=False, omitted_findings=len(records) + omitted
        )
    return payload


def emit_sidecar(report: ReviewReport, resolution: Any, results: Any) -> str:
    """Create a private, non-overwriting observation file when explicitly requested."""
    configured = os.environ.get(OUTPUT_ENV)
    if configured is None:
        return "DISABLED"
    try:
        output = Path(configured)
        if not output.is_absolute() or output.parent.resolve() != output.parent or output.name != "diagnostic.json":
            return "UNAVAILABLE"
        payload = json.dumps(build_sidecar(report, resolution, results), sort_keys=True).encode()
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
    except (OSError, ValueError, TypeError, AttributeError, RecursionError, yaml.YAMLError):
        return "UNAVAILABLE"
    return "WRITTEN"


# This state exists only in the trusted full-review host, never in capsule requests.
PROGRESS_ENV = "SPECFACT_SUPPLEMENTAL_PROGRESS_DIR"
PROGRESS_LIMIT = 16384
TERMINAL_LIMIT = 4096
STAGES = {
    "verified_review_entry",
    "scope_resolved",
    "snapshot_prepare",
    "snapshot_start",
    "member_dispatch",
    "member_return",
    "classification",
    "projection",
}
BINDING_FIELDS = {
    "nonce",
    "producer_commit",
    "payload_sha256",
    "workflow_sha256",
    "supervisor_sha256",
    "base_commit",
    "head_commit",
    "base_tree",
    "head_tree",
    "mode",
}
PRODUCER_MODULES = ("portable_snapshot", "runner", "supplemental_diagnostics")
_PROGRESS: dict[str, Any] | None = None
_STARTED = 0.0


def validate_binding(binding: Any) -> dict[str, str]:
    """Accept only the immutable public experiment and finite cryptographic identities."""
    if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
        raise ValueError("binding_schema")
    if binding["mode"] not in {"full", "smoke"}:
        raise ValueError("binding_mode")
    for key, value in binding.items():
        if key == "mode":
            continue
        length = 40 if key.endswith(("commit", "tree")) else 64
        if not isinstance(value, str) or re.fullmatch(f"[0-9a-f]{{{length}}}", value) is None:
            raise ValueError("binding_identity")
    if (binding["base_commit"], binding["head_commit"]) != EXPECTED_COMMITS or (
        binding["base_tree"],
        binding["head_tree"],
    ) != EXPECTED_TREES:
        raise ValueError("binding_subject")
    return dict(binding)


def _directory_descriptor(directory: Path) -> int:
    import stat

    if not directory.is_absolute() or directory.resolve() != directory:
        raise ValueError("directory_identity")
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(descriptor)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        os.close(descriptor)
        raise ValueError("directory_permissions")
    return descriptor


def atomic_record(directory: Path, name: str, value: dict[str, Any], limit: int) -> None:
    """Replace one complete private record, preserving the old record on failure."""
    if name not in {"binding.json", "progress.json", "terminal.json", "diagnostic-summary.json"}:
        raise ValueError("record_name")
    payload = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    if len(payload) > limit:
        raise ValueError("record_oversized")
    descriptor = _directory_descriptor(directory)
    temporary = name + ".tmp"
    created = False
    try:
        stream_descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor
        )
        created = True
        with os.fdopen(stream_descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Refuse linked destinations rather than silently replacing them.
        try:
            import stat

            if not stat.S_ISREG(os.stat(name, dir_fd=descriptor, follow_symlinks=False).st_mode):
                raise ValueError("record_nonregular")
        except FileNotFoundError:
            pass
        os.replace(temporary, name, src_dir_fd=descriptor, dst_dir_fd=descriptor)
        os.fsync(descriptor)
    finally:
        if created:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=descriptor)
        os.close(descriptor)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("record_duplicate_key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("record_nonfinite")


def read_record(directory: Path, name: str, limit: int) -> dict[str, Any]:
    """Bound bytes before parsing, reject links and changed files, and admit objects only."""
    import stat

    if name not in {"binding.json", "progress.json", "terminal.json", "diagnostic-summary.json"}:
        raise ValueError("record_name")
    descriptor = _directory_descriptor(directory)
    try:
        stream_descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        with os.fdopen(stream_descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > limit:
                raise ValueError("record_oversized")
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or stat.S_IMODE(before.st_mode) != 0o600
            ):
                raise ValueError("record_rejected")
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(data) > limit or (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ino,
            ):
                raise ValueError("record_changed")
    finally:
        os.close(descriptor)
    result = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if not isinstance(result, dict):
        raise ValueError("record_schema")
    return result


def _bounded_integer(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 86400000


def validate_progress(value: dict[str, Any], binding: dict[str, str]) -> None:
    expected = {
        "schema",
        "purpose",
        "binding",
        "sequence",
        "elapsed_ms",
        "stage",
        "side",
        "member",
        "members",
        "producer",
        "complete",
        "actual_loaded_guest_adapter",
        "effective_guest_deadline",
    }
    if (
        set(value) != expected
        or value["schema"] != "supplemental-host-progress-v1"
        or value["purpose"] != "SUPPLEMENTARY_DIAGNOSTIC_ONLY"
        or value["binding"] != validate_binding(binding)
    ):
        raise ValueError("progress_schema")
    if not _bounded_integer(value["sequence"]) or value["sequence"] == 0 or not _bounded_integer(value["elapsed_ms"]):
        raise ValueError("progress_sequence")
    if (
        value["stage"] not in STAGES
        or value["side"] not in {"none", "base", "head"}
        or value["member"] not in {"none", *MEMBERS}
    ):
        raise ValueError("progress_stage")
    if (
        value["complete"] is not False
        or value["actual_loaded_guest_adapter"] != "UNAVAILABLE"
        or value["effective_guest_deadline"] != "UNAVAILABLE"
    ):
        raise ValueError("progress_authority")
    cells = value["members"]
    if not isinstance(cells, dict) or len(cells) > 20:
        raise ValueError("progress_members")
    for key, cell in cells.items():
        if (
            key not in {f"{side}:{member}" for side in ("base", "head") for member in MEMBERS}
            or not isinstance(cell, dict)
            or set(cell) != {"stage", "elapsed_ms"}
            or cell["stage"] not in {"member_dispatch", "member_return"}
            or not _bounded_integer(cell["elapsed_ms"])
            or cell["elapsed_ms"] > value["elapsed_ms"]
        ):
            raise ValueError("progress_cell")
    producer = value["producer"]
    if (
        not isinstance(producer, dict)
        or set(producer) != {"modules", "python", "platform", "environment"}
        or producer["platform"] not in {"linux", "darwin"}
        or producer["environment"] not in {"venv", "base"}
        or not isinstance(producer["python"], str)
        or re.fullmatch(r"3\.[0-9]{1,2}\.[0-9]{1,2}", producer["python"]) is None
    ):
        raise ValueError("producer_identity")
    modules = producer["modules"]
    if (
        not isinstance(modules, dict)
        or set(modules) != {f"src/specfact_code_review/run/{name}.py" for name in PRODUCER_MODULES}
        or any(
            not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None for digest in modules.values()
        )
    ):
        raise ValueError("producer_modules")


def _installed_producer_identity(package: Path, binding: dict[str, str]) -> dict[str, Any]:
    import importlib
    import sys

    from specfact_cli.registry.module_installer import _module_artifact_payload_stable

    expected_package = Path.home() / ".specfact/modules/specfact-code-review"
    if package != expected_package or package.resolve() != package or package.is_symlink():
        raise ValueError("producer_not_installed")
    if hashlib.sha256(_module_artifact_payload_stable(package)).hexdigest() != binding["payload_sha256"]:
        raise ValueError("producer_payload_mismatch")
    modules = {}
    for name in PRODUCER_MODULES:
        module = importlib.import_module(f"specfact_code_review.run.{name}")
        relative = f"src/specfact_code_review/run/{name}.py"
        actual = Path(module.__file__ or "")
        if actual != package / relative or actual.resolve() != actual:
            raise ValueError("producer_origin_mismatch")
        modules[relative] = hashlib.sha256(actual.read_bytes()).hexdigest()
    return {
        "modules": modules,
        "python": ".".join(map(str, sys.version_info[:3])),
        "platform": sys.platform,
        "environment": "venv" if sys.prefix != sys.base_prefix else "base",
    }


def verified_review_entry(package: Path, binding: dict[str, str]) -> None:
    """Verify actual loaded installed bytes before the full-review app is invoked."""
    import time

    global _PROGRESS, _STARTED
    _PROGRESS = None
    configured = os.environ.get(PROGRESS_ENV)
    if configured is None:
        return
    binding = validate_binding(binding)
    producer = _installed_producer_identity(package, binding)
    _STARTED = time.monotonic()
    value = {
        "schema": "supplemental-host-progress-v1",
        "purpose": "SUPPLEMENTARY_DIAGNOSTIC_ONLY",
        "binding": binding,
        "sequence": 1,
        "elapsed_ms": 0,
        "stage": "verified_review_entry",
        "side": "none",
        "member": "none",
        "members": {},
        "producer": producer,
        "complete": False,
        "actual_loaded_guest_adapter": "UNAVAILABLE",
        "effective_guest_deadline": "UNAVAILABLE",
    }
    validate_progress(value, binding)
    atomic_record(Path(configured), "progress.json", value, PROGRESS_LIMIT)
    _PROGRESS = value


def host_checkpoint(stage: str, *, side: str | None = None, member: str = "none") -> str:
    """Persist finite host observations without changing review results on failure."""
    import copy
    import time

    global _PROGRESS
    configured = os.environ.get(PROGRESS_ENV)
    if configured is None or _PROGRESS is None:
        return "DISABLED" if configured is None else "UNAVAILABLE"
    try:
        previous = read_record(Path(configured), "progress.json", PROGRESS_LIMIT)
        validate_progress(previous, _PROGRESS["binding"])
        if previous != _PROGRESS:
            raise ValueError("progress_sequence_mismatch")
        value = copy.deepcopy(_PROGRESS)
        value.update(
            sequence=value["sequence"] + 1,
            elapsed_ms=int((time.monotonic() - _STARTED) * 1000),
            stage=stage,
            side=side or value["side"],
            member=member,
        )
        if member != "none":
            value["members"][f"{value['side']}:{member}"] = {"stage": stage, "elapsed_ms": value["elapsed_ms"]}
        validate_progress(value, value["binding"])
        atomic_record(Path(configured), "progress.json", value, PROGRESS_LIMIT)
        _PROGRESS = value
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        _PROGRESS = None
        return "UNAVAILABLE"
    return "WRITTEN"


def validate_terminal(value: dict[str, Any], binding: dict[str, str]) -> None:
    if (
        set(value)
        != {
            "schema",
            "purpose",
            "binding",
            "category",
            "child_returncode",
            "elapsed_ms",
            "cleanup",
            "capsule_process_observed",
        }
        or value["schema"] != "supplemental-host-terminal-v1"
        or value["purpose"] != "SUPPLEMENTARY_DIAGNOSTIC_ONLY"
        or value["binding"] != validate_binding(binding)
    ):
        raise ValueError("terminal_schema")
    if (
        value["category"] not in {"child_exit", "wrapper_expired", "signal_termination", "supervisor_error"}
        or value["cleanup"] not in {"complete", "incomplete", "pending"}
        or not _bounded_integer(value["elapsed_ms"])
    ):
        raise ValueError("terminal_category")
    if type(value["capsule_process_observed"]) is not bool and value["capsule_process_observed"] != "UNAVAILABLE":
        raise ValueError("terminal_capsule_observation")
    code = value["child_returncode"]
    if code is not None and (type(code) is not int or not -128 <= code <= 255):
        raise ValueError("terminal_returncode")
    category = value["category"]
    if category == "child_exit" and (code is None or code < 0):
        raise ValueError("terminal_exit_category")
    if category == "signal_termination" and (code is None or code >= 0):
        raise ValueError("terminal_signal_category")
    if category in {"wrapper_expired", "supervisor_error"} and code is not None:
        raise ValueError("terminal_nonexit_category")


def _safe_record_inventory(descriptor: int) -> bool:
    import stat

    complete = {"binding.json", "progress.json", "terminal.json", "diagnostic-summary.json"}
    temporary = {
        "progress.json.tmp": PROGRESS_LIMIT,
        "terminal.json.tmp": TERMINAL_LIMIT,
        "diagnostic-summary.json.tmp": MAX_BYTES,
    }
    for name in os.listdir(descriptor):
        if name in complete:
            continue
        if name not in temporary:
            return False
        try:
            info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > temporary[name]
        ):
            return False
    return True


def collect_host_summary(directory: Path, binding: dict[str, str]) -> dict[str, Any]:
    """Independently admit bounded owner records; missing observations are not zero findings."""
    binding = validate_binding(binding)
    summary: dict[str, Any] = {
        "purpose": "SUPPLEMENTARY_DIAGNOSTIC_ONLY",
        "binding": binding,
        "complete": False,
        "progress": "UNAVAILABLE",
        "terminal": "UNAVAILABLE",
        "progress_state": "missing",
        "terminal_state": "missing",
        "actual_loaded_guest_adapter": "UNAVAILABLE",
        "effective_guest_deadline": "UNAVAILABLE",
    }
    descriptor = _directory_descriptor(directory)
    try:
        if not _safe_record_inventory(descriptor):
            summary.update(progress_state="rejected", terminal_state="rejected")
            return summary
    finally:
        os.close(descriptor)
    for name, limit, validate in (
        ("progress", PROGRESS_LIMIT, validate_progress),
        ("terminal", TERMINAL_LIMIT, validate_terminal),
    ):
        try:
            value = read_record(directory, name + ".json", limit)
            validate(value, binding)
            if name == "progress" and value["producer"] != _installed_producer_identity(
                Path.home() / ".specfact/modules/specfact-code-review", binding
            ):
                raise ValueError("progress_producer_mismatch")
            summary[name] = value
            summary[name + "_state"] = "observed"
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            summary[name + "_state"] = "malformed"
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            summary[name + "_state"] = "oversized" if str(error) == "record_oversized" else "rejected"
    return summary
