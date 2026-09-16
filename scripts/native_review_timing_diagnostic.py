"""Time a separate exact-index review without accepting a failed developer hook."""

from __future__ import annotations

# Diagnostic controller APIs do not modify the signed worker.
# pylint: disable=protected-access
import argparse
import hashlib
import json
import os
import selectors
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

from icontract import ensure, require

from specfact_code_review.run import runner
from specfact_code_review.run.portable_snapshot import discover_snapshot
from specfact_code_review.run.runtime_builder import prepare_runtime
from specfact_code_review.run.runtime_interpreter import project_worker
from specfact_code_review.run.runtime_models import ProjectRuntimeError, document_digest


_PREFIXES = ("packages/", "registry/", "scripts/", "tools/", "tests/", "openspec/changes/")
_AUTHORITY = {"authority": "diagnostic-only", "acceptance": False}


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=repository, timeout=30)


@require(lambda repository: repository.is_dir())
@ensure(
    lambda repository, result: all(
        path.is_relative_to(repository) and path.suffix in {".py", ".pyi"} for path in result
    )
)
def staged_files(repository: Path) -> list[Path]:
    """Mirror the hook's staged Python target filtering and Git order."""
    names = _git(repository, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [
        repository / name
        for raw in names.split(b"\0")
        if (name := os.fsdecode(raw)).startswith(_PREFIXES) and name.endswith((".py", ".pyi"))
    ]


@require(lambda repository: repository.is_dir())
@ensure(lambda result: {"base", "tree", "worktree_diff", "untracked", "controls"} == set(result))
def source_state(repository: Path) -> dict[str, object]:
    """Bind original source, index, worktree differences and unchanged hook controls."""
    controls = [repository / ".pre-commit-config.yaml", *sorted((repository / "scripts").glob("pre*commit*"))]
    return {
        "base": _git(repository, "rev-parse", "HEAD").decode().strip(),
        "tree": _git(repository, "write-tree").decode().strip(),
        "worktree_diff": hashlib.sha256(_git(repository, "diff", "--binary")).hexdigest(),
        "untracked": hashlib.sha256(_git(repository, "ls-files", "--others", "--exclude-standard", "-z")).hexdigest(),
        "controls": {
            str(p.relative_to(repository)): hashlib.sha256(p.read_bytes()).hexdigest() for p in controls if p.is_file()
        },
    }


@require(lambda evidence: evidence.is_dir())
def is_review_timeout(evidence: Path) -> bool:
    """Only the exact original timeout with no original report is eligible."""
    log = evidence / "hooks.log"
    return (
        not (evidence / "code-review.json").exists()
        and log.is_file()
        and "Code review gate timed out after 300s" in log.read_text(errors="replace")
    )


@require(lambda repository, files: all(path.is_relative_to(repository) for path in files))
@ensure(lambda result: result[0][:8] == result[1][:8] and result[0][9:] == result[1][9:])
def review_commands(repository: Path, files: list[Path], evidence: Path) -> tuple[list[str], list[str]]:
    """Change only the original CLI's report sink, never selection or enforcement."""
    original = [
        str(repository / ".venv/bin/python"),
        "-m",
        "specfact_cli.cli",
        "code",
        "review",
        "run",
        "--json",
        "--out",
        ".specfact/code-review.json",
        "--enforcement",
        "changed",
        *(p.relative_to(repository).as_posix() for p in files),
    ]
    replay = list(original)
    replay[8] = str(evidence / "review.raw")
    return original, replay


@contextmanager
def _deadline(seconds: int):
    def expired(_signum, _frame):
        raise TimeoutError("diagnostic preparation deadline exceeded")

    previous = signal.signal(signal.SIGALRM, expired)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous)


@ensure(lambda result: result["acceptance"] is False)
def profile_cached_runtime(repository: Path, files: list[Path]) -> dict[str, object]:
    """Measure a reconstructed index cache; never claim the missing original identity."""
    if Path.cwd().resolve() != repository.resolve():
        raise ValueError("diagnostic must retain original repository cwd")
    with _deadline(900):
        runtime, reason = runner._prepare_capsule_runtime()
        if runtime is None:
            raise ValueError(reason)
        try:
            return _profile_index(runtime, files)
        finally:
            runner._cleanup_capsule_runtime(runtime)


