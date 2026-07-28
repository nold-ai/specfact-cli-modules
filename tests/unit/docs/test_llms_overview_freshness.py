"""Guard against stale generated command artifacts (llms.txt and command reference).

The pre-commit command-overview gate only fires when specific paths are staged, and the
PR orchestrator skips overview validation on dev-to-main promote runs, so a commit that
bypasses them (merge commits, --no-verify, registry bot commits with [skip ci]) can land
a stale llms.txt. A stale llms.txt misleads agents worse than a missing one, so this
test re-runs the generator in --check mode on every test run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click
import pytest
import typer
from typer.main import get_command as get_typer_command

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATOR = REPO_ROOT / "scripts" / "generate-command-overview.py"
GENERATED_ARTIFACTS = (
    "llms.txt",
    "docs/reference/commands.generated.json",
    "docs/reference/commands.generated.md",
)


def test_generated_command_artifacts_exist() -> None:
    for relative in GENERATED_ARTIFACTS:
        assert (REPO_ROOT / relative).is_file(), f"Missing generated artifact: {relative}"


def test_llms_and_command_overview_are_current() -> None:
    """llms.txt and the generated command reference must match the current bundle surface."""
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    combined_output = f"{result.stdout}\n{result.stderr}"
    if "No module named 'specfact_cli'" in combined_output:
        pytest.skip("specfact-cli dependency not installed in this environment")
    assert result.returncode == 0, (
        "Generated command artifacts (llms.txt, docs/reference/commands.generated.*) are stale. "
        "Regenerate with 'hatch run generate-command-overview' and commit the result.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_command_overview_records_optional_click_arguments() -> None:
    generator = load_module_from_path("generate_command_overview_arguments", GENERATOR)
    command = click.Command("import", params=[click.Argument(["source_path"], required=False)])

    assert generator._command_arguments(command) == [  # pylint: disable=protected-access
        {"name": "SOURCE_PATH", "required": False, "nargs": 1}
    ]


def test_command_overview_records_typer_parameters() -> None:
    """Typer's pinned Docs Review runtime must retain option and argument metadata."""
    generator = load_module_from_path("generate_command_overview_typer", GENERATOR)
    app = typer.Typer()

    @app.command()
    def inspect(
        source_path: str = typer.Argument(...),
        output_format: str = typer.Option("json", "--format"),
    ) -> None:
        del source_path, output_format

    assert inspect.__name__ == "inspect"
    command = get_typer_command(app)

    assert "--format" in generator._command_options(command)  # pylint: disable=protected-access
    assert {"name": "SOURCE_PATH", "required": True, "nargs": 1} in generator._command_arguments(  # pylint: disable=protected-access
        command
    )


def test_command_overview_preserves_explicit_typer_argument_metavar() -> None:
    """An explicit metavar is user-facing syntax, not a default label to normalize."""
    generator = load_module_from_path("generate_command_overview_typer_metavar", GENERATOR)
    app = typer.Typer()

    @app.command()
    def inspect(source_path: str = typer.Argument(..., metavar="path/to/file")) -> None:
        del source_path

    assert inspect.__name__ == "inspect"
    command = get_typer_command(app)

    assert {"name": "path/to/file", "required": True, "nargs": 1} in generator._command_arguments(  # pylint: disable=protected-access
        command
    )


