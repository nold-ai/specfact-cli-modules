"""Observe one failed signed review without granting acceptance."""

from __future__ import annotations

import argparse
import ast
import contextlib
import ctypes
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, BinaryIO, TypeGuard

import specfact_cli
import yaml
from specfact_cli.registry.crypto_validator import verify_signature
from specfact_cli.registry.module_installer import (
    _bundled_public_key_path,
    _load_public_key_pem,
    _module_artifact_payload_stable,
)


SUBJECT_HEAD = "9fb136d2770d6b472364ca311869dae24f3a319b"
SUBJECT_BASE = "593656f675eaf4954b609aca51aa6504367dc02e"
REGISTRY_REFERENCE = "209b4ed835187ea857d1fa847abdd351f6f6232a"
REGISTRY_SHA256 = "44ed5b79ff6e93742a8f5660443b9ed55990806bc57f6f9c1787d402586337e6"
KEY_SHA256 = "4e54ffb02307e1a85c166c40aba6d1bc40fbb9a8ef40bf756f8870e5bb08d1c8"
PROFILER_REQUIREMENT = "py-spy==0.4.2 --hash=sha256:aeb0323409199c785f730645e9f4bb7a7b9ca2c481f2c331a55642b5d13fa52f\n"
MAX_PROFILE_BYTES = 32 * 1024 * 1024
MAX_SAMPLES = 1_000_000


class Gap(StrEnum):
    IDENTITY_UNVERIFIED = "identity_unverified"
    PROFILE_INVALID = "profile_invalid"
    PROFILE_OVERSIZED = "profile_oversized"
    PROFILE_MISSING = "profile_missing"
    REVIEW_REPORT_MISSING = "review_report_missing"
    INSTALLATION_CHANGED = "installation_changed"
    MEMBER_JOIN_UNAVAILABLE = "member_join_unavailable"
    PROCESS_SAMPLE_JOIN_UNAVAILABLE = "process_sample_join_unavailable"
    NATIVE_COVERAGE_UNAVAILABLE = "native_coverage_unavailable"
    ORIGINAL_INSTALLATION_UNKNOWN = "original_installation_unknown"
    WARM_REPLAY = "warm_replay"
    PREPARATION_FAILED = "preparation_failed"
    PROFILER_FAILED = "profiler_failed"
    DEADLINE = "deadline"
    CANCELLED = "cancelled"
    CLEANUP_INCOMPLETE = "cleanup_incomplete"


