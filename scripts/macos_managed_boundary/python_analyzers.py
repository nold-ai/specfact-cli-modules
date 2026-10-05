"""Disjoint maintainer analyzer integration through exact native broker plans."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.util
import json
import os
import platform
import plistlib
import re
import shutil
import stat
import tempfile
from contextlib import redirect_stdout
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from scripts import build_macos_native_capsule as capsule_builder, native_runtime_inventory as macho
from scripts.macos_managed_boundary import control, project_acquisition, python_candidate as python


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
# The complete analyzer closure plus the pinned pip manager exceeds 512 MiB.
MAX_BYTES = 640 * 1024 * 1024
MAX_FILES = 30000
SEMGREP_PLAN_ID = "semgrep-1.175.0-offline-ca-v2"
SEMGREP_CA_SHA256 = "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
SEMGREP_CORE_SHA256 = "ec9b34d035688a7d8d77c7a45fe1cd2b8e8d9e15ac4f50071eada9c131925e53"
SEMGREP_REFERENCE_SHA256 = "efbae0e733db2ea821702d36f9dfdd377194a22f11335f4208d4a233a76075f8"
SEMGREP_HELPER_SHA256 = "471977480df00f50a7f3e624802db9d964f2afad0a9f6c01707e803ab51be45e"
SEMGREP_REFERENCE = REPO / ".specfact/native-compat/dependency-task-20261003/continuation/semgrep-adapter.json"

NODE_GUARD = """'use strict';
// Type-check namespace only; actual WASM is unsupported, never fabricated.
if (typeof globalThis.WebAssembly === 'undefined') {
  class UnsupportedWasm {
    constructor() { throw new Error('managed runtime incomplete: WASM execution not admitted; no host fallback'); }
  }
  const reject = () => Promise.reject(new Error('managed runtime incomplete: WASM execution not admitted; no host fallback'));
  globalThis.WebAssembly = Object.freeze({Instance: UnsupportedWasm, Module: UnsupportedWasm,
    Memory: UnsupportedWasm, Table: UnsupportedWasm, Global: UnsupportedWasm,
    RuntimeError: Error, CompileError: Error, LinkError: Error,
    compile: reject, instantiate: reject, compileStreaming: reject, instantiateStreaming: reject,
    validate: () => false});
}
"""
LIBRARY_EXPERIMENT_ENTITLEMENTS = {"com.apple.security.cs.disable-library-validation": True}


def record_bytes(path: Path, digest: str, size: str) -> bytes:
    """Verify selected installed input bytes; RECORD is not upstream authority."""
    if path.is_symlink() or not path.is_file() or not digest.startswith("sha256="):
        raise ValueError("selected input lacks regular SHA256 RECORD binding")
    if not size.isdigit() or int(size) > MAX_BYTES:
        raise ValueError("invalid selected RECORD size")
    data = path.read_bytes()
    calculated = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
    if len(data) != int(size) or calculated != digest.split("=", 1)[1]:
        raise ValueError("selected installed input does not match RECORD")
    return data


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def copy_site(venv: Path, payload: Path, version: str, lock: Path) -> dict[str, Any]:
    """Select exact installed files against lock versions and RECORD byte hashes."""
    source = (venv / "lib" / f"python{version}" / "site-packages").resolve(strict=True)
    destination = payload / "site-packages"
    destination.mkdir()
    lock_bytes = lock.read_bytes()
    pins = {
        canonical(name): version
        for name, version in re.findall(r"^([A-Za-z0-9_.-]+)==([^\s]+)", lock_bytes.decode(), re.M)
    }
    captured: dict[str, str] = {}
    distributions: dict[str, str] = {}
    total = 0
    for record in sorted(source.glob("*.dist-info/RECORD")):
        metadata = BytesParser().parsebytes((record.parent / "METADATA").read_bytes())
        name, installed = canonical(str(metadata["Name"])), str(metadata["Version"])
        if pins.get(name) != installed:
            raise ValueError("installed distribution does not match ABI lock")
        distributions[name] = installed
        for relative, digest, size in csv.reader(record.read_text().splitlines()):
            path = source / relative
            if relative.endswith((".pyc", ".pyo", ".dll", ".exe")):
                continue
            if relative.startswith("../"):
                if relative != "../../../bin/ruff":
                    continue  # Console scripts are replaced by explicit prepared entrypoints.
                destination_path = payload / "bin" / "ruff"
                if not path.resolve().is_relative_to(venv.resolve()):
                    raise ValueError("console executable escaped candidate input")
            else:
                if not path.resolve().is_relative_to(source):
                    raise ValueError("installed RECORD path escapes site-packages")
                # Admit only the OSS engine, its exact libs and pure metadata/code.
                if (
                    relative.startswith("semgrep/bin/")
                    and relative != "semgrep/bin/semgrep-core"
                    and not relative.startswith("semgrep/bin/libs/")
                ):
                    continue
                destination_path = destination / relative
            if not digest:
                if path != record:
                    raise ValueError("selected installed entry is unbound")
                data = record.read_bytes()
            else:
                data = record_bytes(path, digest, size)
            if relative == "z3/lib/libz3.5.1.dylib":
                canonical_library = source / "z3/lib/libz3.dylib"
                if canonical_library.is_symlink() or canonical_library.read_bytes() != data:
                    raise ValueError("versioned Z3 alias differs from selected library")
                captured["omitted-identical-z3-alias"] = hashlib.sha256(data).hexdigest()
                continue
            total += len(data)
            if total > MAX_BYTES or len(captured) >= MAX_FILES:
                raise ValueError("selected site budget exceeded")
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(data)
            destination_path.chmod(
                0o755 if relative == "../../../bin/ruff" or relative == "semgrep/bin/semgrep-core" else 0o644
            )
            captured[destination_path.relative_to(payload).as_posix()] = hashlib.sha256(data).hexdigest()
    if set(distributions) != set(pins):
        raise ValueError("candidate venv is not the complete pinned ABI closure")
    return {
        "lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "distributions": distributions,
        "selected_input_hashes": captured,
        "upstream_authenticated": False,
    }


def bind_rpaths(path: Path, image: dict[str, Any], payload: Path, command: Any) -> list[dict[str, Any]]:
    """Replace only known external engine search roots with exact bundled libs."""
    external = []
    for rpath in image["rpaths"]:
        try:
            macho.expand_path(rpath, path, payload / "bin/python", payload)
        except ValueError:
            external.append(rpath)
    if not external:
        return []
    allowed = {
        f"/opt/homebrew/opt/{name}/lib" for name in ("dwarfutils", "gmp", "libev", "pcre2", "zstd", "tree-sitter")
    } | {"/usr/local/opt/tree-sitter/lib"}
    libraries = path.parent / "libs"
    for dependency in image["dependencies"]:
        name = dependency["name"]
        if name.startswith("@rpath/"):
            suffix = name.removeprefix("@rpath/")
            if Path(suffix).name != suffix or not (libraries / suffix).is_file() or (libraries / suffix).is_symlink():
                raise ValueError("rpath dependency lacks exact bundled dylib")
    if path.name != "semgrep-core" or not set(external).issubset(allowed):
        raise ValueError("unapproved external native rpath")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    for rpath in external:
        command(["/usr/bin/install_name_tool", "-delete_rpath", rpath, str(path)])
    if "@loader_path/libs" not in image["rpaths"]:
        command(["/usr/bin/install_name_tool", "-add_rpath", "@loader_path/libs", str(path)])
    return [
        {
            "image": path.relative_to(payload).as_posix(),
            "removed": external,
            "bound": "@loader_path/libs",
            "input_sha256": before,
            "relocated_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    ]


def copy_node(payload: Path) -> dict[str, Any]:
    """Copy exact existing candidate manifest inputs, without running Node."""
    source = REPO / ".specfact/native-node-runtime"
    manifest_bytes = (source / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    destination = payload / "node"
    destination.mkdir()
    for name, record in manifest["files"].items():
        path = source / name
        if not path.resolve().is_relative_to(source) or path.is_symlink():
            raise ValueError("node manifest path escapes selected candidate")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("node input does not match selected manifest")
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        output.chmod(record["mode"])
    return {
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "files": manifest["files"],
        "production_eligible": False,
    }


def write_manager_plans(payload: Path) -> dict[str, str]:
    """Bind the four admitted offline adapters into the immutable payload."""
    plans: dict[str, str] = {}
    for manager, version in sorted(project_acquisition.MANAGER_VERSIONS.items()):
        destination = payload / "managers" / manager / "adapter.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "schema": "specfact-native-manager-plan-v1",
            "manager": {"name": manager, "version": version},
            "module": "specfact_code_review.run.native_project_manager",
            "operation": "authenticated-offline-wheel-preparation",
            "platform": "macos-arm64",
            "abis": ["cp311", "cp312", "cp313"],
            "executes_project_code": False,
            "uses_host_manager": False,
            "uses_network": False,
        }
        payload_bytes = json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
        destination.write_bytes(payload_bytes)
        destination.chmod(0o444)
        plans[manager] = hashlib.sha256(payload_bytes).hexdigest()
    return plans


def exact_inventory(payload: Path) -> dict[str, Any]:
    """Reuse no-link byte/mode inventory with explicit analyzer candidate budgets."""
    return python.inventory(payload, max_files=MAX_FILES, max_bytes=MAX_BYTES)


def static_inventory(payload: Path) -> dict[str, Any]:
    """Retain strict Mach-O resolution within explicit candidate-only budgets."""
    images = {}
    for name, record in exact_inventory(payload).items():
        if record["kind"] != "file":
            continue
        path = payload / name
        image = macho._inspect_image(path, payload, len(images))
        if image is not None:
            images[path] = image
    if not images:
        raise ValueError("selected closure contains no native image")
    return {
        "kind": "candidate-static-macho-inventory",
        "images": list(images.values()),
        "resolutions": macho.resolve_closure(images, payload),
        "production_eligible": False,
    }


def install_managed_git(candidate: dict[str, Any]) -> None:
    """Admit only an explicit verified maintainer Git artifact into the payload."""
    source = os.environ.get("SPECFACT_MANAGED_GIT_ARTIFACT")
    if source:
        candidate["managed_git"] = capsule_builder.install_managed_git_input(Path(source), candidate["payload"])


def inspect_managed_git_signature(path: Path, tools: Any) -> tuple[str, str]:
    """Read the existing Git identity; never rewrite its reviewed signature."""
    tools.command(["/usr/bin/codesign", "--verify", "--strict", str(path)])
    details = tools.command(["/usr/bin/codesign", "--display", "--verbose=4", str(path)]).stderr
    entitlements = tools.command(["/usr/bin/codesign", "--display", "--entitlements", ":-", str(path)]).stdout
    return details, entitlements


def prepare(root: Path, venv: Path, version: str, *, library_loading_experiment: bool = False) -> dict[str, Any]:
    runtime = (venv / "bin/python").resolve(strict=True).parent.parent
    candidate = python.prepare(root, runtime, version)
    payload = candidate["payload"]
    candidate["site"] = copy_site(
        venv,
        payload,
        version,
        REPO / f"scripts/native_analyzer_inputs/darwin-arm64-cp{python.version_key(version)}.txt",
    )
    code = payload / "trusted"
    code.mkdir()
    # Copy only regular trusted repository sources; never project source into broker.
    for source_root, destination in (
        (REPO / "packages/specfact-code-review/src/specfact_code_review", code / "specfact_code_review"),
    ):
        for path in source_root.rglob("*"):
            if path.is_file() and not path.is_symlink() and path.suffix != ".pyc" and "__pycache__" not in path.parts:
                output = destination / path.relative_to(source_root)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(path.read_bytes())
    for name in ("managed_subprocess.py", "python_analyzer_worker.py"):
        (code / name).write_bytes((HERE / name).read_bytes())
    (code / "node_guard.cjs").write_text(NODE_GUARD)
    candidate["platform_evidence"] = {"system": platform.system(), "machine": platform.machine()}
    candidate["semgrep_plan_id"] = SEMGREP_PLAN_ID
    validate_semgrep(candidate)
    candidate["node"] = copy_node(payload)
    managed_uv = os.environ.get("SPECFACT_MANAGED_UV_ARTIFACT")
    if managed_uv:
        from scripts import build_macos_managed_uv

        source = Path(managed_uv)
        provenance = build_macos_managed_uv.validate_artifact(source)
        destination = payload / "uv"
        shutil.copytree(source, destination)
        if build_macos_managed_uv.validate_artifact(destination) != provenance:
            raise ValueError("managed uv artifact changed during copying")
        candidate["managed_uv"] = provenance
    install_managed_git(candidate)
    candidate["manager_plans"] = write_manager_plans(payload)
    rewrites = []
    for name, record in exact_inventory(payload).items():
        if record["kind"] != "file":
            continue
        path = payload / name
        image = macho._inspect_image(path, payload, 0)
        if image:
            rewrites.extend(bind_rpaths(path, image, payload, control.STARTUP.command))
    candidate["loader_rewrites"] = rewrites
    # Static closure captures all selected native built-ins/extensions/dylibs.
    candidate["native_closure"] = static_inventory(payload)
    for image in candidate["native_closure"]["images"]:
        if "arm64" not in image["architectures"]:
            raise ValueError("incompatible selected native image")
    tools = control.BUILD.BuildTools(
        control.STARTUP.command, control.verify_native_clock, control.require, control.MACH.prepare
    )
    signed = []
    for image in candidate["native_closure"]["images"]:
        path = payload / image["path"]
        if image["path"] == "git/bin/git":
            details, entitlements = inspect_managed_git_signature(path, tools)
        elif (path == candidate["target"] or path.name == "semgrep-core") and library_loading_experiment:
            entitlement_path = root / "interpreter-library-loading.plist"
            entitlement_path.write_bytes(plistlib.dumps(LIBRARY_EXPERIMENT_ENTITLEMENTS))
            tools.command(
                [
                    "/usr/bin/codesign",
                    "--force",
                    "--sign",
                    "-",
                    "--options",
                    "runtime",
                    "--entitlements",
                    str(entitlement_path),
                    str(path),
                ]
            )
            tools.command(["/usr/bin/codesign", "--verify", "--strict", str(path)])
            details = tools.command(["/usr/bin/codesign", "--display", "--verbose=4", str(path)]).stderr
            entitlements = tools.command(["/usr/bin/codesign", "--display", "--entitlements", ":-", str(path)]).stdout
            if (
                plistlib.loads(entitlements.encode()) != LIBRARY_EXPERIMENT_ENTITLEMENTS
                or "Signature=adhoc" not in details
                or "runtime" not in details
            ):
                raise ValueError("unexpected interpreter library-loading identity")
        else:
            details, entitlements = control.BUILD._sign(path, tools)
        signed.append(
            {
                "path": image["path"],
                "signing": details,
                "entitlements": entitlements,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    candidate["signed_images"] = signed
    if (
        "managed_git" in candidate
        and capsule_builder.verify_managed_git_input(payload / "git") != candidate["managed_git"]
    ):
        raise ValueError("managed Git input changed during analyzer preparation")
    candidate["library_loading_experiment"] = library_loading_experiment
    candidate["profile_id"] = (
        "cpython-analyzers-library-loading-v1"
        if library_loading_experiment
        else "cpython-analyzers-empty-entitlements-v1"
    )
    for path in payload.rglob("*"):
        path.chmod(0o555 if path.is_dir() or os.access(path, os.X_OK) else 0o444)
    payload.chmod(0o555)
    candidate["inventory"] = exact_inventory(payload)
    candidate["native_closure"] = static_inventory(payload)
    return candidate


def plan_profile(candidate: dict[str, Any], domain: Path, stage: Path, target: Path) -> str:
    payload = candidate["payload"]
    metadata = {payload, domain, stage}
    for path in (payload, domain, stage, *(Path(root) for root in python.SYSTEM_ROOTS)):
        metadata.update(path.parents)

    ancestors = " ".join(f"(literal {python._literal(path)})" for path in sorted(metadata))
    system = " ".join(f"(subpath {python._literal(path)})" for path in python.SYSTEM_ROOTS)
    native = " ".join(f"(literal {python._literal(payload / item['path'])})" for item in candidate["signed_images"])
    return (
        "(version 1)(deny default)(deny process-fork)(deny mach-task-exception-port-set)(allow signal (target self))"
        '(allow sysctl-read (sysctl-name "kern.ostype") (sysctl-name "kern.osrelease")'
        ' (sysctl-name "kern.version") (sysctl-name "kern.hostname") (sysctl-name "hw.machine")'
        ' (sysctl-name "vm.pagesize") (sysctl-name "hw.pagesize_compat") (sysctl-name "hw.pagesize") (sysctl-name "hw.ncpu") (sysctl-name "hw.activecpu"))'
        '(allow file-read* (literal "/"))'
        f"(allow file-read* (subpath {python._literal(payload)}) {system})(allow file-read-metadata {ancestors})"
        f"(allow file-map-executable {native} {system})(allow process-exec (literal {python._literal(target)}))"
        f"(allow file-read* (subpath {python._literal(domain)}) (literal {python._literal(stage / 'request.json')}) (subpath {python._literal(stage / 'io')}))"
        f"(allow file-write* (subpath {python._literal(domain)}) (subpath {python._literal(stage / 'io')}))"
        '(allow file-read* file-write* (literal "/dev/null"))'
        + "".join(
            f"(deny file-write* (literal {python._literal(path)}))"
            for path in domain.iterdir()
            if path.is_file() and (path.suffix in (".py", ".ini") or path.name == ".coveragerc")
        )
    )


def read_output(path: Path) -> str:
    """Bound private native output before UTF-8 decoding, without following links."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return ""
    except OSError as error:
        raise ValueError("native output must be regular") from error
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("native output must be regular")
        data = stream.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("native output exceeds bounded capture")
    return data.decode("utf-8")


