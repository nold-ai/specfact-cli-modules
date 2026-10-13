"""Failure-only diagnostic trust and disclosure controls."""

import json
from pathlib import Path

import pytest
import yaml

from scripts.independent_review_diagnostic import (
    Gap,
    InstalledSymbols,
    Observation,
    ProcessIdentity,
    read_profile,
    same_process,
)


@pytest.fixture
def installed(tmp_path):
    root = tmp_path / "installed"
    root.mkdir()
    source = root / "controller.py"
    source.write_text("def wait_for_member():\n    pass\n")
    return (
        root,
        source,
        InstalledSymbols.from_verified_files(
            root, {"controller.py": __import__("hashlib").sha256(source.read_bytes()).hexdigest()}
        ),
    )


def write_profile(tmp_path, frames, samples=None):
    path = tmp_path / "profile.private.json"
    path.write_text(
        json.dumps(
            {
                "shared": {"frames": frames},
                "profiles": [
                    {"type": "sampled", "name": "SECRET_PROCESS", "samples": samples or [[0]]},
                ],
            }
        )
    )
    return path


def test_exact_installed_symbols_only(tmp_path, installed):
    _, source, symbols = installed
    foreign = tmp_path / "subject" / "controller.py"
    foreign.parent.mkdir()
    foreign.write_text(source.read_text())
    path = write_profile(
        tmp_path,
        [
            {"file": str(source), "name": "wait_for_member", "line": 2},
            {"file": str(foreign), "name": "wait_for_member", "line": 2},
            {"file": str(source), "name": "SECRET_SUBJECT", "line": 2},
        ],
        [[0], [1], [2]],
    )
    result = read_profile(path, symbols)
    assert result.samples == 3
    assert result.symbols == (("controller.py:wait_for_member", 1),)
    public = Observation.from_profile(result, owned=2).to_public_json()
    assert "SECRET" not in public
    assert str(tmp_path) not in public
    assert json.loads(public)["acceptance"] is False
    assert "member_join_unavailable" in public
    assert "process_sample_join_unavailable" in public


def test_changed_installed_file_is_not_projected(tmp_path, installed):
    _, source, symbols = installed
    path = write_profile(tmp_path, [{"file": str(source), "name": "wait_for_member", "line": 2}])
    source.write_text('def wait_for_member():\n    return "SECRET_CHANGED"\n')
    result = read_profile(path, symbols)
    assert result.symbols == ()
    assert Gap.INSTALLATION_CHANGED in result.gaps


@pytest.mark.parametrize("payload", ["SECRET_INVALID", '{"shared":{},"shared":{}}', "[]"])
def test_malformed_profile_never_projects_text(tmp_path, installed, payload):
    path = tmp_path / "bad.json"
    path.write_text(payload)
    result = read_profile(path, installed[2])
    assert result.samples == 0
    assert result.symbols == ()
    assert Gap.PROFILE_INVALID in result.gaps
    assert "SECRET" not in Observation.from_profile(result, owned=0).to_public_json()


def test_oversized_profile_is_rejected_before_parsing(tmp_path, installed, monkeypatch):
    from scripts import independent_review_diagnostic as diagnostic

    monkeypatch.setattr(diagnostic, "MAX_PROFILE_BYTES", 8)
    path = write_profile(tmp_path, [])
    assert Gap.PROFILE_OVERSIZED in read_profile(path, installed[2]).gaps


@pytest.mark.parametrize("sample", [[True], [-1], [100], ["SECRET"], "SECRET"])
def test_invalid_sample_indices_are_rejected(tmp_path, installed, sample):
    path = write_profile(tmp_path, [{"file": str(installed[1]), "name": "wait_for_member"}], [sample])
    assert Gap.PROFILE_INVALID in read_profile(path, installed[2]).gaps


def test_pid_reuse_cannot_preserve_ownership():
    original = ProcessIdentity(42, 10, 100, "namespace1")
    assert same_process(original, ProcessIdentity(42, 10, 100, "namespace1"))
    assert not same_process(original, ProcessIdentity(42, 10, 101, "namespace1"))
    assert not same_process(original, ProcessIdentity(42, 10, 100, "namespace2"))


