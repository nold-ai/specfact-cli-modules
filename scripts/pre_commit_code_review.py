"""Run specfact code review as a staged-file pre-commit gate (modules repo).

Writes a machine-readable JSON report to ``.specfact/code-review.json`` (gitignored)
so IDEs and Copilot can read findings; exit code still reflects the governed CI verdict.

If ``specfact_cli`` is not installed, attempts ``hatch run dev-deps`` / ``ensure_core_dependency``
(sibling ``specfact-cli`` checkout) before failing.
"""

# CrossHair: ignore
# This helper shells out to the CLI and is intentionally side-effecting.

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from subprocess import TimeoutExpired
from typing import Any, cast

from icontract import ensure, require


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dev_bootstrap() -> Any:
    """Load ``specfact_cli_modules.dev_bootstrap`` without package install assumptions."""
    module_path = REPO_ROOT / "src" / "specfact_cli_modules" / "dev_bootstrap.py"
    spec = importlib.util.spec_from_file_location("specfact_cli_modules.dev_bootstrap", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load dev bootstrap module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_dev_bootstrap = _load_dev_bootstrap()
ensure_core_dependency = cast(Callable[[Path], int], _dev_bootstrap.ensure_core_dependency)
apply_specfact_workspace_env = _dev_bootstrap.apply_specfact_workspace_env


# Default matches dogfood / OpenSpec: machine-readable report under ignored ``.specfact/``.
REVIEW_JSON_OUT = ".specfact/code-review.json"
VALID_ENFORCEMENT_MODES = frozenset({"full", "changed", "shadow"})
DEFAULT_ENFORCEMENT_MODE = "changed"
# Staged positional-file review retains the legacy explicit_files assurance kind.


def _is_review_gate_path(path: str) -> bool:
    """Return whether a repo-relative path should participate in the pre-commit review gate."""
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return False
    if normalized.endswith("module-package.yaml"):
        return False
    if normalized.startswith("openspec/changes/") and Path(normalized).name.casefold() == "tdd_evidence.md":
        return False
    prefixes = (
        "packages/",
        "registry/",
        "scripts/",
        "tools/",
        "tests/",
        "openspec/changes/",
    )
    return any(normalized.startswith(prefix) for prefix in prefixes)


@require(lambda paths: paths is not None)
@ensure(lambda result: len(result) == len(set(result)))
def filter_review_gate_paths(paths: Sequence[str]) -> list[str]:
    """Return staged paths under contract- and tooling-heavy trees for the review gate."""
    seen: set[str] = set()
    filtered: list[str] = []
    for path in paths:
        if not _is_review_gate_path(path):
            continue
        if path in seen:
            continue
        seen.add(path)
        filtered.append(path)
    return filtered


def _specfact_review_paths(paths: Sequence[str]) -> list[str]:
    """Paths to pass to SpecFact ``code review run`` (Python sources only; skip Markdown and non-.py/.pyi)."""
    result: list[str] = []
    for raw in paths:
        normalized = raw.replace("\\", "/").strip()
        if normalized.startswith("openspec/changes/") and normalized.lower().endswith(".md"):
            continue
        if not normalized.endswith((".py", ".pyi")):
            continue
        result.append(raw)
    return result


def review_enforcement_mode() -> str:
    """Return configured pre-commit review enforcement mode."""
    configured = os.environ.get("SPECFACT_CODE_REVIEW_ENFORCEMENT", DEFAULT_ENFORCEMENT_MODE).strip().lower()
    if configured in VALID_ENFORCEMENT_MODES:
        return configured
    sys.stderr.write(
        "Invalid SPECFACT_CODE_REVIEW_ENFORCEMENT value "
        f"{configured!r}; expected one of: {', '.join(sorted(VALID_ENFORCEMENT_MODES))}.\n"
    )
    return DEFAULT_ENFORCEMENT_MODE


@require(lambda files: files is not None)
@ensure(lambda result: result[:5] == [sys.executable, "-m", "specfact_cli.cli", "code", "review"])
@ensure(lambda result: "--json" in result and "--out" in result)
@ensure(lambda result: REVIEW_JSON_OUT in result)
def build_review_command(files: Sequence[str], *, enforcement: str | None = None) -> list[str]:
    """Build ``code review run --json --out …`` so findings are written for tooling."""
    mode = enforcement or review_enforcement_mode()
    return [
        sys.executable,
        "-m",
        "specfact_cli.cli",
        "code",
        "review",
        "run",
        "--json",
        "--out",
        REVIEW_JSON_OUT,
        "--enforcement",
        mode,
        *files,
    ]


def _repo_root() -> Path:
    """Repository root (parent of ``scripts/``)."""
    return REPO_ROOT


def _report_path(repo_root: Path) -> Path:
    """Absolute path to the machine-readable review report."""
    return repo_root / REVIEW_JSON_OUT


def _prepare_report_path(repo_root: Path) -> Path:
    """Create the review-report directory and clear any stale report file."""
    report_path = _report_path(repo_root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.is_file():
        report_path.unlink()
    return report_path


def _run_review_subprocess(
    cmd: list[str],
    repo_root: Path,
    files: Sequence[str],
    *,
    enforcement: str,
) -> subprocess.CompletedProcess[str] | None:
    """Run the nested SpecFact review command and handle timeout reporting."""
    env = os.environ.copy()
    # Ensure nested `python -m specfact_cli.cli` bootstraps this checkout's bundle sources first
    # (see `specfact_cli/__init__.py::_bootstrap_bundle_paths`) so ~/.specfact/modules tarballs do not
    # shadow in-repo `specfact_code_review` during the pre-commit gate.
    env["SPECFACT_MODULES_REPO"] = str(repo_root.resolve())
    env["SPECFACT_CLI_MODULES_REPO"] = str(repo_root.resolve())
    env["SPECFACT_MODULES_ROOTS"] = str((repo_root / "packages").resolve())
    package_src_roots = [path / "src" for path in sorted((repo_root / "packages").glob("specfact-*"))]
    prefixes = [str(path) for path in package_src_roots if path.is_dir()]
    previous = env.get("PYTHONPATH", "").strip()
    if previous:
        prefixes.extend(entry for entry in previous.split(os.pathsep) if entry)
    if prefixes:
        env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(prefixes))
    if enforcement == "changed":
        env["SPECFACT_CODE_REVIEW_CHANGED_DIFF"] = "cached"
    try:
        return subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=True,
            cwd=str(repo_root),
            env=env,
            timeout=300,
        )
    except TimeoutExpired:
        joined_cmd = " ".join(cmd)
        sys.stderr.write(f"Code review gate timed out after 300s (command: {joined_cmd!r}, files: {list(files)!r}).\n")
        return None