def fixed_environment(candidate: dict[str, Any], domain: Path) -> dict[str, str]:
    certificate = candidate["payload"] / "site-packages/certifi/cacert.pem"
    record = candidate["inventory"].get("site-packages/certifi/cacert.pem", {})
    if (
        certificate.is_symlink()
        or not certificate.is_file()
        or record.get("kind") != "file"
        or record.get("sha256") != SEMGREP_CA_SHA256
        or hashlib.sha256(certificate.read_bytes()).hexdigest() != record.get("sha256")
    ):
        raise ValueError("Semgrep certificate bundle lacks immutable inventory binding")
    return {
        "SSL_CERT_FILE": str(certificate),
        "PATH": "/nonexistent",
        "HOME": str(domain),
        "TMPDIR": str(domain),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
    }


def execute(
    root: Path,
    candidate: dict[str, Any],
    domain: Path,
    target: Path,
    argv: list[str],
    *,
    request: dict[str, Any],
    assert_process_denied: bool = False,
) -> dict[str, Any]:
    """Build-owned fixed argv/environment; native broker is the only process creator."""
    if exact_inventory(candidate["payload"]) != candidate["inventory"]:
        raise ValueError("analyzer payload changed before launch")
    if target.name == "semgrep-core":
        validate_semgrep(candidate)
        if request.get("plan_id") != SEMGREP_PLAN_ID:
            raise ValueError("native Semgrep requires its immutable versioned plan ID")
    stage = Path(tempfile.mkdtemp(prefix="stage-", dir=root))
    (stage / "request.json").write_text(json.dumps(request))
    stage.chmod(0o700)
    (stage / "io").mkdir(mode=0o700)
    (stage / "request.json").chmod(0o444)
    code = candidate["payload"] / "trusted" / "python_analyzer_worker.py"
    if target == candidate["target"]:
        argv = [str(target), "-I", "-S", "-B", str(code), str(stage / "request.json")]
    environment = fixed_environment(candidate, domain)
    tools = control.BUILD.BuildTools(
        control.STARTUP.command, control.verify_native_clock, control.require, control.MACH.prepare
    )
    args, inputs = control.BUILD._inputs(stage, HERE, tools)
    (stage / "python_candidate_policy.h").write_text(
        ("#define CANDIDATE_ASSERT_PROCESS_DENIED 1\n" if assert_process_denied else "")
        + f"#define PYTHON_PROFILE {json.dumps(plan_profile(candidate, domain, stage, target))}\n"
        + "#define CANDIDATE_FIXED_ARGV {"
        + ",".join(python._literal(arg) for arg in argv)
        + ",NULL}\n"
        + "#define CANDIDATE_FIXED_ENV {"
        + ",".join(python._literal(f"{key}={value}") for key, value in environment.items())
        + ",NULL}\n"
        + f"#define CANDIDATE_CWD {python._literal(domain)}\n"
        + f"#define CANDIDATE_STDOUT {python._literal(stage / 'io/stdout')}\n"
        + f"#define CANDIDATE_STDERR {python._literal(stage / 'io/stderr')}\n"
    )
    target_details = next(
        item
        for item in candidate["signed_images"]
        if item["path"] == target.relative_to(candidate["payload"]).as_posix()
    )
    target_hash = control.BUILD._cdhash({"name": "candidate", "signing": target_details["signing"]}, tools)
    target_macro = "-DFIXED_TARGET=" + python._literal(target)
    worker = stage / "control-worker"
    item = control.BUILD._compile(HERE / "python_candidate.c", worker, tools, [f"-I{stage}", target_macro])
    worker_hash = control.BUILD._cdhash(item, tools)
    observer = stage / "control-observer"
    observer_item = control.BUILD._compile(HERE / "startup_observe.c", observer, tools, [])
    args += [
        "-DFIXED_WORKER=" + python._literal(worker),
        "-DWORKER_REQUIREMENT=" + json.dumps(f'cdhash H"{worker_hash}"'),
        target_macro,
        "-DTARGET_REQUIREMENT=" + json.dumps(f'cdhash H"{target_hash}"'),
        "-framework",
        "Security",
        "-framework",
        "CoreFoundation",
    ]
    broker = stage / "control-broker"
    broker_item = control.BUILD._compile(HERE / "control_broker.c", broker, tools, args)
    with control.Invocation(broker, observer, stage) as invocation:
        client = invocation.connect()
        launched = client.launch(6, timeout_ms=5000)
        status = client.request(2, handle=launched["handle"])
        marker = control._event_from_file(invocation.directory / "events", "exec", launched["pid"])
        verified = (
            marker is not None
            and marker.get("exec") == launched["pid"]
            and marker.get("held") is False
            and status.get("traced") is True
        )
        if target == candidate["target"]:
            entry_file = stage / "io/python-entry.json"
            entry = json.loads(entry_file.read_text()) if entry_file.exists() else {}
            verified = (
                verified
                and marker is not None
                and entry.get("pid") == launched["pid"]
                and type(entry.get("entry_ns")) is int
                and entry["entry_ns"] >= marker["verified_ns"]
            )
        result = {
            "returncode": status["exit"] if not status["signal"] else -status["signal"],
            "stdout": read_output(stage / "io/stdout"),
            "stderr": read_output(stage / "io/stderr"),
            "broker_verified": verified,
            "status": status,
            "image_stop": marker,
            "stage": str(stage),
            "artifacts": {
                "worker": item,
                "observer": observer_item,
                "broker": broker_item,
                "inputs": inputs,
                "plan": {
                    "id": SEMGREP_PLAN_ID if target.name == "semgrep-core" else "cpython-analyzers-fixed-v1",
                    "argv": argv,
                    "environment": environment,
                    "profile": plan_profile(candidate, domain, stage, target),
                    "header_sha256": hashlib.sha256((stage / "python_candidate_policy.h").read_bytes()).hexdigest(),
                    "request_sha256": hashlib.sha256((stage / "request.json").read_bytes()).hexdigest(),
                },
            },
        }
    result["process_denial_verified"] = (
        assert_process_denied and "candidate-process-denial=fork:EPERM,spawn:EPERM" in result["stderr"] and verified
    )
    if exact_inventory(candidate["payload"]) != candidate["inventory"]:
        raise ValueError("analyzer payload changed after launch")
    (stage / "native-result.json").write_text(json.dumps(result, indent=2))
    return result


