from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/publish-modules.yml"


def _publish_job() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["publish"]


def _publish_step() -> dict:
    return next(step for step in _publish_job()["steps"] if step["name"] == "Publish changed bundles into registry")


def _run_publish_step(tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    script = _publish_step()["run"].removeprefix("python - <<'PY'\n").removesuffix("\nPY\n")
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_publish_uses_only_protected_replacement_secrets() -> None:
    job = _publish_job()
    assert job["environment"] == "module-signing"
    for required in ("MODULE_PUBLICATION_ENABLED", "github.ref_protected", "refs/heads/dev", "refs/heads/main"):
        assert required in job["if"]
    step_env = _publish_step()["env"]
    assert step_env["SPECFACT_MODULE_PRIVATE_SIGN_KEY"] == "${{ secrets.MODULE_SIGNING_PRIVATE_KEY_V2 }}"
    assert step_env["SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE"] == (
        "${{ secrets.MODULE_SIGNING_PRIVATE_KEY_PASSPHRASE_V2 }}"
    )


def _prepare_publish_workspace(tmp_path: Path, version: str, case: str) -> None:
    bundle = "specfact-example"
    module_id = f"nold-ai/{bundle}"
    source = tmp_path / "packages" / bundle
    source.mkdir(parents=True)
    manifest = source / "module-package.yaml"
    manifest.write_text(
        yaml.safe_dump({"name": module_id, "version": version, "core_compatibility": ">=0.55.4"}),
        encoding="utf-8",
    )
    (source / "commands.py").write_text("enabled = True\n", encoding="utf-8")
    registry = tmp_path / "registry"
    artifacts = registry / "modules"
    signatures = registry / "signatures"
    artifacts.mkdir(parents=True)
    signatures.mkdir()
    registry_index = registry / "index.json"
    registry_index.write_text(json.dumps({"modules": [{"id": module_id, "latest_version": "1.0.0"}]}))
    previous = artifacts / f"{bundle}-1.0.0.tar.gz"
    previous.write_bytes(b"previous release")
    previous_signature = signatures / f"{bundle}-1.0.0.tar.sig"
    previous_signature.write_bytes(b"previous signature\n")
    if case == "occupied-artifact":
        (artifacts / f"{bundle}-{version}.tar.gz").write_bytes(b"reserved artifact")

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("sign-modules.py", "verify-modules-signature.py", "publish-module.py", "publish_module.py"):
        shutil.copyfile(REPO_ROOT / "scripts" / name, scripts / name)
    shutil.copyfile(REPO_ROOT / "publish_bundle_selection.py", tmp_path / "publish_bundle_selection.py")

    ci = tmp_path / "ci"
    ci.mkdir()
    (ci / "official-module-release-cutoff.json").write_text(
        json.dumps({"latest": {module_id: "1.0.0"}, "archives": {}}),
    )


def _publish_environment(tmp_path: Path, case: str) -> dict[str, str]:
    ci = tmp_path / "ci"
    bundle = "specfact-example"
    key = Ed25519PrivateKey.generate()
    public = key.public_key()
    (ci / "module-signing-public-next.pem").write_bytes(
        public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo),
    )
    fingerprint = hashlib.sha256(
        public.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    ).hexdigest()
    if case == "wrong-key":
        key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"temporary test key"),
    )

    return {
        "PATH": str(Path(sys.executable).parent),
        "BUNDLES_JSON": json.dumps([bundle]),
        "GITHUB_REF_NAME": "dev",
        "EXPECTED_PUBLIC_KEY_SHA256": fingerprint,
        "SPECFACT_MODULE_PRIVATE_SIGN_KEY": "" if case == "missing-key" else pem.decode(),
        "SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE": "temporary test key",
    }


def _assert_registry_publication(tmp_path: Path, version: str, case: str) -> None:
    bundle = "specfact-example"
    registry = tmp_path / "registry"
    manifest = tmp_path / "packages" / bundle / "module-package.yaml"
    entry = json.loads((registry / "index.json").read_text())["modules"][0]
    if case == "new-version":
        archive = registry / "modules" / f"{bundle}-{version}.tar.gz"
        assert entry["latest_version"] == version
        assert entry["checksum_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
        assert entry["core_compatibility"] == ">=0.55.4"
        assert (registry / "signatures" / f"{bundle}-{version}.tar.sig").is_file()
    else:
        assert entry["latest_version"] == "1.0.0"
        assert "integrity" not in yaml.safe_load(manifest.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("already-published", None),
        ("new-version", None),
        ("missing-key", "encrypted replacement signing key"),
        ("wrong-key", "does not match the pinned replacement key"),
        ("occupied-artifact", "Cannot replace existing"),
    ],
)
def test_publish_step_signs_new_release_and_preserves_old_artifacts(
    tmp_path: Path, case: str, expected: str | None
) -> None:
    version = "1.0.0" if case == "already-published" else "1.0.1"
    _prepare_publish_workspace(tmp_path, version, case)
    registry = tmp_path / "registry"
    previous = registry / "modules/specfact-example-1.0.0.tar.gz"
    previous_signature = registry / "signatures/specfact-example-1.0.0.tar.sig"
    result = _run_publish_step(tmp_path, _publish_environment(tmp_path, case))
    assert previous.read_bytes() == b"previous release"
    assert previous_signature.read_bytes() == b"previous signature\n"
    if expected:
        assert result.returncode != 0
        assert expected in result.stderr
    else:
        assert result.returncode == 0, result.stderr
    _assert_registry_publication(tmp_path, version, case)


def test_publish_skips_current_release_and_continues_with_next_bundle(tmp_path: Path) -> None:
    _prepare_publish_workspace(tmp_path, "1.0.0", "already-published")
    artifacts = tmp_path / "registry/modules"
    previous = artifacts / "specfact-example-1.0.0.tar.gz"
    previous_checksum = previous.with_suffix(".gz.sha256")
    previous_checksum.write_text(hashlib.sha256(previous.read_bytes()).hexdigest(), encoding="utf-8")
    previous_signature = tmp_path / "registry/signatures/specfact-example-1.0.0.tar.sig"
    frozen = {path: path.read_bytes() for path in (previous, previous_checksum, previous_signature)}

    new_bundle = tmp_path / "packages/specfact-next"
    new_bundle.mkdir()
    (new_bundle / "module-package.yaml").write_text("name: nold-ai/specfact-next\nversion: 1.0.1\n", encoding="utf-8")
    env = _publish_environment(tmp_path, "mixed")
    env["BUNDLES_JSON"] = json.dumps(["specfact-example", "specfact-next"])
    result = _run_publish_step(tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert "Skipping specfact-example" in result.stdout
    assert (artifacts / "specfact-next-1.0.1.tar.gz").is_file()
    assert {path: path.read_bytes() for path in frozen} == frozen