def _integer(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _source_matches(path: Path, source: SourceIdentity) -> bool:
    return (
        not path.is_symlink()
        and path.resolve() == path
        and path.is_file()
        and hashlib.sha256(path.read_bytes()).hexdigest() == source.digest
    )


@dataclass(frozen=True)
class SourceIdentity:
    digest: str
    symbols: tuple[tuple[str, int, int], ...]
    relative: str


@dataclass(frozen=True)
class InstalledSymbols:
    files: dict[Path, SourceIdentity]

    @classmethod
    def from_verified_files(cls, root: Path, signed_files: dict[str, str]) -> InstalledSymbols:
        files = {}
        for relative, digest in sorted(signed_files.items()):
            path = root / relative
            if path.suffix != ".py":
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("source_identity")
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError("signed_source_changed")
            syntax = ast.parse(content)
            symbols = tuple(
                (node.name, node.lineno, node.end_lineno or node.lineno)
                for node in ast.walk(syntax)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            files[path.resolve()] = SourceIdentity(
                hashlib.sha256(content).hexdigest(), symbols, path.relative_to(root).as_posix()
            )
        return cls(files)

    def symbol(self, frame: dict[str, Any], checked: dict[Path, bool]) -> tuple[str | None, bool]:
        filename, name, line = frame.get("file"), frame.get("name"), frame.get("line")
        if not isinstance(filename, str) or not isinstance(name, str) or not _integer(line):
            return None, False
        path = Path(filename)
        source = self.files.get(path)
        if source is None:
            return None, False
        if path not in checked:
            checked[path] = _source_matches(path, source)
        if not checked[path]:
            return None, True
        if any(name == known and first <= line <= last for known, first, last in source.symbols):
            return f"{source.relative}:{name}", False
        return None, False


@dataclass(frozen=True)
class ProfileCounts:
    samples: int = 0
    symbols: tuple[tuple[str, int], ...] = ()
    gaps: tuple[Gap, ...] = ()


@dataclass(frozen=True)
class Observation:
    profile: ProfileCounts
    owned: int = 0
    elapsed_seconds: int = 0
    gaps: tuple[Gap, ...] = ()

    @classmethod
    def from_profile(cls, profile: ProfileCounts, *, owned: int) -> Observation:
        return cls(profile, owned)

    def to_public_json(self) -> str:
        gaps = sorted(
            set(
                self.profile.gaps
                + self.gaps
                + (
                    Gap.MEMBER_JOIN_UNAVAILABLE,
                    Gap.PROCESS_SAMPLE_JOIN_UNAVAILABLE,
                    Gap.NATIVE_COVERAGE_UNAVAILABLE,
                    Gap.ORIGINAL_INSTALLATION_UNKNOWN,
                    Gap.WARM_REPLAY,
                )
            )
        )
        return json.dumps(
            {
                "status": "DIAGNOSTIC_PARTIAL" if self.profile.samples else "DIAGNOSTIC_UNAVAILABLE",
                "acceptance": False,
                "baseline_result": "FAIL",
                "member": "member_unknown",
                "samples": min(MAX_SAMPLES, max(0, self.profile.samples)),
                "owned_processes": min(100_000, max(0, self.owned)),
                "processes_without_proved_sample_join": min(100_000, max(0, self.owned)),
                "observation_seconds": min(305, max(0, self.elapsed_seconds)),
                "sample_count_is_cpu_or_elapsed_time": False,
                "symbols": [{"symbol": symbol, "inclusive_samples": count} for symbol, count in self.profile.symbols],
                "gaps": gaps,
            },
            sort_keys=True,
        )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_field")
        value[key] = item
    return value


def _public_frames(frames: Any, symbols: InstalledSymbols) -> tuple[list[str | None], bool]:
    if not isinstance(frames, list) or len(frames) > 100_000:
        raise ValueError("frames_shape")
    public = []
    changed = False
    checked: dict[Path, bool] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("frame_shape")
        symbol, modified = symbols.symbol(frame, checked)
        public.append(symbol)
        changed |= modified
    return public, changed


def _sample_symbols(sample: Any, public: list[str | None]) -> set[str]:
    if not isinstance(sample, list) or len(sample) > 512:
        raise ValueError("sample_shape")
    selected = set()
    for index in sample:
        if not _integer(index) or not 0 <= index < len(public):
            raise ValueError("sample_index")
        symbol = public[index]
        if symbol is not None:
            selected.add(symbol)
    return selected


def _samples(profile: Any, public: list[str | None]) -> tuple[int, Counter[str]]:
    if not isinstance(profile, dict) or profile.get("type") != "sampled":
        raise ValueError("profile_type")
    samples = profile.get("samples")
    if not isinstance(samples, list) or len(samples) > MAX_SAMPLES:
        raise ValueError("samples_shape")
    counts: Counter[str] = Counter()
    for sample in samples:
        counts.update(_sample_symbols(sample, public))
    return len(samples), counts


def _profile_counts(data: Any, symbols: InstalledSymbols) -> ProfileCounts:
    public, changed = _public_frames(data["shared"]["frames"], symbols)
    profiles = data["profiles"]
    if not isinstance(profiles, list) or len(profiles) > 256:
        raise ValueError("profiles_shape")
    counts: Counter[str] = Counter()
    total = 0
    for profile in profiles:
        amount, observed = _samples(profile, public)
        total += amount
        if total > MAX_SAMPLES:
            raise ValueError("samples_limit")
        counts.update(observed)
    gaps = (Gap.INSTALLATION_CHANGED,) if changed else ()
    return ProfileCounts(total, tuple(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:30]), gaps)


def read_profile(path: Path, symbols: InstalledSymbols) -> ProfileCounts:
    try:
        if path.stat().st_size > MAX_PROFILE_BYTES:
            return ProfileCounts(gaps=(Gap.PROFILE_OVERSIZED,))
        with path.open("rb") as stream:
            raw = stream.read(MAX_PROFILE_BYTES + 1)
        if len(raw) > MAX_PROFILE_BYTES:
            return ProfileCounts(gaps=(Gap.PROFILE_OVERSIZED,))
        return _profile_counts(json.loads(raw, object_pairs_hook=_unique_object), symbols)
    except FileNotFoundError:
        return ProfileCounts(gaps=(Gap.PROFILE_MISSING,))
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        return ProfileCounts(gaps=(Gap.PROFILE_INVALID,))


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    parent: int
    started: int
    namespace: str
    state: str = ""


def same_process(original: ProcessIdentity, current: ProcessIdentity) -> bool:
    return (original.pid, original.started, original.namespace) == (current.pid, current.started, current.namespace)


def _process_identity(pid: int) -> ProcessIdentity | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
        return ProcessIdentity(pid, int(stat[1]), int(stat[19]), os.readlink(f"/proc/{pid}/ns/pid"), stat[0])
    except (OSError, ValueError, IndexError):
        return None


class OwnedProcesses:
    def __init__(self) -> None:
        self.identities: dict[int, ProcessIdentity] = {}
        self.handles: dict[int, int] = {}
        self.started = time.monotonic()

    def observe(self) -> None:
        pending = [
            identity
            for path in Path("/proc").iterdir()
            if path.name.isdigit() and (identity := _process_identity(int(path.name))) is not None
        ]
        while pending:
            added = False
            remaining = []
            for identity in pending:
                if not self._owned_parent(identity.parent):
                    remaining.append(identity)
                    continue
                self._remember(identity)
                added = True
            if not added:
                break
            pending = remaining

    def _owned_parent(self, pid: int) -> bool:
        if pid == os.getpid():
            return True
        parent = self.identities.get(pid)
        current = _process_identity(pid) if parent else None
        return parent is not None and current is not None and same_process(parent, current)

    def _remember(self, identity: ProcessIdentity) -> None:
        previous = self.identities.get(identity.pid)
        if previous is not None and same_process(previous, identity):
            return
        if identity.pid in self.handles:
            os.close(self.handles.pop(identity.pid))
        try:
            handle = os.pidfd_open(identity.pid)
            current = _process_identity(identity.pid)
            if current is None or not same_process(identity, current):
                os.close(handle)
                return
            self.identities[identity.pid] = identity
            self.handles[identity.pid] = handle
        except ProcessLookupError:
            return

    def cleanup(self) -> bool:
        deadline = time.monotonic() + 5
        empty_scans = 0
        while time.monotonic() < deadline:
            self.observe()
            for handle in self.handles.values():
                with contextlib.suppress(ProcessLookupError):
                    signal.pidfd_send_signal(handle, signal.SIGKILL)
            self._reap()
            self.observe()
            remaining = any(_process_identity(pid) is not None for pid in self.identities)
            empty_scans = 0 if remaining else empty_scans + 1
            if empty_scans == 2:
                self._close()
                return True
            time.sleep(0.05)
        self._close()
        return False

    @staticmethod
    def _reap() -> None:
        try:
            while os.waitpid(-1, os.WNOHANG)[0] != 0:
                pass
        except ChildProcessError:
            pass

    def has_live_descendants(self) -> bool:
        for original in self.identities.values():
            current = _process_identity(original.pid)
            if current is not None and same_process(original, current) and current.state not in {"Z", "X"}:
                return True
        return False

    def run(
        self,
        command: list[str],
        directory: Path,
        environment: dict[str, str],
        seconds: int,
        output: BinaryIO | None = None,
    ) -> tuple[int, int, bool]:
        with subprocess.Popen(
            command,
            cwd=directory,
            env=environment,
            start_new_session=True,
            stdout=output,
            stderr=subprocess.STDOUT if output else None,
        ) as process:
            try:
                while time.monotonic() - self.started < seconds:
                    self.observe()
                    code = process.poll()
                    if code is not None and not self.has_live_descendants():
                        break
                    time.sleep(0.1)
                else:
                    code = 124
            finally:
                previous = {sig: signal.signal(sig, signal.SIG_IGN) for sig in (signal.SIGINT, signal.SIGTERM)}
                try:
                    cleaned = self.cleanup()
                    process.wait(timeout=5)
                finally:
                    for sig, handler in previous.items():
                        signal.signal(sig, handler)
        return code, len(self.identities), cleaned

    def _close(self) -> None:
        for handle in self.handles.values():
            os.close(handle)
        self.handles.clear()


@dataclass(frozen=True)
class VerifiedContext:
    root: Path
    repository: Path
    attempt: Path
    symbols: InstalledSymbols
    environment: dict[str, str]
    deadline: float = float("inf")

    @property
    def python(self) -> str:
        return str(self.root / "venv/bin/python")


def _git(repository: Path, *args: str) -> bytes:
    command = ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repository), *args]
    with tempfile.TemporaryFile() as output:
        code, _, cleaned = OwnedProcesses().run(command, repository, dict(os.environ), 30, output)
        if code or not cleaned:
            raise ValueError("git_operation_failed")
        output.seek(0)
        return output.read()


