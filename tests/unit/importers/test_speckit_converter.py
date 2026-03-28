"""Tests for Spec-Kit <-> OpenSpec conversion helpers."""

from __future__ import annotations

from pathlib import Path

from specfact_project.importers.speckit_converter import SpecKitConverter


def _write_sample_speckit_feature(feature_dir: Path, include_plan: bool = True) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        """---
**Feature Branch**: `001-auth-sync`
**Created**: 2026-03-28
**Status**: Draft
---

# Feature Specification: Authentication Sync

## User Scenarios & Testing

### User Story 1 - Sign in (Priority: P1)
Users can sign in securely

**Why this priority**: Login is required before any sync work can happen.

**Independent**: YES
**Negotiable**: YES
**Valuable**: YES
**Estimable**: YES
**Small**: YES
**Testable**: YES

**Acceptance Criteria:**

1. **Given** valid credentials, **When** the user authenticates, **Then** the session is created

**Scenarios:**

- **Primary Scenario**: valid credentials authenticate successfully

## Functional Requirements

**FR-001**: System MUST sync authenticated sessions to the target system

## Success Criteria

**SC-001**: Users complete login without duplicate prompts

### Edge Cases

- expired tokens are rejected cleanly
""",
        encoding="utf-8",
    )
    if include_plan:
        (feature_dir / "plan.md").write_text(
            """# Implementation Plan: Authentication Sync

## Summary
Ship authentication sync with minimal moving parts.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies:**
- `typer` - CLI framework

**Technology Stack:**
- Python 3.11
- Typer CLI

**Constraints:**
- Must preserve existing login flows

**Unknowns:**
- SSO rollout timing is undecided

## Phase 0: Research
Confirm SSO fallback policy.

## Phase 1: Design
Define the sync trigger and API boundaries.
""",
            encoding="utf-8",
        )
    (feature_dir / "tasks.md").write_text(
        """# Tasks

## Phase 1: Setup

- [ ] [T001] [P] [US1] Prepare the auth sync CLI flow

## Phase 2: Implementation

- [x] [T002] [US1] Persist session tokens after login
""",
        encoding="utf-8",
    )


def test_convert_to_change_proposal_creates_expected_artifacts(tmp_path: Path) -> None:
    """Spec-Kit features convert into a complete OpenSpec change directory."""
    repo_path = tmp_path
    feature_dir = repo_path / "specs" / "001-auth-sync"
    _write_sample_speckit_feature(feature_dir)

    converter = SpecKitConverter(repo_path)
    change_dir = converter.convert_to_change_proposal(
        feature_path=feature_dir,
        change_name="auth-sync",
        output_dir=repo_path / "openspec" / "changes",
    )

    proposal = (change_dir / "proposal.md").read_text(encoding="utf-8")
    design = (change_dir / "design.md").read_text(encoding="utf-8")
    spec_files = list((change_dir / "specs").glob("*/spec.md"))
    tasks = (change_dir / "tasks.md").read_text(encoding="utf-8")

    assert change_dir.exists()
    assert "## Why" in proposal
    assert "sync authenticated sessions to the target system" in proposal
    assert "<!-- speckit_feature: 001-auth-sync -->" in proposal
    assert "## Context" in design
    assert "Python 3.11" in design
    assert len(spec_files) == 1
    assert "#### Scenario: Sign in" in spec_files[0].read_text(encoding="utf-8")
    assert "- [ ] 1.1 Prepare the auth sync CLI flow" in tasks


def test_convert_to_change_proposal_handles_missing_plan(tmp_path: Path) -> None:
    """Missing plan.md still yields a minimal OpenSpec design document."""
    repo_path = tmp_path
    feature_dir = repo_path / "specs" / "001-auth-sync"
    _write_sample_speckit_feature(feature_dir, include_plan=False)

    converter = SpecKitConverter(repo_path)
    change_dir = converter.convert_to_change_proposal(
        feature_path=feature_dir,
        change_name="auth-sync",
        output_dir=repo_path / "openspec" / "changes",
    )

    design = (change_dir / "design.md").read_text(encoding="utf-8")

    assert "Spec-Kit `plan.md` was not present during conversion." in design
    assert "Missing `plan.md` limited the technical context" in design


def test_convert_to_speckit_feature_roundtrip_preserves_core_content(tmp_path: Path) -> None:
    """Roundtrip conversion keeps story and task text available in exported Spec-Kit files."""
    repo_path = tmp_path
    feature_dir = repo_path / "specs" / "001-auth-sync"
    _write_sample_speckit_feature(feature_dir)
    converter = SpecKitConverter(repo_path)
    change_dir = converter.convert_to_change_proposal(
        feature_path=feature_dir,
        change_name="auth-sync",
        output_dir=repo_path / "openspec" / "changes",
    )

    exported_feature = converter.convert_to_speckit_feature(
        change_dir=change_dir,
        output_dir=repo_path / "exported-specs",
    )

    exported_spec = (exported_feature / "spec.md").read_text(encoding="utf-8")
    exported_tasks = (exported_feature / "tasks.md").read_text(encoding="utf-8")

    assert "Authentication Sync" in exported_spec
    assert "Sign in" in exported_spec
    assert "Prepare the auth sync CLI flow" in exported_tasks
    assert "Persist session tokens after login" in exported_tasks