def _emit_completed_output(result: subprocess.CompletedProcess[str]) -> None:
    """Forward captured subprocess output to stderr when the JSON report is missing."""
    if result.stdout:
        sys.stderr.write(result.stdout if result.stdout.endswith("\n") else result.stdout + "\n")
    if result.stderr:
        sys.stderr.write(result.stderr if result.stderr.endswith("\n") else result.stderr + "\n")


def _missing_report_exit_code(
    report_path: Path,
    result: subprocess.CompletedProcess[str],
) -> int:
    """Return the gate exit code when the nested review run failed to create its JSON report."""
    _emit_completed_output(result)
    sys.stderr.write(
        f"Code review: expected review report at {report_path.relative_to(_repo_root())} but it was not created.\n",
    )
    return result.returncode if result.returncode != 0 else 1


def _classify_severity(item: object) -> str:
    """Map one review finding to a bucket name."""
    if not isinstance(item, dict):
        return "other"
    row = cast(dict[str, Any], item)
    raw = row.get("severity")
    if not isinstance(raw, str):
        return "other"

    key = raw.lower().strip()
    if key in ("error", "err"):
        return "error"
    if key in ("warning", "warn"):
        return "warning"
    if key in ("advisory", "advise"):
        return "advisory"
    if key == "info":
        return "info"
    return "other"


