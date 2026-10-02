#!/usr/bin/env python3
"""Fixed-fixture Semgrep 1.175.0 parity; never production or sandbox evidence.

Run with an explicit Python interpreter. No targets, config overrides, installs,
ambient tool discovery, or shell commands are accepted. Capture stdout in ignored
.specfact/native-compat/semgrep-native-parity.json for maintainer evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import platform
import stat
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from types import CodeType


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "scripts/native_analyzer_smoke.py"
SMOKE_SOURCE = SMOKE_PATH.read_bytes()


class _CapturedSmokeLoader(importlib.machinery.SourceFileLoader):
    """Import the fixed smoke helper from captured bytes, without bytecode reuse."""

    def get_code(self, fullname: str) -> CodeType:
        """Use normal loader execution with exactly the source bound in evidence."""
        if fullname != self.name:
            raise ImportError("captured smoke helper identity mismatch")
        return compile(SMOKE_SOURCE, self.path, "exec")


SMOKE_SPEC = importlib.util.spec_from_file_location(
    "native_parity_smoke", SMOKE_PATH, loader=_CapturedSmokeLoader("native_parity_smoke", str(SMOKE_PATH))
)
assert SMOKE_SPEC is not None and SMOKE_SPEC.loader is not None
smoke = importlib.util.module_from_spec(SMOKE_SPEC)
SMOKE_SPEC.loader.exec_module(smoke)
VERSION = "1.175.0"
TIMEOUT_SECONDS = 30
FILE_LIMIT = 256 * 1024 * 1024
INPUT_LIMIT = 512 * 1024
VENV = ROOT / ".specfact/native-compat/venv"
SITE = VENV / "lib/python3.13/site-packages"
RULES = ROOT / "packages/specfact-code-review/src/specfact_code_review/.semgrep"
ASSET_PINS = {
    "python": (VENV / "bin/python", "091704d2238fa5d3d95299894a24d02fa0cf0f874d7b1cd019f9a19b767628ab"),
    "frontend": (VENV / "bin/semgrep", "90f87f661e29c56f2e87ced4411694b2a32f1d202e7834d99df5aa738bdfe0b3"),
    "core": (SITE / "semgrep/bin/semgrep-core", "ec9b34d035688a7d8d77c7a45fe1cd2b8e8d9e15ac4f50071eada9c131925e53"),
    "clean_code": (RULES / "clean_code.yaml", "5f279f456c0b13acc281e6b39a7aca24fa7af352e569bba72ff738cb9335ecea"),
    "ca_bundle": (SITE / "certifi/cacert.pem", "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"),
    "bugs": (RULES / "bugs.yaml", "0d207b87d5ecedae4a8273b0a57a8db693a1765b66ab714363d8a689de4e36b2"),
}
INVALID_RULE = (
    b"rules:\n- id: invalid-pattern\n  languages: [python]\n"
    b"  message: benign invalid pattern\n  severity: ERROR\n  pattern: '('\n"
)

CASES = {}
for _pack, _member in (("clean_code", "semgrepclean"), ("bugs", "semgrepbugs")):
    for _case in ("clean", "defective", "nosem"):
        _source = smoke.CLEAN if _case == "clean" else smoke.DEFECTS[_member]
        if _case == "nosem":
            _source = _source.rstrip() + "  # nosemgrep\n"
        CASES[f"{_pack}_{_case}"] = {
            "pack": _pack,
            "source": _source,
            "expected_rule": None if _case == "clean" else smoke.MEMBERS[_member][2],
        }
CASES.update(
    {
        "parse_error": {
            "pack": "clean_code",
            "source": "def broken():\n    print('unterminated\n",
            "expected_rule": None,
        },
        "invalid_rule": {"pack": "invalid", "source": smoke.CLEAN, "expected_rule": None},
    }
)


def _regular_file(path: Path, *, allow_interpreter_link: bool = False) -> None:
    if not path.is_absolute() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"absolute path with real parent directories required: {path}")
    if path.is_symlink() and not allow_interpreter_link:
        raise ValueError(f"symlink input rejected: {path}")
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"regular file required: {path}")


def sha256_file(path: Path, *, limit: int) -> str:
    """Bound hashing memory and bytes read, including concurrent file growth."""
    if path.stat().st_size > limit:
        raise ValueError(f"input size limit exceeded: {path}")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            total += len(block)
            if total > limit:
                raise ValueError(f"input size limit exceeded: {path}")
            digest.update(block)
    return digest.hexdigest()


def verify_file(
    path: Path, digest: str, *, limit: int, executable: bool = False, allow_interpreter_link: bool = False
) -> Path:
    _regular_file(path, allow_interpreter_link=allow_interpreter_link)
    if executable and not os.access(path, os.X_OK):
        raise ValueError(f"executable permission required: {path}")
    if sha256_file(path, limit=limit) != digest:
        raise ValueError(f"SHA-256 mismatch: {path}")
    return path


def validate_assets() -> tuple[dict, dict]:
    """Pin local reviewed bytes; do not execute version probes before validation."""
    assets = {}
    for name, (path, digest) in ASSET_PINS.items():
        assets[name] = verify_file(
            path,
            digest,
            limit=FILE_LIMIT
            if name == "core"
            else INPUT_LIMIT
            if name in {"frontend", "clean_code", "bugs"}
            else FILE_LIMIT,
            executable=name in {"python", "frontend", "core"},
            allow_interpreter_link=name == "python",
        )
    metadata = SITE / f"semgrep-{VERSION}.dist-info/METADATA"
    _regular_file(metadata)
    if metadata.stat().st_size > INPUT_LIMIT:
        raise ValueError("distribution metadata size limit exceeded")
    headers = metadata.read_text().split("\n\n", 1)[0].splitlines()
    if "Name: semgrep" not in headers or f"Version: {VERSION}" not in headers:
        raise ValueError("Semgrep distribution version mismatch")
    packs = {name: assets[name].read_bytes() for name in ("clean_code", "bugs")}
    for name, content in packs.items():
        if hashlib.sha256(content).hexdigest() != ASSET_PINS[name][1]:
            raise ValueError("rule pack changed after validation")
    return assets, packs


def _fixture_inputs(case: str, packs: dict) -> dict[str, bytes]:
    selected = CASES[case]
    pack = selected["pack"]
    return {
        "fixture.py": selected["source"].encode(),
        f"{pack}.yaml": INVALID_RULE if pack == "invalid" else packs[pack],
    }


def prepare_fixture(directory: Path, case: str, packs: dict) -> None:
    for name, content in _fixture_inputs(case, packs).items():
        path = directory / name
        if path.is_symlink():
            raise ValueError("symlink fixture rejected")
        path.write_bytes(content)
    verify_fixture(directory, case, packs)


def verify_fixture(directory: Path, case: str, packs: dict) -> None:
    for name, content in _fixture_inputs(case, packs).items():
        verify_file(directory / name, hashlib.sha256(content).hexdigest(), limit=INPUT_LIMIT)


def build_command(frontend: str, assets: dict, directory: Path, case: str) -> tuple[list[str], str]:
    if frontend not in {"python", "native"} or case not in CASES:
        raise ValueError("only fixed frontends and cases are supported")
    native = frontend != "python"
    command = ["osemgrep"] if native else [str(assets["python"]), "-I", "-B", str(assets["frontend"])]
    command += [
        "scan",
        *(["--experimental"] if native else ["--legacy"]),
        "--oss-only",
        "--jobs=1",
        "--metrics=off",
        "--disable-version-check",
        "--novcs",
        "--no-git-ignore",
        "--project-root",
        str(directory),
        "--disable-nosem",
        "--json",
        "--config",
        str(directory / f"{CASES[case]['pack']}.yaml"),
        "fixture.py",
    ]
    return command, str(assets["core"] if native else assets["python"])


def run_command(argv: list[str], *, executable: str, cwd: Path, env: dict) -> subprocess.CompletedProcess:
    """Reserve group leader PID through cleanup; no shell or unbounded pipes."""
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(  # pylint: disable=consider-using-with
            argv,
            executable=executable,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=errors,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        try:
            smoke.wait_worker_exit(process.pid, TIMEOUT_SECONDS, (output, errors))
        finally:
            try:
                smoke.terminate_worker_group(process.pid)
            finally:
                process.wait(timeout=10)
        captured = []
        for stream in (output, errors):
            stream.seek(0)
            content = stream.read(smoke.WORKER_OUTPUT_LIMIT + 1)
            if len(content) > smoke.WORKER_OUTPUT_LIMIT:
                raise ValueError("worker output limit exceeded")
            captured.append(content.decode("utf-8"))
        return subprocess.CompletedProcess(argv, process.returncode, *captured)


def _relative_path(value: object, directory: Path, *, rule_allowed: bool = False) -> str:
    if not isinstance(value, str) or not value or ".." in Path(value).parts:
        raise ValueError("invalid evidence path")
    path = Path(value)
    path = path if path.is_absolute() else directory / path
    try:
        relative = path.relative_to(directory).as_posix()
    except ValueError as exc:
        raise ValueError("evidence path outside fixture") from exc
    allowed = {"fixture.py"} | ({"clean_code.yaml", "bugs.yaml", "invalid.yaml"} if rule_allowed else set())
    if relative not in allowed:
        raise ValueError("evidence path outside fixed inputs")
    _regular_file(path)
    return relative


def _line(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("positive integer line required")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("nonempty evidence string required")
    return value


def _error_type(value: object, directory: Path) -> object:
    if isinstance(value, str):
        return _text(value)
    if not isinstance(value, list) or len(value) != 2 or value[0] != "PartialParsing" or not isinstance(value[1], list):
        raise ValueError("unsupported structured error type")
    locations = [
        {
            "path": _relative_path(location["path"], directory),
            "line": _line(location["start"]["line"]),
            "end_line": _line(location["end"]["line"]),
        }
        for location in value[1]
    ]
    if not locations:
        raise ValueError("partial parsing requires locations")
    return ["PartialParsing", locations]


def _error_tag(error: dict) -> str:
    value = error["type"]
    return value[0] if isinstance(value, list) else value


def _finding(item: dict, directory: Path) -> dict:
    return {
        "rule_id": _text(item["check_id"]),
        "path": _relative_path(item["path"], directory),
        "line": _line(item["start"]["line"]),
        "end_line": _line(item["end"]["line"]),
        "message": _text(item["extra"]["message"]),
        "severity": _text(item["extra"]["severity"]),
    }


def _error_span(span: dict, directory: Path) -> dict:
    location: dict[str, object] = {"line": _line(span["start"]["line"])}
    if "end" in span:
        location["end_line"] = _line(span["end"]["line"])
    if "file" in span:
        location["path"] = _relative_path(span["file"], directory, rule_allowed=True)
    return location


def _error_record(item: dict, directory: Path) -> dict:
    error: dict[str, object] = {"type": _error_type(item["type"], directory), "level": _text(item["level"])}
    if item.get("path") is not None:
        error["path"] = _relative_path(item["path"], directory, rule_allowed=True)
    if item.get("rule_id") is not None:
        error["rule_id"] = _text(item["rule_id"])
    spans = item.get("spans", [])
    if not isinstance(spans, list):
        raise ValueError("error spans array required")
    error["spans"] = [_error_span(span, directory) for span in spans]
    return error


def canonicalize(payload: dict, directory: Path) -> dict:
    """Project stable semantic evidence, retaining all findings and errors."""
    if not isinstance(payload, dict) or payload.get("version") != VERSION:
        raise ValueError("missing or incorrect JSON version")
    if not all(isinstance(payload.get(key), list) for key in ("results", "errors")):
        raise ValueError("results and errors arrays required")
    paths = payload.get("paths")
    if not isinstance(paths, dict) or not isinstance(paths.get("scanned"), list):
        raise ValueError("scanned target array required")
    try:
        findings = [_finding(item, directory) for item in payload["results"]]
        errors = [_error_record(item, directory) for item in payload["errors"]]
        scanned = [_relative_path(path, directory) for path in paths["scanned"]]
    except (KeyError, TypeError) as exc:
        raise ValueError("malformed semantic evidence") from exc
    if len(scanned) != len(set(scanned)):
        raise ValueError("duplicate scanned target evidence")
    return {
        "findings": sorted(findings, key=lambda item: json.dumps(item, sort_keys=True)),
        "errors": sorted(errors, key=lambda item: json.dumps(item, sort_keys=True)),
        "scanned": sorted(scanned),
    }


def execution_row(result: subprocess.CompletedProcess, directory: Path) -> dict:
    row = {"argv": result.args, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    row["canonical"] = canonicalize(json.loads(result.stdout), directory)
    return row


def _error_control(case: str, status: int, canonical: dict) -> bool:
    if canonical["findings"] or not canonical["errors"]:
        return False
    if case == "invalid_rule":
        return status > 1 and all(_error_tag(error) == "Rule parse error" for error in canonical["errors"])
    return status == 0 and all(_error_tag(error) in {"Syntax error", "PartialParsing"} for error in canonical["errors"])


def _expected_findings(case: str, findings: list) -> bool:
    expected = CASES[case]["expected_rule"]
    if expected is None:
        return not findings
    if len(findings) != 1:
        return False
    return all(
        findings[0][key] == value for key, value in {"rule_id": expected, "path": "fixture.py", "line": 2}.items()
    )


def _positive_control(case: str, row: dict) -> bool:
    if "canonical" not in row or "error" in row:
        return False
    canonical, status = row["canonical"], row["returncode"]
    if case in {"invalid_rule", "parse_error"}:
        return _error_control(case, status, canonical)
    if status != 0 or canonical["errors"] or canonical["scanned"] != ["fixture.py"]:
        return False
    return _expected_findings(case, canonical["findings"])


def assess_case(case: str, reference: dict, native: dict) -> dict:
    differences = [name for name in ("returncode", "canonical") if reference.get(name) != native.get(name)]
    controls = {"python": _positive_control(case, reference), "native": _positive_control(case, native)}
    return {
        "passed": not differences and all(controls.values()),
        "differences": differences,
        "positive_controls": controls,
        "python": reference,
        "native": native,
    }


def make_receipt(rows: dict, *, system: str, machine: str) -> dict:
    complete = {name: rows.get(name, {"passed": False, "error": "required case missing"}) for name in CASES}
    return {
        "evidence_kind": "native_semgrep_frontend_parity_only",
        "schema_version": 1,
        "execution": "controlled_maintainer_execution",
        "semgrep_version": VERSION,
        "sandbox_verified": False,
        "production_eligible": False,
        "single_process_verified": False,
        "system": system,
        "architecture": machine,
        "os_version": platform.platform(),
        "timeout_seconds_per_launch": TIMEOUT_SECONDS,
        "output_limit_bytes_per_stream": smoke.WORKER_OUTPUT_LIMIT,
        "passed": system == "Darwin"
        and machine == "arm64"
        and all(row.get("passed") is True for row in complete.values()),
        "cases": complete,
    }


def _frontend_execution(frontend: str, assets: dict, directory: Path, case: str, packs: dict) -> dict:
    raw = {}
    try:
        with tempfile.TemporaryDirectory(prefix=f"semgrep-{frontend}-home-") as home:
            env = smoke.controlled_env(
                Path(home).resolve(),
                {"system_tools": {"uname": "/usr/bin/uname"}, "ca_bundle": str(assets["ca_bundle"])},
            )
            verify_fixture(directory, case, packs)
            argv, executable = build_command(frontend, assets, directory, case)
            result = run_command(argv, executable=executable, cwd=directory, env=env)
            raw = {
                "argv": argv,
                "executable": executable,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            raw["canonical"] = canonicalize(json.loads(result.stdout), directory)
            verify_fixture(directory, case, packs)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raw["error"] = f"{type(exc).__name__}: {exc}"
    return raw


def run_parity() -> dict:
    started = time.monotonic()
    rows = {}
    receipt_assets = {}
    try:
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise ValueError("actual native evidence requires Darwin arm64")
        assets, packs = validate_assets()
        receipt_assets = {name: {"path": str(path), "sha256": digest} for name, (path, digest) in ASSET_PINS.items()}
        for case in CASES:
            with tempfile.TemporaryDirectory(prefix="native-semgrep-parity-") as temporary:
                directory = Path(temporary).resolve()
                prepare_fixture(directory, case, packs)
                executions = {
                    frontend: _frontend_execution(frontend, assets, directory, case, packs)
                    for frontend in ("python", "native")
                }
                rows[case] = assess_case(case, executions["python"], executions["native"])
    except (OSError, ValueError) as exc:
        rows = {case: {"passed": False, "error": f"{type(exc).__name__}: {exc}"} for case in CASES}
    receipt = make_receipt(rows, system=platform.system(), machine=platform.machine())
    receipt["timestamp_utc"] = datetime.now(UTC).isoformat()
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
    receipt["assets"] = receipt_assets
    receipt["smoke_sha256"] = hashlib.sha256(SMOKE_SOURCE).hexdigest()
    return receipt


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    receipt = run_parity()
    sys.stdout.write(json.dumps(receipt, indent=2) + "\n")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
