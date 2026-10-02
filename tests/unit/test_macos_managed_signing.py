"""Release-signing preflight must never turn local mocks into boundary proof."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


FINGERPRINT = "A" * 40
TEAM = "ABCDE12345"


@pytest.fixture(name="signing")
def fixture_signing():
    """Import the standalone maintainer preflight without running commands."""
    path = Path(__file__).parents[2] / "scripts/macos_managed_boundary/preflight.py"
    spec = importlib.util.spec_from_file_location("managed_signing", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_preflight(signing, monkeypatch, outputs, **overrides):
    """Record native command arguments and provide bounded synthetic results."""
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["timeout"] <= 60
        assert kwargs["capture_output"] is True
        captured = outputs[len(calls) - 1]
        if isinstance(captured, Exception):
            raise captured
        return captured

    monkeypatch.setattr(signing.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(signing.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(signing.subprocess, "run", run)
    args = {"identity": FINGERPRINT, "team": TEAM, "notary_profile": "specfact-release"}
    args.update(overrides)
    return signing.preflight(**args), calls


def result(stdout="", returncode=0, stderr=""):
    """Represent captured command output without real signing credentials."""
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def valid_identity():
    """Use a synthetic matching Developer ID identity for unit tests only."""
    return result(f'  1) {FINGERPRINT} "Developer ID Application: Fixture ({TEAM})"\n1 valid identities found')


@pytest.mark.parametrize("identity", ["", "-", "Developer ID Application: Fixture", "B" * 39, "G" * 40])
def test_no_ambiguous_or_adhoc_identity(signing, monkeypatch, identity):
    receipt, calls = run_preflight(signing, monkeypatch, [], identity=identity)
    assert receipt["status"] == "blocked"
    assert not calls
    assert receipt["production_approved"] is False


@pytest.mark.parametrize("overrides", [{"team": ""}, {"team": "bad"}, {"notary_profile": ""}])
def test_missing_configuration_never_runs_build(signing, monkeypatch, overrides):
    receipt, calls = run_preflight(signing, monkeypatch, [], **overrides)
    assert receipt["status"] == "blocked"
    assert not calls


def test_no_local_signing_identity_is_blocked(signing, monkeypatch):
    receipt, calls = run_preflight(signing, monkeypatch, [result("0 valid identities found")])
    assert receipt["status"] == "blocked"
    assert len(calls) == 1


@pytest.mark.parametrize("label", ["Apple Development", "Developer ID Installer"])
def test_wrong_certificate_class_rejected(signing, monkeypatch, label):
    identity = result(f'1) {FINGERPRINT} "{label}: Fixture ({TEAM})"')
    receipt, calls = run_preflight(signing, monkeypatch, [identity])
    assert receipt["status"] == "blocked"
    assert len(calls) == 1


def test_wrong_team_rejected(signing, monkeypatch):
    receipt, _ = run_preflight(signing, monkeypatch, [valid_identity()], team="OTHER12345")
    assert receipt["status"] == "blocked"


def test_notary_auth_failure_is_sanitized(signing, monkeypatch):
    receipt, calls = run_preflight(signing, monkeypatch, [valid_identity(), result(returncode=1, stderr="SECRET")])
    assert receipt["status"] == "blocked"
    assert "SECRET" not in json.dumps(receipt)
    assert calls[1] == [
        "/usr/bin/xcrun",
        "notarytool",
        "history",
        "--keychain-profile",
        "specfact-release",
        "--output-format",
        "json",
    ]


@pytest.mark.parametrize("notary", [result("not-json"), result("[]"), result("{}"), result('{"history": "bad"}')])
def test_unrecognized_notary_response_cannot_pass(signing, monkeypatch, notary):
    receipt, _ = run_preflight(signing, monkeypatch, [valid_identity(), notary])
    assert receipt["status"] == "blocked"


@pytest.mark.parametrize("failure", [OSError("SECRET"), subprocess.TimeoutExpired("SECRET", 60)])
def test_command_failures_become_blocked_receipts(signing, monkeypatch, failure):
    receipt, _ = run_preflight(signing, monkeypatch, [failure])
    assert receipt["status"] == "blocked"
    assert "SECRET" not in json.dumps(receipt)


def test_credentials_ready_is_not_signed_boundary_acceptance(signing, monkeypatch):
    receipt, calls = run_preflight(signing, monkeypatch, [valid_identity(), result('{"history": []}')])
    assert receipt["status"] == "credentials_available"
    assert receipt["production_approved"] is False
    assert receipt["signed_boundary_verified"] is False
    assert len(calls) == 2
    assert not any("clang" in call or "codesign" in call for call in calls)


def test_unsupported_host_does_not_access_keychain(signing, monkeypatch):
    monkeypatch.setattr(signing.platform, "system", lambda: "Linux")
    monkeypatch.setattr(signing.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("keychain access"))
    assert signing.preflight(FINGERPRINT, TEAM, "release")["status"] == "blocked"
