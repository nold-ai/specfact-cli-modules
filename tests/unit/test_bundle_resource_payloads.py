"""Official bundles ship audited prompt and backlog template resources at stable paths."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SIGN_SCRIPT = REPO_ROOT / "scripts" / "sign-modules.py"


_EXPECTED_PROMPTS: dict[str, tuple[str, ...]] = {
    "specfact-codebase": (
        "specfact.01-import.md",
        "specfact.validate.md",
    ),
    "specfact-project": (
        "specfact.02-plan.md",
        "specfact.03-review.md",
        "specfact.04-sdd.md",
        "specfact.06-sync.md",
        "specfact.compare.md",
    ),
    "specfact-govern": ("specfact.05-enforce.md",),
    "specfact-spec": ("specfact.07-contracts.md",),
}

_COMPANION = "shared/cli-enforcement.md"

_FIELD_MAPPING_SEEDS = (
    "ado_agile.yaml",
    "ado_custom.yaml",
    "ado_default.yaml",
    "ado_kanban.yaml",
    "ado_safe.yaml",
    "ado_scrum.yaml",
    "github_custom.yaml",
)


@pytest.mark.parametrize("bundle,prompts", list(_EXPECTED_PROMPTS.items()))
def test_official_bundles_package_expected_prompt_files(bundle: str, prompts: tuple[str, ...]) -> None:
    root = REPO_ROOT / "packages" / bundle / "resources" / "prompts"
    for name in prompts:
        path = root / name
        assert path.is_file(), f"missing prompt {path}"
    companion = root / _COMPANION
    assert companion.is_file(), f"missing companion {companion}"


def test_prompt_companion_resolves_relative_to_prompt_root() -> None:
    """IDE/export layouts preserve ./shared/cli-enforcement.md next to prompt files."""
    for bundle, names in _EXPECTED_PROMPTS.items():
        first = REPO_ROOT / "packages" / bundle / "resources" / "prompts" / names[0]
        text = first.read_text(encoding="utf-8")
        if "./shared/cli-enforcement.md" in text:
            companion = REPO_ROOT / "packages" / bundle / "resources" / "prompts" / "shared" / "cli-enforcement.md"
            assert companion.is_file(), bundle


def test_backlog_bundle_packages_field_mapping_seed_set() -> None:
    module_root = REPO_ROOT / "packages" / "specfact-backlog"
    roots = (
        module_root / "resources" / "templates" / "backlog" / "field_mappings",
        module_root / "src" / "specfact_backlog" / "resources" / "templates" / "backlog" / "field_mappings",
    )
    for name in _FIELD_MAPPING_SEEDS:
        for base in roots:
            path = base / name
            assert path.is_file(), f"missing field mapping seed {path}"


def test_module_package_layout_matches_init_ide_resource_contract() -> None:
    """Core discovers resources/prompts and resources/templates/... under the module package root."""
    backlog = REPO_ROOT / "packages" / "specfact-backlog"
    assert (backlog / "resources" / "templates" / "backlog" / "field_mappings" / "ado_default.yaml").is_file()
    codebase = REPO_ROOT / "packages" / "specfact-codebase"
    assert (codebase / "resources" / "prompts" / "specfact.01-import.md").is_file()


def test_resource_change_changes_signed_payload_checksum(tmp_path: Path) -> None:
    """Bundled resource files participate in the module integrity payload (resource-aware integrity)."""
    sign_script = load_module_from_path("sign_modules_payload", SIGN_SCRIPT)
    module_payload = vars(sign_script)["_module_payload"]

    module_dir = tmp_path / "packages" / "specfact-example"
    (module_dir / "resources" / "prompts").mkdir(parents=True)
    (module_dir / "resources" / "prompts" / "specfact.example.md").write_text("v1\n", encoding="utf-8")
    manifest = module_dir / "module-package.yaml"
    manifest.write_text(
        yaml.safe_dump({"name": "nold-ai/specfact-example", "version": "0.1.0"}, sort_keys=False),
        encoding="utf-8",
    )

    first = hashlib.sha256(module_payload(module_dir, payload_from_filesystem=True)).hexdigest()
    (module_dir / "resources" / "prompts" / "specfact.example.md").write_text("v2\n", encoding="utf-8")
    second = hashlib.sha256(module_payload(module_dir, payload_from_filesystem=True)).hexdigest()

    assert first != second


def test_version_bump_enforcement_detects_unchanged_version(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Resource-only publish attempts must bump module version (enforced against base ref in CI)."""
    verify_script = load_module_from_path(
        "verify_modules_signature_vb",
        REPO_ROOT / "scripts" / "verify-modules-signature.py",
    )
    manifest = tmp_path / "packages" / "specfact-example" / "module-package.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump({"name": "nold-ai/specfact-example", "version": "0.1.0"}, sort_keys=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(verify_script, "_changed_manifests_from_git", lambda _base: [manifest])
    monkeypatch.setattr(verify_script, "_read_manifest_version_from_git", lambda _ref, _path: "0.1.0")

    failures = verify_script._verify_version_bumps("origin/dev")  # pylint: disable=protected-access
    assert failures and "not incremented" in failures[0]