def _profile_index(runtime, files: list[Path]) -> dict[str, object]:
    """Keep the private materialized snapshot alive through worker preparation."""
    with tempfile.TemporaryDirectory(prefix="specfact-timing-index-") as temporary:
        snapshot = runner._cached_analysis_snapshot(files, Path(temporary))
        if snapshot is None:
            raise ValueError("cached_snapshot_materialization_unavailable")
        plan = discover_snapshot(snapshot.root, config_path=None, source_snapshot=snapshot)
        with project_worker(runtime, plan) as selected:
            return _profile_selected(plan, selected)


def _profile_selected(plan, selected) -> dict[str, object]:
    """Measure only genuine cache lookup and, on exact miss, ordinary preparation."""
    start = time.monotonic()
    offline_miss = False
    prepared = None
    try:
        prepared = prepare_runtime(plan, runtime=selected, offline=True)
    except ProjectRuntimeError as exc:
        if str(exc).split(":", 1)[0] != "project_runtime_offline_cache_miss":
            raise
        offline_miss = True
    offline_seconds = time.monotonic() - start
    start = time.monotonic()
    if offline_miss:
        prepared = prepare_runtime(plan, runtime=selected)
    assert prepared is not None
    return {
        **_AUTHORITY,
        "source_identity": plan.source_identity,
        "project_identity": plan.identity,
        "worker_identity": selected.identity,
        "environment_id": selected.environment_id,
        "runtime_identity": prepared.identity,
        "bound_capsule_identity": document_digest({"capsule": selected.identity, "project_runtime": prepared.identity}),
        "offline_cache_miss": offline_miss,
        "offline_seconds": offline_seconds,
        "online_seconds": time.monotonic() - start if offline_miss else 0.0,
        "original_runtime_identity_known": False,
        "profile_limit_seconds": 900,
    }


@ensure(lambda result: len(result["processes"]) <= 4096)
def same_uid_pid_snapshot() -> dict[str, object]:
    """Collect bounded same-user process metadata, never argv or environment."""
    root = Path("/proc")
    if not (root / "uptime").is_file():
        return {"available": False, "processes": []}
    uptime = float((root / "uptime").read_text().split()[0])
    ticks = os.sysconf("SC_CLK_TCK")
    rows = []
    for entry in root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            data = (entry / "stat").read_text()
            tail = data.rsplit(")", 1)[1].split()
            rows.append(
                {
                    "pid": int(entry.name),
                    "ppid": int(tail[1]),
                    "pgid": int(tail[2]),
                    "elapsed_seconds": uptime - int(tail[19]) / ticks,
                    "cpu_seconds": (int(tail[11]) + int(tail[12])) / ticks,
                    "comm": data.split("(", 1)[1].rsplit(")", 1)[0][:128],
                }
            )
        except (OSError, ValueError, IndexError):
            continue
        if len(rows) >= 4096:
            break
    return {"available": True, "processes": rows, "truncated": len(rows) >= 4096}


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


class _Stream:
    """Retain a bounded prefix while hashing every observed stream byte."""

    def __init__(self, path: Path, limit: int):
        self.path = path
        self.limit = limit
        self.count = 0
        self.stored = 0
        self.digest = hashlib.sha256()
        self.complete = False
        path.write_bytes(b"")

    @require(lambda chunk: isinstance(chunk, bytes))
    @ensure(lambda self: 0 <= self.stored <= self.limit and self.stored <= self.count)
    def append(self, chunk: bytes) -> None:
        self.count += len(chunk)
        self.digest.update(chunk)
        retained = chunk[: max(0, self.limit - self.stored)]
        if retained:
            with self.path.open("ab") as destination:
                destination.write(retained)
            self.stored += len(retained)

    @ensure(lambda self, result: result["bytes"] == self.count and result["stored_bytes"] <= self.limit)
    def receipt(self) -> dict[str, object]:
        return {
            "bytes": self.count,
            "sha256": self.digest.hexdigest(),
            "stored_bytes": self.stored,
            "truncated": self.count > self.stored,
            "complete": self.complete,
        }