@dataclass(frozen=True)
class VerifiedPackage:
    root: Path
    metadata: dict[str, Any]
    files: dict[str, str]


def _verify_package(package: Path, key: str) -> VerifiedPackage:
    if any(path.is_symlink() for path in package.rglob("*")):
        raise ValueError("package_symlink")
    metadata = yaml.safe_load((package / "module-package.yaml").read_text())
    payload = _module_artifact_payload_stable(package)
    integrity = metadata["integrity"]
    if integrity["checksum"] != "sha256:" + hashlib.sha256(payload).hexdigest():
        raise ValueError("package_checksum")
    if not verify_signature(payload, integrity["signature"], key):
        raise ValueError("package_signature")
    files = dict(entry.rsplit(":", 1) for entry in payload.decode().splitlines())
    return VerifiedPackage(package, metadata, files)


def _verified_modules(
    root: Path, repository: Path, key: str, rows: dict[str, Any]
) -> tuple[VerifiedPackage, list[dict[str, Any]]]:
    manifests = list((root / "home/.specfact/modules").glob("*/module-package.yaml"))
    if not manifests:
        raise ValueError("installation_missing")
    reviewer = None
    bindings = []
    for manifest in manifests:
        package = _verify_package(manifest.parent, key)
        metadata = package.metadata
        module_id = metadata["name"]
        name = module_id.removeprefix("nold-ai/")
        reference = yaml.safe_load(
            _git(repository, "show", f"{REGISTRY_REFERENCE}:packages/{name}/module-package.yaml")
        )
        if metadata["integrity"] != reference["integrity"] or metadata["version"] != rows[module_id]["latest_version"]:
            raise ValueError("installed_reference_mismatch")
        bindings.append({"name": name, "version": metadata["version"], "integrity": metadata["integrity"]})
        if module_id == "nold-ai/specfact-code-review" and metadata["version"] == "0.51.2":
            reviewer = package
    required = {"specfact-code-review", "specfact-codebase", "specfact-requirements", "specfact-project"}
    if reviewer is None or not required.issubset({binding["name"] for binding in bindings}):
        raise ValueError("reviewer_dependencies_missing")
    return reviewer, bindings


