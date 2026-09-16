"""The external corpus accepts findings, but cannot accept incomplete execution."""

import hashlib
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load():
    source = Path(__file__).parents[2] / "scripts/external_capsule_corpus.py"
    spec = importlib.util.spec_from_file_location("external_capsule_corpus", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_gate_rejects_unknown_despite_fail_status() -> None:
    module = _load()
    with pytest.raises(ValueError, match="incomplete"):
        module.assert_completed_report({"assurance_status": "FAIL", "has_unknown_required_evidence": True})


def test_external_gate_requires_actual_test_execution() -> None:
    module = _load()
    with pytest.raises(ValueError, match="test execution"):
        module.assert_completed_report({"assurance_status": "PASS", "analyzer_evidence": []})


def test_external_gate_rejects_missing_analyzer_even_with_real_tests() -> None:
    report = {
        "assurance_status": "PASS",
        "analyzer_evidence": [
            {
                "id": "targeted-pytest-coverage",
                "evidence_outcome": "PASS",
                "target_execution": {
                    "collected": ["test_app.py::test_app"],
                    "records": [{"nodeid": "test_app.py::test_app", "phase": "call", "outcome": "passed"}],
                    "coverage": {"files": {"app.py": {}}},
                },
            }
        ],
    }
    with pytest.raises(ValueError, match="roster"):
        _load().assert_completed_report(report)


def test_reconstruction_materializes_real_source_without_mutating_template(tmp_path: Path) -> None:
    module = _load()
    fixture = tmp_path / "template"
    fixture.mkdir()
    template = fixture / "test_native.py.in"
    template.write_text("def test_native():\n    assert True\n")
    destination = tmp_path / "checkout"
    module.materialize_reconstruction(fixture, destination)
    assert (destination / "test_native.py").read_text() == template.read_text()
    assert not (destination / "test_native.py.in").exists()
    assert template.is_file()


def test_corpus_attempts_remaining_repositories_after_a_failure(tmp_path: Path, monkeypatch) -> None:

    module = _load()
    manifest = tmp_path / "corpus.json"
    manifest.write_text(json.dumps({"python": ["3.12"], "repositories": [{"name": "first"}, {"name": "second"}]}))
    monkeypatch.setattr(module, "MANIFEST", manifest)
    monkeypatch.setattr(module.sys, "argv", ["corpus", "--workspace", str(tmp_path / "work")])
    monkeypatch.setattr(module.sys, "version_info", type("Version", (), {"major": 3, "minor": 12})())
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(module.os, "getuid", lambda: 1000)
    attempted = []

    def run_entry(entry, _workspace):
        attempted.append(entry["name"])
        if entry["name"] == "first":
            raise ValueError("controlled incomplete analysis")

    monkeypatch.setattr(module, "run_entry", run_entry)
    assert module.main() == 1
    assert attempted == ["first", "second"]


def test_host_baseline_rejects_startup_failure_without_test_execution(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"host.*execution"):
        _load().assert_host_execution(tmp_path / "missing.xml")


def test_host_baseline_rejects_only_setup_errors(tmp_path: Path) -> None:
    result = tmp_path / "tests.xml"
    result.write_text(
        '<testsuites><testsuite><testcase name="test_app"><error message="setup failed"/>'
        "</testcase></testsuite></testsuites>"
    )
    with pytest.raises(ValueError, match=r"host.*execution"):
        _load().assert_host_execution(result)


def test_source_identity_detects_new_untracked_and_ignored_files(tmp_path: Path) -> None:
    module = _load()
    (tmp_path / ".git").mkdir()
    (tmp_path / "source.py").write_text("VALUE = 1\n")
    before = module.tracked_identity(tmp_path)
    (tmp_path / "generated.py").write_text("VALUE = 2\n")
    assert module.tracked_identity(tmp_path) != before


def test_network_evidence_excludes_loopback_and_reports_counter_deltas(tmp_path: Path) -> None:
    module = _load()
    counters = tmp_path / "net-dev"
    counters.write_text(
        "Inter-| Receive | Transmit\n"
        " face |bytes packets errs drop fifo frame compressed multicast|"
        "bytes packets errs drop fifo colls carrier compressed\n"
        " lo: 900 0 0 0 0 0 0 0 800 0 0 0 0 0 0 0\n eth0: 120 0 0 0 0 0 0 0 70 0 0 0 0 0 0 0\n"
    )
    before = module.network_counters(counters)
    assert before == {"received_bytes": 120, "sent_bytes": 70}
    counters.write_text(counters.read_text().replace("eth0: 120", "eth0: 220").replace("0 70 0", "0 90 0"))
    assert module.network_delta(before, module.network_counters(counters)) == {
        "received_bytes": 100,
        "sent_bytes": 20,
        "scope": "host_non_loopback_interface_counters",
    }
    assert module.network_counters(tmp_path / "unavailable") is None


def test_controlled_defect_preserves_separate_report(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    root = tmp_path / "upstream"
    (root / "tests").mkdir(parents=True)
    (root / "src/customer").mkdir(parents=True)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "cold-auto-report.json").write_text('{"untouched": true}')

    def execute(argv, **_context):
        output = Path(argv[argv.index("--out") + 1])
        output.write_text(
            json.dumps(
                {
                    "findings": [
                        {"rule": "TEST_OUTCOME_NOT_PASS"},
                        {"tool": "basedpyright", "file": "specfact_controlled.py"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        return ""

    monkeypatch.setattr(module, "execute", execute)
    monkeypatch.setattr(module, "assert_completed_report", lambda _report: None)
    _invoke_controlled(module, root, evidence, tmp_path, _controlled_entry())
    assert (evidence / "controlled-defect-report.json").is_file()
    assert json.loads((evidence / "cold-auto-report.json").read_text()) == {"untouched": True}


def _controlled_entry() -> dict:
    """Identify the exact package context of the disposable regression project."""
    return {
        "controlled_defect": {"source": "src/customer/specfact_controlled.py", "import": "customer.specfact_controlled"}
    }


def _invoke_controlled(module, root, evidence, workspace, entry) -> None:
    """Keep the new behavior regression callable against the original four-argument harness."""
    options = {"entry": entry} if "entry" in inspect.signature(module.controlled_defect).parameters else {}
    module.controlled_defect(root, evidence, workspace / "config.toml", workspace, **options)


def _detected_controlled_findings() -> dict:
    """Stub only the unrelated signed analyzer boundary during fixture-generation tests."""
    return {"findings": [{"rule": "TEST_OUTCOME_NOT_PASS"}, {"tool": "basedpyright", "file": "specfact_controlled.py"}]}


@pytest.mark.parametrize("scope", ["source_pkgs", "omit_only"])
def test_controlled_fixture_executes_inside_unchanged_native_measurement(tmp_path, monkeypatch, scope) -> None:
    """The generated test must really call the bad function under native coverage filters."""
    module = _load()
    root = tmp_path / "upstream"
    (root / "tests").mkdir(parents=True)
    (root / "src/customer").mkdir(parents=True)
    (root / "src/customer/__init__.py").write_text("")
    (root / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath=["src"]\n')
    configured = "source_pkgs = customer, tests" if scope == "source_pkgs" else "omit = customer/unused/*"
    (root / ".coveragerc").write_text(f"[run]\n{configured}\n")
    original = module.tracked_identity(root)

    def review(copy, _evidence, _config, paths, **_kwargs):
        report = tmp_path / "native-coverage.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "pytest_cov",
                "--cov",
                f"--cov-report=json:{report}",
                paths[1],
            ],
            cwd=copy,
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "COVERAGE_FILE": str(tmp_path / ".coverage")},
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert completed.returncode == 1, completed.stdout + completed.stderr
        assert "SPECFACT_CONTROLLED_473" in completed.stdout
        assert "injected wrong type" in completed.stdout
        payload = json.loads(report.read_text())
        selected = "src/customer/specfact_controlled.py"
        assert paths == [selected, "tests/test_specfact_controlled.py"]
        assert payload["files"][selected]["executed_lines"] == [1, 2]
        assert module.tracked_identity(root) == original
        assert (copy / ".coveragerc").read_bytes() == (root / ".coveragerc").read_bytes()
        return _detected_controlled_findings()

    monkeypatch.setattr(module, "review", review)
    _invoke_controlled(module, root, tmp_path, tmp_path, _controlled_entry())


@pytest.mark.parametrize(
    "unsafe", ["parent-link", "test-parent-link", "source-exists", "test-exists", "destination-link"]
)
def test_controlled_fixture_rejects_unsafe_write_targets(tmp_path, monkeypatch, unsafe) -> None:
    """Copy injection cannot follow customer links or overwrite existing fixture paths."""
    module = _load()
    root = tmp_path / "upstream"
    (root / "src/customer").mkdir(parents=True)
    (root / "tests").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    targets = {"parent-link": root / "src/customer", "test-parent-link": root / "tests"}
    if unsafe in targets:
        targets[unsafe].rmdir()
        targets[unsafe].symlink_to(outside, target_is_directory=True)
    elif unsafe == "destination-link":
        (tmp_path / "controlled").symlink_to(outside, target_is_directory=True)
    else:
        name = (
            "src/customer/specfact_controlled.py" if unsafe == "source-exists" else "tests/test_specfact_controlled.py"
        )
        (root / name).write_text("ORIGINAL = True\n")
    original = module.tracked_identity(root)
    monkeypatch.setattr(module, "review", lambda *_args, **_kwargs: _detected_controlled_findings())
    with pytest.raises(ValueError, match=r"controlled.*(path|destination)"):
        _invoke_controlled(module, root, tmp_path, tmp_path, _controlled_entry())
    assert module.tracked_identity(root) == original
    assert not list(outside.iterdir())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "../outside.py"),
        ("source", "/outside.py"),
        ("import", "customer;raise RuntimeError"),
        ("import", "other.specfact_controlled"),
        ("import", "customer.class"),
    ],
)
def test_controlled_fixture_rejects_invalid_explicit_package_declaration(tmp_path, monkeypatch, field, value) -> None:
    """An explicit corpus path and import must describe the same contained Python module."""
    module = _load()
    root = tmp_path / "upstream"
    (root / "src/customer").mkdir(parents=True)
    (root / "tests").mkdir()
    entry = _controlled_entry()
    entry["controlled_defect"][field] = value
    monkeypatch.setattr(module, "review", lambda *_args, **_kwargs: _detected_controlled_findings())
    with pytest.raises(ValueError, match=r"controlled.*(path|import)"):
        _invoke_controlled(module, root, tmp_path, tmp_path, entry)


def test_pinned_corpus_records_explicit_controlled_package_context() -> None:
    """Each frozen upstream and reconstruction has its own reviewed package destination."""
    module = _load()
    manifest = json.loads(module.MANIFEST.read_text())
    entries = [*manifest["repositories"], *manifest["reconstructions"]]
    expected = {
        "requests": "requests",
        "hatch": "hatch",
        "flask": "flask",
        "poetry": "poetry",
        "hatch-detached": "portable_customer",
    }
    for entry in entries:
        package = expected[entry["name"]]
        assert entry.get("controlled_defect") == {
            "source": f"src/{package}/specfact_controlled.py",
            "import": f"{package}.specfact_controlled",
        }


def test_offline_corpus_requires_provisioned_launcher(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    monkeypatch.delenv("SPECFACT_CORPUS_OFFLINE_LAUNCHER", raising=False)
    launcher = tmp_path / "root/opt/specfact/bin/bwrap-static"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"not the signed launcher")
    with pytest.raises(ValueError, match=r"administrator-provisioned.*launcher"):
        module.offline_command(["specfact", "code", "review", "runtime", "prepare", "--offline"])


def test_offline_corpus_rejects_customer_writable_launcher(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    launcher = tmp_path / "bwrap"
    launcher.write_text('#!/bin/sh\necho SPECFACT_OFFLINE_NETWORK_VERIFIED >&2\nexec "$@"\n')
    launcher.chmod(0o755)
    monkeypatch.setenv("SPECFACT_CORPUS_OFFLINE_LAUNCHER", str(launcher))
    monkeypatch.setattr(module.os, "readlink", lambda _path: "net:[fixture]")
    with pytest.raises(ValueError, match="offline_launcher"):
        module.offline_command(["specfact", "code", "review", "run"])


def test_corpus_identity_detects_empty_directories(tmp_path: Path) -> None:
    module = _load()
    before = module.tracked_identity(tmp_path)
    (tmp_path / "new-empty-directory").mkdir()
    assert module.tracked_identity(tmp_path) != before


@pytest.mark.parametrize("owner,mode", [(1001, 0o100555), (0, 0o100775), (0, 0o100557), (0, 0o120777)])
def test_offline_launcher_rejects_untrusted_ownership_or_mode(owner: int, mode: int) -> None:
    module = _load()
    path = SimpleNamespace(name="launcher", lstat=lambda: SimpleNamespace(st_uid=owner, st_mode=mode))
    with pytest.raises(ValueError, match="offline_launcher_untrusted"):
        module._check_offline_path(path)


def test_offline_launcher_rejects_changed_provisioned_bytes(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    launcher = tmp_path / "bwrap"
    launcher.write_bytes(b"original provisioned executable")
    launcher.chmod(0o555)
    (tmp_path / "bwrap.sha256").write_text(hashlib.sha256(launcher.read_bytes()).hexdigest())
    monkeypatch.setattr(module, "OFFLINE_ROOT", tmp_path)
    # Isolate the byte identity check; ownership/mode rejection is tested separately.
    monkeypatch.setattr(module, "_check_offline_path", lambda *_args, **_kwargs: None)
    assert module._verified_offline_launcher(str(launcher)) == launcher
    launcher.chmod(0o755)
    launcher.write_bytes(b"replacement")
    with pytest.raises(ValueError, match="offline_launcher_untrusted:identity"):
        module._verified_offline_launcher(str(launcher))


def test_offline_provisioning_avoids_writable_hosted_runner_ancestor(monkeypatch) -> None:
    module = _load()
    payload = b"administrator-provisioned launcher fixture"

    def permissions(path):
        mode = 0o100555 if path.name in {"bwrap", "bwrap.sha256"} else 0o40755
        if path == Path("/opt"):
            mode = 0o40775
        return SimpleNamespace(st_uid=0, st_mode=mode)

    monkeypatch.setattr(Path, "lstat", permissions)
    monkeypatch.setattr(Path, "read_bytes", lambda _path: payload)
    monkeypatch.setattr(Path, "read_text", lambda _path, **_kwargs: hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(module.os, "access", lambda *_args: True)
    launcher = module.OFFLINE_ROOT / "bwrap"
    assert module._verified_offline_launcher(str(launcher)) == launcher


def _run_poetry_import_guard(tmp_path: Path, monkeypatch, phase: str, finding: dict) -> None:
    module = _load()
    entry = next(row for row in json.loads(module.MANIFEST.read_text())["repositories"] if row["name"] == "poetry")
    evidence = tmp_path / "evidence/poetry"
    evidence.mkdir(parents=True)
    descriptor = tmp_path / "runtime/project-runtime.json"
    descriptor.parent.mkdir()
    descriptor.write_text("{}")
    monkeypatch.setattr(module, "checkout", lambda *_args: None)
    monkeypatch.setattr(module, "tracked_identity", lambda *_args: "unchanged")
    monkeypatch.setattr(module, "host_test", lambda *_args: None)
    monkeypatch.setattr(module, "controlled_defect", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "execute", lambda *_args, **_kwargs: json.dumps({"descriptor": str(descriptor)}))

    def review(*_args, **kwargs):
        actual_phase = "warm" if "descriptor" in kwargs else "cold"
        return {"findings": [finding] if actual_phase == phase else []}

    monkeypatch.setattr(module, "review", review)
    module.run_entry(entry, tmp_path)


@pytest.mark.parametrize("phase", ["cold", "warm"])
@pytest.mark.parametrize("line", [7, 9, 10])
@pytest.mark.parametrize("rule", ["E0401", "E0611"])
def test_poetry_corpus_rejects_known_import_misresolution(tmp_path: Path, monkeypatch, phase, line, rule) -> None:
    finding = {"tool": "pylint", "rule": rule, "file": "tests/utils/test_extras.py", "line": line}
    with pytest.raises(ValueError, match="verified import"):
        _run_poetry_import_guard(tmp_path, monkeypatch, phase, finding)


@pytest.mark.parametrize(
    "finding",
    [
        {"tool": "pylint", "rule": "E0401", "file": "tests/other.py", "line": 7},
        {"tool": "pylint", "rule": "E0401", "file": "tests/utils/test_extras.py", "line": 20},
        {"tool": "pylint", "rule": "W0611", "file": "tests/utils/test_extras.py", "line": 7},
    ],
)
def test_poetry_corpus_preserves_unrelated_findings(tmp_path: Path, monkeypatch, finding) -> None:
    _run_poetry_import_guard(tmp_path, monkeypatch, "cold", finding)
    assert json.loads((tmp_path / "evidence/poetry/acceptance.json").read_text())["status"] == "PASS"
