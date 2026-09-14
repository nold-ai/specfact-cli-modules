"""The external corpus accepts findings, but cannot accept incomplete execution."""

import hashlib
import importlib.util
import json
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
    module.controlled_defect(root, evidence, tmp_path / "config.toml", tmp_path)
    assert (evidence / "controlled-defect-report.json").is_file()
    assert json.loads((evidence / "cold-auto-report.json").read_text()) == {"untouched": True}


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