def load_candidate(root: Path) -> dict[str, Any]:
    candidate = json.loads((root / "candidate.json").read_text())
    for key in ("payload", "target"):
        candidate[key] = Path(candidate[key])
    return candidate


def admit_request(
    candidate: dict[str, Any], domain: Path, member: str, request: dict[str, Any]
) -> tuple[Path, list[str], dict[str, Any]]:
    """Resolve a trusted fixed fixture request; no general host argv API exists."""
    expected = {"semgrepclean": "semgrep", "semgrepbugs": "semgrep", "pytestcoverage": "pytestcoverage"}.get(
        member, member
    )
    if request.get("tool") != expected or request.get("cwd") != str(domain):
        raise ValueError("request outside bound analyzer domain")
    argv = request.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or len(argv) > 128
        or any(not isinstance(arg, str) or "\0" in arg for arg in argv)
    ):
        raise ValueError("invalid bound analyzer argv")
    payload = candidate["payload"]
    logical = payload / "bin" / (f"python{candidate['version']}" if member == "pytestcoverage" else expected)
    if argv[0] != str(logical):
        raise ValueError("request executable is not the prebound analyzer")
    # This integration accepts fixed harmless fixtures only. All requests are
    # retained with code/domain hashes; project-provided commands are not admitted.
    allowed_prefix = {
        "ruff": ["check", "--output-format", "json"],
        "radon": ["cc", "-j"],
        "pylint": ["--output-format", "json"],
        "contracts": ["check", "--per_path_timeout", "2"],
        "semgrep": ["--disable-version-check", "--quiet", "--disable-nosem"],
    }
    if (
        expected in allowed_prefix
        and argv[1 : 1 + len(allowed_prefix[expected])] != allowed_prefix[expected]
        and not (expected == "radon" and argv[1:3] in (["mi", "-j"], ["hal", "-j"]))
    ):
        raise ValueError("request argv does not match fixed adapter plan")
    if expected == "ruff":
        return payload / "bin/ruff", argv, {"kind": "native-tool"}
    if expected == "semgrep":
        target = payload / "site-packages/semgrep/bin/semgrep-core"
        command = [
            "osemgrep",
            "scan",
            "--experimental",
            "--oss-only",
            "--jobs=1",
            "--metrics=off",
            "--novcs",
            "--no-git-ignore",
            "--project-root",
            str(domain),
            "--no-rewrite-rule-ids",
            *argv[1:],
        ]
        return target, command, {"kind": "native-tool", "plan_id": SEMGREP_PLAN_ID}
    if expected == "basedpyright":
        target = payload / "node/bin/node"
        return (
            target,
            [
                str(target),
                "--jitless",
                "--unhandled-rejections=warn",
                "--require",
                str(payload / "trusted/node_guard.cjs"),
                str(payload / "node/basedpyright/index.js"),
                *argv[1:],
            ],
            {"kind": "native-tool"},
        )
    tool_request = {
        "kind": "tool",
        "tool": expected,
        "argv": argv,
        "abi": list(map(int, candidate["version"].split("."))),
        "version": candidate["version"],
    }
    if expected == "pytestcoverage" and (
        len(argv) < 4 or argv[1] != "-c" or not argv[-1].startswith("test_fixture.py::")
    ):
        raise ValueError("pytest request does not match selected fixed observer plan")
    return candidate["target"], [], tool_request


