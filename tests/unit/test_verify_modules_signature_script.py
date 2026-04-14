from __future__ import annotations

from pathlib import Path

import yaml

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