def _drain(process, streams, start: float, timeout: float) -> bool:
    """Observe complete pipes until the owned command deadline, then drain after killing."""
    timed_out = False
    with selectors.DefaultSelector() as selector:
        for name in streams:
            pipe = getattr(process, name)
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, streams[name])
        while selector.get_map():
            elapsed = time.monotonic() - start
            if elapsed >= timeout and not timed_out:
                timed_out = True
                _kill_group(process)
            if elapsed >= timeout + 3:
                break
            _read_ready_streams(selector, min(0.05, max(0.0, timeout + 3 - elapsed)))
        return _wait_owned_child(process, start, timeout) or timed_out


def _read_ready_streams(selector, wait_seconds: float) -> None:
    """Drain ready descriptors and distinguish EOF from a truncated observation."""
    for key, _ in selector.select(wait_seconds):
        chunk = os.read(key.fd, 65536)
        stream = key.data
        if chunk:
            stream.append(chunk)
        else:
            stream.complete = True
            selector.unregister(key.fileobj)


def _wait_owned_child(child, start: float, timeout: float) -> bool:
    """Reap the owned child within its remaining deadline, killing only its group."""
    timed_out = False
    if child.poll() is None:
        try:
            child.wait(timeout=max(0.0, timeout - (time.monotonic() - start)))
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(child)
    child.wait(timeout=3)
    return timed_out


@dataclass(frozen=True)
class CaptureLimits:
    """Independent execution deadline and stored stream-prefix budget."""

    timeout: float = 900
    prefix_bytes: int = 4 * 1024 * 1024


_DEFAULT_CAPTURE_LIMITS = CaptureLimits()


@require(lambda limits: 0 < limits.timeout <= 900 and 0 <= limits.prefix_bytes <= 4 * 1024 * 1024)
@ensure(lambda result: result["acceptance"] is False)
def capture_command(
    command: list[str],
    repository: Path,
    environment: dict[str, str],
    evidence: Path,
    *,
    limits: CaptureLimits = _DEFAULT_CAPTURE_LIMITS,
) -> dict[str, object]:
    """Drain both streams; kill only this replay's owned process group on timeout."""
    start = time.monotonic()
    streams = {name: _Stream(evidence / f"review.{name}", limits.prefix_bytes) for name in ("stdout", "stderr")}
    timed_out = False
    with subprocess.Popen(
        command, cwd=repository, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    ) as process:

        def cancelled(_signum, _frame):
            _kill_group(process)
            raise TimeoutError("diagnostic replay cancelled")

        old_handlers = {sig: signal.signal(sig, cancelled) for sig in (signal.SIGTERM, signal.SIGINT)}
        try:
            timed_out = _drain(process, streams, start, limits.timeout)
        finally:
            _kill_group(process)
            for sig, previous in old_handlers.items():
                signal.signal(sig, previous)
    return {
        **_AUTHORITY,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": time.monotonic() - start,
        **{name: stream.receipt() for name, stream in streams.items()},
    }


def _runtime_comparison(report, preparation: dict[str, object]) -> dict[str, object]:
    """Match the reconstructed runtime to the completed replay, not the absent original."""
    actual = report.get("scope_evidence", {}).get("project_runtime", {})
    members = report.get("analyzer_evidence", [])
    capsules = {row.get("capsule_identity") for row in members if row.get("capsule_identity")}
    fields = {
        "project_identity": "project_identity",
        "identity": "runtime_identity",
        "environment_id": "environment_id",
    }
    if actual.get("status") != "PASS" or not capsules or any(not actual.get(key) for key in fields):
        return {"status": "unavailable", "warm_runtime_identity_verified": False}
    matched = all(actual[key] == preparation[target] for key, target in fields.items()) and capsules == {
        preparation["bound_capsule_identity"]
    }
    return {"status": "match" if matched else "mismatch", "warm_runtime_identity_verified": matched}