def native_incomplete(member: str, response: dict[str, Any]) -> str | None:
    if member.startswith("semgrep") and "Failure: run ['uname' '-s']" in response.get("stderr", ""):
        return "unadapted native process request: Semgrep uname bootstrap; no host fallback"
    return None


def adapter_case(root: Path, candidate: dict[str, Any], member: str, case: str) -> dict[str, Any]:
    from scripts import native_analyzer_smoke as fixtures

    domain = root / f"{member}-{case}"
    domain.mkdir(mode=0o700, exist_ok=True)
    source = (
        (fixtures.CONTRACT_CLEAN if member == "contracts" else fixtures.CLEAN)
        if case == "clean"
        else fixtures.DEFECTS[member]
    )
    path = domain / "fixture.py"
    if path.exists():
        if path.read_text() != source:
            raise ValueError("existing fixed project fixture differs")
    else:
        path.write_text(source)
        path.chmod(0o444)
    if member == "pytestcoverage":
        (domain / "test_fixture.py").write_text(
            "from fixture import increment\n\ndef test_increment():\n    assert increment(1) == 2\n"
        )
        (domain / "pytest.ini").write_text("[pytest]\n")
        (domain / ".coveragerc").write_text("[run]\nbranch = False\n")
        for name in ("test_fixture.py", "pytest.ini", ".coveragerc"):
            (domain / name).chmod(0o444)
    replies = []
    stages = []
    row = {
        "completed": False,
        "member": member,
        "case": case,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "stages": stages,
    }
    for _ in range(8):
        request = {
            "kind": "adapter",
            "member": member,
            "abi": list(map(int, candidate["version"].split("."))),
            "version": candidate["version"],
            "replies": replies,
        }
        execution = execute(root, candidate, domain, candidate["target"], [], request=request)
        stages.append(
            {
                "kind": "adapter",
                "stage": execution["stage"],
                "returncode": execution["returncode"],
                "broker_verified": execution["broker_verified"],
            }
        )
        stage = Path(execution["stage"])
        if not execution["broker_verified"]:
            row["incomplete"] = "dynamic image verification missing"
            break
        if execution["returncode"] == 0 and (stage / "io/adapter.json").is_file():
            row.update(json.loads((stage / "io/adapter.json").read_text()), completed=True)
            break
        if execution["returncode"] != 75 or not (stage / "io/pending.json").is_file():
            row["incomplete"] = (
                "analyzer stage failed or unadapted native process creation (private diagnostics retained)"
            )
            break
        pending = json.loads((stage / "io/pending.json").read_text())
        try:
            target, argv, child = admit_request(candidate, domain, member, pending)
            response = execute(root, candidate, domain, target, argv, request=child)
        except ValueError as error:
            row["incomplete"] = str(error)
            break
        stages.append(
            {
                "kind": "tool",
                "stage": response["stage"],
                "returncode": response["returncode"],
                "broker_verified": response["broker_verified"],
            }
        )
        if not response["broker_verified"] or response["returncode"] in (-9, -5):
            row["incomplete"] = "tool stage exceeded broker bound or attempted an unadapted exec; no host fallback"
            break
        reason = native_incomplete(member, response)
        if reason:
            row["incomplete"] = reason
            break
        replies.append(
            {
                "request": pending,
                "result": {key: response[key] for key in ("returncode", "stdout", "stderr", "broker_verified")},
            }
        )
    else:
        row["incomplete"] = "managed request stage budget exceeded"
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["source_sha256"]:
        raise ValueError("project fixture bytes changed during staged execution")
    (root / f"{member}-{case}.json").write_text(json.dumps(row, indent=2))
    return row


