"""Real signed-install regression for #459; all artifacts stay in pytest tmp_path."""

from __future__ import annotations

import base64
import hashlib
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from specfact_cli.models.module_package import ModulePackageMetadata
from specfact_cli.registry import module_installer
from specfact_cli.registry.module_discovery import DiscoveredModule

from specfact_code_review.run import toolchain


MODULE_ID = "nold-ai/specfact-code-review"


def _fixture_package(root: Path, layout: str, *, real_bundle: bool) -> Path:
    module = root / "fixture"
    package = module / layout / "specfact_code_review"
    if real_bundle:
        source = Path(toolchain.__file__).resolve().parents[1]
        shutil.copytree(source, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text("print('fixture-started')\n", encoding="utf-8")
        resource = package / "resources" / "policy.json"
        resource.parent.mkdir()
        resource.write_text('{"fixture":true}\n', encoding="utf-8")
        resource.chmod(0o640)
    return module


def _signed_fixture(root: Path, layout: str, *, real_bundle: bool = False) -> tuple[Path, Path, str]:
    """Sign an inert package with an ephemeral test key, never a publisher key."""
    module = _fixture_package(root, layout, real_bundle=real_bundle)
    manifest = {
        "name": MODULE_ID,
        "version": "0.0.1",
        "commands": ["code"],
        "core_compatibility": ">=0.55.1,<1.0.0",
        "publisher": {"name": "nold-ai", "email": "fixture@example.invalid"},
    }
    manifest_path = module / "module-package.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    payload = module_installer._module_artifact_payload_signed(module)
    key = Ed25519PrivateKey.generate()
    public_pem = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode("utf-8")
    )
    public_path = root / "fixture-public.pem"
    public_path.write_text(public_pem, encoding="utf-8")
    manifest["integrity"] = {
        "checksum": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "signature": base64.b64encode(key.sign(payload)).decode("ascii"),
    }
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    archive_path = root / "fixture.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(module, arcname="specfact-code-review")
    return archive_path, public_path, public_pem


def _install_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str, *, real_bundle: bool = False
) -> tuple[DiscoveredModule, Path, Path]:
    archive, public_key, public_pem = _signed_fixture(tmp_path, layout, real_bundle=real_bundle)
    monkeypatch.delenv("SPECFACT_ALLOW_UNSIGNED", raising=False)
    monkeypatch.setenv("SPECFACT_MODULE_PUBLIC_KEY_PEM", public_pem)
    # Replace download transport only; extraction, metadata, checksum, signature,
    # install markers, and atomic placement use the real core implementation.
    monkeypatch.setattr(module_installer, "_download_archive_with_cache", lambda *_a, **_kw: archive)
    install_root = tmp_path / "user-modules"
    installed = module_installer.install_module(
        MODULE_ID,
        module_installer.InstallModuleOptions(install_root=install_root, skip_deps=True, non_interactive=True),
    )
    archive.unlink()
    metadata = ModulePackageMetadata.model_validate(
        yaml.safe_load((installed / "module-package.yaml").read_text(encoding="utf-8"))
    )
    assert module_installer.verify_module_artifact(
        installed,
        metadata,
        allow_unsigned=False,
        require_integrity=True,
        require_signature=True,
        public_key_pem=public_pem,
    )
    assert not archive.exists()
    return DiscoveredModule(installed, metadata, "user"), install_root, public_key


@pytest.mark.parametrize("layout", ["src", ""], ids=["src", "flat"])
def test_signed_install_handoff_and_copy_after_archive_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str
) -> None:
    """459-1-1/459-1-2: preserve installed paths, resources, modes and copy startup."""
    discovered, install_root, public_key = _install_fixture(tmp_path, monkeypatch, layout)
    handoff = toolchain.derive_core_0_55_1_install_handoff(
        discovered,
        expected_registry_id=MODULE_ID,
        user_modules_root=install_root,
        marketplace_modules_root=tmp_path / "marketplace",
        public_key_path=public_key,
    )
    assert handoff.status == "PASS", handoff.reason
    payload = toolchain.verify_installed_module_payload(handoff)
    assert payload.status == "PASS", payload.reason
    prefix = Path(layout) / "specfact_code_review"
    assert {entry.path for entry in payload.manifest} == {
        (prefix / name).as_posix() for name in ("__init__.py", "__main__.py", "resources/policy.json")
    }
    capsule_root = tmp_path / "capsule"
    copied = toolchain.install_builtin_payload(payload, capsule_root=capsule_root)
    assert copied.status == "PASS", copied.reason
    assert copied.destination == "/opt/specfact/builtin/specfact_code_review"
    destination = capsule_root / copied.destination.lstrip("/")
    for entry in payload.manifest:
        relative = Path(entry.path).relative_to(prefix)
        target = destination / relative
        assert "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest() == entry.digest
        assert stat.S_IMODE(target.stat().st_mode) == entry.mode
    # Exercise only inert fixture startup, not a real analyzer or Linux sandbox.
    startup = subprocess.run(
        [sys.executable, "-B", "-E", "-s", "-m", "specfact_code_review"],
        cwd=destination.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert startup.returncode == 0, startup.stderr
    assert startup.stdout.strip() == "fixture-started"


@pytest.mark.parametrize("layout", ["src", ""], ids=["src", "flat"])
def test_signed_installed_bundle_runs_copied_builtin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str
) -> None:
    """Run the actual AST built-in from the signed, installed and copied bundle."""
    discovered, install_root, public_key = _install_fixture(tmp_path, monkeypatch, layout, real_bundle=True)
    handoff = toolchain.derive_core_0_55_1_install_handoff(
        discovered,
        expected_registry_id=MODULE_ID,
        user_modules_root=install_root,
        marketplace_modules_root=tmp_path / "marketplace",
        public_key_path=public_key,
    )
    assert handoff.status == "PASS", handoff.reason
    payload = toolchain.verify_installed_module_payload(handoff)
    capsule_root = tmp_path / "capsule"
    copied = toolchain.install_builtin_payload(payload, capsule_root=capsule_root)
    assert copied.status == "PASS", copied.reason
    builtin_root = capsule_root / "opt/specfact/builtin"
    target = builtin_root / "fixture_source.py"
    target.write_text("def _unused_extension():\n    pass\n", encoding="utf-8")
    probe = (
        "from pathlib import Path; "
        "from specfact_code_review.tools import ast_clean_code_runner as analyzer; "
        "assert Path(analyzer.__file__).resolve().is_relative_to(Path.cwd()); "
        "findings = analyzer.run_ast_clean_code([Path('fixture_source.py')]); "
        "assert findings, 'expected a finding from the unused stub'; "
        "print('copied-builtin-completed')"
    )
    startup = subprocess.run(
        [sys.executable, "-B", "-E", "-s", "-c", probe],
        cwd=builtin_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert startup.returncode == 0, startup.stderr
    assert startup.stdout.strip() == "copied-builtin-completed"