def test_workflow_keeps_baseline_failed_for_all_diagnostic_results():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/capsule-customer-execution.yml").read_text())
    job = workflow["jobs"]["independent-review"]
    assert job["if"] == "github.event_name == 'pull_request'"
    steps = job["steps"]
    review = next(s for s in steps if s.get("id") == "independent_review")
    diagnostic = next(s for s in steps if s.get("name") == "Observe failed independent review privately")
    assert steps.index(diagnostic) > steps.index(review)
    assert diagnostic["if"].startswith("failure() && steps.independent_review.outcome == 'failure'")
    assert not review.get("continue-on-error", False)
    assert 'exit "$review_exit"' in review["run"]
    assert "timeout=600" in review["run"]
    assert "--scope index --enforcement changed --bug-hunt" in review["run"]
    assert "SPECFACT_MODULES_BRANCH=main" in review["run"]
    assert "review-attempted" in diagnostic["run"]
    assert "upload-artifact" not in diagnostic["run"]


def test_subprocess_output_is_private(tmp_path):
    import subprocess
    import sys

    script = Path(__file__).resolve().parents[2] / "scripts/independent_review_diagnostic.py"
    program = (
        "import importlib.util,sys,subprocess\n"
        f'spec=importlib.util.spec_from_file_location("diagnostic",{str(script)!r})\n'
        "m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)\n"
        f"with m.private_output(m.Path({str(tmp_path / 'private.log')!r})):\n"
        ' print("SECRET_PYTHON")\n'
        " subprocess.run([sys.executable,\"-c\",\"import os;os.write(1,b'SECRET_CHILD');os.write(2,b'SECRET_ERROR')\"],check=True)\n"
        'print("PUBLIC_DONE")\n'
    )
    result = subprocess.run([sys.executable, "-c", program], check=True, capture_output=True, text=True)
    assert result.stdout == "PUBLIC_DONE\n"
    assert result.stderr == ""
    private = (tmp_path / "private.log").read_text()
    assert all(marker in private for marker in ("SECRET_PYTHON", "SECRET_CHILD", "SECRET_ERROR"))


@pytest.mark.parametrize("failure", [ValueError, SyntaxError, AttributeError])
def test_unverified_context_refuses_before_subject_launch(tmp_path, monkeypatch, capfd, failure):
    import sys

    from scripts import independent_review_diagnostic as diagnostic

    (tmp_path / "review-attempted").touch()
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--trusted-root", str(tmp_path), "--repository", str(tmp_path)])
    monkeypatch.setattr(sys, "platform", "linux")

    class LinuxCalls:
        @staticmethod
        def prctl(*_args):
            return 0

    monkeypatch.setattr(diagnostic.ctypes, "CDLL", lambda *_args, **_kwargs: LinuxCalls())

    def unverified(*_args):
        raise failure("SECRET_IDENTITY_FAILURE")

    monkeypatch.setattr(diagnostic, "verify_context", unverified)
    launches = []
    monkeypatch.setattr(diagnostic, "diagnose_failed_review", lambda *_args: launches.append("launched"))
    assert diagnostic.main() == 0
    assert launches == []
    public = capfd.readouterr()
    assert "SECRET" not in public.out + public.err
    assert json.loads(public.out)["status"] == "DIAGNOSTIC_UNAVAILABLE"
    assert json.loads(public.out)["acceptance"] is False


