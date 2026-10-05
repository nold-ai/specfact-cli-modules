"""Fixed sealed uv acquisition worker; project hooks run as broker-owned children."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import require

from specfact_code_review.run.runtime_models import ProjectRuntimeError


VERSION = "0.12.13"
SCHEMA = "native-uv-request-v1"
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


@beartype
@require(lambda project: project.is_dir())
def read_request(project: Path) -> dict[str, Any]:
    path = project / ".specfact-uv.json"
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 1 << 20:
        raise ProjectRuntimeError("project_native_uv_request_invalid")
    value = json.loads(path.read_text())
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "environment", "groups", "extras", "locked"}
        or value["schema"] != SCHEMA
        or value["environment"] != "default"
        or type(value["locked"]) is not bool
        or any(
            not isinstance(value[key], list)
            or len(value[key]) > 128
            or any(not isinstance(item, str) or not _NAME.fullmatch(item) for item in value[key])
            for key in ("groups", "extras")
        )
    ):
        raise ProjectRuntimeError("project_native_uv_request_invalid:select supported groups and extras")
    return value


def sync_command(capsule: Path, source: Path, cache: Path, request: dict[str, Any]) -> list[str]:
    command = [
        str(capsule / "tools/uv"),
        "sync",
        "--project",
        str(source),
        "--cache-dir",
        str(cache),
        "--python",
        str(capsule / "python/bin/python3"),
        "--no-python-downloads",
        "--no-managed-python",
        "--no-editable",
        "--keyring-provider",
        "disabled",
    ]
    if request["locked"]:
        command.append("--locked")
    if request["groups"]:
        command.append("--no-default-groups")
    for option, key in (("--group", "groups"), ("--extra", "extras")):
        for value in request[key]:
            command.extend((option, value))
    return command


def main() -> int:
    if len(sys.argv) != 5:
        return 76
    capsule, project, output, temporary = (Path(value) for value in sys.argv[1:])
    try:
        request = read_request(project)
        source = temporary / "source"
        shutil.copytree(project, source, ignore=shutil.ignore_patterns(".specfact-uv.json"))
        for directory, _children, files in os.walk(source):
            Path(directory).chmod(0o700)
            for name in files:
                path = Path(directory) / name
                path.chmod(0o700 if path.stat().st_mode & 0o111 else 0o600)
        tool = capsule / "tools/uv"
        if tool.is_symlink() or not tool.is_file() or tool.stat().st_mode & 0o222:
            raise ProjectRuntimeError("project_native_uv_image_not_admitted")
        environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONUTF8": "1",
            "HOME": str(temporary),
            "TMPDIR": str(temporary),
            "XDG_CACHE_HOME": str(temporary),
            "UV_NO_PROGRESS": "1",
            "UV_LINK_MODE": "copy",
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_PROJECT_ENVIRONMENT": str(output / "environment"),
            "SPECFACT_MANAGED_UV": "1",
            "SPECFACT_MANAGED_CAPSULE": str(capsule),
            "SPECFACT_MANAGED_PROJECT": str(project),
            "SPECFACT_MANAGED_OUTPUT": str(output),
            "SPECFACT_MANAGED_TEMPORARY": str(temporary),
        }
        os.chdir(source)
        os.execve(tool, sync_command(capsule, source, temporary / "uv-cache", request), environment)
        return 76
    except (OSError, ValueError, TypeError) as exc:
        (output / "preparation-error.json").write_text(json.dumps({"diagnostic": str(exc)}) + "\n")
        return 74


if __name__ == "__main__":
    raise SystemExit(main())
