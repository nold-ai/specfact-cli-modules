#!/usr/bin/env python3
"""Run unchanged developer hooks on a bounded, exact staged Linux snapshot."""

from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import io
import json
import os
import re
import signal
import stat
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
            "PR478_ATTACHED_VCS_GIT_EVIDENCE.md",
            "PR478_ATTACHED_VCS_GIT_RED.txt",
            "PR478_CORE_DECLARATION_RED.txt",
            "PR478_CORE_NATIVE_RED.json",
            "PR478_PUBLIC_TRUST_NATIVE_PROBE.json",
            "PR478_PUBLIC_TRUST_RED.txt",
            "PR478_PUBLISHED_CORE_API.json",
            "PR478_SEMGREP_PARSER_EVIDENCE.json",
            "PR478_DEV_ALIGNMENT_RED.txt",
            "PR478_NATIVE_TOOLS_RED.txt",
            "PR478_NATIVE_TOOLS_CLOSURE_RED.txt",
            "PR478_NATIVE_TOOLS_GIT_RED.txt",
            "PR478_NATIVE_TOOLS_COLLISION_RED.txt",
            "PR478_NATIVE_TOOLS_LINUX_SMOKE.json",
            "PR478_SEALED_SHELL_AUDIT.json",
            "PR478_IMPLICIT_HATCH_DEFAULT_RED.txt",
            "PR478_CASE_IDENTITIES_EVIDENCE.md",
            "PR478_NODE_DOMAIN_RED.txt",
            "PR478_NODE_DOMAIN_EVIDENCE.md",
            "PR478_NODE_POLICY_CACHE_RED.txt",
            "PR478_INDEX_ACTIVATION_RED.txt",
            "PR478_SEMGREP_DIAGNOSTICS_RED.txt",
            "PR478_NATIVE_ENVIRONMENT_PACKAGES.txt",
            "PR478_NATIVE_ENVIRONMENT_FAILURE.txt",
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
            "portable_snapshot.py",
            "runtime_discovery.py",
            "portable_worker.py",
            "runner.py",
            "runtime_builder.py",
            "runtime_models.py",
            "runtime_tools.py",
            "runtime_trust.py",
            "runtime_vcs.py",
            "runtime_compatibility.py",
            "target_pytest.py",
        )
    ]
    + [
        "pyproject.toml",
        "docs/guides/portable-project-runtime.md",
        "tests/unit/specfact_code_review/run/test_runtime_tools.py",
        "tests/unit/specfact_code_review/run/test_runtime_trust.py",
        "tests/unit/specfact_code_review/run/test_runtime_vcs.py",
        "tests/unit/specfact_code_review/run/test_runtime_artifact_boundary.py",
        "tests/unit/specfact_code_review/run/test_runtime_artifact_hardlinks.py",
        "tests/unit/specfact_code_review/run/test_runtime_builder_logging.py",
        "tests/unit/specfact_code_review/run/test_runner.py",
        "tests/unit/specfact_code_review/run/test_runtime_builder.py",
        "tests/unit/specfact_code_review/run/test_runtime_compatibility.py",
        "tests/unit/specfact_code_review/run/test_snapshot_activation.py",
        "packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py",
        "tests/unit/specfact_code_review/tools/test_semgrep_runner.py",
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
_MAX_ENCODED_PATCH = 4 * ((_MAX_PATCH + 2) // 3)


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


def _control_patch() -> bytes:
    """Read only the fixed regular data file beside the trusted control helper."""
    path = Path(__file__).with_name("native_hook_snapshot.patch.gz.b64")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("control patch must be a regular file")
        encoded = stream.read(_MAX_ENCODED_PATCH + 1)
    if len(encoded) > _MAX_ENCODED_PATCH:
        raise ValueError("encoded patch size exceeds limit")
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise ValueError("invalid control patch base64") from exc
    if len(compressed) > _MAX_PATCH:
        raise ValueError("compressed patch size exceeds limit")
    if base64.b64encode(compressed) != encoded:
        raise ValueError("control patch base64 must be canonical")
    return compressed


def _compressed_patch(request: dict[str, str]) -> tuple[bytes, dict[str, object]]:
    identity_fields = {"base", "tree", "sha256"}
    if set(request) == identity_fields | {"patch"}:
        if len(request["patch"]) > 60_000:
            raise ValueError("compressed patch size exceeds limit")
        compressed = base64.b64decode(request["patch"], validate=True)
        metadata: dict[str, object] = {"mode": "inline-gzip"}
    elif set(request) == identity_fields | {"patch_source"} and request["patch_source"] == "control-checkout":
        compressed = _control_patch()
        metadata = {"mode": "control-checkout", "path": "scripts/native_hook_snapshot.patch.gz.b64"}
    else:
        raise ValueError("request fields or patch source mismatch")
    metadata.update(compressed_sha256=hashlib.sha256(compressed).hexdigest(), compressed_bytes=len(compressed))
    return compressed, metadata


def _decode_request(request: dict[str, str]) -> tuple[bytes, dict[str, object]]:
    compressed, metadata = _compressed_patch(request)
    for field, size in (("base", 40), ("tree", 40), ("sha256", 64)):
        if re.fullmatch(rf"[0-9a-f]{{{size}}}", request[field]) is None:
            raise ValueError(f"invalid {field}")
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        patch = stream.read(_MAX_PATCH + 1)
    if len(patch) > _MAX_PATCH:
        raise ValueError("expanded patch size exceeds limit")
    if hashlib.sha256(patch).hexdigest() != request["sha256"]:
        raise ValueError("patch sha256 mismatch")
    metadata["raw_bytes"] = len(patch)
    return patch, metadata


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


def _verify_development_alignment(repository: Path, paths: list[str]) -> None:
    if "pyproject.toml" not in paths:
        return
    expected = _git(repository, "show", "HEAD:pyproject.toml")
    for original, replacement in (
        (b'"beartype>=0.22.0"', b'"specfact-cli==0.55.4",\n    "beartype>=0.22.0"'),
        (b'"pylint>=4.0.2"', b'"pylint==4.0.7"'),
        (b'"basedpyright>=1.32.1"', b'"basedpyright==1.39.10",\n    "nodejs-wheel-binaries==24.16.0"'),
        (
            b"[tool.hatch.envs.default]\n",
            b'[tool.specfact.code-review]\nnative_tools = ["git", "uname", "sed"]\n\n[tool.hatch.envs.default]\n',
        ),
    ):
        if expected.count(original) != 1:
            raise ValueError("unexpected base development dependency declaration")
        expected = expected.replace(original, replacement)
    if (repository / "pyproject.toml").read_bytes() != expected:
        raise ValueError("unreviewed development dependency change")


@ensure(lambda result: bool(result["tree"]) and bool(result["paths"]))
def prepare_snapshot(repository: Path, request: dict[str, str]) -> dict[str, object]:
    """Validate and stage only the reviewed patch against its declared clean base."""
    patch, transport = _decode_request(request)
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
    _verify_development_alignment(repository, paths)
    tree = _git(repository, "write-tree").decode().strip()
    if tree != request["tree"]:
        raise ValueError("tree mismatch")
    return {
        "base": request["base"],
        "tree": tree,
        "sha256": request["sha256"],
        "paths": paths,
        "patch_transport": transport,
    }


@ensure(lambda result: set(result).issubset(_ENVIRONMENT))
def hook_environment(caller: dict[str, str]) -> dict[str, str]:
    """Keep only explicit noncredential developer context without publisher authority."""
    return {name: value for name, value in caller.items() if name in _ENVIRONMENT}


@ensure(lambda result, repository: result["SPECFACT_MODULES_ROOTS"] == str((repository / "packages").resolve()))
def runtime_environment(repository: Path, caller: dict[str, str]) -> dict[str, str]:
    """Mirror unchanged hook-owned workspace selection, excluding inherited import overlays."""
    environment = hook_environment(caller)
    environment["SPECFACT_MODULES_REPO"] = str(repository.resolve())
    environment["SPECFACT_CLI_MODULES_REPO"] = str(repository.resolve())
    environment["SPECFACT_MODULES_ROOTS"] = str((repository / "packages").resolve())
    roots = [path / "src" for path in sorted((repository / "packages").glob("specfact-*"))]
    environment["PYTHONPATH"] = os.pathsep.join(str(path.resolve()) for path in roots if path.is_dir())
    return environment


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
    untracked = _git(repository, "ls-files", "--others", "--exclude-standard").strip()
    if untracked or changed or receipt["tree_after"] != receipt["tree"] or _control_hashes(repository) != before:
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
    environment = runtime_environment(repository, dict(os.environ))
    receipt["runtime_workspace_roots"] = {name: environment[name] for name in ("SPECFACT_MODULES_ROOTS", "PYTHONPATH")}
    receipt["runtime_environment_allowlist"] = sorted(environment)
    with (
        (evidence / "runtime.stdout").open("w", encoding="utf-8") as output,
        (evidence / "runtime.log").open("w", encoding="utf-8") as errors,
    ):
        result = subprocess.run(
            command,
            cwd=repository,
            env=environment,
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


def _inventory_hook_environment(repository: Path, evidence: Path, receipt: dict[str, object]) -> None:
    command = [str(repository / ".venv/bin/python"), "-m", "pip", "freeze", "--all"]
    receipt["hook_inventory_command"] = command
    inventory = evidence / "hook-python-freeze.txt"
    with (
        inventory.open("w", encoding="utf-8") as output,
        (evidence / "hook-inventory.log").open("w", encoding="utf-8") as errors,
    ):
        subprocess.run(
            command,
            cwd=repository,
            env=hook_environment(dict(os.environ)),
            stdout=output,
            stderr=errors,
            timeout=120,
            check=True,
        )
    receipt["hook_inventory_sha256"] = hashlib.sha256(inventory.read_bytes()).hexdigest()


def _diagnose_failed_semgrep(repository: Path, evidence: Path, receipt: dict[str, object]) -> None:
    """Run a separate diagnostic child without replacing the original hook failure."""
    command = [
        str(repository / ".venv/bin/python"),
        str(Path(__file__).with_name("native_semgrep_diagnostic.py")),
        "--checkout",
        str(repository),
        "--evidence",
        str(evidence),
    ]
    receipt["semgrep_diagnostic_command"] = command
    receipt["semgrep_diagnostic_acceptance"] = False
    try:
        with (evidence / "semgrep-diagnostic.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                command,
                cwd=repository,
                env=runtime_environment(repository, dict(os.environ)),
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=900,
            )
        receipt["semgrep_diagnostic_exit"] = result.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        receipt["semgrep_diagnostic_failure"] = f"{type(exc).__name__}: {exc}"


@ensure(lambda receipt: receipt["basedpyright_diagnostic_acceptance"] is False)
def diagnose_failed_basedpyright(repository: Path, evidence: Path, receipt: dict[str, object]) -> None:
    """Optional replay preserves the unchanged hook result and never grants acceptance."""
    command = [
        "hatch",
        "run",
        "python",
        str(Path(__file__).with_name("native_basedpyright_diagnostic.py")),
        "--checkout",
        str(repository),
        "--evidence",
        str(evidence),
    ]
    receipt["basedpyright_diagnostic_command"] = command
    receipt["basedpyright_diagnostic_acceptance"] = False
    try:
        with (evidence / "basedpyright-diagnostic.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                command,
                cwd=repository,
                env=runtime_environment(repository, dict(os.environ)),
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=90,
            )
        receipt["basedpyright_diagnostic_exit"] = result.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        receipt["basedpyright_diagnostic_failure"] = f"{type(exc).__name__}: {exc}"


@ensure(lambda result, process: isinstance(result, int) and process.returncode == result)
def wait_diagnostic_child(process: subprocess.Popen, *, timeout: float = 1860, grace: float = 5) -> int:
    """Bound a controller-owned diagnostic session and retain its real exit."""
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=grace)
        raise


@ensure(lambda receipt: receipt["review_timing_diagnostic_acceptance"] is False)
def diagnose_failed_review_timing(repository: Path, evidence: Path, receipt: dict[str, object]) -> None:
    """Time only a separate failed-review replay without replacing hook authority."""
    command = [
        "hatch",
        "run",
        "python",
        str(Path(__file__).with_name("native_review_timing_diagnostic.py")),
        "--checkout",
        str(repository),
        "--evidence",
        str(evidence),
    ]
    receipt["review_timing_diagnostic_command"] = command
    receipt["review_timing_diagnostic_acceptance"] = False
    try:
        with (
            (evidence / "review-timing-diagnostic.log").open("w", encoding="utf-8") as log,
            subprocess.Popen(
                command,
                cwd=repository,
                env=runtime_environment(repository, dict(os.environ)),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            ) as process,
        ):
            receipt["review_timing_diagnostic_exit"] = wait_diagnostic_child(process)
    except (OSError, subprocess.SubprocessError) as exc:
        receipt["review_timing_diagnostic_failure"] = f"{type(exc).__name__}: {exc}"


@ensure(lambda result: isinstance(result, int))
def main() -> int:
    """Validate, execute and always retain the exact outer workflow receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--basedpyright-diagnostic", action="store_true")
    parser.add_argument("--review-timing-diagnostic", action="store_true")
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
        _inventory_hook_environment(args.checkout, args.evidence, receipt)
        exit_code = execute_hooks(args.checkout, args.evidence, receipt)
        receipt["exit_code"] = exit_code
        if exit_code:
            if args.review_timing_diagnostic:
                diagnose_failed_review_timing(args.checkout, args.evidence, receipt)
            _diagnose_failed_semgrep(args.checkout, args.evidence, receipt)
            if args.basedpyright_diagnostic:
                diagnose_failed_basedpyright(args.checkout, args.evidence, receipt)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        receipt["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        (args.evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
