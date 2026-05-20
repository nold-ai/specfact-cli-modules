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


@require(lambda files: files is not None)
@ensure(lambda result: result[:5] == [sys.executable, "-m", "specfact_cli.cli", "code", "review"])
@ensure(lambda result: "--json" in result and "--out" in result)
@ensure(lambda result: REVIEW_JSON_OUT in result)
def build_review_command(files: Sequence[str]) -> list[str]:
    """Build ``code review run --json --out …`` so findings are written for tooling."""
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
) -> subprocess.CompletedProcess[str] | None:
    """Run the nested SpecFact review command and handle timeout reporting."""
    env = os.environ.copy()
    # Ensure nested `python -m specfact_cli.cli` bootstraps this checkout's bundle sources first
    # (see `specfact_cli/__init__.py::_bootstrap_bundle_paths`) so ~/.specfact/modules tarballs do not
    # shadow in-repo `specfact_code_review` during the pre-commit gate.
    env["SPECFACT_MODULES_REPO"] = str(repo_root.resolve())
    env["SPECFACT_CLI_MODULES_REPO"] = str(repo_root.resolve())
    code_review_src = repo_root / "packages" / "specfact-code-review" / "src"
    if code_review_src.is_dir():
        prefix = str(code_review_src)
        previous = env.get("PYTHONPATH", "").strip()
        env["PYTHONPATH"] = f"{prefix}{os.pathsep}{previous}" if previous else prefix
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


def _print_review_findings_summary(repo_root: Path) -> tuple[bool, int | None, int | None]:
    """Parse ``REVIEW_JSON_OUT``, print counts, return ``(ok, error_count, ci_exit_code)``.

    Callers should use ``ci_exit_code`` as the hook exit code; ``error_count`` is informational only
    because fixable error-severity findings may still yield a passing ``ci_exit_code``.
    """
    report_path = _report_path(repo_root)
    if not report_path.is_file():
        sys.stderr.write(f"Code review: no report file at {REVIEW_JSON_OUT} (could not print findings summary).\n")
        return False, None, None
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"Code review: could not read {REVIEW_JSON_OUT}: {exc}\n")
        return False, None, None
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Code review: invalid JSON in {REVIEW_JSON_OUT}: {exc}\n")
        return False, None, None

    if not isinstance(data, dict):
        sys.stderr.write(f"Code review: expected top-level JSON object in {REVIEW_JSON_OUT}.\n")
        return False, None, None

    findings_raw = data.get("findings")
    if not isinstance(findings_raw, list):
        sys.stderr.write(f"Code review: report has no findings list in {REVIEW_JSON_OUT}.\n")
        return False, None, None

    counts = count_findings_by_severity(findings_raw)
    ai_bloat_count = _count_ai_bloat_findings(findings_raw)
    total = len(findings_raw)
    verdict = data.get("overall_verdict", "?")
    ci_exit_code = data.get("ci_exit_code")
    if ci_exit_code not in {0, 1}:
        ci_exit_code = 1 if verdict == "FAIL" else 0
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
    summary = ", ".join(parts)
    sys.stderr.write(f"Code review summary: {total} finding(s) ({summary}); overall_verdict={verdict!r}.\n")
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
    cmd = build_review_command(specfact_files)
    report_path = _prepare_report_path(repo_root)
    result = _run_review_subprocess(cmd, repo_root, specfact_files)
    if result is None:
        return 1
    if not report_path.is_file():
        return _missing_report_exit_code(report_path, result)
    # Do not echo nested `specfact code review run` stdout/stderr (verbose tool banners); full report
    # is in REVIEW_JSON_OUT; we print a short summary on stderr below.
    summary_ok, _error_count, ci_exit_code = _print_review_findings_summary(repo_root)
    if not summary_ok or ci_exit_code is None:
        return 1
    return int(ci_exit_code)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