def validate_semgrep(candidate: dict[str, Any]) -> None:
    site = candidate.get("site", {})
    if (
        site.get("distributions", {}).get("semgrep") != "1.175.0"
        or site.get("selected_input_hashes", {}).get("site-packages/semgrep/bin/semgrep-core") != SEMGREP_CORE_SHA256
    ):
        raise ValueError("candidate lacks pinned Semgrep 1.175.0 input identity")


def load_semgrep_reference(path: Path = SEMGREP_REFERENCE) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("invalid pinned Semgrep reference")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SEMGREP_REFERENCE_SHA256:
        raise ValueError("pinned Semgrep reference bytes changed")
    return json.loads(data)


def run_semgrep_parity(root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    """Only fixed 14-case plans; read Sagan's pinned adapter without running its host launcher."""
    validate_semgrep(candidate)
    reference = load_semgrep_reference()
    helper_path = REPO / "scripts/native_semgrep_parity.py"
    if hashlib.sha256(helper_path.read_bytes()).hexdigest() != SEMGREP_HELPER_SHA256:
        raise ValueError("pinned Semgrep semantic adapter bytes changed")
    spec = importlib.util.spec_from_file_location("candidate_semgrep_parity", helper_path)
    if spec is None or spec.loader is None:
        raise ValueError("semantic adapter unavailable")
    parity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parity)
    assets, packs = parity.validate_assets()
    if set(reference["cases"]) != set(parity.CASES) or len(parity.CASES) != 14:
        raise ValueError("required Semgrep reference case matrix changed")
    for key, (_, digest) in parity.ASSET_PINS.items():
        if reference["assets"][key]["sha256"] != digest:
            raise ValueError("reference asset identity mismatch")
    target = candidate["payload"] / "site-packages/semgrep/bin/semgrep-core"
    cases = {}
    for case in parity.CASES:
        domain = root / ("semgrep-reference-" + case)
        domain.mkdir(mode=0o700)
        parity.prepare_fixture(domain, case, packs)
        argv, _ = parity.build_command("native", assets, domain, case)
        discovery = execute(
            root,
            candidate,
            domain,
            target,
            [*argv[:2], "--x-ls", *argv[2:]],
            request={"kind": "native-tool", "plan_id": SEMGREP_PLAN_ID, "case": case, "operation": "discover"},
        )
        native = execute(
            root,
            candidate,
            domain,
            target,
            argv,
            request={"kind": "native-tool", "plan_id": SEMGREP_PLAN_ID, "case": case, "operation": "scan"},
        )
        native["discovery"] = discovery
        parity.verify_fixture(domain, case, packs)
        row = parity.assess_adapter_case(case, reference["cases"][case]["python"], native, domain)
        row["native_stage"] = native["stage"]
        row["discovery_stage"] = discovery["stage"]
        row["broker_verified"] = native["broker_verified"] and discovery["broker_verified"]
        row["passed"] = row["passed"] and row["broker_verified"]
        cases[case] = row
        (root / "semgrep-reference-receipt.json").write_text(
            json.dumps({"cases": cases, "production_eligible": False}, indent=2)
        )
    summary = {
        "abi": candidate["version"],
        "matched_cases": sum(row["passed"] for row in cases.values()),
        "required_cases": 14,
        "reference_sha256": SEMGREP_REFERENCE_SHA256,
        "semantic_adapter_sha256": SEMGREP_HELPER_SHA256,
        "plan_id": SEMGREP_PLAN_ID,
        "production_eligible": False,
    }
    (root / "semgrep-reference-safe-summary.json").write_text(json.dumps(summary))
    return summary


