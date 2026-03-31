from __future__ import annotations

import subprocess
from pathlib import Path
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


def create_noisy_file(tmp_path: Path, *, name: str = "target.py", body_lines: int = 81) -> Path:
    file_path = tmp_path / name
    body = "\n".join(f"                    total += {index}" for index in range(body_lines))
    file_path.write_text(
        (
            "def noisy(a, b, c, d, e, f):\n"
            "    total = 0\n"
            "    if a:\n"
            "        if b:\n"
            "            if c:\n"
            "                if d:\n"
            f"{body}\n"
            "    return total\n"
        ),
        encoding="utf-8",
    )
    return file_path