def test_command_overview_rejects_unrepresented_official_inventory(tmp_path: Path, monkeypatch) -> None:
    generator = load_module_from_path("generate_command_overview_inventory", GENERATOR)
    manifest = tmp_path / "packages" / "specfact-example" / "module-package.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "\n".join(
            (
                "name: nold-ai/specfact-example",
                "tier: official",
                "publisher:",
                "  name: nold-ai",
                "bundle_group_command: example",
                "commands:",
                "  - example",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    registry = tmp_path / "registry" / "index.json"
    registry.parent.mkdir()
    registry.write_text(
        '{"modules": [{"id": "nold-ai/specfact-example", "tier": "official", "publisher": {"name": "nold-ai"}}]}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "MODULE_APP_MOUNTS", ())

    with pytest.raises(ValueError, match="missing command mounts"):
        generator.validate_official_mount_inventory()


def _write_official_example_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "packages" / "specfact-example" / "module-package.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "\n".join(
            (
                "name: nold-ai/specfact-example",
                "version: 1.2.3",
                "tier: official",
                "publisher:",
                "  name: nold-ai",
                "  email: example@noldai.com",
                "bundle_dependencies: []",
                "core_compatibility: '>=1.0.0,<2.0.0'",
                "description: Example module.",
                "bundle_group_command: example",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _write_official_example_registry(
    tmp_path: Path,
    *,
    latest_version: str = "1.2.3",
    download_url: str = "modules/specfact-example-1.2.3.tar.gz",
    description: str = "Example module.",
) -> None:
    registry = tmp_path / "registry" / "index.json"
    registry.parent.mkdir()
    registry.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "id": "nold-ai/specfact-example",
                        "latest_version": latest_version,
                        "download_url": download_url,
                        "tier": "official",
                        "publisher": {"name": "nold-ai", "email": "example@noldai.com"},
                        "bundle_dependencies": [],
                        "core_compatibility": ">=1.0.0,<2.0.0",
                        "description": description,
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_official_inventory_rejects_registry_description_divergence(tmp_path: Path, monkeypatch) -> None:
    generator = load_module_from_path("generate_command_overview_metadata_drift", GENERATOR)
    _write_official_example_manifest(tmp_path)
    _write_official_example_registry(tmp_path, description="Stale module description.")
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        generator,
        "MODULE_APP_MOUNTS",
        (("example.commands", "app", ("specfact", "example"), "nold-ai/specfact-example"),),
    )

    with pytest.raises(ValueError, match="description"):
        generator.validate_official_mount_inventory()


def _prepare_official_example_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module_name: str):
    generator = load_module_from_path(module_name, GENERATOR)
    _write_official_example_manifest(tmp_path)
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        generator,
        "MODULE_APP_MOUNTS",
        (("example.commands", "app", ("specfact", "example"), "nold-ai/specfact-example"),),
    )
    return generator, tmp_path / "packages" / "specfact-example" / "module-package.yaml"


@pytest.mark.parametrize(
    "release_case",
    (
        ("1.2.2", "1.2.3", "modules/specfact-example-1.2.3.tar.gz", "latest_version"),
        ("1.2.3", "1.2.3", "modules/specfact-example-1.2.4.tar.gz", "download_url"),
    ),
)
def test_official_inventory_rejects_published_release_conflicts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release_case: tuple[str, str, str, str],
) -> None:
    manifest_version, registry_version, download_url, error_field = release_case
    generator, manifest = _prepare_official_example_inventory(
        tmp_path, monkeypatch, "generate_command_overview_release_metadata"
    )
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("version: 1.2.3", f"version: {manifest_version}"), encoding="utf-8"
    )
    _write_official_example_registry(tmp_path, latest_version=registry_version, download_url=download_url)

    with pytest.raises(ValueError, match=error_field):
        generator.validate_official_mount_inventory()


@pytest.mark.parametrize(
    ("module_name", "manifest_version"),
    (
        ("generate_command_overview_approved_dev_release", "1.2.4"),
        ("generate_command_overview_registry_version_spelling", "1.2.3.0"),
    ),
)
def test_official_inventory_permits_pending_and_normalized_release_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module_name: str, manifest_version: str
) -> None:
    generator, manifest = _prepare_official_example_inventory(tmp_path, monkeypatch, module_name)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("version: 1.2.3", f"version: {manifest_version}"),
        encoding="utf-8",
    )
    _write_official_example_registry(tmp_path)

    generator.validate_official_mount_inventory()


def test_command_overview_rejects_duplicate_official_registry_entries(tmp_path: Path, monkeypatch) -> None:
    generator = load_module_from_path("generate_command_overview_duplicate_registry", GENERATOR)
    registry = tmp_path / "registry" / "index.json"
    registry.parent.mkdir()
    registry.write_text(
        """{
  "modules": [
    {"id": "nold-ai/specfact-example", "tier": "official", "publisher": {"name": "nold-ai"}},
    {"id": "nold-ai/specfact-example", "tier": "official", "publisher": {"name": "nold-ai"}}
  ]
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)

    with pytest.raises(ValueError, match="Duplicate official registry entry: nold-ai/specfact-example"):
        generator._official_registry_inventory()  # pylint: disable=protected-access