def test_package_signature_rejects_changed_installed_source(tmp_path):
    import base64
    import hashlib

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from specfact_cli.registry.module_installer import _module_artifact_payload_stable

    from scripts.independent_review_diagnostic import _verify_package

    package = tmp_path / "installed"
    package.mkdir()
    source = package / "module.py"
    source.write_text("VALUE = 1\n")
    manifest = package / "module-package.yaml"
    metadata: dict[str, object] = {"name": "test/diagnostic", "version": "0.1.0"}
    manifest.write_text(yaml.safe_dump(metadata))
    payload = _module_artifact_payload_stable(package)
    private_key = Ed25519PrivateKey.generate()
    public_key = (
        private_key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    metadata["integrity"] = {
        "checksum": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "signature": base64.b64encode(private_key.sign(payload)).decode(),
    }
    manifest.write_text(yaml.safe_dump(metadata))
    assert _verify_package(package, public_key).metadata["name"] == "test/diagnostic"
    source.write_text("SECRET_MODIFIED = True\n")
    with pytest.raises(ValueError, match="package_checksum"):
        _verify_package(package, public_key)


def test_repeated_frames_hash_installed_file_once(tmp_path, installed, monkeypatch):
    source = installed[1]
    path = write_profile(tmp_path, [{"file": str(source), "name": "wait_for_member", "line": 2}] * 100)
    calls = []
    original = Path.read_bytes

    def observed(candidate):
        if candidate == source:
            calls.append(candidate)
        return original(candidate)

    monkeypatch.setattr(Path, "read_bytes", observed)
    assert read_profile(path, installed[2]).samples == 1
    assert calls == [source]


def test_unsigned_source_under_package_root_is_not_admitted(tmp_path):
    import hashlib

    trusted = tmp_path / "trusted.py"
    trusted.write_text("def trusted_function():\n    pass\n")
    hidden = tmp_path / "tests" / "hidden.py"
    hidden.parent.mkdir()
    hidden.write_text("def SECRET_FUNCTION():\n    pass\n")
    symbols = InstalledSymbols.from_verified_files(
        tmp_path, {"trusted.py": hashlib.sha256(trusted.read_bytes()).hexdigest()}
    )
    path = write_profile(tmp_path, [{"file": str(hidden), "name": "SECRET_FUNCTION", "line": 2}])
    assert read_profile(path, symbols).symbols == ()


def test_signed_source_changed_before_allowlist_refuses(tmp_path):
    source = tmp_path / "trusted.py"
    source.write_text("def changed():\n    pass\n")
    with pytest.raises(ValueError, match="signed_source_changed"):
        InstalledSymbols.from_verified_files(tmp_path, {"trusted.py": "0" * 64})


def test_cleanup_rescans_after_parent_exit_for_late_adoption(monkeypatch):
    from scripts import independent_review_diagnostic as diagnostic

    parent = ProcessIdentity(100, 1, 10, "namespace")
    child = ProcessIdentity(101, 1, 11, "namespace")
    alive = {parent.pid: True, child.pid: False}
    owner = diagnostic.OwnedProcesses()
    owner.identities[parent.pid] = parent
    owner.handles[parent.pid] = parent.pid

    def observe():
        if alive[child.pid]:
            owner.identities[child.pid] = child
            owner.handles[child.pid] = child.pid

    def kill(handle, _signal):
        if handle == parent.pid and alive[parent.pid]:
            alive[child.pid] = True
        alive[handle] = False

    monkeypatch.setattr(owner, "observe", observe)
    monkeypatch.setattr(owner, "_reap", lambda: None)
    monkeypatch.setattr(owner, "_close", lambda: None)
    monkeypatch.setattr(diagnostic.signal, "pidfd_send_signal", kill, raising=False)
    monkeypatch.setattr(diagnostic, "_process_identity", lambda pid: owner.identities.get(pid) if alive[pid] else None)
    assert owner.cleanup() is True
    assert not any(alive.values())


def test_insufficient_optional_budget_refuses_before_subject(tmp_path, monkeypatch):
    import time

    from scripts import independent_review_diagnostic as diagnostic

    context = diagnostic.VerifiedContext(tmp_path, tmp_path, tmp_path, InstalledSymbols({}), {})
    object.__setattr__(context, "deadline", time.monotonic() + 309)
    launches = []
    monkeypatch.setattr(diagnostic, "_fixed_subject", lambda *_args: launches.append(True))
    monkeypatch.setattr(diagnostic, "_owned_run", lambda *_args: (1, 0, True))
    observation = diagnostic.diagnose_failed_review(context)
    assert launches == []
    assert Gap.DEADLINE in observation.gaps
