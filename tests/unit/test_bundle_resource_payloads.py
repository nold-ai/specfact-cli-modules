"""Official bundles ship audited prompt and backlog template resources at stable paths."""

from __future__ import annotations

import hashlib
import shutil
import tarfile
from pathlib import Path

import pytest
import yaml
from specfact_cli.models.protocol import Protocol, Transition
from specfact_cli.utils import ide_setup

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SIGN_SCRIPT = REPO_ROOT / "scripts" / "sign-modules.py"


_EXPECTED_PROMPTS: dict[str, tuple[str, ...]] = {
    "specfact-backlog": (
        "specfact.backlog-add.md",
        "specfact.backlog-daily.md",
        "specfact.backlog-refine.md",
        "specfact.sync-backlog.md",
    ),
    "specfact-codebase": (
        "specfact.01-import.md",
        "specfact.validate.md",
    ),
    "specfact-project": (
        "specfact.02-plan.md",
        "specfact.03-review.md",
        "specfact.04-sdd.md",
        "specfact.06-sync.md",
        "specfact.08-simplify.md",
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

_PROJECT_RUNTIME_TEMPLATES = (
    "protocol.yaml.j2",
    "github-action.yml.j2",
)
_PROJECT_PERSONA_TEMPLATES = ("default.md.j2",)

_IGNORED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "logs"}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _build_bundle_artifact(bundle: str, tmp_path: Path) -> Path:
    bundle_dir = REPO_ROOT / "packages" / bundle
    artifact = tmp_path / f"{bundle}.tar.gz"
    with tarfile.open(artifact, "w:gz") as archive:
        for path in sorted(bundle_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(bundle_dir)
            if any(part in _IGNORED_DIR_NAMES for part in rel.parts):
                continue
            if path.suffix.lower() in _IGNORED_SUFFIXES:
                continue
            archive.add(path, arcname=f"{bundle}/{rel.as_posix()}")
    return artifact


def _top_level_prompt_names(prompt_root: Path) -> set[str]:
    return {path.name for path in prompt_root.glob("specfact*.md") if path.is_file()}


@pytest.mark.parametrize("bundle,prompts", list(_EXPECTED_PROMPTS.items()))
def test_official_bundles_package_expected_prompt_files(bundle: str, prompts: tuple[str, ...]) -> None:
    root = REPO_ROOT / "packages" / bundle / "resources" / "prompts"
    assert _top_level_prompt_names(root) == set(prompts)
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


def test_github_custom_seed_includes_bug_parent_hierarchy() -> None:
    """Aligns packaged seed with map-fields defaults so bugs keep valid parent constraints after init copy."""
    module_root = REPO_ROOT / "packages" / "specfact-backlog"
    expected_bug = ["story", "feature", "epic"]
    for rel in (
        "resources/templates/backlog/field_mappings/github_custom.yaml",
        "src/specfact_backlog/resources/templates/backlog/field_mappings/github_custom.yaml",
    ):
        data = yaml.safe_load((module_root / rel).read_text(encoding="utf-8"))
        ch = data.get("creation_hierarchy") or {}
        assert ch.get("bug") == expected_bug


def test_module_package_layout_matches_init_ide_resource_contract() -> None:
    """Core discovers resources/prompts and resources/templates/... under the module package root."""
    backlog = REPO_ROOT / "packages" / "specfact-backlog"
    assert (backlog / "resources" / "prompts" / "specfact.backlog-refine.md").is_file()
    assert (backlog / "resources" / "templates" / "backlog" / "field_mappings" / "ado_default.yaml").is_file()
    codebase = REPO_ROOT / "packages" / "specfact-codebase"
    assert (codebase / "resources" / "prompts" / "specfact.01-import.md").is_file()


def test_project_bundle_packages_runtime_generator_templates() -> None:
    module_root = REPO_ROOT / "packages" / "specfact-project"
    for name in _PROJECT_RUNTIME_TEMPLATES:
        path = module_root / "resources" / "templates" / name
        assert path.is_file(), f"missing project runtime template {path}"
    for name in _PROJECT_PERSONA_TEMPLATES:
        path = module_root / "resources" / "templates" / "persona" / name
        assert path.is_file(), f"missing project persona template {path}"


def test_project_runtime_templates_resolve_at_runtime(tmp_path: Path) -> None:
    from specfact_project.generators.persona_exporter import PersonaExporter
    from specfact_project.generators.protocol_generator import ProtocolGenerator
    from specfact_project.generators.workflow_generator import WorkflowGenerator

    protocol = Protocol(
        states=["draft", "qa:review"],
        start="draft",
        transitions=[
            Transition(
                from_state="draft",
                on_event="complete:now",
                to_state="qa:review",
                guard="ready `#1`",
            )
        ],
    )

    protocol_output = tmp_path / "protocol.yaml"
    ProtocolGenerator().generate(protocol, protocol_output)
    protocol_data = yaml.safe_load(protocol_output.read_text(encoding="utf-8"))
    assert protocol_data["states"] == protocol.states
    assert protocol_data["start"] == protocol.start
    assert len(protocol_data["transitions"]) == 1
    tr = protocol_data["transitions"][0]
    assert tr["from_state"] == protocol.transitions[0].from_state
    assert tr["on_event"] == protocol.transitions[0].on_event
    assert tr["to_state"] == protocol.transitions[0].to_state
    assert tr["guard"] == protocol.transitions[0].guard

    workflow_output = tmp_path / "specfact-gate.yml"
    WorkflowGenerator().generate_github_action(workflow_output, repo_name="example/project")
    workflow_data = yaml.safe_load(workflow_output.read_text(encoding="utf-8"))
    validate_step = next(
        step for step in workflow_data["jobs"]["specfact"]["steps"] if step.get("name") == "Run validation"
    )
    assert "example/project" in validate_step["run"]

    exporter = PersonaExporter()
    assert exporter.templates_dir.name == "persona"
    assert (exporter.templates_dir / "default.md.j2").is_file()


def test_code_review_bundle_packages_clean_code_policy_pack_manifest() -> None:
    module_root = REPO_ROOT / "packages" / "specfact-code-review"
    roots = (
        module_root / "resources" / "policy-packs" / "specfact" / "clean-code-principles.yaml",
        module_root
        / "src"
        / "specfact_code_review"
        / "resources"
        / "policy-packs"
        / "specfact"
        / "clean-code-principles.yaml",
    )
    expected_rules = {
        "banned-generic-public-names",
        "swallowed-exception-pattern",
        "kiss.loc.warning",
        "kiss.loc.error",
        "kiss.nesting.warning",
        "kiss.nesting.error",
        "kiss.parameter-count.warning",
        "kiss.parameter-count.error",
        "yagni.unused-private-helper",
        "dry.duplicate-function-shape",
        "solid.mixed-dependency-role",
        "clean-code.pr-checklist-missing-rationale",
    }

    for manifest_path in roots:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        assert data["pack_ref"] == "specfact/clean-code-principles"
        assert data["default_mode"] == "advisory"
        assert {rule["id"] for rule in data["rules"]} == expected_rules


def test_code_review_bundle_packages_ai_bloat_policy_pack_manifest() -> None:
    module_root = REPO_ROOT / "packages" / "specfact-code-review"
    manifest_path = module_root / "resources" / "policy-packs" / "specfact" / "ai-bloat-patterns.yaml"
    semgrep_path = module_root / "resources" / "semgrep-rules" / "ai-bloat.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    expected_rules = {
        "ai-bloat.manual-loop-comprehension",
        "ai-bloat.passthrough-lambda",
        "ai-bloat.identity-try-except",
        "ai-bloat.none-then-none",
        "ai-bloat.single-call-wrapper",
        "ai-bloat.unused-optional-param",
        "ai-bloat.dead-branch",
        "ai-bloat.loc-vs-complexity",
        "ai-bloat.redundant-intermediate",
    }

    assert semgrep_path.is_file()
    assert data["pack_ref"] == "specfact/ai-bloat-patterns"
    assert data["default_mode"] == "advisory"
    assert {rule["id"] for rule in data["rules"]} == expected_rules
    assert {rule["category"] for rule in data["rules"]} == {"ai_bloat"}
    assert {rule["principle"] for rule in data["rules"]} == {"ai_bloat"}


def test_backlog_artifact_contains_prompt_payload(tmp_path: Path) -> None:
    artifact = _build_bundle_artifact("specfact-backlog", tmp_path)
    with tarfile.open(artifact, "r:gz") as archive:
        names = {
            name
            for name in archive.getnames()
            if name.startswith("specfact-backlog/resources/prompts/") and name.count("/") == 3 and name.endswith(".md")
        }

    expected = {f"specfact-backlog/resources/prompts/{prompt}" for prompt in _EXPECTED_PROMPTS["specfact-backlog"]}
    assert names == expected


def test_code_review_artifact_contains_policy_pack_payload(tmp_path: Path) -> None:
    artifact = _build_bundle_artifact("specfact-code-review", tmp_path)
    with tarfile.open(artifact, "r:gz") as archive:
        names = set(archive.getnames())

    assert "specfact-code-review/resources/policy-packs/specfact/clean-code-principles.yaml" in names
    assert "specfact-code-review/resources/policy-packs/specfact/ai-bloat-patterns.yaml" in names
    assert "specfact-code-review/resources/semgrep-rules/ai-bloat.yaml" in names


def test_project_artifact_contains_runtime_generator_templates(tmp_path: Path) -> None:
    artifact = _build_bundle_artifact("specfact-project", tmp_path)
    with tarfile.open(artifact, "r:gz") as archive:
        names = set(archive.getnames())

    for name in _PROJECT_RUNTIME_TEMPLATES:
        assert f"specfact-project/resources/templates/{name}" in names
    for name in _PROJECT_PERSONA_TEMPLATES:
        assert f"specfact-project/resources/templates/persona/{name}" in names


def test_core_prompt_discovery_finds_installed_backlog_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules_root = tmp_path / "modules"
    installed_bundle = modules_root / "specfact-backlog"
    shutil.copytree(REPO_ROOT / "packages" / "specfact-backlog", installed_bundle)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    monkeypatch.setattr(ide_setup, "_module_discovery_roots", lambda _repo: [(modules_root, "custom")])
    catalog = ide_setup.discover_prompt_sources_catalog(repo_path, include_package_fallback=False)

    assert "nold-ai/specfact-backlog" in catalog
    names = {path.name for path in catalog["nold-ai/specfact-backlog"]}
    assert names == set(_EXPECTED_PROMPTS["specfact-backlog"])

    source_id = "nold-ai/specfact-backlog"
    segment = ide_setup.source_id_to_path_segment(source_id)
    copied, _ = ide_setup._copy_template_files_to_ide(  # pylint: disable=protected-access
        repo_path,
        "vscode",
        list(catalog[source_id]),
        source_segment=segment,
        write_settings=False,
    )
    assert copied
    copied_names = {path.name for path in copied}
    expected_names = {f"{Path(name).stem}.prompt.md" for name in _EXPECTED_PROMPTS["specfact-backlog"]}
    assert copied_names == expected_names
    assert all(path.parent.name == segment for path in copied)


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
