"""Exercise installed capsule analyzers and reject incomplete customer evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from icontract import ensure, require


ANALYZERS = frozenset(
    {
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
    }
)


def _validate_inventory(rows: list[dict[str, Any]]) -> None:
    if len(rows) != len(ANALYZERS) or {row.get("id") for row in rows} != ANALYZERS:
        raise ValueError("analyzer inventory is incomplete")
    for row in rows:
        if row.get("execution_state") != "ran" or row.get("evidence_outcome") not in {"PASS", "FAIL"}:
            raise ValueError("analyzer execution is incomplete or UNKNOWN")


def _validate_expected_outcome(report: dict[str, Any], returncode: int, expected: str) -> None:
    status = report.get("assurance_status")
    if expected == "clean" and (returncode, status) != (0, "PASS"):
        raise ValueError("clean fixture did not pass")
    if expected == "defective":
        detected = any(row.get("evidence_outcome") == "FAIL" for row in report["analyzer_evidence"])
        if (returncode, status) != (1, "FAIL") or not detected or not report.get("findings"):
            raise ValueError("controlled defect was not detected with a failing exit")
    if expected == "repository" and (returncode, status) not in {(0, "PASS"), (1, "FAIL")}:
        raise ValueError("repository review did not complete")


@require(lambda expected: expected in {"clean", "defective", "repository"})
@ensure(lambda result: result is None)
def validate_report(report: dict[str, Any], *, returncode: int, expected: str) -> None:
    """Require every selected analyzer to execute, including conditional members."""
    _validate_inventory(report.get("analyzer_evidence", []))
    if report.get("has_unknown_required_evidence") is not False:
        raise ValueError("required evidence is UNKNOWN")
    _validate_expected_outcome(report, returncode, expected)


def _cache_identities(cache: Path) -> dict[str, str]:
    identities = {}
    for path in sorted(cache.rglob("blobs/sha256/*")):
        if path.is_file():
            with path.open("rb") as stream:
                identities[path.relative_to(cache).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    return identities


def _fixture(root: Path, *, defective: bool) -> None:
    root.mkdir()
    source = '"""Small arithmetic fixture."""\n\n\ndef add(left: int, right: int) -> int:\n    """Return the sum of two integers."""\n    return left + right\n'
    if defective:
        source = source.replace("\n\n\ndef add", "\n\nimport json\n\n\ndef add")
    (root / "calculator.py").write_text(source, encoding="utf-8")
    (root / "test_calculator.py").write_text(
        '"""Arithmetic fixture tests."""\n\nfrom calculator import add\n\n\n'
        'def test_add() -> None:\n    """Exercise the fixture arithmetic."""\n    assert add(2, 3) == 5\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Capsule CI",
            "-c",
            "user.email=capsule@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "-m",
            "Controlled capsule fixture",
        ],
        check=True,
    )


def _review(root: Path, evidence: Path, name: str, expected: str) -> None:
    report_path = evidence / f"{name}.json"
    command = [
        "specfact",
        "code",
        "review",
        "run",
        "--scope",
        "full",
        "--enforcement",
        "full",
        "--bug-hunt",
        "--json",
        "--out",
        str(report_path),
    ]
    with (evidence / f"{name}.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=root,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=False,
            umask=0o077 if name == "warm" else 0o022,
            env={**os.environ, "SPECFACT_CODE_REVIEW_CAPSULE_OFFLINE": "1" if name == "warm" else "0"},
        )
    (evidence / f"{name}-command.json").write_text(
        json.dumps({"argv": command, "exit_code": result.returncode}), encoding="utf-8"
    )
    validate_report(
        json.loads(report_path.read_text(encoding="utf-8")), returncode=result.returncode, expected=expected
    )


def _run_reviews(evidence: Path, cache: Path, repository: Path, clean: Path, defective: Path) -> list[str]:
    failures = []
    cold = {}
    for name, root, expected in [
        ("cold", clean, "clean"),
        ("warm", clean, "clean"),
        ("defective", defective, "defective"),
        ("repository", repository, "repository"),
    ]:
        try:
            _review(root, evidence, name, expected)
            identities = _cache_identities(cache)
            if not identities:
                raise ValueError("runtime cache contains no verified OCI artifacts")
            if name == "cold":
                cold = identities
            elif cold and identities != cold:
                raise ValueError("warm cache identities changed")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            failures.append(f"{name}: {exc}")
    return failures


@ensure(lambda result: result in {0, 1})
def main() -> int:
    """Run cold, warm, defective and repository reviews without elevated privileges."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--mode", choices=("candidate", "public"), required=True)
    args = parser.parse_args()
    if os.geteuid() == 0 or platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("customer gate requires a non-root Linux x86-64 runner")
    forbidden = ["GITHUB_TOKEN", "GH_TOKEN", "PYTHONPATH"]
    if args.mode == "public":
        forbidden += ["SPECFACT_ALLOW_UNSIGNED", "SPECFACT_MODULES_ROOTS", "SPECFACT_MODULES_REPO"]
    if any(os.environ.get(name) for name in forbidden):
        raise ValueError("customer gate has credentials or development overrides")
    cache = Path(os.environ["SPECFACT_CODE_REVIEW_CAPSULE_CACHE"])
    if cache.exists() and any(cache.iterdir()):
        raise ValueError("customer gate must start with an empty cache")
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True)
    (evidence / "environment.json").write_text(
        json.dumps(
            {
                "python": sys.version,
                "platform": platform.platform(),
                "uid": os.geteuid(),
                "core": importlib.metadata.version("specfact-cli"),
                "mode": args.mode,
                "commit": os.environ.get("GITHUB_SHA"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    clean = evidence.parent / "clean"
    defective = evidence.parent / "defective"
    _fixture(clean, defective=False)
    _fixture(defective, defective=True)
    failures = _run_reviews(evidence, cache, args.repository, clean, defective)
    (evidence / "cache-identities.json").write_text(json.dumps(_cache_identities(cache), indent=2), encoding="utf-8")
    (evidence / "result.json").write_text(
        json.dumps({"failures": failures, "mode": args.mode}, indent=2), encoding="utf-8"
    )
    for failure in failures:
        sys.stderr.write(f"{failure}\n")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
