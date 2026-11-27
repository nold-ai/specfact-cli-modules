"""Verify Spec-Kit plan, protocol, and validation workflow outputs."""

from __future__ import annotations

from pathlib import Path

from specfact_cli.models.plan import Feature, PlanBundle, Product
from specfact_cli.models.protocol import Protocol

from specfact_project.importers.speckit_converter import SpecKitConverter


class TestSpecKitConverter:
    """Test cases for SpecKitConverter - focused on edge cases and business logic."""

    def test_convert_protocol_with_features(self, tmp_path: Path) -> None:
        """Test converting features to protocol - integration test."""
        # Create modern Spec-Kit structure
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir(parents=True)

        specs_dir = tmp_path / "specs" / "001-test-feature"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text("# Feature Specification: Test Feature\n")

        converter = SpecKitConverter(tmp_path)
        protocol = converter.convert_protocol()

        # Contract ensures Protocol with states (covered by return type annotation)
        assert isinstance(protocol, Protocol)
        assert len(protocol.states) >= 2  # INIT + at least one feature + COMPLETE
        assert "INIT" in protocol.states
        assert "COMPLETE" in protocol.states

    def test_convert_protocol_empty_repo(self, tmp_path: Path) -> None:
        """Test converting empty repo to minimal protocol (edge case)."""
        # Only .specify directory, no features
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir(parents=True)

        converter = SpecKitConverter(tmp_path)
        protocol = converter.convert_protocol()

        assert isinstance(protocol, Protocol)
        assert len(protocol.states) == 2  # INIT and COMPLETE
        assert "INIT" in protocol.states
        assert "COMPLETE" in protocol.states

    def test_convert_plan_with_markdown_features(self, tmp_path: Path) -> None:
        """Test converting markdown features to plan - integration test."""
        # Create modern Spec-Kit structure
        specify_dir = tmp_path / ".specify" / "memory"
        specify_dir.mkdir(parents=True)

        specs_dir = tmp_path / "specs" / "001-test-feature"
        specs_dir.mkdir(parents=True)
        spec_content = """# Feature Specification: Test Feature

## User Scenarios & Testing

### User Story 1 - Test Story (Priority: P1)

As a user, I want to test features so that I can validate functionality.

## Requirements

- **FR-001**: System MUST test features correctly

## Success Criteria

- **SC-001**: All tests pass
"""
        (specs_dir / "spec.md").write_text(spec_content)

        converter = SpecKitConverter(tmp_path)
        plan_bundle = converter.convert_plan()

        # Contract ensures PlanBundle (covered by return type annotation)
        assert isinstance(plan_bundle, PlanBundle)
        assert plan_bundle.version == "1.1"
        assert len(plan_bundle.features) == 1
        assert plan_bundle.features[0].title == "Test Feature"

    def test_convert_plan_empty_repo(self, tmp_path: Path) -> None:
        """Test converting empty repo to plan with no features (edge case)."""
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir(parents=True)

        converter = SpecKitConverter(tmp_path)
        plan_bundle = converter.convert_plan()

        assert isinstance(plan_bundle, PlanBundle)
        assert len(plan_bundle.features) == 0

    def test_generate_github_action(self, tmp_path: Path) -> None:
        """Test generating GitHub Action workflow - file I/O test."""
        converter = SpecKitConverter(tmp_path)

        output_path = converter.generate_github_action(repo_name="test-repo")

        # Contract ensures Path returned (covered by return type annotation)
        assert output_path.exists()
        assert output_path.name == "specfact-gate.yml"

        # Verify workflow content (business logic)
        content = output_path.read_text()
        assert "SpecFact Validation" in content
        assert 'specfact project health-check --repo . --project-name "test-repo"' in content
        assert "semgrep" not in content.lower()
        assert not (tmp_path / ".semgrep").exists()

    def test_convert_to_speckit_sequential_numbering(self, tmp_path: Path) -> None:
        """Test convert_to_speckit uses sequential numbering when feature keys lack numbers."""
        features = [
            Feature(
                key="FEATURE-USER-AUTH",
                title="User Authentication",
                outcomes=["Users can authenticate"],
                acceptance=["Authentication works"],
            ),
            Feature(
                key="FEATURE-PAYMENT",
                title="Payment Processing",
                outcomes=["Users can process payments"],
                acceptance=["Payments work"],
            ),
            Feature(
                key="FEATURE-003",
                title="Third Feature",
                outcomes=["Third feature works"],
                acceptance=["Feature works"],
            ),
        ]

        plan_bundle = PlanBundle(
            version="1.0",
            product=Product(themes=["Core"], releases=[]),
            features=features,
            metadata=None,
            idea=None,
            business=None,
            clarifications=None,
        )

        converter = SpecKitConverter(tmp_path)
        features_converted = converter.convert_to_speckit(plan_bundle)

        assert features_converted == 3

        # Verify feature directories use correct sequential numbering (not "000-")
        specs_dir = tmp_path / "specs"
        feature_dirs = sorted(specs_dir.iterdir()) if specs_dir.exists() else []

        assert len(feature_dirs) == 3

        expected_names = ("001-user-authentication", "002-payment-processing", "003-third-feature")
        for feature_dir, expected_name in zip(feature_dirs, expected_names, strict=True):
            prefix, slug = expected_name.split("-", 1)
            assert feature_dir.name.startswith(f"{prefix}-")
            assert slug in feature_dir.name
            spec_content = (feature_dir / "spec.md").read_text()
            assert f"**Feature Branch**: `{prefix}-" in spec_content
            assert "000-" not in spec_content


def test_conversion_accepts_custom_output_paths_and_retains_existing_protocol(tmp_path: Path) -> None:
    (tmp_path / ".specify").mkdir()
    output = tmp_path / "exports"
    output.mkdir()
    converter = SpecKitConverter(tmp_path)
    protocol = output / "workflow.protocol.yaml"

    converter.convert_protocol(protocol)
    original = protocol.read_bytes()
    converter.convert_protocol(protocol)
    assert protocol.read_bytes() == original

    converter.convert_plan(output / "migration.yaml")
    assert (output / "migration.yaml").is_file()

    workflow = converter.generate_github_action(output / "custom.yml", budget=15, python_version="3.11")
    config = workflow.read_text(encoding="utf-8")
    assert workflow.name == "custom.yml"
    assert "timeout-minutes: 15" in config
    assert 'python-version: "3.11"' in config
    assert f'--project-name "{tmp_path.name}"' in config