def run_matrix(root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    from scripts import native_analyzer_smoke as fixtures

    members = {}
    for member in fixtures.MEMBERS:
        rows = {}
        for case in ("clean", "defective"):
            try:
                rows[case] = adapter_case(root, candidate, member, case)
            except Exception as error:
                (root / f"{member}-{case}-failure.txt").write_text(f"{type(error).__name__}: {error}")
                rows[case] = {
                    "completed": False,
                    "incomplete": "native candidate stage failure; private diagnostics retained",
                }
        passed = all(row["completed"] for row in rows.values()) and fixtures.assess(
            rows["clean"].get("findings", []), rows["defective"].get("findings", []), fixtures.MEMBERS[member][2]
        )
        members[member] = {"passed": passed, **rows}
        (root / "analyzer-receipt.json").write_text(
            json.dumps(
                {
                    "abi": candidate["version"],
                    "members": members,
                    "production_eligible": False,
                    "profile_id": candidate["profile_id"],
                },
                indent=2,
            )
        )
    result = {
        "abi": candidate["version"],
        "members": len(members),
        "passed": sum(row["passed"] for row in members.values()),
        "completed_cases": sum(
            case.get("completed") is True
            for member in members.values()
            for case in (member["clean"], member["defective"])
        ),
        "production_eligible": False,
        "library_loading_experiment": candidate["library_loading_experiment"],
    }
    (root / "analyzer-safe-summary.json").write_text(json.dumps(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv-input", type=Path, required=True)
    parser.add_argument("--version", choices=("3.13", "3.11", "3.12"), required=True)
    parser.add_argument("--experimental-interpreter-library-loading", action="store_true")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="sf-analyzers-" + python.version_key(args.version) + "-", dir="/private/tmp"))
    root.chmod(0o700)
    summary = {"abi": args.version, "members": 10, "passed": 0, "completed_cases": 0, "production_eligible": False}
    with (root / "diagnostics.log").open("w") as output, redirect_stdout(output):
        try:
            candidate = prepare(
                root,
                args.venv_input.resolve(),
                args.version,
                library_loading_experiment=args.experimental_interpreter_library_loading,
            )
            (root / "candidate.json").write_text(json.dumps(candidate, default=str))
            summary = run_matrix(root, candidate)
            reference = run_semgrep_parity(root, candidate)
            summary["semgrep_reference_passed"] = reference["matched_cases"]
            summary["semgrep_reference_required"] = reference["required_cases"]
        except Exception as error:
            (root / "failure.txt").write_text(f"{type(error).__name__}: {error}")
    (root / "analyzer-safe-summary.json").write_text(json.dumps(summary))
    print(json.dumps(summary))
    return 0 if summary["passed"] == 10 and summary.get("semgrep_reference_passed") == 14 else 2


if __name__ == "__main__":
    raise SystemExit(main())
