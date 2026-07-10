"""Guard against stale generated command artifacts (llms.txt and command reference).

The pre-commit command-overview gate only fires when specific paths are staged, and the
PR orchestrator skips overview validation on dev-to-main promote runs, so a commit that
bypasses them (merge commits, --no-verify, registry bot commits with [skip ci]) can land
a stale llms.txt. A stale llms.txt misleads agents worse than a missing one, so this
test re-runs the generator in --check mode on every test run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

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
