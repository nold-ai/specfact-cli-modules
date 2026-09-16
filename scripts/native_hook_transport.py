#!/usr/bin/env python3
"""Run unchanged developer hooks on a bounded, exact staged Linux snapshot."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from icontract import ensure


_CHANGE = "openspec/changes/code-review-16-portable-project-runtime/"
_RUN = "packages/specfact-code-review/src/specfact_code_review/run/"
_ALLOWED = frozenset(
    [
        _CHANGE + name
        for name in (
            "PR478_INSTALLED_ALIAS_CWD_RED.txt",
            "PR478_INSTALLED_ALIAS_RED.txt",
            "PR478_INSTALLED_COVERAGE_RED.txt",
            "PR478_INSTALLED_FLAT_RED.txt",
            "PR478_INSTALLED_RENAMED_RED.txt",
            "REVIEW_EXCEPTIONS.md",
            "TDD_EVIDENCE.md",
            "requirements-evidence.yaml",
            "specs/portable-project-runtime/spec.md",
            "tasks.md",
        )
    ]
    + [
        _RUN + name
        for name in (
            "installed_coverage.py",
            "portable_worker.py",
            "runner.py",
            "runtime_builder.py",
            "target_pytest.py",
        )
    ]
    + [
        "packages/specfact-code-review/module-package.yaml",
        "tests/unit/specfact_code_review/run/test_installed_coverage.py",
    ]
)
_ENVIRONMENT = frozenset(
    {
        "HOME",
        "PATH",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "SSL_CERT_FILE",
        "PRE_COMMIT_HOME",
        "npm_config_cache",
        "SPECFACT_CLI_REPO",
        "SPECFACT_MODULES_REPO",
        "SPECFACT_CODE_REVIEW_CAPSULE_CACHE",
    }
)
_CONTEXT = (
    "GITHUB_ACTIONS",
    "GITHUB_REPOSITORY",
    "GITHUB_WORKFLOW_REF",
    "GITHUB_WORKFLOW_SHA",
    "GITHUB_REF",
    "GITHUB_SHA",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_JOB",
)
_MAX_PATCH = 1_000_000


def _git(repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=data,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise ValueError(f"git {' '.join(arguments[:2])} failed: {result.stderr.decode(errors='replace')}")
    return result.stdout


def _decode_request(request: dict[str, str]) -> bytes:
    if set(request) != {"base", "tree", "sha256", "patch"}:
        raise ValueError("request fields mismatch")
    for field, size in (("base", 40), ("tree", 40), ("sha256", 64)):
        if re.fullmatch(rf"[0-9a-f]{{{size}}}", request[field]) is None:
            raise ValueError(f"invalid {field}")
    if len(request["patch"]) > 60_000:
        raise ValueError("compressed patch size exceeds limit")
    compressed = base64.b64decode(request["patch"], validate=True)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        patch = stream.read(_MAX_PATCH + 1)
    if len(patch) > _MAX_PATCH:
        raise ValueError("expanded patch size exceeds limit")
    if hashlib.sha256(patch).hexdigest() != request["sha256"]:
        raise ValueError("patch sha256 mismatch")
    return patch


def _patch_paths(repository: Path, patch: bytes) -> list[str]:
    rows = _git(repository, "apply", "--numstat", "-z", "-", data=patch).split(b"\0")
    paths = []
    for row in filter(None, rows):
        pieces = row.split(b"\t", 2)
        if len(pieces) != 3:
            raise ValueError("unsupported patch path record")
        path = pieces[2].decode("utf-8")
        if path not in _ALLOWED or path in paths:
            raise ValueError("patch path outside reviewed allowlist or duplicated")
        paths.append(path)
    if not paths:
        raise ValueError("patch paths empty")
    for line in patch.splitlines():
        if re.match(rb"(?:new file|old|new|deleted file) mode ", line) and line.rsplit(b" ", 1)[-1] != b"100644":
            raise ValueError("patch file mode must be regular nonexecutable")
    return sorted(paths)


@ensure(lambda result: bool(result["tree"]) and bool(result["paths"]))
def prepare_snapshot(repository: Path, request: dict[str, str]) -> dict[str, object]:
    """Validate and stage only the reviewed patch against its declared clean base."""
    patch = _decode_request(request)
    if _git(repository, "rev-parse", "HEAD").decode().strip() != request["base"]:
        raise ValueError("base mismatch")
    if _git(repository, "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("source checkout must be clean")
    paths = _patch_paths(repository, patch)
    _git(repository, "apply", "--check", "--index", "-", data=patch)
    _git(repository, "apply", "--index", "-", data=patch)
    for path in paths:
        entry = _git(repository, "ls-files", "--stage", "--", path)
        if not entry.startswith(b"100644 ") or not (repository / path).is_file() or (repository / path).is_symlink():
            raise ValueError("staged file mode must be regular")
    tree = _git(repository, "write-tree").decode().strip()
    if tree != request["tree"]:
        raise ValueError("tree mismatch")
    return {"base": request["base"], "tree": tree, "sha256": request["sha256"], "paths": paths}


@ensure(lambda result: set(result).issubset(_ENVIRONMENT))
def hook_environment(caller: dict[str, str]) -> dict[str, str]:
    """Keep only explicit noncredential developer context without publisher authority."""
    return {name: value for name, value in caller.items() if name in _ENVIRONMENT}


def _control_hashes(repository: Path) -> dict[str, str]:
    paths = [repository / ".pre-commit-config.yaml", *sorted((repository / "scripts").glob("pre*commit*"))]
    return {
        str(path.relative_to(repository)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
        if path.is_file()
    }


@ensure(lambda result: isinstance(result, int))
def execute_hooks(repository: Path, evidence: Path, receipt: dict[str, object]) -> int:
    """Run the actual unchanged pre-commit implementation and fail on source mutation."""
    environment = hook_environment(dict(os.environ))
    receipt["environment_allowlist"] = sorted(environment)
    receipt["environment_removed"] = sorted(set(os.environ) - set(environment))
    before = _control_hashes(repository)
    receipt["controls_sha256"] = before
    command = [
        str(repository / ".venv/bin/python"),
        "-m",
        "pre_commit",
        "hook-impl",
        "--config=.pre-commit-config.yaml",
        "--hook-type=pre-commit",
        "--hook-dir=.git/hooks",
    ]
    receipt["command"] = command
    with (evidence / "hooks.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command, cwd=repository, env=environment, stdout=log, stderr=subprocess.STDOUT, check=False, timeout=5_100
        )
    receipt["hook_exit"] = result.returncode
    report = repository / ".specfact/code-review.json"
    if report.is_file():
        report_bytes = report.read_bytes()
        (evidence / "code-review.json").write_bytes(report_bytes)
        receipt["review_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    receipt["hook_log_sha256"] = hashlib.sha256((evidence / "hooks.log").read_bytes()).hexdigest()
    receipt["tree_after"] = _git(repository, "write-tree").decode().strip()
    changed = _git(repository, "diff", "--name-only").strip()
    if changed or receipt["tree_after"] != receipt["tree"] or _control_hashes(repository) != before:
        receipt["failure"] = "hooks modified tested source or controls"
        return 1
    return result.returncode


@ensure(lambda result: result["authority"] == "local_build" and bool(result["identity"]))
def parse_runtime_output(output: str) -> dict[str, object]:
    """Extract exactly one complete runtime descriptor while retaining CLI decorations separately."""
    decoder = json.JSONDecoder()
    documents = []
    for match in re.finditer(r"(?m)^\{", output):
        try:
            value, _ = decoder.raw_decode(output[match.start() :])
        except ValueError:
            continue
        if not isinstance(value, dict) or value.get("authority") != "local_build":
            continue
        if not all(isinstance(value.get(name), str) and value[name] for name in ("identity", "descriptor")):
            continue
        if not isinstance(value.get("project"), dict) or not value["project"]:
            continue
        documents.append(value)
    if len(documents) != 1:
        raise ValueError("expected exactly one complete typed local runtime descriptor")
    return documents[0]


def _prepare_runtime(repository: Path, evidence: Path, receipt: dict[str, object]) -> None:
    command = ["hatch", "run", "python", "-m", "specfact_cli.cli", "code", "review", "runtime", "prepare", "--json"]
    receipt["runtime_command"] = command
    with (
        (evidence / "runtime.stdout").open("w", encoding="utf-8") as output,
        (evidence / "runtime.log").open("w", encoding="utf-8") as errors,
    ):
        result = subprocess.run(
            command,
            cwd=repository,
            env=hook_environment(dict(os.environ)),
            stdout=output,
            stderr=errors,
            timeout=1_800,
            check=False,
        )
    receipt["runtime_exit"] = result.returncode
    if result.returncode:
        raise ValueError("explicit project runtime preparation failed; see runtime.log")
    raw_output = (evidence / "runtime.stdout").read_bytes()
    runtime = parse_runtime_output(raw_output.decode("utf-8"))
    data = (json.dumps(runtime, indent=2) + "\n").encode("utf-8")
    (evidence / "runtime.json").write_bytes(data)
    receipt["runtime_stdout_sha256"] = hashlib.sha256(raw_output).hexdigest()
    receipt["runtime_sha256"] = hashlib.sha256(data).hexdigest()
    receipt["runtime_identity"] = runtime["identity"]


@ensure(lambda result: isinstance(result, int))
def main() -> int:
    """Validate, execute and always retain the exact outer workflow receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, object] = {
        "schema": "native-developer-hooks-v1",
        "authority": "local-uncommitted-explicit-files",
        "github": {name: os.environ.get(name, "") for name in _CONTEXT},
        "exit_code": 1,
    }
    exit_code = 1
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        receipt.update(prepare_snapshot(args.checkout, request))
        _prepare_runtime(args.checkout, args.evidence, receipt)
        exit_code = execute_hooks(args.checkout, args.evidence, receipt)
        receipt["exit_code"] = exit_code
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        receipt["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        (args.evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