@require(lambda findings: findings is not None)
@ensure(lambda result: set(result) == {"error", "warning", "advisory", "info", "other"})
def count_findings_by_severity(findings: list[object]) -> dict[str, int]:
    """Bucket review findings by severity (unknown severities go to ``other``)."""
    buckets = {"error": 0, "warning": 0, "advisory": 0, "info": 0, "other": 0}
    for item in findings:
        buckets[_classify_severity(item)] += 1
    return buckets


def _count_ai_bloat_findings(findings: list[object]) -> int:
    """Count advisory AI-bloat findings in a ReviewReport payload."""
    count = 0
    for item in findings:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        if isinstance(category, str) and category == "ai_bloat":
            count += 1
    return count


def _repo_relative_report_path(repo_root: Path, raw_path: object) -> str | None:
    """Normalize a finding path to a repository-relative POSIX path."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    if path.is_absolute():
        try:
            path = path.relative_to(repo_root)
        except ValueError:
            return None
    return path.as_posix()


def _parse_added_lines_from_cached_diff(diff_text: str) -> dict[str, set[int]]:
    """Return staged new-line numbers by repo-relative file from a zero-context diff."""
    changed_lines: dict[str, set[int]] = {}
    current_file: str | None = None
    previous_was_source_header = False
    for line in diff_text.splitlines():
        if line.startswith("--- "):
            previous_was_source_header = True
            continue
        if previous_was_source_header and line.startswith("+++ "):
            previous_was_source_header = False
            destination = line[4:].strip()
            current_file = None if destination == "/dev/null" else destination.removeprefix("b/")
            if current_file is not None:
                changed_lines.setdefault(current_file, set())
            continue
        previous_was_source_header = False
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


def _staged_changed_lines(repo_root: Path) -> dict[str, set[int]]:
    """Collect staged new-line numbers so legacy file findings do not block unrelated commits."""
    completed = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--no-ext-diff"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {}
    return _parse_added_lines_from_cached_diff(completed.stdout)


def _finding_is_blocking(item: object) -> bool:
    """Return whether a raw finding has blocking review semantics."""
    if not isinstance(item, dict):
        return False
    severity = item.get("severity")
    return isinstance(severity, str) and severity.lower().strip() == "error" and item.get("fixable") is not True


def _finding_targets_staged_line(repo_root: Path, item: object, changed_lines: dict[str, set[int]]) -> bool:
    """Return whether a finding points at a staged changed line."""
    if not isinstance(item, dict):
        return False
    relative_path = _repo_relative_report_path(repo_root, item.get("file"))
    if relative_path is None or relative_path not in changed_lines:
        return False
    line_number = item.get("line")
    if isinstance(line_number, int):
        return line_number in changed_lines[relative_path]
    return bool(changed_lines[relative_path])


def _load_review_report(repo_root: Path) -> dict[str, Any] | None:
    """Load the review report JSON object, printing a precise diagnostic on failure."""
    report_path = _report_path(repo_root)
    if not report_path.is_file():
        sys.stderr.write(f"Code review: no report file at {REVIEW_JSON_OUT} (could not print findings summary).\n")
        return None
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"Code review: could not read {REVIEW_JSON_OUT}: {exc}\n")
        return None
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Code review: invalid JSON in {REVIEW_JSON_OUT}: {exc}\n")
        return None
    if not isinstance(data, dict):
        sys.stderr.write(f"Code review: expected top-level JSON object in {REVIEW_JSON_OUT}.\n")
        return None
    return cast(dict[str, Any], data)


def _raw_ci_exit_code(report: dict[str, Any]) -> int:
    """Read the report CI exit code, deriving it from the verdict when missing."""
    raw = report.get("ci_exit_code")
    if raw in {0, 1}:
        return int(raw)
    return 1 if report.get("overall_verdict") == "FAIL" else 0


def _schema_version_at_least(value: object, required_minor: int) -> bool:
    try:
        major_text, minor_text, *_ = str(value).split(".")
        major = int(major_text)
        minor = int(minor_text)
    except (ValueError, TypeError):
        return False
    return major > 1 or (major == 1 and minor >= required_minor)


def _authoritative_report_exit_code(report: dict[str, Any], *, enforcement: str) -> int | None:
    """Return schema 1.6 authoritative exit policy, or None for legacy reports."""

    if not _schema_version_at_least(report.get("schema_version", "0"), 6):
        return None
    if enforcement == "shadow":
        return 0
    if report.get("assurance_status") in {"PASS", "NOT_APPLICABLE"}:
        return 0
    return 1


def _changed_line_blockers(repo_root: Path, findings_raw: list[object]) -> list[object]:
    """Return blocking findings that point at staged changed lines."""
    changed_lines = _staged_changed_lines(repo_root)
    return [
        item
        for item in findings_raw
        if _finding_is_blocking(item) and _finding_targets_staged_line(repo_root, item, changed_lines)
    ]


def _enforced_exit_code(
    repo_root: Path, findings_raw: list[object], *, enforcement: str, raw_ci_exit_code: int
) -> tuple[int, list[object]]:
    """Apply configured enforcement to the raw report exit code."""
    if enforcement == "full":
        return raw_ci_exit_code, []
    if enforcement == "shadow":
        return 0, []
    blockers = _changed_line_blockers(repo_root, findings_raw)
    return (1 if blockers else 0), blockers


def _finding_summary_parts(counts: dict[str, int], *, ai_bloat_count: int) -> list[str]:
    """Format finding count buckets for concise stderr output."""
    parts = [
        f"errors={counts['error']}",
        f"warnings={counts['warning']}",
        f"advisory={counts['advisory']}",
    ]
    if counts["info"]:
        parts.append(f"info={counts['info']}")
    if counts["other"]:
        parts.append(f"other={counts['other']}")
    if ai_bloat_count:
        parts.append(f"ai_bloat={ai_bloat_count}")
    return parts


def _print_enforcement_summary(
    *,
    enforcement: str,
    raw_ci_exit_code: int,
    ci_exit_code: int,
    blocking_changed_findings: list[object],
) -> None:
    """Print the enforcement decision evidence."""
    sys.stderr.write(f"Code review enforcement: {enforcement}.\n")
    if enforcement == "shadow" and raw_ci_exit_code == 1:
        sys.stderr.write("Code review shadow gate: findings are evidence-only and do not block.\n")
    elif raw_ci_exit_code == 1 and ci_exit_code == 0:
        sys.stderr.write(
            "Code review changed-line gate: no blocking findings target staged lines; "
            "legacy findings remain in the JSON report.\n"
        )
    elif blocking_changed_findings:
        sys.stderr.write(
            f"Code review changed-line gate: {len(blocking_changed_findings)} blocking finding(s) target staged lines.\n"
        )


def _print_review_findings_summary(repo_root: Path, *, enforcement: str) -> tuple[bool, int | None, int | None]:
    """Parse ``REVIEW_JSON_OUT``, print counts, return ``(ok, error_count, ci_exit_code)``.

    Callers should use ``ci_exit_code`` as the hook exit code; ``error_count`` is informational only
    because fixable error-severity findings may still yield a passing ``ci_exit_code``.
    """
    data = _load_review_report(repo_root)
    if data is None:
        return False, None, None

    findings_raw = data.get("findings")
    if not isinstance(findings_raw, list):
        sys.stderr.write(f"Code review: report has no findings list in {REVIEW_JSON_OUT}.\n")
        return False, None, None

    counts = count_findings_by_severity(findings_raw)
    ai_bloat_count = _count_ai_bloat_findings(findings_raw)
    total = len(findings_raw)
    verdict = data.get("overall_verdict", "?")
    raw_ci_exit_code = _raw_ci_exit_code(data)
    authoritative_exit = _authoritative_report_exit_code(data, enforcement=enforcement)
    if authoritative_exit is None:
        ci_exit_code, blocking_changed_findings = _enforced_exit_code(
            repo_root, findings_raw, enforcement=enforcement, raw_ci_exit_code=raw_ci_exit_code
        )
    else:
        ci_exit_code, blocking_changed_findings = authoritative_exit, []
    summary = ", ".join(_finding_summary_parts(counts, ai_bloat_count=ai_bloat_count))
    sys.stderr.write(f"Code review summary: {total} finding(s) ({summary}); overall_verdict={verdict!r}.\n")
    _print_enforcement_summary(
        enforcement=enforcement,
        raw_ci_exit_code=raw_ci_exit_code,
        ci_exit_code=ci_exit_code,
        blocking_changed_findings=blocking_changed_findings,
    )
    report_path = _report_path(repo_root)
    abs_report = report_path.resolve()
    sys.stderr.write(f"Code review report file: {REVIEW_JSON_OUT}\n")
    sys.stderr.write(f"  absolute path: {abs_report}\n")
    sys.stderr.write("Copy-paste for Copilot or Cursor:\n")
    sys.stderr.write(
        f"  Read `{REVIEW_JSON_OUT}` and fix every finding (errors first), using file and line from each entry.\n"
    )
    sys.stderr.write(f"  @workspace Open `{REVIEW_JSON_OUT}` and remediate each item in `findings`.\n")
    return True, counts["error"], ci_exit_code


@ensure(lambda result: isinstance(result, tuple) and len(result) == 2)
@ensure(lambda result: isinstance(result[0], bool) and (result[1] is None or isinstance(result[1], str)))
def ensure_runtime_available() -> tuple[bool, str | None]:
    """Verify the current Python environment can import SpecFact CLI; try local sibling install."""
    try:
        importlib.import_module("specfact_cli.cli")
    except ModuleNotFoundError:
        root = _repo_root()
        if ensure_core_dependency(root) != 0:
            return (
                False,
                "Could not install local specfact-cli. Run `hatch run dev-deps` or set SPECFACT_CLI_REPO.",
            )
        try:
            importlib.import_module("specfact_cli.cli")
        except ModuleNotFoundError:
            return (
                False,
                "specfact_cli still not importable after ensure_core_dependency; check sibling checkout.",
            )
    return True, None


@ensure(lambda result: isinstance(result, int))
def main(argv: Sequence[str] | None = None) -> int:
    """Run the code review gate; write JSON under ``.specfact/`` and return CLI exit code."""
    apply_specfact_workspace_env(REPO_ROOT)
    files = filter_review_gate_paths(list(argv or []))
    if len(files) == 0:
        sys.stdout.write(
            "No staged review-relevant files under packages/, registry/, scripts/, tools/, tests/, "
            "or openspec/changes/; skipping code review gate.\n"
        )
        return 0

    specfact_files = _specfact_review_paths(files)
    if len(specfact_files) == 0:
        sys.stdout.write(
            "Staged review paths are only OpenSpec Markdown under openspec/changes/; "
            "skipping SpecFact code review (no staged .py/.pyi targets; Markdown is not passed to SpecFact).\n"
        )
        return 0

    available, guidance = ensure_runtime_available()
    if available is False:
        sys.stdout.write(f"Unable to run the code review gate. {guidance}\n")
        return 1

    repo_root = _repo_root()
    enforcement = review_enforcement_mode()
    cmd = build_review_command(specfact_files, enforcement=enforcement)
    report_path = _prepare_report_path(repo_root)
    result = _run_review_subprocess(cmd, repo_root, specfact_files, enforcement=enforcement)
    if result is None:
        return 1
    if not report_path.is_file():
        return _missing_report_exit_code(report_path, result)
    # Do not echo nested `specfact code review run` stdout/stderr (verbose tool banners); full report
    # is in REVIEW_JSON_OUT; we print a short summary on stderr below.
    summary_ok, _error_count, ci_exit_code = _print_review_findings_summary(repo_root, enforcement=enforcement)
    if not summary_ok or ci_exit_code is None:
        return 1
    return int(ci_exit_code)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
