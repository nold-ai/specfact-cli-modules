from __future__ import annotations

import base64
import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[3]
PAYLOAD = Path("ci/codebase-0.42.1.signing-payload.txt")
PAYLOAD_SHA256 = "a826c75ef57409191711f1af03dd13877d56d48769ba3a2e29d1929e16ce9909"
PUBLIC_KEY_SHA256 = "68ebe68cd4394c5319b85fe5b021460f3bae411dbfad795782657d0fe005d053"


def _workflow() -> dict[str, Any]:
    path = ROOT / ".github/workflows/module-signing-key-preflight.yml"
    return cast(dict[str, Any], yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader))


def test_signing_job_requires_payload_push_to_protected_dev() -> None:
    workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["on"]["push"] == {"branches": ["dev"], "paths": [str(PAYLOAD)]}
    assert "workflow_dispatch" in workflow["on"]
    job = workflow["jobs"]["sign-codebase-candidate"]
    assert job["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/dev' && github.ref_protected"
    assert job["environment"] == "module-signing"
    assert job["steps"][0]["with"]["persist-credentials"] == "false"
    payload = (ROOT / PAYLOAD).read_bytes().removesuffix(b"\n")
    assert hashlib.sha256(payload).hexdigest() == PAYLOAD_SHA256


def _run_signer(
    tmp_path: Path, key: Ed25519PrivateKey, mismatch: str | None = None
) -> subprocess.CompletedProcess[str]:
    payload = (ROOT / PAYLOAD).read_bytes()
    (tmp_path / PAYLOAD.parent).mkdir()
    (tmp_path / PAYLOAD).write_bytes(payload + b"changed" if mismatch == "payload" else payload)

    public_key = key.public_key()
    key_der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    (tmp_path / "ci/module-signing-public-next.pem").write_bytes(
        public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    fingerprint = hashlib.sha256(key_der).hexdigest()
    command = _workflow()["jobs"]["sign-codebase-candidate"]["steps"][-1]["run"]
    command = command.replace(PUBLIC_KEY_SHA256, fingerprint, 1)
    password = b"disposable-test-passphrase"
    signing_key = Ed25519PrivateKey.generate() if mismatch == "private-key" else key
    encrypted_key = signing_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password),
    )
    return subprocess.run(
        ["bash", "-c", command],
        cwd=tmp_path,
        env={
            **os.environ,
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
            "MODULE_PRIVATE_KEY": encrypted_key.decode(),
            "MODULE_KEY_PASSPHRASE": password.decode(),
            "EXPECTED_PUBLIC_KEY_SHA256": "0" * 64 if mismatch == "fingerprint" else fingerprint,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_candidate_signing_command(tmp_path: Path) -> None:
    key = Ed25519PrivateKey.generate()
    result = _run_signer(tmp_path, key)
    assert result.returncode == 0, result.stderr
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    signature = summary.split("~~~text\n", 1)[1].splitlines()[0]
    key.public_key().verify(
        base64.b64decode(signature, validate=True), (ROOT / PAYLOAD).read_bytes().removesuffix(b"\n")
    )


@pytest.mark.parametrize(
    ("mismatch", "diagnostic"),
    [("payload", "payload checksum"), ("fingerprint", "fingerprint"), ("private-key", "verify the detached signature")],
)
def test_mismatch_prevents_signature_output(tmp_path: Path, mismatch: str, diagnostic: str) -> None:
    result = _run_signer(tmp_path, Ed25519PrivateKey.generate(), mismatch)
    assert result.returncode != 0
    assert diagnostic in result.stderr
    assert not (tmp_path / "summary.md").exists()
