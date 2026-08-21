"""Semgrep runner for governed code-review findings."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.tools.tool_availability import skip_if_tool_missing


SEMGREP_RULE_CATEGORY = {
    "get-modify-same-method": "clean_code",
    "unguarded-nested-access": "clean_code",
    "cross-layer-call": "architecture",
    "module-level-network": "architecture",
    "print-in-src": "architecture",
    "banned-generic-public-names": "naming",
    "swallowed-exception-pattern": "clean_code",
    "ai-bloat.manual-loop-comprehension": "ai_bloat",
    "ai-bloat.passthrough-lambda": "ai_bloat",
    "ai-bloat.identity-try-except": "ai_bloat",
    "ai-bloat.none-then-none": "ai_bloat",
    "ai-bloat.single-call-wrapper": "ai_bloat",
}
SEMGREP_TIMEOUT_SECONDS = 90
SEMGREP_RETRY_ATTEMPTS = 2
_SEMGREP_STDERR_SNIP_MAX = 4000
_MAX_CONFIG_PARENT_WALK = 32
SemgrepCategory = Literal["clean_code", "architecture", "naming", "ai_bloat"]
BugSemgrepCategory = Literal["security", "clean_code"]


@dataclass(frozen=True)
class SemgrepReconciliation:
    """Closed Semgrep input/result reconciliation decision."""

    status: Literal["PASS", "UNKNOWN"]
    reason: str = ""


@dataclass(frozen=True)
class SemgrepSnapshotInvocation:
    """Controller-owned Semgrep launch inputs and deterministic probe rules."""

    argv: tuple[str, ...]
    expected_rules: tuple[str, ...]
    suppression_controls_disabled: bool


def reconcile_scanned_paths(
    *, eligible: tuple[str, ...], scanned: tuple[str, ...], skipped: tuple[str, ...]
) -> SemgrepReconciliation:
    """Require one pass to report every eligible input exactly once and no skip."""

    if skipped:
        return SemgrepReconciliation("UNKNOWN", "semgrep_skipped_eligible_input")
    if len(scanned) != len(set(scanned)) or tuple(sorted(scanned)) != tuple(sorted(set(eligible))):
        return SemgrepReconciliation("UNKNOWN", "semgrep_scanned_input_mismatch")
    return SemgrepReconciliation("PASS")


def validate_rule_pack(payload: dict[str, object]) -> SemgrepReconciliation:
    """Reject rule-local include/exclude controls before Semgrep launch."""

    rules = payload.get("rules")
    if not isinstance(rules, list):
        return SemgrepReconciliation("UNKNOWN", "semgrep_rule_pack_invalid")
    for rule in rules:
        if not isinstance(rule, dict):
            return SemgrepReconciliation("UNKNOWN", "semgrep_rule_pack_invalid")
        paths = rule.get("paths")
        if isinstance(paths, dict) and any(paths.get(control) for control in ("include", "exclude")):
            return SemgrepReconciliation("UNKNOWN", "semgrep_rule_target_narrowing")
    return SemgrepReconciliation("PASS")


def reconcile_passes(*, eligible: tuple[str, ...], passes: tuple[dict[str, object], ...]) -> SemgrepReconciliation:
    """Require each mandatory pass—not merely their union—to cover every input."""

    pass_ids: set[str] = set()
    for pass_result in passes:
        pass_id = pass_result.get("id")
        scanned = pass_result.get("scanned")
        skipped = pass_result.get("skipped")
        if (
            not isinstance(pass_id, str)
            or pass_id in pass_ids
            or not isinstance(scanned, tuple)
            or not all(isinstance(path, str) for path in scanned)
            or not isinstance(skipped, tuple)
            or not all(isinstance(path, str) for path in skipped)
        ):
            return SemgrepReconciliation("UNKNOWN", "semgrep_pass_evidence_invalid")
        pass_ids.add(pass_id)
        result = reconcile_scanned_paths(eligible=eligible, scanned=scanned, skipped=skipped)
        if result.status != "PASS":
            return result
    return SemgrepReconciliation("PASS")


def build_snapshot_invocation(*, eligible: tuple[str, ...], source: bytes) -> SemgrepSnapshotInvocation:
    """Build a nosem-disabled launch and deterministic security-rule probe manifest."""

    expected_rules: set[str] = set()
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        tree = ast.Module(body=[], type_ignores=[])
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            expected_rules.add("python.lang.security.audit.eval-detected")
    return SemgrepSnapshotInvocation(
        argv=("semgrep", "--disable-nosem", "--json", *tuple(sorted(set(eligible)))),
        expected_rules=tuple(sorted(expected_rules)),
        suppression_controls_disabled=True,
    )


@dataclass(frozen=True)
class _AiBloatGuidance:
    guidance_kind: Literal["safe_mechanical", "needs_tests", "design_judgment", "preserve"]
    recommended_action: Literal["remove", "inline", "collapse", "deduplicate", "make_required", "keep", "inspect"]
    clean_code_principle: Literal["kiss", "dry", "yagni", "contracts", "api_stability", "readability"]
    rationale: str
    safety_checks: list[str]


AI_BLOAT_GUIDANCE: dict[str, _AiBloatGuidance] = {
    "ai-bloat.manual-loop-comprehension": _AiBloatGuidance(
        guidance_kind="needs_tests",
        recommended_action="collapse",
        clean_code_principle="kiss",
        rationale="The loop appears structural, but iterator behavior and ordering need test coverage.",
        safety_checks=["targeted tests cover ordering and empty input", "no side effects are hidden in the loop"],
    ),
    "ai-bloat.passthrough-lambda": _AiBloatGuidance(
        guidance_kind="design_judgment",
        recommended_action="inspect",
        clean_code_principle="readability",
        rationale="A pass-through lambda can be noise, but it may also document callback shape at a boundary.",
        safety_checks=["confirm the callable signature is unchanged", "keep if the lambda documents API intent"],
    ),
    "ai-bloat.identity-try-except": _AiBloatGuidance(
        guidance_kind="safe_mechanical",
        recommended_action="remove",
        clean_code_principle="kiss",
        rationale="The handler immediately re-raises without adding context or cleanup.",
        safety_checks=["handler contains only a bare raise", "try block has no else or finally body"],
    ),
    "ai-bloat.none-then-none": _AiBloatGuidance(
        guidance_kind="needs_tests",
        recommended_action="collapse",
        clean_code_principle="kiss",
        rationale="The None branch may be redundant, but None semantics often encode a contract boundary.",
        safety_checks=["tests cover None input", "callers do not depend on early-return timing"],
    ),
    "ai-bloat.single-call-wrapper": _AiBloatGuidance(
        guidance_kind="design_judgment",
        recommended_action="inspect",
        clean_code_principle="dry",
        rationale="A single-call wrapper may be bloat or a deliberate compatibility boundary.",
        safety_checks=["confirm whether the wrapper is public API", "keep wrappers that encode compatibility"],
    ),
}

BUG_RULE_CATEGORY: dict[str, BugSemgrepCategory] = {
    "specfact-bugs-eval-exec": "security",
    "specfact-bugs-os-system": "security",
    "specfact-bugs-pickle-loads": "security",
    "specfact-bugs-yaml-unsafe": "security",
    "specfact-bugs-hardcoded-password": "security",
    "specfact-bugs-useless-comparison": "clean_code",
}


def _normalize_path_variants(path_value: str | Path) -> set[str]:
    path = Path(path_value)
    variants = {
        os.path.normpath(str(path)),
        os.path.normpath(path.as_posix()),
    }
    try:
        resolved = path.resolve()
    except OSError:
        return variants
    variants.add(os.path.normpath(str(resolved)))
    variants.add(os.path.normpath(resolved.as_posix()))
    return variants


def _allowed_paths(files: list[Path]) -> set[str]:
    allowed: set[str] = set()
    for file_path in files:
        allowed.update(_normalize_path_variants(file_path))
    return allowed


def _tool_error(file_path: Path, message: str) -> list[ReviewFinding]:
    return [
        ReviewFinding(
            category="tool_error",
            severity="error",
            tool="semgrep",
            rule="tool_error",
            file=str(file_path),
            line=1,
            message=message,
            fixable=False,
        )
    ]


def _normalize_rule_id(rule: str) -> str:
    for suffix in SEMGREP_RULE_CATEGORY:
        if rule == suffix or rule.endswith(f".{suffix}"):
            return suffix
    return rule


def _is_bundle_boundary(directory: Path) -> bool:
    """True when ``directory`` is a sensible workspace root (do not search parents above it)."""
    return (directory / ".git").exists() or (directory / "module-package.yaml").is_file()


@beartype
@require(lambda bundle_root, module_file: bundle_root is None or isinstance(bundle_root, Path))
@require(lambda bundle_root, module_file: module_file is None or isinstance(module_file, Path))
@ensure(lambda result: isinstance(result, Path), "result must be a Path")
def find_semgrep_config(
    *,
    bundle_root: Path | None = None,
    module_file: Path | None = None,
) -> Path:
    """Locate ``.semgrep/clean_code.yaml`` for this package or an explicit bundle root.

    When ``bundle_root`` is set, only ``bundle_root/.semgrep/clean_code.yaml`` is considered.

    Otherwise walk parents of ``module_file`` (default: this module), checking each directory for
    ``.semgrep/clean_code.yaml``. Stop ascending when a bundle boundary is hit (``.git`` or
    ``module-package.yaml``) so unrelated trees (e.g. a stray ``~/.semgrep``) are never used.
    """
    if bundle_root is not None:
        br = bundle_root.resolve()
        candidate = br / ".semgrep" / "clean_code.yaml"
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"Semgrep config not found at {candidate} (bundle_root={br})")

    here = (module_file if module_file is not None else Path(__file__)).resolve()
    for depth, parent in enumerate([here.parent, *here.parents]):
        if depth > _MAX_CONFIG_PARENT_WALK:
            break
        if parent == parent.parent:
            break
        candidate = parent / ".semgrep" / "clean_code.yaml"
        if candidate.is_file():
            return candidate
        if _is_bundle_boundary(parent):
            break
        # Installed wheels live under site-packages; do not walk into lib/, $HOME, or other trees.
        if parent.name == "site-packages":
            break
    raise FileNotFoundError(f"Semgrep config not found (no .semgrep/clean_code.yaml under bundle for {here})")


@beartype
@require(lambda bundle_root, module_file: bundle_root is None or isinstance(bundle_root, Path))
@require(lambda bundle_root, module_file: module_file is None or isinstance(module_file, Path))
@ensure(lambda result: result is None or isinstance(result, Path))
def find_semgrep_bugs_config(
    *,
    bundle_root: Path | None = None,
    module_file: Path | None = None,
) -> Path | None:
    """Locate ``.semgrep/bugs.yaml`` for this package or bundle root; return ``None`` if absent."""
    if bundle_root is not None:
        br = bundle_root.resolve()
        candidate = br / ".semgrep" / "bugs.yaml"
        return candidate if candidate.is_file() else None

    here = (module_file if module_file is not None else Path(__file__)).resolve()
    for depth, parent in enumerate([here.parent, *here.parents]):
        if depth > _MAX_CONFIG_PARENT_WALK:
            break
        if parent == parent.parent:
            break
        candidate = parent / ".semgrep" / "bugs.yaml"
        if candidate.is_file():
            return candidate
        if _is_bundle_boundary(parent):
            break
        if parent.name == "site-packages":
            break
    return None


@beartype
@require(lambda bundle_root, module_file: bundle_root is None or isinstance(bundle_root, Path))
@require(lambda bundle_root, module_file: module_file is None or isinstance(module_file, Path))
@ensure(lambda result: result is None or isinstance(result, Path))
def find_semgrep_ai_bloat_config(
    *,
    bundle_root: Path | None = None,
    module_file: Path | None = None,
) -> Path | None:
    """Locate the optional AI-bloat Semgrep rule pack for this package or bundle root."""
    rel = Path("resources") / "semgrep-rules" / "ai-bloat.yaml"
    if bundle_root is not None:
        candidate = bundle_root.resolve() / rel
        return candidate if candidate.is_file() else None

    here = (module_file if module_file is not None else Path(__file__)).resolve()
    for depth, parent in enumerate([here.parent, *here.parents]):
        if depth > _MAX_CONFIG_PARENT_WALK:
            break
        if parent == parent.parent:
            break
        candidate = parent / rel
        if candidate.is_file():
            return candidate
        if _is_bundle_boundary(parent):
            break
        if parent.name == "site-packages":
            break
    return None


def _run_semgrep_command(
    files: list[Path], *, bundle_root: Path | None, config_file: Path | list[Path]
) -> subprocess.CompletedProcess[str]:
    del bundle_root
    config_files = config_file if isinstance(config_file, list) else [config_file]
    config_args = [arg for path in config_files for arg in ("--config", str(path))]
    with tempfile.TemporaryDirectory(prefix="semgrep-home-") as temp_home:
        semgrep_home = Path(temp_home)
        semgrep_log_dir = semgrep_home / ".semgrep"
        semgrep_config_dir = semgrep_home / ".config"
        semgrep_cache_dir = semgrep_home / ".cache"
        semgrep_log_dir.mkdir(parents=True, exist_ok=True)
        semgrep_config_dir.mkdir(parents=True, exist_ok=True)
        semgrep_cache_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = str(semgrep_home)
        env["XDG_CONFIG_HOME"] = str(semgrep_config_dir)
        env["XDG_CACHE_HOME"] = str(semgrep_cache_dir)
        env["SEMGREP_SETTINGS_FILE"] = str(semgrep_log_dir / "settings.yml")
        env.setdefault("SEMGREP_SEND_METRICS", "off")
        return subprocess.run(
            [
                "semgrep",
                "--disable-version-check",
                "--quiet",
                "--disable-nosem",
                *config_args,
                "--json",
                *(str(file_path) for file_path in files),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=SEMGREP_TIMEOUT_SECONDS,
            env=env,
        )


def _snip_stderr_tail(stderr: str) -> str:
    """Keep the last ``_SEMGREP_STDERR_SNIP_MAX`` chars so the most recent diagnostics stay visible."""
    err_raw = stderr.strip()
    if len(err_raw) <= _SEMGREP_STDERR_SNIP_MAX:
        return err_raw
    return "…" + err_raw[-_SEMGREP_STDERR_SNIP_MAX:]


def _load_semgrep_results(
    files: list[Path], *, bundle_root: Path | None, config_file: Path | list[Path]
) -> list[object]:
    last_error: Exception | None = None
    for _attempt in range(SEMGREP_RETRY_ATTEMPTS):
        try:
            result = _run_semgrep_command(files, bundle_root=bundle_root, config_file=config_file)
            raw_out = result.stdout.strip()
            if not raw_out:
                err_tail = _snip_stderr_tail(result.stderr or "")
                raise ValueError(f"semgrep returned empty stdout (returncode={result.returncode}); stderr={err_tail!r}")
            return _parse_semgrep_results(json.loads(raw_out))
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            last_error = exc
    if last_error is None:
        raise ValueError("semgrep returned no usable results")
    raise last_error


def _parse_semgrep_results(payload: dict[str, object]) -> list[object]:
    if not isinstance(payload, dict):
        raise ValueError("semgrep output must be an object")
    if "results" not in payload:
        raise ValueError("semgrep output missing results key")
    raw_results = payload["results"]
    if not isinstance(raw_results, list):
        raise ValueError("semgrep results must be a list")
    return raw_results


def _category_for_rule(rule: str) -> SemgrepCategory | None:
    category = SEMGREP_RULE_CATEGORY.get(rule)
    if category in {"clean_code", "architecture", "naming", "ai_bloat"}:
        return cast(SemgrepCategory, category)
    return None


def _extract_common_finding_fields(
    item: dict[str, object], *, allowed_paths: set[str]
) -> tuple[str, str, int, str, dict[str, object]] | None:
    filename = item["path"]
    if not isinstance(filename, str):
        raise ValueError("semgrep filename must be a string")
    if _normalize_path_variants(filename).isdisjoint(allowed_paths):
        return None

    raw_rule = item["check_id"]
    if not isinstance(raw_rule, str):
        raise ValueError("semgrep rule must be a string")

    start = item["start"]
    if not isinstance(start, dict):
        raise ValueError("semgrep start location must be an object")
    line = start["line"]
    if not isinstance(line, int):
        raise ValueError("semgrep line must be an integer")

    extra = item["extra"]
    if not isinstance(extra, dict):
        raise ValueError("semgrep extra payload must be an object")
    message = extra["message"]
    if not isinstance(message, str):
        raise ValueError("semgrep message must be a string")

    return filename, raw_rule, line, message, extra


def _finding_from_result(item: dict[str, object], *, allowed_paths: set[str]) -> ReviewFinding | None:
    extracted = _extract_common_finding_fields(item, allowed_paths=allowed_paths)
    if extracted is None:
        return None
    filename, raw_rule, line, message, _extra = extracted
    rule = _normalize_rule_id(raw_rule)
    category = _category_for_rule(rule)
    if category is None:
        return None
    if category == "ai_bloat":
        return _ai_bloat_finding_from_result(rule=rule, filename=filename, line=line, message=message)

    return ReviewFinding(
        category=category,
        severity="warning",
        tool="semgrep",
        rule=rule,
        file=filename,
        line=line,
        message=message,
        fixable=False,
    )


def _ai_bloat_finding_from_result(*, rule: str, filename: str, line: int, message: str) -> ReviewFinding:
    guidance = AI_BLOAT_GUIDANCE[rule]
    return ReviewFinding(
        category="ai_bloat",
        severity="info",
        tool="semgrep",
        rule=rule,
        file=filename,
        line=line,
        message=message,
        fixable=False,
        confidence="high",
        canonical_pattern=rule.removeprefix("ai-bloat."),
        rewrite_hint=message,
        estimated_deletion_lines=1,
        guidance_kind=guidance.guidance_kind,
        recommended_action=guidance.recommended_action,
        clean_code_principle=guidance.clean_code_principle,
        rationale=guidance.rationale,
        safety_checks=guidance.safety_checks,
        action_status="recommended",
    )


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_semgrep(files: list[Path], *, bundle_root: Path | None = None) -> list[ReviewFinding]:
    """Run Semgrep for the provided files and map findings into ReviewFinding records.

    Args:
        files: Paths to scan.
        bundle_root: Optional directory that contains ``.semgrep/clean_code.yaml`` (e.g. extracted
            bundle root). When omitted, config is resolved from this package upward until a bundle
            boundary (``.git`` or ``module-package.yaml``).
    """
    if not files:
        return []

    skipped = skip_if_tool_missing("semgrep", files[0])
    if skipped:
        return skipped

    try:
        config_path = find_semgrep_config(bundle_root=bundle_root)
        config_paths = [config_path]
        ai_bloat_config = find_semgrep_ai_bloat_config(bundle_root=bundle_root)
        if ai_bloat_config is not None:
            config_paths.append(ai_bloat_config)
        raw_results = _load_semgrep_results(files, bundle_root=bundle_root, config_file=config_paths)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return _tool_error(files[0], f"Unable to parse Semgrep output: {exc}")

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    try:
        for item in raw_results:
            _append_semgrep_result(findings, item, allowed_paths=allowed_paths, bug_pass=False)
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(files[0], f"Unable to parse Semgrep finding payload: {exc}")

    return findings


def _append_semgrep_result(
    findings: list[ReviewFinding],
    item: object,
    *,
    allowed_paths: set[str],
    bug_pass: bool,
) -> None:
    if not isinstance(item, dict):
        raise ValueError("semgrep finding must be an object")
    finding = (
        _finding_from_bug_result(item, allowed_paths=allowed_paths)
        if bug_pass
        else _finding_from_result(item, allowed_paths=allowed_paths)
    )
    if finding is not None:
        findings.append(finding)


def _normalize_bug_rule_id(rule: str) -> str:
    for rule_id in BUG_RULE_CATEGORY:
        if rule == rule_id or rule.endswith(f".{rule_id}"):
            return rule_id
    return rule.rsplit(".", 1)[-1]


def _finding_from_bug_result(item: dict[str, object], *, allowed_paths: set[str]) -> ReviewFinding | None:
    extracted = _extract_common_finding_fields(item, allowed_paths=allowed_paths)
    if extracted is None:
        return None
    filename, raw_rule, line, message, extra = extracted
    rule = _normalize_bug_rule_id(raw_rule)
    category = BUG_RULE_CATEGORY.get(rule)
    if category is None:
        return None

    severity_raw = extra.get("severity", "WARNING")
    severity: Literal["error", "warning"] = (
        "error" if isinstance(severity_raw, str) and severity_raw.upper() == "ERROR" else "warning"
    )

    return ReviewFinding(
        category=category,
        severity=severity,
        tool="semgrep",
        rule=rule,
        file=filename,
        line=line,
        message=message,
        fixable=False,
    )


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_semgrep_bugs(files: list[Path], *, bundle_root: Path | None = None) -> list[ReviewFinding]:
    """Second Semgrep pass using ``.semgrep/bugs.yaml`` when present; no-op if config is absent.

    When ``semgrep`` is not on PATH, returns no findings: ``run_semgrep`` (first pass) already emits
    the single skip finding for the missing tool.
    """
    if not files:
        return []

    skipped = skip_if_tool_missing("semgrep", files[0])
    if skipped:
        return []

    config_path = find_semgrep_bugs_config(bundle_root=bundle_root)
    if config_path is None:
        return []

    try:
        raw_results = _load_semgrep_results(files, bundle_root=bundle_root, config_file=config_path)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return _tool_error(files[0], f"Unable to parse Semgrep bugs pass output: {exc}")

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    try:
        for item in raw_results:
            _append_semgrep_result(findings, item, allowed_paths=allowed_paths, bug_pass=True)
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(files[0], f"Unable to parse Semgrep bugs finding payload: {exc}")

    return findings