@contextmanager
def _cancellation_guard():
    def cancelled(_signum, _frame):
        raise TimeoutError("diagnostic preparation cancelled")

    old = {sig: signal.signal(sig, cancelled) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


@require(lambda evidence: evidence.is_dir())
@ensure(lambda result: not result["report_present"] or {"raw_report_sha256", "runtime_comparison"} <= set(result))
def wrap_report(evidence: Path, preparation: dict[str, object]) -> dict[str, object]:
    raw = evidence / "review.raw"
    if not raw.is_file():
        return {"report_present": False}
    payload = raw.read_bytes()
    report = json.loads(payload)
    (evidence / "review.json").write_text(json.dumps({**_AUTHORITY, "report": report}, indent=2) + "\n")
    return {
        "report_present": True,
        "raw_report_sha256": hashlib.sha256(payload).hexdigest(),
        "runtime_comparison": _runtime_comparison(report, preparation),
    }


@ensure(lambda result: result in {0, 1})
def diagnose(repository: Path, evidence: Path) -> int:
    """Retain timings as diagnostic data while leaving the failed hook authoritative."""
    output = evidence / "review-timing"
    output.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, object] = {
        **_AUTHORITY,
        "schema": "native-review-timing-v1",
        "exclusive_execution_verified": False,
        "timings_may_overlap_original_workload": True,
        "timing_scope": "cached preparation and total replay only; no member timings",
        "startup_differences": ["separate diagnostic report sink", "PYTHONUNBUFFERED=1", "post-timeout cache state"],
        "review_limit_seconds": 900,
    }
    exit_code = 1
    before = None
    try:
        if not is_review_timeout(evidence) or (repository / ".specfact/code-review.json").exists():
            raise ValueError("original timeout without report required")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise ValueError("credential-free Hatch child required")
        for name in ("review.raw", "review.json"):
            (output / name).unlink(missing_ok=True)
        receipt["original_hook_log_sha256"] = hashlib.sha256((evidence / "hooks.log").read_bytes()).hexdigest()
        before = source_state(repository)
        receipt["source_before"] = before
        receipt["processes_before"] = same_uid_pid_snapshot()
        files = staged_files(repository)
        if not files:
            raise ValueError("no staged Python review inputs")
        preparation = _record_preparation(repository, files, receipt)
        original, replay = review_commands(repository, files, output)
        receipt.update(original_command=original, replay_command=replay)
        environment = dict(os.environ)
        environment.update(SPECFACT_CODE_REVIEW_CHANGED_DIFF="cached", PYTHONUNBUFFERED="1")
        receipt["replay"] = capture_command(replay, repository, environment, output)
        receipt.update(wrap_report(output, preparation))
        exit_code = 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        receipt["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        if not _record_final_identity(repository, before, receipt):
            exit_code = 1
        (output / "diagnostic.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return exit_code


def _record_preparation(repository, files, receipt) -> dict[str, object]:
    """Retain elapsed preparation time even when cancellation or preparation fails."""
    started = time.monotonic()
    try:
        with _cancellation_guard():
            preparation = profile_cached_runtime(repository, files)
            receipt["preparation"] = preparation
            return preparation
    finally:
        receipt["profile_elapsed_seconds"] = time.monotonic() - started


def _record_final_identity(repository, before, receipt) -> bool:
    """Fail the diagnostic when original source, controls or report authority changes."""
    try:
        receipt["processes_after"] = same_uid_pid_snapshot()
        if before is None:
            return True
        after = source_state(repository)
        receipt["source_after"] = after
        if after != before or (repository / ".specfact/code-review.json").exists():
            receipt["failure"] = "source/control/original-report identity changed during replay"
            return False
        return True
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        receipt["final_identity_failure"] = str(exc)
        return False


@ensure(lambda result: result in {0, 1})
def main() -> int:
    """Run only after the original hook failed with its existing timeout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    repository = args.checkout.resolve()
    os.chdir(repository)
    return diagnose(repository, args.evidence.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
