"""
Spec-Kit backlog extension helpers.

This module detects existing issue references created by Spec-Kit backlog
extensions so SpecFact backlog export can avoid creating duplicates.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require
from pydantic import BaseModel


class SpecKitIssueMapping(BaseModel):
    """Structured issue reference discovered from Spec-Kit tasks."""

    tool: str
    issue_ref: str
    source: str = "speckit-extension"


class SpecKitBacklogSync:
    """Detect issue references from active Spec-Kit backlog extensions."""

    _PATTERNS: dict[str, re.Pattern[str]] = {
        "jira": re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b"),
        "ado": re.compile(r"\bAB#\d+\b"),
        "linear": re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b"),
        "github": re.compile(r"(?<![A-Za-z0-9])#\d+\b"),
    }
    _EXTENSION_TOOLS: dict[str, str] = {
        "jira": "jira",
        "azure-devops": "ado",
        "ado": "ado",
        "linear": "linear",
        "github": "github",
        "github-projects": "github",
        "trello": "trello",
    }

    @beartype
    @require(lambda feature_path: feature_path.exists(), "Feature path must exist")
    @require(lambda feature_path: feature_path.is_dir(), "Feature path must be a directory")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def detect_issue_mappings(self, feature_path: Path, capabilities: Any) -> list[SpecKitIssueMapping]:
        """
        Detect issue references for active backlog extensions from a feature tasks.md file.

        Args:
            feature_path: Spec-Kit feature directory containing tasks.md
            capabilities: ToolCapabilities-like object with optional extension metadata

        Returns:
            Structured issue mappings discovered in tasks.md
        """
        active_tools = self._active_backlog_tools(capabilities)
        if not active_tools:
            return []

        tasks_path = Path(feature_path) / "tasks.md"
        if not tasks_path.exists():
            return []

        content = tasks_path.read_text(encoding="utf-8")
        mappings: list[SpecKitIssueMapping] = []
        seen: set[tuple[str, str]] = set()
        for tool in active_tools:
            pattern = self._PATTERNS.get(tool)
            if pattern is None:
                continue
            for match in pattern.finditer(content):
                key = (tool, match.group(0))
                if key in seen:
                    continue
                seen.add(key)
                mappings.append(SpecKitIssueMapping(tool=tool, issue_ref=match.group(0)))
        return mappings

    @beartype
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _active_backlog_tools(self, capabilities: Any) -> list[str]:
        """Resolve active backlog-capable tools from extension metadata."""
        extension_names = list(getattr(capabilities, "extensions", None) or [])
        extension_commands = getattr(capabilities, "extension_commands", None) or {}
        for extension_name in extension_commands:
            if extension_name not in extension_names:
                extension_names.append(extension_name)

        active_tools: list[str] = []
        for extension_name in extension_names:
            tool = self._EXTENSION_TOOLS.get(str(extension_name).lower())
            if tool and tool not in active_tools:
                active_tools.append(tool)
        return active_tools
