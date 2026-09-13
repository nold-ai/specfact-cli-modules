"""Exercise installed capsule analyzers and reject incomplete customer evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
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


_NAMESPACE_POLICY_FILES = {
    Path("/sys/module/apparmor/parameters/enabled"): "Y",
    Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns"): "1",
}


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
        _validate_detected_defect(report, returncode)
    if expected == "repository" and (returncode, status) not in {(0, "PASS"), (1, "FAIL")}:
        raise ValueError("repository review did not complete")


def _validate_detected_defect(report: dict[str, Any], returncode: int) -> None:
    if (returncode, report.get("assurance_status")) != (1, "FAIL") or not report.get("findings"):
        raise ValueError("controlled defect was not detected with a failing exit")
    pytest_row = next(row for row in report["analyzer_evidence"] if row["id"] == "targeted-pytest-coverage")
    failed_test = any(
        finding.get("tool") == "pytest" and finding.get("rule") == "TEST_OUTCOME_NOT_PASS"
        for finding in report["findings"]
    )
    if pytest_row.get("evidence_outcome") != "FAIL" or not failed_test:
        raise ValueError("pytest did not execute the deliberately defective assertion")


def _capsule_identities(report: dict[str, Any]) -> dict[str, str]:
    identities = {}
    for row in report.get("analyzer_evidence", []):
        identity = row.get("capsule_identity", "")
        if not isinstance(identity, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", identity) is None:
            raise ValueError("capsule composition identity is missing or invalid")
        identities[row["id"]] = identity
    if set(identities) != ANALYZERS:
        raise ValueError("capsule composition inventory is incomplete")
    return identities


def _validate_warm_composition(cold: dict[str, Any], warm: dict[str, Any]) -> None:
    if _capsule_identities(cold) != _capsule_identities(warm):
        raise ValueError("warm capsule composition identities changed")


def _materialization_denial_identity(rows: list[dict[str, Any]]) -> dict[str, str]:
    python_version = os.environ.get("MATRIX_PYTHON", "")
    if python_version not in {"3.11", "3.12", "3.13"}:
        raise ValueError("namespace denial has no supported matrix ABI")
    environment_id = "linux-x86_64-cp" + python_version.replace(".", "")
    pattern = (
        r"capsule_materialization_failed:namespace_unavailable:stage=offline-install:launcher=(sha256:[0-9a-f]{64}):.+"
    )
    launchers = set()
    for row in rows:
        diagnostic = re.fullmatch(pattern, str(row.get("diagnostic", "")))
        if diagnostic is None or row.get("environment_id") != environment_id:
            raise ValueError("namespace denial lacks a verified materialization launcher and matching ABI")
        launchers.add(diagnostic.group(1))
    if len(launchers) != 1:
        raise ValueError("namespace denial launcher identities disagree")
    return {"stage": "offline-install", "launcher_digest": launchers.pop(), "environment_id": environment_id}


def _namespace_denial_identity(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("analyzer_evidence", [])
    if any(str(row.get("diagnostic", "")).startswith("capsule_materialization_failed:") for row in rows):
        return _materialization_denial_identity(rows)
    try:
        identities = _capsule_identities(report)
    except ValueError as exc:
        raise ValueError(f"namespace denial did not reach a verified capsule: {exc}") from exc
    if any(not str(row.get("diagnostic", "")).startswith("namespace_unavailable:") for row in rows):
        raise ValueError("namespace denial lacks a specific launcher diagnostic")
    return {"stage": "analyzer-launch", "capsule_identities": identities}


def _validate_namespace_denial(report: dict[str, Any], returncode: int) -> None:
    if (returncode, report.get("assurance_status"), report.get("has_unknown_required_evidence")) != (
        1,
        "UNKNOWN",
        True,
    ):
        raise ValueError("namespace denial must fail closed with UNKNOWN and a failing exit")
    rows = report.get("analyzer_evidence", [])
    if len(rows) != len(ANALYZERS) or {row.get("id") for row in rows} != ANALYZERS:
        raise ValueError("namespace denial analyzer inventory is incomplete")
    for row in rows:
        if (row.get("execution_state"), row.get("evidence_outcome")) != ("error", "UNKNOWN"):
            raise ValueError("namespace denial unexpectedly executed an analyzer")
    _namespace_denial_identity(report)


def _namespace_baseline(evidence: Path) -> None:
    observed = {str(path): path.read_text(encoding="utf-8").strip() for path in _NAMESPACE_POLICY_FILES}
    (evidence / "namespace-policy.json").write_text(json.dumps(observed, indent=2), encoding="utf-8")
    if any(observed[str(path)] != expected for path, expected in _NAMESPACE_POLICY_FILES.items()):
        raise ValueError("Ubuntu AppArmor namespace restriction baseline is absent")


@require(lambda expected: expected in {"clean", "defective", "repository", "namespace-denial"})
@ensure(lambda result: result is None)
def validate_report(report: dict[str, Any], *, returncode: int, expected: str) -> None:
    """Require every selected analyzer to execute, including conditional members."""
    if expected == "namespace-denial":
        _validate_namespace_denial(report, returncode)
        return
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


_FIXTURE_TEST_SOURCE = '''"""Arithmetic and capsule filesystem acceptance tests."""

import errno
import os
from pathlib import Path

from calculator import add


def _assert_private_write(root: Path) -> None:
    probe = root / ".capsule-write-probe"
    probe.write_text("private capsule state", encoding="utf-8")
    assert probe.read_text(encoding="utf-8") == "private capsule state"
    probe.unlink()


def _assert_sealed_write_denied(root: Path) -> None:
    try:
        (root / ".capsule-write-probe").touch(exist_ok=False)
    except OSError as error:
        assert error.errno == errno.EROFS, f"sealed write failed for another reason: {error}"
    else:
        raise AssertionError(f"sealed capsule path was writable: {root}")


def _assert_capsule_filesystem() -> None:
    private = Path("/opt/specfact/tmp")
    roots = {
        "HOME": private / "home",
        "TMPDIR": private,
        "XDG_CACHE_HOME": private / "cache",
        "XDG_CONFIG_HOME": private / "config",
        "XDG_DATA_HOME": private / "data",
        "XDG_STATE_HOME": private / "state",
    }
    for variable, root in roots.items():
        assert os.environ[variable] == str(root)
        _assert_private_write(root)
    _assert_private_write(Path("/opt/specfact/output"))
    for root in ("python", "analyzers", "snapshot", "config"):
        _assert_sealed_write_denied(Path("/opt/specfact") / root)


def test_add() -> None:
    """Exercise arithmetic and prove the active capsule mount permissions."""
    assert add(2, 3) == 5
    _assert_capsule_filesystem()
'''


def _fixture(root: Path, *, defective: bool, unrelated_failure: bool = False) -> None:
    root.mkdir()
    source = '"""Small arithmetic fixture."""\n\n\ndef add(left: int, right: int) -> int:\n    """Return the sum of two integers."""\n    return left + right\n'
    if defective:
        source = source.replace("\n\n\ndef add", "\n\nimport json\n\n\ndef add")
    (root / "calculator.py").write_text(source, encoding="utf-8")
    test_source = (
        _FIXTURE_TEST_SOURCE.replace("assert add(2, 3) == 5", "assert add(2, 3) == 6")
        if defective
        else _FIXTURE_TEST_SOURCE
    )
    (root / "test_calculator.py").write_text(test_source, encoding="utf-8")
    if unrelated_failure:
        (root / "test_unrelated.py").write_text(
            '"""Unrelated scope regression fixture."""\n\n\ndef test_unrelated() -> None:\n    """Fail if an unrelated test is collected."""\n    assert 1 == 2\n',
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


_CANDIDATE_CONTEXT_NAMES = (
    "GITHUB_ACTIONS",
    "GITHUB_REPOSITORY",
    "GITHUB_EVENT_NAME",
    "GITHUB_SHA",
    "GITHUB_WORKFLOW",
    "GITHUB_WORKFLOW_REF",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_JOB",
    "SPECFACT_MODULES_ROOTS",
)


def _review_environment(*, cache: Path | None, offline: bool, mode: str) -> dict[str, str]:
    executable_root = Path(sys.executable).absolute().parent
    environment = {name: os.environ[name] for name in ("HOME", "TMPDIR") if name in os.environ}
    environment.update(
        {
            "PATH": os.pathsep.join((str(executable_root), "/usr/bin", "/bin")),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "SPECFACT_CODE_REVIEW_CAPSULE_OFFLINE": "1" if offline else "0",
        }
    )
    selected_cache = cache or Path(
        os.environ.get("SPECFACT_CODE_REVIEW_CAPSULE_CACHE", str(Path.home() / ".cache/specfact/code-review/capsules"))
    )
    environment["SPECFACT_CODE_REVIEW_CAPSULE_CACHE"] = str(selected_cache)
    if mode == "candidate":
        environment.update({name: os.environ[name] for name in _CANDIDATE_CONTEXT_NAMES if name in os.environ})
        environment["SPECFACT_ALLOW_UNSIGNED"] = "1"
    return environment


def _review_selection(name: str, expected: str) -> tuple[str, ...]:
    if name == "targeted":
        return ("calculator.py",)
    return _REPOSITORY_PATHS if expected == "repository" else ("--scope", "full")


def _review(
    root: Path, evidence: Path, name: str, expected: str, *, cache: Path | None = None, mode: str = "public"
) -> dict[str, Any]:
    report_path = evidence / f"{name}.json"
    command = [
        str(Path(sys.executable).absolute().parent / "specfact"),
        "code",
        "review",
        "run",
        *_review_selection(name, expected),
        "--enforcement",
        "full",
        "--bug-hunt",
        "--json",
        "--out",
        str(report_path),
    ]
    environment = _review_environment(cache=cache, offline=name in {"warm", "targeted"}, mode=mode)
    umask = 0o077 if name in {"warm", "alternate"} else 0o022
    print(f"capsule review {name}: started; expected={expected}", flush=True)
    with (evidence / f"{name}.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=root,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=False,
            umask=umask,
            env=environment,
        )
    (evidence / f"{name}-command.json").write_text(
        json.dumps(
            {
                "argv": command,
                "exit_code": result.returncode,
                "umask": oct(umask),
                "cache": environment.get("SPECFACT_CODE_REVIEW_CAPSULE_CACHE"),
                "offline": name in {"warm", "targeted"},
            }
        ),
        encoding="utf-8",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    status = report.get("assurance_status")
    status = status if status in {"PASS", "FAIL", "UNKNOWN"} else "invalid"
    print(f"capsule review {name}: finished; exit={result.returncode}; assurance={status}", flush=True)
    validate_report(report, returncode=result.returncode, expected=expected)
    return report


def _write_filesystem_evidence(report: dict[str, Any], root: Path, evidence: Path, name: str) -> None:
    pytest_row = next(row for row in report["analyzer_evidence"] if row["id"] == "targeted-pytest-coverage")
    if (pytest_row.get("execution_state"), pytest_row.get("evidence_outcome")) != ("ran", "PASS"):
        raise ValueError("filesystem proof requires successful targeted pytest execution")
    source = (root / "test_calculator.py").read_bytes()
    if source != _FIXTURE_TEST_SOURCE.encode("utf-8"):
        raise ValueError("filesystem proof fixture differs from the controlled acceptance test")
    (evidence / f"{name}-filesystem-proof.json").write_text(
        json.dumps(
            {
                "marker": "capsule-private-writes-and-sealed-denials-v1",
                "basis": "controlled test_add assertions, targeted-pytest PASS, and failing-assertion execution witness",
                "fixture_sha256": hashlib.sha256(source).hexdigest(),
                "capsule_identity": _capsule_identities(report)["targeted-pytest-coverage"],
                "private_writes": [
                    "HOME",
                    "TMPDIR",
                    "XDG_CACHE_HOME",
                    "XDG_CONFIG_HOME",
                    "XDG_DATA_HOME",
                    "XDG_STATE_HOME",
                    "/opt/specfact/output",
                ],
                "sealed_write_errno": "EROFS",
                "sealed_roots": ["python", "analyzers", "snapshot", "config"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_completed_filesystem_evidence(reports: dict[str, dict[str, Any]], clean: Path, evidence: Path) -> None:
    witness = reports.get("defective")
    if witness is None:
        return
    _validate_detected_defect(witness, 1)
    for name in ("cold", "warm", "alternate"):
        if name in reports:
            _write_filesystem_evidence(reports[name], clean, evidence, name)


def _run_reviews(
    evidence: Path, cache: Path, repository: Path, clean: Path, defective: Path, *, mode: str = "public"
) -> list[str]:
    alternate = cache.with_name(f"{cache.name}-077")
    if alternate.exists() and any(alternate.iterdir()):
        raise ValueError("alternate cache must start empty")
    failures = []
    cold = {}
    cold_report: dict[str, Any] = {}
    reports: dict[str, dict[str, Any]] = {}
    for name, root, expected in [
        ("cold", clean, "clean"),
        ("warm", clean, "clean"),
        ("alternate", clean, "clean"),
        ("defective", defective, "defective"),
        ("repository", repository, "repository"),
    ]:
        try:
            selected_cache = alternate if name == "alternate" else cache
            report = _review(root, evidence, name, expected, cache=selected_cache, mode=mode)
            identities = _cache_identities(selected_cache)
            if not identities:
                raise ValueError("runtime cache contains no verified OCI artifacts")
            (evidence / f"{name}-cache-identities.json").write_text(json.dumps(identities, indent=2), encoding="utf-8")
            if name == "cold":
                cold = identities
                cold_report = report
            elif name in {"warm", "alternate"}:
                _validate_warm_composition(cold_report, report)
                if identities != cold:
                    raise ValueError(f"{name} cache identities changed")
            reports[name] = report
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            failures.append(f"{name}: {exc}")
    _write_completed_filesystem_evidence(reports, clean, evidence)
    return failures


def _run_namespace_denial(evidence: Path, *, mode: str = "public") -> list[str]:
    try:
        _namespace_baseline(evidence)
        fixture = evidence / "namespace-fixture"
        _fixture(fixture, defective=False)
        report = _review(fixture, evidence, "namespace-denial", "namespace-denial", mode=mode)
        (evidence / "namespace-denial-identity.json").write_text(
            json.dumps(_namespace_denial_identity(report), indent=2), encoding="utf-8"
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return [f"namespace-denial: {exc}"]
    return []


def _run_targeted_review(evidence: Path, cache: Path, *, mode: str = "public") -> list[str]:
    root = evidence.parent / "targeted"
    _fixture(root, defective=False, unrelated_failure=True)
    try:
        cached = _cache_identities(cache)
        report = _review(root, evidence, "targeted", "clean", cache=cache, mode=mode)
        if not cached or _cache_identities(cache) != cached:
            raise ValueError("targeted review did not preserve verified offline cache identities")
        witness = json.loads((evidence / "defective.json").read_text(encoding="utf-8"))
        _validate_detected_defect(witness, 1)
        _write_filesystem_evidence(report, root, evidence, "targeted")
        receipt = {
            "selected_source": "calculator.py",
            "mapped_test": "test_calculator.py",
            "excluded_test": "test_unrelated.py",
            "scope": "explicit_files",
            "files_sha256": {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.glob("*.py"))
            },
            "cache_identities": cached,
        }
        (evidence / "targeted-selection.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return [f"targeted: {exc}"]
    return []


def _run_customer_reviews(evidence: Path, cache: Path, repository: Path, *, mode: str = "public") -> list[str]:
    clean = evidence.parent / "clean"
    defective = evidence.parent / "defective"
    _fixture(clean, defective=False)
    _fixture(defective, defective=True)
    selected_repository = _repository_slice(repository, evidence)
    failures = _run_reviews(evidence, cache, selected_repository, clean, defective, mode=mode)
    failures.extend(_run_targeted_review(evidence, cache, mode=mode))
    return failures


def _registry_entry(repository: Path) -> dict[str, Any]:
    registry = json.loads((repository / "registry/index.json").read_text(encoding="utf-8"))
    return next(entry for entry in registry["modules"] if entry["id"] == "nold-ai/specfact-code-review")


def _expected_installation(repository: Path) -> dict[str, Any]:
    import tarfile

    import yaml

    entry = _registry_entry(repository)
    archive = repository / "registry" / entry["download_url"]
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != entry["checksum_sha256"]:
            raise ValueError("registry archive does not match the checkout checksum")
    with tarfile.open(archive, "r:gz") as package:
        manifest_file = package.extractfile("specfact-code-review/module-package.yaml")
        if manifest_file is None:
            raise ValueError("registry archive has no module manifest")
        manifest = yaml.safe_load(manifest_file.read())
    if (manifest.get("name"), str(manifest.get("version"))) != (entry["id"], entry["latest_version"]):
        raise ValueError("registry archive manifest version does not match the checkout")
    return manifest


def _validate_installed_manifest(expected: dict[str, Any], installed: dict[str, Any]) -> None:
    if installed != expected:
        raise ValueError("installed module identity differs from the pinned registry artifact")


def _release_checkout_identity(repository: Path) -> dict[str, str]:
    commit = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    tag = os.environ.get("RELEASE_TAG", "")
    if tag:
        tag_commit = subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"], text=True
        ).strip()
        if tag_commit != commit:
            raise ValueError("release tag does not match the registry checkout commit")
    return {"commit": commit, "release_tag": tag}


def _verify_installation(repository: Path, evidence: Path) -> None:
    import yaml
    from specfact_cli.models.module_package import ModulePackageMetadata
    from specfact_cli.registry import module_installer

    expected = _expected_installation(repository)
    package = module_installer.USER_MODULES_ROOT / "specfact-code-review"
    installed = yaml.safe_load((package / "module-package.yaml").read_text(encoding="utf-8"))
    _validate_installed_manifest(expected, installed)
    public_key = module_installer._bundled_public_key_path().read_text(encoding="utf-8")
    if not module_installer.verify_module_artifact(
        package,
        ModulePackageMetadata.model_validate(installed),
        allow_unsigned=False,
        require_integrity=True,
        require_signature=True,
        public_key_pem=public_key,
    ):
        raise ValueError("installed module signature or payload verification failed")
    evidence.mkdir(parents=True)
    receipt = {
        **_release_checkout_identity(repository),
        "module": installed["name"],
        "version": installed["version"],
        "publisher": installed["publisher"],
        "integrity": installed["integrity"],
        "registry_archive_sha256": _registry_entry(repository)["checksum_sha256"],
        "public_key_sha256": hashlib.sha256(public_key.encode("utf-8")).hexdigest(),
        "signature_verified": True,
    }
    (evidence / "installed-identity.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")


_REPOSITORY_PATHS = ("publish_bundle_selection.py", "tests/unit/test_publish_bundle_selection.py")


def _repository_slice(repository: Path, evidence: Path) -> Path:
    commit = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    root = evidence.parent / "repository-slice"
    subprocess.run(
        ["git", "clone", "--shared", "--no-checkout", "--quiet", str(repository.resolve()), str(root)], check=True
    )
    subprocess.run(
        ["git", "-C", str(root), "sparse-checkout", "set", "--no-cone", *(f"/{path}" for path in _REPOSITORY_PATHS)],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "checkout", "--detach", "--quiet", commit], check=True)
    identities = {}
    for relative in _REPOSITORY_PATHS:
        payload = (root / relative).read_bytes()
        committed = subprocess.check_output(["git", "-C", str(repository), "show", f"{commit}:{relative}"])
        if payload != committed:
            raise ValueError("repository slice differs from its recorded source commit")
        identities[relative] = hashlib.sha256(payload).hexdigest()
    (evidence / "repository-selection.json").write_text(
        json.dumps(
            {"commit": commit, "scope": "selected repository source and original tests", "files_sha256": identities},
            indent=2,
        ),
        encoding="utf-8",
    )
    return root


def _validate_customer_environment(mode: str) -> Path:
    if os.geteuid() == 0 or platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("customer gate requires a non-root Linux x86-64 runner")
    forbidden = ["GITHUB_TOKEN", "GH_TOKEN", "PYTHONPATH"]
    if mode == "public":
        forbidden += ["SPECFACT_ALLOW_UNSIGNED", "SPECFACT_MODULES_ROOTS", "SPECFACT_MODULES_REPO"]
    if any(os.environ.get(name) for name in forbidden):
        raise ValueError("customer gate has credentials or development overrides")
    cache = Path(os.environ["SPECFACT_CODE_REVIEW_CAPSULE_CACHE"])
    if cache.exists() and any(cache.iterdir()):
        raise ValueError("customer gate must start with an empty cache")
    return cache


@ensure(lambda result: result in {0, 1})
def main() -> int:
    """Run cold, warm, defective and repository reviews without elevated privileges."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--mode", choices=("candidate", "public"), required=True)
    parser.add_argument("--expect-namespace-denial", action="store_true")
    parser.add_argument("--installation-version", action="store_true")
    parser.add_argument("--verify-installation", action="store_true")
    args = parser.parse_args()
    if args.installation_version:
        _release_checkout_identity(args.repository)
        print(_expected_installation(args.repository)["version"])
        return 0
    if args.verify_installation:
        _verify_installation(args.repository, args.evidence)
        return 0
    cache = _validate_customer_environment(args.mode)
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
    failures = (
        _run_namespace_denial(evidence, mode=args.mode)
        if args.expect_namespace_denial
        else _run_customer_reviews(evidence, cache, args.repository, mode=args.mode)
    )
    (evidence / "cache-identities.json").write_text(json.dumps(_cache_identities(cache), indent=2), encoding="utf-8")
    (evidence / "result.json").write_text(
        json.dumps(
            {"failures": failures, "mode": args.mode, "expected_namespace_denial": args.expect_namespace_denial},
            indent=2,
        ),
        encoding="utf-8",
    )
    for failure in failures:
        sys.stderr.write(f"{failure}\n")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
