from __future__ import annotations

import base64
import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tests.unit._script_test_utils import block_contract_imports, load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify-modules-signature.py"


def _load_verify_script():
    return load_module_from_path("verify_modules_signature", SCRIPT_PATH)


def test_verify_script_loads_without_beartype_or_icontract(monkeypatch) -> None:
    block_contract_imports(monkeypatch)

    verify_script = _load_verify_script()

    assert callable(verify_script.beartype)
    assert callable(verify_script.require)
    assert callable(verify_script.ensure)


def test_verify_manifest_falls_back_to_filesystem_payload_when_checksum_matches(tmp_path: Path) -> None:
    verify_script = _load_verify_script()
    module_dir = tmp_path / "packages" / "specfact-example"
    tests_dir = module_dir / "tests"
    module_dir.mkdir(parents=True)
    tests_dir.mkdir()
    (module_dir / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tests_dir / "test_src.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    manifest_path = module_dir / "module-package.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-example",
                "version": "0.1.0",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    module_payload = vars(verify_script)["_module_payload"]
    digest = verify_script.hashlib.sha256(module_payload(module_dir, payload_from_filesystem=True)).hexdigest()
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-example",
                "version": "0.1.0",
                "integrity": {
                    "checksum": f"sha256:{digest}",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    verification_mode = verify_script.verify_manifest(
        manifest_path,
        require_signature=False,
        public_key_pem="",
        payload_from_filesystem=False,
    )

    assert verification_mode == "filesystem"


def test_verify_manifest_allows_unverified_optional_signature_without_public_key(tmp_path: Path) -> None:
    verify_script = _load_verify_script()
    module_dir = tmp_path / "packages" / "specfact-example"
    module_dir.mkdir(parents=True)
    (module_dir / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    manifest_path = module_dir / "module-package.yaml"
    manifest_path.write_text(
        yaml.safe_dump({"name": "nold-ai/specfact-example", "version": "0.1.0"}, sort_keys=False),
        encoding="utf-8",
    )
    payload = verify_script._module_payload(module_dir, payload_from_filesystem=True)  # pylint: disable=protected-access
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-example",
                "version": "0.1.0",
                "integrity": {
                    "checksum": f"sha256:{verify_script.hashlib.sha256(payload).hexdigest()}",
                    "signature": "a" * 44,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    verification_mode = verify_script.verify_manifest(
        manifest_path,
        require_signature=False,
        public_key_pem="",
        payload_from_filesystem=True,
        allow_missing_public_key=True,
    )

    assert verification_mode == "filesystem"


def test_verify_manifest_integrity_shape_only_accepts_checksum_only_manifest(tmp_path: Path) -> None:
    verify_script = _load_verify_script()
    module_dir = tmp_path / "packages" / "specfact-example"
    module_dir.mkdir(parents=True)
    manifest_path = module_dir / "module-package.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-example",
                "version": "0.1.0",
                "integrity": {
                    "checksum": "sha256:" + "a" * 64,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    verify_script.verify_manifest_integrity_shape_only(manifest_path, require_signature=False)


def test_verify_manifest_integrity_shape_only_rejects_bad_checksum_format(tmp_path: Path) -> None:
    verify_script = _load_verify_script()
    module_dir = tmp_path / "packages" / "specfact-example"
    module_dir.mkdir(parents=True)
    manifest_path = module_dir / "module-package.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-example",
                "version": "0.1.0",
                "integrity": {"checksum": "not-a-valid-checksum"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    try:
        verify_script.verify_manifest_integrity_shape_only(manifest_path, require_signature=False)
    except ValueError as exc:
        assert "checksum" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_verify_manifest_integrity_shape_only_enforces_signature_when_requested(tmp_path: Path) -> None:
    verify_script = _load_verify_script()
    module_dir = tmp_path / "packages" / "specfact-example"
    module_dir.mkdir(parents=True)
    manifest_path = module_dir / "module-package.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "name": "nold-ai/specfact-example",
                "version": "0.1.0",
                "integrity": {"checksum": "sha256:" + "b" * 64},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    try:
        verify_script.verify_manifest_integrity_shape_only(manifest_path, require_signature=True)
    except ValueError as exc:
        assert "signature" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


@pytest.mark.parametrize(
    "case",
    (
        "signature-only",
        "wrong-key",
        "substituted-key",
        "checksum",
        "extra-file",
        "working-tree",
        "metadata-only",
        "cutoff",
    ),
)
def test_verify_version_bump_accepts_only_authenticated_signature_rotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    verify_script = _load_verify_script()
    monkeypatch.chdir(tmp_path)

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args], text=True
        ).strip()

    git("init", "--quiet")
    git("config", "user.email", "fixture@example.test")
    git("config", "user.name", "Fixture")
    package = Path("packages/specfact-example")
    package.mkdir(parents=True)
    (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    manifest = package / "module-package.yaml"
    manifest.write_text("name: nold-ai/specfact-example\nversion: 0.1.0\n", encoding="utf-8")
    payload = verify_script._module_payload(package, payload_from_filesystem=True)
    checksum = hashlib.sha256(payload).hexdigest()
    previous_key = Ed25519PrivateKey.generate()
    replacement_key = Ed25519PrivateKey.generate()
    public = replacement_key.public_key()
    public_path = tmp_path / "module-signing-public-next.pem"
    public_path.write_bytes(
        public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    public_der = public.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    monkeypatch.setattr(verify_script, "_REPLACEMENT_PUBLIC_KEY", public_path, raising=False)
    monkeypatch.setattr(
        verify_script, "_REPLACEMENT_PUBLIC_KEY_SHA256", hashlib.sha256(public_der).hexdigest(), raising=False
    )
    original_signature = base64.b64encode(previous_key.sign(payload)).decode()
    original = manifest.read_text(encoding="utf-8") + (
        f"integrity:\n  checksum: sha256:{checksum}\n  signature: {original_signature}\n"
    )
    manifest.write_text(original, encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "Initial source manifest")
    base_ref = git("rev-parse", "HEAD")

    key = Ed25519PrivateKey.generate() if case in ("wrong-key", "substituted-key") else replacement_key
    if case == "substituted-key":
        public_path.write_bytes(
            key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        )
    signature = base64.b64encode(key.sign(payload)).decode()

    candidate = original.replace(original_signature, signature)
    if case == "checksum":
        candidate = candidate.replace(checksum, "0" * 64)
    manifest.write_text(candidate, encoding="utf-8")
    if case == "extra-file":
        excluded = package / "tests"
        excluded.mkdir()
        (excluded / "test_module.py").write_text("# new test content\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "Rotate source manifest signature")
    if case == "working-tree":
        manifest.write_text(candidate + "\n", encoding="utf-8")
    if case == "cutoff":
        monkeypatch.setattr(verify_script, "_matches_published_cutoff", lambda *_: True)

    if case == "metadata-only":
        from argparse import Namespace

        failures = verify_script._version_bump_failures_for_cli(
            Namespace(enforce_version_bump=True, version_check_base=base_ref, metadata_only=True)
        )
    else:
        failures = verify_script._verify_version_bumps(base_ref)
    if case == "signature-only":
        assert failures == []
    else:
        assert len(failures) == 1
        assert "version was not incremented" in failures[0]