def _core_source_digest() -> str:
    root = Path(specfact_cli.__file__).resolve().parent
    files = [
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*.py"))
    ]
    return hashlib.sha256(json.dumps(files, separators=(",", ":")).encode()).hexdigest()


def verify_context(root: Path, repository: Path, attempt: Path) -> VerifiedContext:
    if sys.platform != "linux" or os.getuid() == 0 or specfact_cli.__version__ != "0.55.4":
        raise ValueError("platform_or_core")
    if not Path(specfact_cli.__file__).resolve().is_relative_to((root / "venv").resolve()):
        raise ValueError("core_location")
    key = _load_public_key_pem()
    if hashlib.sha256(_bundled_public_key_path().read_bytes()).hexdigest() != KEY_SHA256:
        raise ValueError("key_identity")
    registry = _git(repository, "show", f"{REGISTRY_REFERENCE}:registry/index.json")
    if hashlib.sha256(registry).hexdigest() != REGISTRY_SHA256:
        raise ValueError("registry_identity")
    rows = {row["id"]: row for row in json.loads(registry)["modules"]}
    reviewer, bindings = _verified_modules(root, repository, key, rows)
    environment = {
        "HOME": str(root / "home"),
        "TMPDIR": str(root / "tmp"),
        "PATH": str(root / "venv/bin") + ":/usr/bin:/bin",
        "SPECFACT_MODULES_BRANCH": "main",
        "SPECFACT_CODE_REVIEW_CAPSULE_CACHE": str(root / "cache"),
    }
    (attempt / "identity.private.json").write_text(
        json.dumps(
            {
                "core": "0.55.4",
                "core_observed_source_sha256": _core_source_digest(),
                "core_digest_authority": "observed_installed_sources_not_wheel_authentication",
                "registry_reference": REGISTRY_REFERENCE,
                "registry_sha256": REGISTRY_SHA256,
                "key_sha256": KEY_SHA256,
                "modules": bindings,
                "original_mutable_main_binding": "unknown",
                "workflow_head": _git(repository, "rev-parse", "HEAD").decode().strip(),
                "subject": SUBJECT_HEAD,
                "base": SUBJECT_BASE,
            }
        )
    )
    return VerifiedContext(
        root,
        repository,
        attempt,
        InstalledSymbols.from_verified_files(reviewer.root.resolve(), reviewer.files),
        environment,
    )


