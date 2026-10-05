from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import build_macos_native_capsule as builder
from scripts.macos_managed_boundary import python_analyzers as analyzers
from tests.unit import test_build_macos_native_capsule as build_tests


managed_git_case = build_tests.managed_git_case


def test_authoritative_preparation_installs_explicit_verified_git(monkeypatch, managed_git_case):
    artifact, payload, signature = managed_git_case
    monkeypatch.setenv("SPECFACT_MANAGED_GIT_ARTIFACT", str(artifact))
    original = builder.install_managed_git_input
    monkeypatch.setattr(
        builder,
        "install_managed_git_input",
        lambda source, target: original(source, target, signature_inspector=lambda _path: signature),
    )
    candidate = {"payload": payload}
    analyzers.install_managed_git(candidate)
    assert candidate["managed_git"]["files"]["bin/git"]["sha256"] == builder.sha256(
        (payload / "git/bin/git").read_bytes()
    )
    assert not list((payload / "git").rglob("build.log"))


def test_authoritative_preparation_does_not_infer_git_from_path(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECFACT_MANAGED_GIT_ARTIFACT", raising=False)
    monkeypatch.setattr(builder, "install_managed_git_input", lambda *_args: pytest.fail("implicit Git input"))
    candidate = {"payload": tmp_path}
    analyzers.install_managed_git(candidate)
    assert "managed_git" not in candidate


def test_authoritative_git_identity_is_verified_without_resigning():
    commands = []

    def command(args):
        commands.append(args)
        return SimpleNamespace(stderr="Signature=adhoc runtime arm64", stdout="")

    image = Path("/private/candidate/payload/git/bin/git")
    details, entitlements = analyzers.inspect_managed_git_signature(image, SimpleNamespace(command=command))
    assert details == "Signature=adhoc runtime arm64"
    assert entitlements == ""
    assert commands == [
        ["/usr/bin/codesign", "--verify", "--strict", str(image)],
        ["/usr/bin/codesign", "--display", "--verbose=4", str(image)],
        ["/usr/bin/codesign", "--display", "--entitlements", ":-", str(image)],
    ]
