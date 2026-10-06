import pytest

from scripts.native_release import acceptance


def test_supported_platform_receipt_rejects_a_newer_mac(monkeypatch):
    monkeypatch.setattr(acceptance.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(acceptance.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        acceptance, "system_value", lambda name: {"-productVersion": "27.0.1", "-buildVersion": "26A434"}[name]
    )
    with pytest.raises(ValueError, match="platform"):
        acceptance.platform_context("macos-26")


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
    from types import SimpleNamespace

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
    from types import SimpleNamespace

    monkeypatch.setattr(
        acceptance.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="denied"),
    )
    with pytest.raises(ValueError, match="trust observation"):
        acceptance.observe_customer_trust(tmp_path, "cold", 2)