def _fixed_subject(context: VerifiedContext) -> Path:
    subject = context.attempt / "subject"
    _git(context.repository, "worktree", "add", "--detach", str(subject), SUBJECT_HEAD)
    if _git(subject, "rev-parse", "HEAD").decode().strip() != SUBJECT_HEAD:
        raise ValueError("subject_identity")
    if _git(subject, "merge-base", SUBJECT_HEAD, SUBJECT_BASE).decode().strip() != SUBJECT_BASE:
        raise ValueError("base_identity")
    key = _load_public_key_pem()
    for manifest in (subject / "packages").glob("*/module-package.yaml"):
        _verify_package(manifest.parent, key)
    _git(subject, "reset", "--soft", SUBJECT_BASE)
    if _git(subject, "write-tree") != _git(context.repository, "rev-parse", f"{SUBJECT_HEAD}^{{tree}}"):
        raise ValueError("index_identity")
    (context.attempt / "project.toml").write_text('manager = "hatch"\nenvironment = "default"\n')
    return subject


def _owned_run(
    context: VerifiedContext, command: list[str], seconds: int, output: BinaryIO | None = None
) -> tuple[int, int, bool]:
    owner = OwnedProcesses()
    try:
        available = context.deadline - time.monotonic() - 5
        if available <= 0:
            raise TimeoutError("diagnostic_deadline")
        budget = min(seconds, int(available)) if available != float("inf") else seconds
        return owner.run(command, context.root, context.environment, budget, output)
    finally:
        (context.attempt / "processes.private.json").write_text(
            json.dumps(
                [
                    {"pid": item.pid, "parent": item.parent, "started": item.started, "namespace": item.namespace}
                    for item in owner.identities.values()
                ]
            )
        )


def _checked_output(context: VerifiedContext, command: list[str], seconds: int) -> bytes:
    with tempfile.TemporaryFile() as output:
        code, _, cleaned = _owned_run(context, command, seconds, output)
        if code or not cleaned:
            raise ValueError("diagnostic_provisioning_failed")
        output.seek(0)
        return output.read(65536)


def _install_profiler(context: VerifiedContext) -> Path:
    destination = context.attempt / "profiler"
    _checked_output(context, [context.python, "-I", "-m", "venv", str(destination)], 60)
    requirements = context.attempt / "requirements.txt"
    requirements.write_text(PROFILER_REQUIREMENT)
    _checked_output(
        context,
        [
            str(destination / "bin/python"),
            "-I",
            "-m",
            "pip",
            "install",
            "--only-binary=:all:",
            "--no-deps",
            "--require-hashes",
            "-r",
            str(requirements),
        ],
        180,
    )
    profiler = destination / "bin/py-spy"
    version = _checked_output(context, [str(profiler), "--version"], 10)
    help_text = _checked_output(context, [str(profiler), "record", "--help"], 10)
    flags = (b"--duration", b"--rate", b"--idle", b"--subprocesses", b"--format", b"--pid")
    if version.strip() != b"py-spy 0.4.2" or any(flag not in help_text for flag in flags):
        raise ValueError("profiler_identity")
    return profiler


SAMPLER_BOOTSTRAP = """import os,subprocess,sys
child=subprocess.Popen(sys.argv[4:])
os.execv(sys.argv[1],[sys.argv[1],"record","--rate","10","--idle","--subprocesses",
 "--format","speedscope","--duration",sys.argv[3],"--output",sys.argv[2],"--pid",str(child.pid)])
"""


