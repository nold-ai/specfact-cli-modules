"""Check how incremental imports classify persisted features with missing source."""

from __future__ import annotations

from pathlib import Path

from specfact_cli.models.plan import Feature, PlanBundle, Product
from specfact_cli.models.source_tracking import SourceTracking

from specfact_project.import_cmd.commands import _validate_existing_features


def test_existing_features_distinguish_orphans_from_recoverable_changes(tmp_path: Path) -> None:
    for name in ("service.py", "test_service.py"):
        (tmp_path / name).touch()
    features = [
        Feature(
            key="FEATURE-VALID",
            title="Existing files without generated stories",
            source_tracking=SourceTracking(implementation_files=["service.py"], test_files=["test_service.py"]),
        ),
        Feature(
            key="FEATURE-ORPHAN",
            title="All files removed",
            source_tracking=SourceTracking(implementation_files=["missing.py"], test_files=["test_missing.py"]),
        ),
        Feature(
            key="FEATURE-PARTIAL",
            title="Only the test remains",
            source_tracking=SourceTracking(implementation_files=["missing.py"], test_files=["test_service.py"]),
        ),
        Feature(key="FEATURE-UNTRACKED", title="No source tracking"),
    ]
    bundle = PlanBundle(
        idea=None, business=None, product=Product(themes=[]), features=features, metadata=None, clarifications=None
    )

    results = _validate_existing_features(bundle, tmp_path)

    assert results == {
        "valid_features": ["FEATURE-VALID"],
        "orphaned_features": ["FEATURE-ORPHAN"],
        "invalid_features": ["FEATURE-PARTIAL", "FEATURE-UNTRACKED"],
        "missing_files": {
            "FEATURE-ORPHAN": ["missing.py", "test_missing.py"],
            "FEATURE-PARTIAL": ["missing.py"],
        },
        "total_checked": 4,
    }
