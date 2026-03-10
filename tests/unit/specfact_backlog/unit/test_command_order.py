"""Unit tests for backlog-core command ordering in help output."""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

import re

from typer.testing import CliRunner

from specfact_backlog.backlog_core.main import backlog_app


runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


def _find_line(lines: list[str], needle: str) -> int:
    """Find line containing command name in help output."""
    # Strip ANSI codes and normalize for comparison
    for idx, line in enumerate(lines):
        clean_line = _strip_ansi(line)
        # Look for command name at start of line (after box drawing chars)
        if re.search(rf"[│├└]\s+{re.escape(needle)}\b", clean_line):
            return idx
    return -1


def test_backlog_core_help_lists_command_groups_before_leaf_commands() -> None:
    """`backlog --help` lists grouped commands before leaf commands for discoverability."""
    result = runner.invoke(backlog_app, ["--help"])
    assert result.exit_code == 0

    # Strip ANSI codes from output for consistent parsing
    output = _strip_ansi(result.stdout)
    lines = output.splitlines()

    delta_idx = _find_line(lines, "delta")
    sync_idx = _find_line(lines, "sync")
    verify_idx = _find_line(lines, "verify-readiness")

    assert delta_idx != -1, "'delta' command not found in help output"
    assert sync_idx != -1, "'sync' command not found in help output"
    assert verify_idx != -1, "'verify-readiness' command not found in help output"
    assert delta_idx < sync_idx, "'delta' should appear before 'sync'"
    assert delta_idx < verify_idx, "'delta' should appear before 'verify-readiness'"