def diagnose_failed_review(context: VerifiedContext) -> Observation:
    if context.deadline - time.monotonic() < 310:
        return Observation(ProfileCounts(), gaps=(Gap.DEADLINE,))
    subject = _fixed_subject(context)
    wrapper = [context.python, "-I", str(context.root / "reviewer.py"), str(subject)]
    prepare = [*wrapper, "prepare-index", str(context.attempt / "project.toml")]
    available = context.deadline - time.monotonic() - 310
    if available <= 0:
        return Observation(ProfileCounts(), gaps=(Gap.DEADLINE,))
    preparation_budget = min(1800, int(available)) if available != float("inf") else 1800
    code, _, cleaned = _owned_run(context, prepare, preparation_budget)
    if code != 0 or not cleaned:
        return Observation(ProfileCounts(), gaps=(Gap.PREPARATION_FAILED,))
    profiler = _install_profiler(context)
    if context.deadline - time.monotonic() < 310:
        return Observation(ProfileCounts(), gaps=(Gap.DEADLINE,))
    profile = context.attempt / "profile.private.json"
    command = [
        context.python,
        "-I",
        "-c",
        SAMPLER_BOOTSTRAP,
        str(profiler),
        str(profile),
        "280",
        context.python,
        "-I",
        "-c",
        "import subprocess,sys\ntry:\n sys.exit(subprocess.run(sys.argv[1:],timeout=300,check=False).returncode)\n"
        "except subprocess.TimeoutExpired:\n sys.exit(124)",
        *wrapper,
        "code",
        "review",
        "run",
        "--scope",
        "index",
        "--enforcement",
        "changed",
        "--bug-hunt",
        "--project-config",
        str(context.attempt / "project.toml"),
        "--json",
        "--out",
        str(context.attempt / "review.private.json"),
    ]
    started = time.monotonic()
    code, owned, cleaned = _owned_run(context, command, 300)
    gaps = () if code == 0 else (Gap.DEADLINE if code == 124 else Gap.PROFILER_FAILED,)
    if not cleaned:
        gaps += (Gap.CLEANUP_INCOMPLETE,)
    if not (context.attempt / "review.private.json").is_file():
        gaps += (Gap.REVIEW_REPORT_MISSING,)
    return Observation(read_profile(profile, context.symbols), owned, int(time.monotonic() - started), gaps)


def _deadline(_signum: int, _frame: Any) -> None:
    raise TimeoutError("diagnostic_deadline")


def _cancel(_signum: int, _frame: Any) -> None:
    raise InterruptedError("cancelled")


@contextlib.contextmanager
def private_output(path: Path):
    sys.stdout.flush()
    sys.stderr.flush()
    stdout, stderr = os.dup(1), os.dup(2)
    try:
        with path.open("w") as private:
            os.dup2(private.fileno(), 1)
            os.dup2(private.fileno(), 2)
            with contextlib.redirect_stdout(private), contextlib.redirect_stderr(private):
                yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(stdout, 1)
        os.dup2(stderr, 2)
        os.close(stdout)
        os.close(stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    arguments = parser.parse_args()
    os.umask(0o077)
    root = arguments.trusted_root.resolve()
    attempt = Path(tempfile.mkdtemp(prefix="diagnostic-", dir=root))
    observation = Observation(ProfileCounts(), gaps=(Gap.IDENTITY_UNVERIFIED,))
    with private_output(attempt / "operations.private.log"):
        try:
            if not (root / "review-attempted").is_file():
                raise ValueError("review_not_attempted")
            if sys.platform != "linux" or ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
                raise ValueError("subreaper_unavailable")
            signal.signal(signal.SIGTERM, _cancel)
            signal.signal(signal.SIGINT, _cancel)
            deadline = time.monotonic() + 840
            signal.signal(signal.SIGALRM, _deadline)
            signal.alarm(840)
            context = verify_context(root, arguments.repository.resolve(), attempt)
            observation = diagnose_failed_review(replace(context, deadline=deadline))
        except TimeoutError:
            observation = Observation(ProfileCounts(), gaps=(Gap.DEADLINE,))
        except InterruptedError:
            observation = Observation(ProfileCounts(), gaps=(Gap.CANCELLED,))
        except (
            OSError,
            ValueError,
            RuntimeError,
            TypeError,
            KeyError,
            SyntaxError,
            AttributeError,
            subprocess.SubprocessError,
            yaml.YAMLError,
        ) as error:
            print(type(error).__name__, str(error), file=sys.stderr)
        finally:
            signal.alarm(0)
    print(observation.to_public_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
