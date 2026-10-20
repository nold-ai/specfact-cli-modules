import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.native_release import acceptance, platforms


def test_supported_platform_receipt_rejects_a_newer_mac(monkeypatch):
    monkeypatch.setattr(platforms.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platforms.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        platforms.subprocess,
        "run",
        lambda command, **_kwargs: SimpleNamespace(
            stdout={"-productVersion": "27.0.1", "-buildVersion": "26A434"}[command[1]]
        ),
    )
    with pytest.raises(ValueError, match="platform"):
        platforms.platform_context("macos-26")


def test_customer_gate_rejects_all_development_overrides():
    for name in acceptance.FORBIDDEN_CUSTOMER_ENV:
        with pytest.raises(ValueError, match="customer"):
            acceptance.require_customer_context({name: "1"})


def test_extension_receipt_uses_verified_boolean_phase_outcome(monkeypatch):
    monkeypatch.setattr(acceptance, "assert_completed_report", lambda _report: None)
    report = {
        "analyzer_evidence": [
            {
                "id": "targeted-pytest-coverage",
                "target_execution": {
                    "records": [
                        {
                            "nodeid": "tests/test_native_capsule.py::test_native_extension",
                            "phase": "call",
                            "passed": True,
                        }
                    ]
                },
            }
        ]
    }
    acceptance.verify_extension_execution(report)
    report["analyzer_evidence"][0]["target_execution"]["records"][0]["passed"] = False
    with pytest.raises(ValueError, match="extension"):
        acceptance.verify_extension_execution(report)


def test_customer_trust_observation_preserves_quarantine(monkeypatch, tmp_path):
    commands = []

    def observe(command, **options):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="file: com.apple.quarantine: 0081;...", stderr="")

    monkeypatch.setattr(acceptance.subprocess, "run", observe)
    result = acceptance.observe_customer_trust(tmp_path, "cold", 0)
    assert commands == [["/usr/bin/xattr", "-lrs", str(tmp_path)]]
    assert result["quarantine_attributes"] == 1
    assert result["execution"] == "completed"
    assert result["dialog_observation"] == "unavailable in unattended CLI"


def test_customer_trust_observation_rejects_failed_attribute_query(monkeypatch, tmp_path):
    monkeypatch.setattr(
        acceptance.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="denied"),
    )
    with pytest.raises(ValueError, match="trust observation"):
        acceptance.observe_customer_trust(tmp_path, "cold", 2)


@pytest.mark.parametrize("empty_option", ["-productVersion", "-buildVersion"])
def test_platform_context_refuses_empty_native_observation(monkeypatch, empty_option):
    monkeypatch.setattr(platforms.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platforms.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(platforms.os, "getuid", lambda: 1000)
    monkeypatch.setattr(
        platforms.subprocess,
        "run",
        lambda command, **_kwargs: SimpleNamespace(stdout="" if command[1] == empty_option else "observed"),
    )
    with pytest.raises(ValueError, match="native platform observations"):
        platforms.platform_context("local")


def test_customer_entry_help_works_without_developer_import_paths():
    environment = {name: value for name, value in os.environ.items() if name not in acceptance.FORBIDDEN_CUSTOMER_ENV}
    root = Path(__file__).resolve().parents[3]
    namespace = subprocess.run(
        [sys.executable, "-B", "-c", "import importlib.util; print(importlib.util.find_spec('specfact_code_review'))"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert namespace.stdout.strip() == "None", "startup regression requires an absent developer namespace"
    result = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.native_release.acceptance", "--help"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--mode {candidate,customer}" in result.stdout
