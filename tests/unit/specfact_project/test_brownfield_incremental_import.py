"""Exercise the public import route across fresh and incremental runs."""

from __future__ import annotations

from pathlib import Path

import pytest
from specfact_cli.models.plan import Feature
from specfact_cli.models.source_tracking import SourceTracking
from specfact_cli.utils.bundle_loader import load_project_bundle, save_project_bundle
from specfact_cli.utils.structure import SpecFactStructure
from typer.testing import CliRunner, Result

from specfact_codebase.code.commands import app
from specfact_project import import_runtime_patches
from specfact_project.import_cmd import commands
from specfact_project.utils import incremental_check


@pytest.fixture(name="widget_repo")
def make_widget_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("widget-repo")
    (repo / "src").mkdir()
    (repo / "src" / "widget.py").write_text(
        """class WidgetService:
    \"\"\"Manage widget records.\"\"\"

    def create_widget(self, name: str) -> str:
        \"\"\"Create one widget.\"\"\"
        return name
""",
        encoding="utf-8",
    )
    return repo


def invoke_import(repo: Path, *args: str) -> Result:
    return CliRunner().invoke(
        app, ["import", "from-code", "--repo", str(repo), "--confidence", "0", "--no-enrich-for-speckit", *args]
    )


def require_checkpoint_repair(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        incremental_check,
        "check_incremental_changes",
        lambda *_args, **_kwargs: {
            "relationships": True,
            "graph": False,
            "contracts": False,
            "enrichment_context": True,
            "bundle": False,
        },
    )


def test_import_resumes_a_bundle_checkpoint(widget_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    initial = invoke_import(widget_repo, "--force", "--shadow-only", "widget-suite")
    assert initial.exit_code == 0, initial.output
    assert "Force mode enabled" in initial.output
    assert "Shadow mode" in initial.output
    bundle = SpecFactStructure.project_dir(base_path=widget_repo, bundle_name="widget-suite")
    feature = bundle / "features" / "FEATURE-WIDGETSERVICE.yaml"
    assert feature.is_file()
    SpecFactStructure.set_active_plan("widget-suite", base_path=widget_repo)
    context = bundle / "enrichment_context.md"
    context.unlink()
    require_checkpoint_repair(monkeypatch)

    resumed = invoke_import(widget_repo)

    assert resumed.exit_code == 0, resumed.output
    assert "Using active plan: widget-suite" in resumed.output
    assert "Features exist from checkpoint" in resumed.output
    assert "Skipping codebase analysis" in resumed.output
    assert feature.is_file() and context.is_file()


def test_import_reanalyzes_a_changed_source_file(widget_repo: Path) -> None:
    initial = invoke_import(widget_repo, "widget-suite")
    assert initial.exit_code == 0, initial.output
    source = widget_repo / "src" / "widget.py"
    with source.open("a", encoding="utf-8") as content:
        content.write('\n    def remove_widget(self) -> None:\n        """Remove the widget."""\n')

    updated = invoke_import(widget_repo, "widget-suite")

    assert updated.exit_code == 0, updated.output
    assert "Source files changed" in updated.output
    bundle = SpecFactStructure.project_dir(base_path=widget_repo, bundle_name="widget-suite")
    assert "remove_widget" in (bundle / "features" / "FEATURE-WIDGETSERVICE.yaml").read_text(encoding="utf-8")


def test_import_with_no_active_bundle_explains_how_to_proceed(widget_repo: Path) -> None:
    result = invoke_import(widget_repo)

    assert result.exit_code == 1, result.output
    assert "Bundle name required" in result.output


def test_failed_import_reports_the_read_error(widget_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_to_analyze(*_args: object, **_kwargs: object) -> None:
        raise OSError("Source fixture could not be read")

    import_runtime_patches.apply_import_runtime_patches(commands_module=commands)
    monkeypatch.setattr(commands, "_analyze_codebase", fail_to_analyze)
    result = invoke_import(widget_repo, "unreadable")

    assert result.exit_code == 1, result.output
    assert "Import failed" in result.output
    assert "Source fixture could not be read" in result.output
    assert not (widget_repo / ".specfact" / "projects" / "unreadable" / "bundle.manifest.yaml").exists()


def test_unchanged_import_uses_the_saved_bundle(widget_repo: Path) -> None:
    initial = invoke_import(widget_repo, "widget-suite")
    assert initial.exit_code == 0, initial.output
    manifest = widget_repo / ".specfact" / "projects" / "widget-suite" / "bundle.manifest.yaml"
    original = manifest.read_bytes()

    repeated = invoke_import(widget_repo, "widget-suite")

    assert repeated.exit_code == 0, repeated.output
    assert "No changes detected" in repeated.output
    assert manifest.read_bytes() == original


def test_checkpoint_report_lists_missing_sources(widget_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    initial = invoke_import(widget_repo, "widget-suite")
    assert initial.exit_code == 0, initial.output
    bundle_dir = SpecFactStructure.project_dir(base_path=widget_repo, bundle_name="widget-suite")
    bundle = load_project_bundle(bundle_dir, validate_hashes=False)
    original = bundle.features["FEATURE-WIDGETSERVICE"].source_tracking
    assert original is not None
    add_missing_features(bundle.features, original)
    save_project_bundle(bundle, bundle_dir, atomic=True)
    require_checkpoint_repair(monkeypatch)

    checked = invoke_import(widget_repo, "widget-suite")

    assert checked.exit_code == 0, checked.output
    assert "6 orphaned, 6 with missing files" in checked.output
    assert "Features with missing files" in checked.output
    assert "--revalidate-features" in checked.output


def add_missing_features(features: dict[str, Feature], original: SourceTracking) -> None:
    for index in range(6):
        orphan = Feature(
            key=f"FEATURE-ORPHAN{index}",
            title="All sources removed",
            source_tracking=SourceTracking(implementation_files=["src/gone.py"]),
        )
        partial = Feature(
            key=f"FEATURE-PARTIAL{index}",
            title="One source removed",
            source_tracking=original.model_copy(update={"implementation_files": ["src/widget.py", "src/gone.py"]}),
        )
        features.update({orphan.key: orphan, partial.key: partial})
