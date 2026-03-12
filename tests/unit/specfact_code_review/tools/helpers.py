from __future__ import annotations

import subprocess
from unittest.mock import Mock


def completed_process(
    tool: str, *, stdout: str, stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[tool], returncode=returncode, stdout=stdout, stderr=stderr)


def assert_tool_run(run_mock: Mock, expected_command: list[str]) -> None:
    run_mock.assert_called_once_with(
        expected_command,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
