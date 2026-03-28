"""Helpers for importing Spec-Kit backlog references into bridge sync."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure

from specfact_project.sync_runtime.bridge_probe import BridgeProbe
from specfact_project.sync_runtime.speckit_backlog_sync import SpecKitBacklogSync


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def detect_speckit_backlog_mappings(repo_path: Path, proposal_name: str, adapter_type: str) -> list[dict[str, Any]]:
    """Import backlog references from a matching Spec-Kit feature when available."""
    capabilities = BridgeProbe(repo_path).detect()
    if capabilities.tool != "speckit":
        return []

    feature_path = find_speckit_feature_path(repo_path, proposal_name)
    if feature_path is None:
        return []

    detector = SpecKitBacklogSync()
    mappings = detector.detect_issue_mappings(feature_path, capabilities)
    repo_identifier = infer_backlog_repo_identifier(repo_path, adapter_type)
    return [
        _to_backlog_entry(mapping, feature_path.name, repo_identifier)
        for mapping in mappings
        if mapping.tool == adapter_type
    ]


@beartype
@ensure(lambda result: result is None or isinstance(result, Path), "Must return None or Path")
def find_speckit_feature_path(repo_path: Path, proposal_name: str) -> Path | None:
    """Resolve a likely Spec-Kit feature directory from a change proposal name."""
    specs_root = repo_path / "specs"
    if not specs_root.exists():
        return None

    normalized_change = proposal_name.replace("_", "-").lower()
    for feature_dir in sorted(path for path in specs_root.iterdir() if path.is_dir()):
        feature_name = feature_dir.name.lower()
        if feature_name == normalized_change or _strip_numeric_prefix(feature_name) == normalized_change:
            return feature_dir
    return None


@beartype
@ensure(lambda result: result is None or isinstance(result, str), "Must return None or str")
def infer_backlog_repo_identifier(repo_path: Path, adapter_type: str) -> str | None:
    """Infer the current repo identifier for GitHub and ADO backlog dedupe."""
    if adapter_type not in {"github", "ado"}:
        return None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    remote_url = result.stdout.strip()
    if adapter_type == "github":
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote_url)
        return match.group(1) if match else None
    https_match = re.search(r"dev\.azure\.com/([^/]+)/([^/]+)(?:/|$)", remote_url)
    if https_match:
        return f"{https_match.group(1)}/{https_match.group(2)}"
    ssh_match = re.search(r"ssh\.dev\.azure\.com:v3/([^/]+)/([^/]+)(?:/|$)", remote_url)
    if ssh_match:
        return f"{ssh_match.group(1)}/{ssh_match.group(2)}"
    return None


@beartype
@ensure(lambda result: isinstance(result, dict), "Must return dict")
def _to_backlog_entry(mapping: Any, feature_name: str, repo_identifier: str | None) -> dict[str, Any]:
    """Convert a detected Spec-Kit mapping into bridge source-tracking format."""
    return {
        "source_type": mapping.tool,
        "source_id": mapping.issue_ref.lstrip("#"),
        "source_ref": mapping.issue_ref,
        "source_repo": repo_identifier,
        "source_metadata": {
            "imported_from": mapping.source,
            "speckit_feature": feature_name,
        },
    }


@beartype
@ensure(lambda result: isinstance(result, str), "Must return string")
def _strip_numeric_prefix(feature_name: str) -> str:
    """Remove a leading numeric prefix from a Spec-Kit feature directory name."""
    return re.sub(r"^\d+-", "", feature_name)
