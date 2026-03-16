from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify-modules-signature.py"


def _load_verify_script():
    spec = importlib.util.spec_from_file_location("verify_modules_signature", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load verify-modules-signature.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    digest = verify_script.hashlib.sha256(
        verify_script._module_payload(module_dir, payload_from_filesystem=True)
    ).hexdigest()
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
