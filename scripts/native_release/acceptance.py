"""Execute native candidates and ordinary installed modules with separate evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from scripts.capsule_customer_gate import _capsule_identities, _validate_warm_composition
from scripts.external_capsule_corpus import MANIFEST, assert_completed_report, checkout, json_document
from scripts.native_release.platforms import PLATFORMS, REQUIRED_CHECKS


if TYPE_CHECKING:
    from specfact_code_review.run import runner


FORBIDDEN_CUSTOMER_ENV = (
    "SPECFACT_CODE_REVIEW_NATIVE_ARTIFACT_DIR",
    "SPECFACT_ALLOW_UNSIGNED",
    "SPECFACT_MODULES_ROOTS",
    "PYTHONPATH",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "SPECFACT_NATIVE_CAPSULE_PRIVATE_SIGN_KEY",
)
ROOT = Path(__file__).resolve().parents[2]


def system_value(option: str) -> str:
    return subprocess.run(
        ["/usr/bin/sw_vers", option], check=True, text=True, capture_output=True, timeout=10
    ).stdout.strip()


def platform_context(label: str) -> dict[str, str]:
    version, build = system_value("-productVersion"), system_value("-buildVersion")
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("native platform is not Darwin ARM64")
    if label != "local" and (version, build) != PLATFORMS.get(label):
        raise ValueError("supported native platform image drift")
    if os.getuid() == 0:
        raise ValueError("native acceptance requires an ordinary user")
    subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}"], check=True, capture_output=True, timeout=10)
    return {"runner": label, "os_version": version, "os_build": build, "architecture": "arm64"}


def require_customer_context(environment: Mapping[str, str]) -> None:
    if any(environment.get(name) for name in FORBIDDEN_CUSTOMER_ENV):
        raise ValueError("ordinary customer acceptance forbids developer overrides and credentials")


def flask_project(work: Path) -> tuple[Path, Path, list[str]]:
    entries = json.loads(MANIFEST.read_bytes())["repositories"]
    entry = next(row for row in entries if row["name"] == "flask")
    project = work / "flask"
    checkout(entry, project, work / "checkout-evidence")
    extension_test = project / "tests/test_native_capsule.py"
    extension_test.write_text(
        '"""Prove a real project native extension loads inside the capsule."""\n'
        "from markupsafe import _speedups\n\n"
        "def test_native_extension():\n"
        '    """Require native bytes and execute their exported function."""\n'
        '    assert _speedups.__file__.endswith(".so")\n'
        '    assert _speedups._escape_inner("<") == "&lt;"\n'
    )
    config = work / "project-runtime.toml"
    config.write_text('manager="uv"\nenvironment="default"\ngroups=["tests"]\nnative_libraries=[]\n')
    return project, config, [*entry["paths"], "tests/test_native_capsule.py"]


def verify_extension_execution(report: dict) -> None:
    assert_completed_report(report)
    row = next(item for item in report["analyzer_evidence"] if item["id"] == "targeted-pytest-coverage")
    calls = row["target_execution"].get("records", [])
    if not any(
        item.get("phase") == "call"
        and "test_native_capsule.py::test_native_extension" in item.get("nodeid", "")
        and item.get("passed") is True
        for item in calls
    ):
        raise ValueError("native project extension test did not pass")


def _review_candidate(
    runtime: runner.CapsuleRuntime, project: Path, config: Path, paths: list[str], output: Path
) -> dict:
    from specfact_code_review.review.commands import review_app
    from specfact_code_review.run import runner

    arguments = ["review", "run", *paths, "--project-config", str(config), "--bug-hunt", "--json", "--out", str(output)]
    previous = Path.cwd()
    try:
        os.chdir(project)
        with (
            patch.object(runner, "_prepare_capsule_runtime", return_value=(runtime, "")),
            patch.object(sys, "argv", arguments),
        ):
            try:
                review_app()
            except SystemExit as error:
                if error.code not in (0, 1):
                    raise ValueError("native candidate CLI did not complete") from error
    finally:
        os.chdir(previous)
    report = json.loads(output.read_bytes())
    verify_extension_execution(report)
    return report


def fixture_authentication(artifact) -> tuple[str, bytes]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    from scripts.build_macos_native_capsule import _sign

    # Ephemeral test authentication exercises the consumer, never publisher authority.
    key = ed25519.Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    signature = _sign(artifact.manifest, key)
    return signature, public


@contextmanager
def candidate_runtime(artifact_path: Path, cache: Path) -> Iterator[runner.CapsuleRuntime]:
    from scripts.native_release.artifacts import inspect_archive
    from specfact_code_review.run import native_backend, native_capsule, runner

    artifact = inspect_archive(artifact_path)
    signature, public = fixture_authentication(artifact)
    identity = artifact.document["environment_id"]
    parameters = {
        "environment_id": identity,
        "backend": native_backend.BACKEND_VERSION,
        "policy": native_backend.POLICY_VERSION,
    }
    lease = native_capsule.acquire_native_capsule(
        cache,
        artifact.manifest,
        signature,
        public,
        reader=lambda: (artifact_path / "capsule.tar").open("rb"),
        **parameters,
    )
    try:
        offline = native_capsule.acquire_native_capsule(
            cache, artifact.manifest, signature, public, offline=True, **parameters
        )
        offline.close()
        yield runner.CapsuleRuntime(
            lease.path,
            "sha256:" + artifact.manifest_sha256,
            identity,
            "python/bin/python3",
            "bin/specfact-native-bootstrap",
            None,
            backend="darwin-arm64",
            native_lease=lease,
            analyzer_versions=lease.analyzer_versions,
        )
    finally:
        lease.close()


def boundary_acceptance(context: dict[str, str]) -> None:
    root = Path(os.environ["RUNNER_TEMP"]) / "specfact-macos-boundary"
    root.mkdir(mode=0o700)
    document = {
        **context,
        "image_version": os.environ["ImageVersion"],  # noqa: SIM112 -- GitHub-hosted image variable
        "python": platform.python_version(),
        "gui_launchd_available": True,
    }
    (root / "platform.json").write_text(json.dumps(document))
    subprocess.run(
        [sys.executable, "-B", str(ROOT / "scripts/check_macos_boundary_ci_receipts.py")], check=True, timeout=1800
    )


def write_candidate_receipt(artifact, work: Path, context: dict[str, str]) -> None:
    checks = dict.fromkeys(REQUIRED_CHECKS, True)
    checks["native_boundary"] = context["runner"] != "local"
    receipt = {
        "schema": "specfact-native-acceptance-v1",
        "source_sha": os.environ["SOURCE_SHA"],
        **context,
        "environment_id": artifact.document["environment_id"],
        "manifest_sha256": artifact.manifest_sha256,
        "archive_sha256": artifact.document["archive"]["sha256"],
        "checks": checks,
    }
    (work / "receipt.json").write_text(json.dumps(receipt, sort_keys=True))
    (work / "scope.json").write_text(
        json.dumps(
            {
                "scope": "unsigned candidate with ephemeral test key",
                "customer_installation": False,
                "production_eligible": False,
            }
        )
    )


def candidate_acceptance(artifact_path: Path, work: Path, label: str) -> None:
    from scripts.native_release.artifacts import inspect_archive
    from specfact_code_review.run.runtime_builder import prepare_runtime
    from specfact_code_review.run.runtime_discovery import discover_project

    context = platform_context(label)
    work.mkdir(mode=0o700)
    if label != "local":
        boundary_acceptance(context)
    project, config, paths = flask_project(work)
    artifact = inspect_archive(artifact_path)
    with candidate_runtime(artifact_path, work / "capsule-cache") as runtime:
        from scripts.native_release.boundary import delivered_boundary

        delivered_boundary(runtime.root, work / "delivered-boundary")
        plan = discover_project(project, config_path=config)
        prepared = prepare_runtime(plan, runtime=runtime, cache_root=work / "project-cache")
        offline = prepare_runtime(plan, runtime=runtime, cache_root=work / "project-cache", offline=True)
        if offline.identity != prepared.identity:
            raise ValueError("offline project identity changed")
        _review_candidate(runtime, project, config, paths, work / "review.json")
    write_candidate_receipt(artifact, work, context)


def offline_descriptor(project: Path, config: Path, environment: dict[str, str]) -> str:
    prepared = subprocess.run(
        [
            "specfact",
            "code",
            "review",
            "runtime",
            "prepare",
            "--project-config",
            str(config),
            "--offline",
            "--json",
        ],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    return json_document(prepared.stdout)["descriptor"]


def observe_customer_trust(cache: Path, mode: str, returncode: int) -> dict:
    """Observe the actual cache attributes without removing or changing them."""
    result = subprocess.run(
        ["/usr/bin/xattr", "-lrs", str(cache)], capture_output=True, text=True, timeout=60, check=False
    )
    if result.returncode != 0:
        raise ValueError("customer trust observation failed")
    return {
        "mode": mode,
        "quarantine_attributes": result.stdout.count("com.apple.quarantine:"),
        "execution": "completed" if returncode in (0, 1) else "blocked or failed",
        "dialog_observation": "unavailable in unattended CLI",
    }


def customer_review(project: Path, command: list[str], environment: dict[str, str], output: Path) -> tuple[dict, int]:
    completed = subprocess.run(
        command, cwd=project, env=environment, capture_output=True, text=True, timeout=4500, check=False
    )
    output.with_suffix(".stdout").write_text(completed.stdout)
    output.with_suffix(".stderr").write_text(completed.stderr)
    # Preserve failure and trust observations even if a blocked loader writes no report.
    report = json.loads(output.read_bytes()) if output.is_file() else {}
    return report, completed.returncode


def customer_acceptance(work: Path, label: str) -> None:
    require_customer_context(os.environ)
    context = platform_context(label)
    work.mkdir(mode=0o700)
    project, config, paths = flask_project(work)
    cache = work / "capsule-cache"
    environment = dict(os.environ, SPECFACT_CODE_REVIEW_CAPSULE_CACHE=str(cache))
    command = ["specfact", "code", "review", "run", *paths, "--project-config", str(config), "--bug-hunt", "--json"]
    reports = {}
    observations = []
    for mode in ("cold", "offline"):
        report_path = work / f"{mode}.json"
        if mode == "offline":
            environment["SPECFACT_CODE_REVIEW_NATIVE_OFFLINE"] = "1"
            descriptor = offline_descriptor(project, config, environment)
            arguments = [*command, "--project-runtime", descriptor]
        else:
            arguments = command
        report, returncode = customer_review(project, [*arguments, "--out", str(report_path)], environment, report_path)
        observations.append(observe_customer_trust(cache, mode, returncode))
        (work / "trust.json").write_text(json.dumps(observations, sort_keys=True))
        if returncode not in (0, 1):
            raise ValueError("installed native customer CLI failed")
        verify_extension_execution(report)
        reports[mode] = report
    _validate_warm_composition(reports["cold"], reports["offline"])
    (work / "acceptance.json").write_text(
        json.dumps(
            {
                **context,
                "scope": "normal signed installed module, anonymous registry cold and native offline reuse",
                "status": "PASS",
                "capsule_identities": _capsule_identities(reports["cold"]),
                "trust_observations": observations,
            }
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("candidate", "customer"), required=True)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--runner", choices=(*PLATFORMS, "local"), required=True)
    args = parser.parse_args()
    if args.mode == "candidate":
        if args.artifact is None:
            parser.error("candidate acceptance requires --artifact")
        candidate_acceptance(args.artifact, args.work, args.runner)
    else:
        customer_acceptance(args.work, args.runner)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
