"""Standard-library-only build driver, executed inside a disposable namespace."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
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


def select_hatch_environment(export: dict, requested: str, python: str) -> str:
    """Select a concrete native export entry without expanding resolver semantics."""
    if requested in export:
        return requested
    candidates = sorted(
        name for name, config in export.items() if name.startswith(requested + ".") and config.get("python") == python
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"project_environment_ambiguous:{requested}:{','.join(candidates)}; select a concrete Hatch environment"
        )
    return candidates[0]


def _prepare_hatch(config: dict, tools_python: str, env: dict[str, str]) -> None:
    env["HATCH_UV"] = str(Path(tools_python).with_name("uv"))
    export = json.loads(_run([tools_python, "-m", "hatch", "env", "show", "--json"], env=env))
    selected = select_hatch_environment(
        export, str(config["environment"]), f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    config["environment"] = selected
    config["commands"] = [[tools_python, "-m", "hatch", "env", "create", selected]]


def _environment_path(config: dict[str, object], tools_python: str, env: dict[str, str]) -> Path:
    if config["manager"] != "hatch":
        return ROOT / "env"
    result = _run([tools_python, "-m", "hatch", "env", "find", str(config["environment"])], env=env)
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


def copy_executables(environment: Path, artifact: Path, records: list[dict]) -> list[dict]:
    """Copy only distribution-owned environment commands, never arbitrary host bins."""
    directory = artifact / "bin"
    directory.mkdir(exist_ok=True)
    copied = []
    for record in records:
        source = Path(record["path"])
        if source.name.startswith("python") or not source.is_file():
            continue
        if source.parent != environment / "bin" or not source.resolve().is_relative_to(environment):
            raise RuntimeError(f"project_executable_escape:{source.name}")
        destination = directory / source.name
        if destination.exists():
            raise RuntimeError(f"project_executable_collision:{source.name}")
        content = source.read_bytes()
        if content.startswith(b"\x7fELF"):
            (artifact / "executables").mkdir(exist_ok=True)
            binary = artifact / "executables" / source.name
            binary.write_bytes(content)
            binary.chmod(0o755)
            root = "/opt/specfact/project-runtime"
            destination.write_text(
                "#!/opt/specfact/python/bin/python\nimport os,sys\n"
                + f"root={root!r}\nbinary=root+'/executables/'+{source.name!r}\n"
                + "loader=root+'/native/ld-linux-x86-64.so.2'\n"
                + "argv=[loader,'--library-path',root+'/native',binary,*sys.argv[1:]] if os.pat"
                "h.isfile(loader) else [binary,*sys.argv[1:]]\n" + "os.execv(argv[0],argv)\n",
                encoding="utf-8",
            )
        elif content.startswith(b"#!") and b"python" in content.split(b"\n", 1)[0]:
            destination.write_bytes(b"#!/opt/specfact/project-runtime/bin/python\n" + content.split(b"\n", 1)[1])
        else:
            raise RuntimeError(
                f"project_executable_unsupported:{source.name}; declare its interpreter/runtime requirements"
            )
        destination.chmod(0o755)
        copied.append({"name": source.name, "distribution": record["distribution"]})
    return copied


def _executable_records(python: str) -> list[dict]:
    script = (
        "import importlib.metadata,json,sys; from pathlib import Path; "
        "directory=Path(sys.executable).parent; "
        "print(json.dumps([{'path':str(path),'distribution':dist.metadata['Name']} "
        "for dist in importlib.metadata.distributions() for file in (dist.files or []) "
        "if (path:=Path(dist.locate_file(file)).absolute()).resolve().parent==directory.resolve()]))"
    )
    records = json.loads(_run([python, "-c", script]))
    for record in records:
        record["path"] = str(Path(record["path"]).resolve())
    return records


def installer_environment(manager: str, inherited: dict[str, str]) -> dict[str, str]:
    """Keep one manager's environment controls out of another manager's installer."""
    env = {
        key: value
        for key, value in inherited.items()
        if key not in {"VIRTUAL_ENV", "PIP_PYTHON", "UV_PROJECT_ENVIRONMENT", "POETRY_VIRTUALENVS_CREATE"}
    }
    env.update(
        HATCH_DATA_DIR=str(ROOT / "hatch-data"),
        HATCH_CACHE_DIR=str(ROOT / "hatch-cache"),
        PATH=str(ROOT / "tools/bin") + ":" + env.get("PATH", ""),
    )
    controls = {
        "pip": {"PIP_PYTHON": str(ROOT / "env/bin/python")},
        "uv": {"VIRTUAL_ENV": str(ROOT / "env"), "UV_PROJECT_ENVIRONMENT": str(ROOT / "env")},
        "poetry": {"VIRTUAL_ENV": str(ROOT / "env"), "POETRY_VIRTUALENVS_CREATE": "false"},
        "hatch": {},
    }
    env.update(controls[manager])
    return env


def main() -> None:
    config = json.loads((ROOT / "build.json").read_text(encoding="utf-8"))
    interpreter = str(config["interpreter"])
    _run([interpreter, "-m", "venv", str(ROOT / "tools")])
    tools_python = str(ROOT / "tools/bin/python")
    _run([tools_python, "-m", "pip", "install", "--disable-pip-version-check", *config["manager_requirements"]])
    _run([interpreter, "-m", "venv", str(ROOT / "env")])
    env = installer_environment(config["manager"], dict(os.environ))
    if config["manager"] == "hatch":
        _prepare_hatch(config, tools_python, env)
    for command in config["commands"]:
        _run(command, env=env)
    environment = _environment_path(config, tools_python, env)
    python = str(environment / "bin/python")
    inventory = _run([tools_python, "-m", "pip", "--python", python, "inspect", "--local"])
    artifact = ROOT / "artifact"
    artifact.mkdir()
    (artifact / "worker-config").mkdir()
    (artifact / "worker-config/hosts").write_text("127.0.0.1 localhost\n::1 localhost\n", encoding="ascii")
    _copy_site_packages(python, artifact / "site-packages")
    facts = clean_inventory(json.loads(inventory))
    facts["resolved_environment"] = config["environment"]
    facts["executables"] = copy_executables(environment, artifact, _executable_records(python))
    (artifact / "inventory.json").write_text(json.dumps(facts) + "\n", encoding="utf-8")
    (artifact / "bin").mkdir(exist_ok=True)
    launcher = artifact / "bin/python"
    launcher.write_text(
        "#!/opt/specfact/python/bin/python\nimport runpy\nrunpy.run_path('/opt/specfact"
        "/builtin/specfact_code_review/run/target_launch.py', run_name='__main__')\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    for name in ("uv.lock", "poetry.lock", "pylock.toml"):
        path = ROOT / "project" / name
        if path.is_file():
            (artifact / name).write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
