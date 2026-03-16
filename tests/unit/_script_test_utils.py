from __future__ import annotations

import builtins
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def run_python_script(script_path: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def load_module_from_path(module_name: str, script_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def block_contract_imports(monkeypatch) -> None:
    original_import = builtins.__import__

    def raising_import(name, globalns=None, localns=None, fromlist=(), level=0):
        if name in {"beartype", "icontract"}:
            raise ImportError(f"blocked import for {name}")
        return original_import(name, globalns, localns, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", raising_import)
