from __future__ import annotations

import base64
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[3]
PUBLIC_KEY = Path("scripts/native_release/module-signing-public.pem")
DEFAULT_KEY = Path("resources/keys/module-signing-public.pem")
MANIFEST = Path("packages/specfact-example/module-package.yaml")
SECRET_NAMES = ("SPECFACT_MODULE_PUBLIC_SIGN_KEY", "SPECFACT_MODULE_SIGNING_PUBLIC_KEY_PEM")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _public_pem(key: Ed25519PrivateKey) -> str:
    return (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


def _sign_module(repo: Path, key: Ed25519PrivateKey) -> None:
    manifest: dict[str, object] = {"name": "nold-ai/specfact-example", "version": "0.1.0"}
    entries = {
        "module-package.yaml": yaml.safe_dump(manifest, sort_keys=True, allow_unicode=False).encode(),
        "src.py": (repo / MANIFEST.parent / "src.py").read_bytes(),
    }
    payload = "\n".join(f"{name}:{hashlib.sha256(data).hexdigest()}" for name, data in entries.items()).encode()
    manifest["integrity"] = {
        "checksum": f"sha256:{hashlib.sha256(payload).hexdigest()}",
        "signature": base64.b64encode(key.sign(payload)).decode(),
    }
    (repo / MANIFEST).write_text(yaml.safe_dump(manifest))


@pytest.fixture
def signed_repository(tmp_path: Path) -> tuple[Path, str, Ed25519PrivateKey]:
    repo = tmp_path / "repository"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Signing regression")
    _git(repo, "config", "user.email", "signing-regression@example.invalid")
    key = Ed25519PrivateKey.generate()
    (repo / PUBLIC_KEY).parent.mkdir(parents=True)
    (repo / PUBLIC_KEY).write_text(_public_pem(key))
    (repo / "scripts/verify-modules-signature.py").write_bytes(
        (ROOT / "scripts/verify-modules-signature.py").read_bytes()
    )
    (repo / MANIFEST).parent.mkdir(parents=True)
    (repo / MANIFEST.parent / "src.py").write_text("VALUE = 1\n")
    _sign_module(repo, key)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Trusted signed module")
    base = _git(repo, "rev-parse", "HEAD")
    for branch in ("dev", "main"):
        _git(repo, "update-ref", f"refs/remotes/origin/{branch}", base)
    _git(repo, "commit", "--allow-empty", "-m", "Candidate checkout")
    return repo, base, key


def _run_verification(
    repo: Path, base: str, *, event: str = "pull_request", branch: str = "dev", secrets: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    job = workflow["jobs"]["verify-module-signatures"]
    step = next(item for item in job["steps"] if "scripts/verify-modules-signature.py" in item.get("run", ""))
    expressions = {
        "github.event_name": event,
        "github.event.pull_request.base.ref": branch,
        "github.event.pull_request.base.sha": base if event == "pull_request" else "",
        "github.event.before": base if event == "push" else "",
        "github.ref_name": branch,
        **{f"secrets.{name}": (secrets or {}).get(name, "") for name in SECRET_NAMES},
    }

    def render(value: str) -> str:
        return re.sub(r"\$\{\{\s*(.*?)\s*\}\}", lambda match: expressions[match.group(1)], value)

    runner = repo.parent / "runner"
    runner.mkdir(exist_ok=True)
    home = repo.parent / "home"
    home.mkdir(exist_ok=True)
    env = {
        "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
        "HOME": str(home),
        "RUNNER_TEMP": str(runner),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        **{name: render(str(value)) for name, value in {**job.get("env", {}), **step.get("env", {})}.items()},
    }
    return subprocess.run(
        ["bash", "-c", render(step["run"])], cwd=repo, env=env, capture_output=True, text=True, timeout=20
    )


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_signature_workflow_uses_trusted_event_key_without_secrets(signed_repository, event):
    repo, base, _ = signed_repository
    result = _run_verification(repo, base, event=event)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Verified 1 module manifest(s)." in result.stdout


def test_signature_workflow_rejects_candidate_key_replacement(signed_repository):
    repo, base, _ = signed_repository
    candidate_key = Ed25519PrivateKey.generate()
    (repo / PUBLIC_KEY).write_text(_public_pem(candidate_key))
    (repo / DEFAULT_KEY).parent.mkdir(parents=True)
    (repo / DEFAULT_KEY).write_text(_public_pem(candidate_key))
    _sign_module(repo, candidate_key)
    result = _run_verification(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Signature validation failed" in result.stderr


@pytest.mark.parametrize("fault", ["payload", "signature"])
def test_signature_workflow_rejects_tampering(signed_repository, fault):
    repo, base, _ = signed_repository
    if fault == "payload":
        (repo / MANIFEST.parent / "src.py").write_text("VALUE = 2\n")
    else:
        manifest = yaml.safe_load((repo / MANIFEST).read_text())
        manifest["integrity"]["signature"] = base64.b64encode(bytes(64)).decode()
        (repo / MANIFEST).write_text(yaml.safe_dump(manifest))
    result = _run_verification(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr
    assert ("checksum mismatch" if fault == "payload" else "Signature validation failed") in result.stderr


@pytest.mark.parametrize("event", ["pull_request", "push"])
@pytest.mark.parametrize("fault", ["missing", "zero", "malformed", "unavailable", "keyless"])
def test_signature_workflow_rejects_missing_trust_even_with_candidate_default(signed_repository, event, fault):
    repo, base, key = signed_repository
    (repo / DEFAULT_KEY).parent.mkdir(parents=True)
    (repo / DEFAULT_KEY).write_text(_public_pem(key))
    if fault == "keyless":
        _git(repo, "rm", str(PUBLIC_KEY))
        _git(repo, "commit", "-m", "Revision without signing key")
        base = _git(repo, "rev-parse", "HEAD")
        (repo / PUBLIC_KEY).write_text(_public_pem(key))
    else:
        base = {"missing": "", "zero": "0" * 40, "malformed": "HEAD", "unavailable": "f" * 40}[fault]
    result = _run_verification(repo, base, event=event)
    assert result.returncode != 0, result.stdout + result.stderr


@pytest.mark.parametrize("name", SECRET_NAMES)
@pytest.mark.parametrize("secret", ["invalid PEM", " \t\n"], ids=["malformed-pem", "blank"])
def test_signature_workflow_rejects_invalid_secret_even_with_candidate_default(signed_repository, name, secret):
    repo, base, key = signed_repository
    (repo / DEFAULT_KEY).parent.mkdir(parents=True)
    (repo / DEFAULT_KEY).write_text(_public_pem(key))
    result = _run_verification(repo, base, secrets={name: secret})
    assert result.returncode != 0, result.stdout + result.stderr


@pytest.mark.parametrize("name", SECRET_NAMES)
def test_signature_workflow_prefers_configured_secret(signed_repository, name):
    repo, base, _ = signed_repository
    secret_key = Ed25519PrivateKey.generate()
    _sign_module(repo, secret_key)
    result = _run_verification(repo, base, secrets={name: _public_pem(secret_key)})
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_signature_workflow_still_requires_signatures_on_main(signed_repository, event):
    repo, base, key = signed_repository
    manifest = yaml.safe_load((repo / MANIFEST).read_text())
    del manifest["integrity"]["signature"]
    (repo / MANIFEST).write_text(yaml.safe_dump(manifest))
    result = _run_verification(repo, base, event=event, branch="main", secrets={SECRET_NAMES[0]: _public_pem(key)})
    assert result.returncode != 0, result.stdout + result.stderr
    assert "missing integrity.signature" in result.stderr


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_signature_workflow_still_rejects_payload_changes_without_version_bump(signed_repository, event):
    repo, base, key = signed_repository
    (repo / MANIFEST.parent / "src.py").write_text("VALUE = 2\n")
    _sign_module(repo, key)
    _git(repo, "add", str(MANIFEST.parent))
    _git(repo, "commit", "-m", "Changed payload without version bump")
    result = _run_verification(repo, base, event=event, secrets={SECRET_NAMES[0]: _public_pem(key)})
    assert result.returncode != 0, result.stdout + result.stderr
    assert "module version was not incremented" in result.stderr
