"""Standard-library-only build driver, executed inside a disposable namespace."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


ROOT = Path("/opt/specfact/output")


def clean_inventory(raw: dict) -> dict:
    """Retain dependency graph facts, stripping URI credentials and arbitrary metadata."""

    def redact(value: Any) -> Any:
        if isinstance(value, str):

            def safe_url(match):
                parsed = urlsplit(match.group(0))
                host = parsed.hostname or ""
                if parsed.port:
                    host += f":{parsed.port}"
                return urlunsplit((parsed.scheme, host, parsed.path, "", ""))

            return re.sub(r"(?:https?|git\+https)://[^\s]+", safe_url, value)
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        return value

    installed = []
    for distribution in raw.get("installed", []):
        metadata = distribution.get("metadata", {})
        installed.append(
            {
                "metadata": {
                    key: metadata[key]
                    for key in ("name", "version", "requires_python", "requires_dist")
                    if key in metadata
                },
                "requested": distribution.get("requested", False),
                "direct_url": distribution.get("direct_url", {}),
            }
        )
    return redact(
        {
            "version": raw.get("version"),
            "pip_version": raw.get("pip_version"),
            "environment": raw.get("environment", {}),
            "installed": installed,
        }
    )


def _run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command, cwd=ROOT / "project", env=env, text=True, capture_output=True, check=False, timeout=3600
    )
    with (ROOT / "build.log").open("a", encoding="utf-8") as stream:
        stream.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"project_manager_failed:{command[2:4]}:exit={result.returncode}")
    return result.stdout.strip()


def _environment_path(config: dict[str, object], tools_python: str, env: dict[str, str]) -> Path:
    if config["manager"] != "hatch":
        return ROOT / "env"
    result = _run([tools_python, "-m", "hatch", "-e", str(config["environment"]), "env", "find"], env=env)
    path = Path(result.splitlines()[-1])
    if not path.resolve().is_relative_to(ROOT):
        raise RuntimeError("project_environment_escape")
    return path


def _copy_site_packages(python: str, destination: Path) -> None:
    paths = json.loads(_run([python, "-c", "import json,site; print(json.dumps(site.getsitepackages()))"]))
    destination.mkdir()
    for raw in paths:
        path = Path(raw)
        if not path.is_dir():
            continue
        if not path.resolve().is_relative_to(ROOT):
            raise RuntimeError("project_site_packages_escape")
        shutil.copytree(
            path, destination, dirs_exist_ok=True, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    # Editable paths refer to the disposable copy. Rebind only that exact source
    # prefix; the changed bytes are subsequently included in the artifact identity.
    for path in destination.rglob("*"):
        if path.is_file() and (path.suffix == ".pth" or path.name.startswith("__editable__")):
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace(str(ROOT / "project"), "/opt/specfact/snapshot"), encoding="utf-8")


def main() -> None:
    config = json.loads((ROOT / "build.json").read_text(encoding="utf-8"))
    interpreter = str(config["interpreter"])
    _run([interpreter, "-m", "venv", str(ROOT / "tools")])
    tools_python = str(ROOT / "tools/bin/python")
    _run([tools_python, "-m", "pip", "install", "--disable-pip-version-check", *config["manager_requirements"]])
    _run([interpreter, "-m", "venv", str(ROOT / "env")])
    env = dict(os.environ)
    env.update(
        VIRTUAL_ENV=str(ROOT / "env"),
        PIP_PYTHON=str(ROOT / "env/bin/python"),
        UV_PROJECT_ENVIRONMENT=str(ROOT / "env"),
        HATCH_DATA_DIR=str(ROOT / "hatch-data"),
        HATCH_CACHE_DIR=str(ROOT / "hatch-cache"),
        POETRY_VIRTUALENVS_CREATE="false",
        PATH=str(ROOT / "tools/bin") + ":" + env.get("PATH", ""),
    )
    for command in config["commands"]:
        _run(command, env=env)
    environment = _environment_path(config, tools_python, env)
    python = str(environment / "bin/python")
    inventory = _run([tools_python, "-m", "pip", "--python", python, "inspect", "--local"])
    artifact = ROOT / "artifact"
    artifact.mkdir()
    _copy_site_packages(python, artifact / "site-packages")
    (artifact / "inventory.json").write_text(
        json.dumps(clean_inventory(json.loads(inventory))) + "\n", encoding="utf-8"
    )
    (artifact / "bin").mkdir()
    launcher = artifact / "bin/python"
    launcher.write_text(
        "#!/opt/specfact/python/bin/python\nimport runpy\nrunpy.run_path('/opt/specfact/builtin/specfact_code_review/run/target_launch.py', run_name='__main__')\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    for name in ("uv.lock", "poetry.lock", "pylock.toml"):
        path = ROOT / "project" / name
        if path.is_file():
            (artifact / name).write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
