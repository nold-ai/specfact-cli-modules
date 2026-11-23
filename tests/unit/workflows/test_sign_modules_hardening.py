from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from runpy import run_path
from typing import Any, cast

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/sign-modules.yml"
VERIFIER = REPO_ROOT / "scripts/verify-modules-signature.py"


def _workflow() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader))


def test_verification_triggers_on_push_pr_and_dispatch() -> None:
    events = _workflow()["on"]
    for event in ("push", "pull_request"):
        assert events[event]["branches"] == ["dev", "main"]
        assert "packages/**" in events[event]["paths"]
        assert "registry/**" in events[event]["paths"]
        assert "ci/official-module-release-cutoff.json" in events[event]["paths"]
        assert "ci/module-signing-public-next.pem" in events[event]["paths"]
    assert events["workflow_dispatch"]["inputs"]["base_branch"]["options"] == ["dev", "main"]


def test_native_review_workflow_changes_trigger_pr_signature_verification() -> None:
    events = _workflow()["on"]
    reviewer_path = ".github/workflows/native-pr-review.yml"
    assert reviewer_path in events["pull_request"]["paths"]
    assert reviewer_path not in events["push"]["paths"]


def test_verification_cannot_sign_or_write_to_github() -> None:
    workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}
    verify = workflow["jobs"]["verify"]
    assert verify["name"] == "Verify Module Signatures"
    assert {"environment", "permissions"}.isdisjoint(verify)
    checkout = verify["steps"][0]["with"]
    assert checkout["persist-credentials"] == "false"
    assert "github.event.pull_request.head.sha" in checkout["ref"]
    required = {
        "scripts/verify-modules-signature.py",
        "--payload-from-filesystem",
        "--require-signature",
        "--enforce-version-bump",
        "--version-check-base",
    }
    verifier_command = verify["steps"][-1]["run"]
    assert all(token in verifier_command for token in required)
    verify_text = yaml.safe_dump(verify)
    assert not any(text in verify_text for text in ("secrets.", "git push", "scripts/sign-modules.py"))


def test_only_protected_main_reproducibility_can_use_signing_secrets() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert set(jobs) == {"verify", "reproducibility"}
    repro = jobs["reproducibility"]
    assert (repro["name"], repro["environment"], repro["needs"]) == (
        "Assert signing reproducibility",
        "module-signing",
        ["verify"],
    )
    assert repro["if"] == "github.event_name == 'push' && github.ref_protected && github.ref == 'refs/heads/main'"
    assert repro["steps"][0]["with"] == {"ref": "${{ github.sha }}", "persist-credentials": "false"}
    assert repro["steps"][-1]["env"] == {
        "MODULE_PRIVATE_KEY": "${{ secrets.MODULE_SIGNING_PRIVATE_KEY_V2 }}",
        "MODULE_KEY_PASSPHRASE": "${{ secrets.MODULE_SIGNING_PRIVATE_KEY_PASSPHRASE_V2 }}",
        "EXPECTED_PUBLIC_KEY_SHA256": "${{ vars.MODULE_SIGNING_PUBLIC_KEY_SHA256 }}",
    }
    assert "secrets.SPECFACT_MODULE_PRIVATE_SIGN_KEY" not in WORKFLOW.read_text(encoding="utf-8")
    assert "git push" not in yaml.safe_dump(workflow)


def test_pr_approval_cannot_write_signatures() -> None:
    approval_workflow = REPO_ROOT / ".github/workflows/sign-modules-on-approval.yml"
    assert not approval_workflow.exists()


def _prepare_reproducibility_workspace(tmp_path: Path, key: Ed25519PrivateKey) -> tuple[Path, Path]:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(VERIFIER, scripts / VERIFIER.name)
    ci = tmp_path / "ci"
    ci.mkdir()
    (ci / "module-signing-public-next.pem").write_bytes(
        key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )

    frozen = tmp_path / "packages/frozen/module-package.yaml"
    frozen.parent.mkdir(parents=True)
    frozen.write_text("name: nold-ai/specfact-frozen\nversion: 1.0.0\n", encoding="utf-8")
    file_digest = hashlib.sha256(frozen.read_bytes()).hexdigest()
    frozen_tree = hashlib.sha256(f"module-package.yaml:{file_digest}".encode()).hexdigest()
    (ci / "official-module-release-cutoff.json").write_text(
        json.dumps({"archives": {"nold-ai/specfact-frozen": {"1.0.0": {"tree": frozen_tree}}}}),
        encoding="utf-8",
    )
    source = tmp_path / "packages/source/module-package.yaml"
    source.parent.mkdir()
    source.write_text("name: nold-ai/specfact-source\nversion: 2.0.0\n", encoding="utf-8")
    (source.parent / "commands.py").write_text("enabled = True\n", encoding="utf-8")
    signer = run_path(str(REPO_ROOT / "scripts/sign-modules.py"), run_name="specfact_module_signer")
    signer["sign_manifest"](source, key, payload_from_filesystem=True)
    return frozen, source


def _run_reproducibility_step(
    tmp_path: Path, key: Ed25519PrivateKey, private: Ed25519PrivateKey
) -> subprocess.CompletedProcess[str]:
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    passphrase = b"temporary test passphrase"
    private_pem = private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(passphrase)
    )
    step = _workflow()["jobs"]["reproducibility"]["steps"][-1]
    script = step["run"].removeprefix("python - <<'PYTHON'\n").removesuffix("\nPYTHON\n")
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={
            "PATH": str(Path(sys.executable).parent),
            "MODULE_PRIVATE_KEY": private_pem.decode(),
            "MODULE_KEY_PASSPHRASE": passphrase.decode(),
            "EXPECTED_PUBLIC_KEY_SHA256": hashlib.sha256(public_der).hexdigest(),
        },
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("valid", "Reproduced replacement signature"),
        ("wrong-key", "does not match the pinned public key"),
        ("changed-frozen-tree", "do not match the approved release cutoff"),
        ("changed-signature", "Replacement signature is not reproducible"),
    ],
    ids=("valid", "wrong-key", "changed-frozen-tree", "changed-signature"),
)
def test_reproducibility_step_checks_cutoff_and_replacement(tmp_path: Path, case: str, expected: str) -> None:
    key = Ed25519PrivateKey.generate()
    frozen, source = _prepare_reproducibility_workspace(tmp_path, key)
    if case == "changed-frozen-tree":
        (frozen.parent / "payload.txt").write_text("changed", encoding="utf-8")
    if case == "changed-signature":
        data = yaml.safe_load(source.read_bytes())
        data["integrity"]["signature"] = base64.b64encode(key.sign(b"different payload")).decode()
        source.write_text(yaml.safe_dump(data), encoding="utf-8")

    original_manifests = [frozen.read_bytes(), source.read_bytes()]
    private = Ed25519PrivateKey.generate() if case == "wrong-key" else key
    result = _run_reproducibility_step(tmp_path, key, private)
    assert [frozen.read_bytes(), source.read_bytes()] == original_manifests
    if case == "valid":
        assert result.returncode == 0, result.stderr
        assert "Verified immutable cutoff tree" in result.stdout
        assert expected in result.stdout
    else:
        assert result.returncode != 0
        assert expected in result.stderr
