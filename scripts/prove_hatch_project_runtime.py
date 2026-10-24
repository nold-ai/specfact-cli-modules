"""Repeatable first-slice native Hatch proof. Receipt and projects stay external."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from specfact_codebase.project_runtime import (
    PreparedProject,
    ProjectCommand,
    ProjectSelection,
    inspect_project,
    prepare_project,
)


ROOT = Path(__file__).resolve().parents[1]
COMPANION = ROOT / "tests/fixtures/portable-runtime/hatch-bootstrap-companion"
ORIGINAL = ROOT / "tests/fixtures/portable-runtime/hatch-detached"
INVENTORY = """import importlib.metadata as m,json
print(json.dumps(sorted((d.metadata['Name'],d.version,d.read_text('direct_url.json')) for d in m.distributions())))
"""


def fixture_files(root: Path):
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not {".ruff_cache", ".pytest_cache", "__pycache__"}.intersection(path.relative_to(root).parts)
    )


def files_identity(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture_files(root)}


def declarations(root: Path) -> dict[str, str]:
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("pyproject.toml", "hatch.toml", ".python-version")
    }


def materialize(root: Path) -> None:
    for source in fixture_files(COMPANION):
        relative = source.relative_to(COMPANION)
        target = root / relative.with_suffix("") if source.suffix == ".in" else root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


def inventory(python: Path, root: Path) -> list:
    process = subprocess.run(
        [str(python), "-I", "-c", INVENTORY], cwd=root, capture_output=True, text=True, check=True, timeout=30
    )
    return json.loads(process.stdout)


def prove(workspace: Path, *, hatch: Path, python: Path) -> dict:
    if not __debug__:
        raise RuntimeError("Native proof refuses optimized Python; assertions must remain enabled")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Proof requires controller Python 3.12")
    workspace = workspace.resolve()
    if workspace.exists() or workspace.is_relative_to(ROOT):
        raise ValueError("Use a fresh external proof workspace")
    workspace.mkdir(parents=True, mode=0o700)
    original = files_identity(ORIGINAL)
    receipt = {
        "scope": "first existing+cold detached Hatch milestone only",
        "explicit_pytest_args": ["-p", "no:asyncio"],
        "companion_delta": "pyodbc/native assertions omitted only in companion; customer Ruff/config added",
        "controller": {"executable": sys.executable, "version": list(sys.version_info[:3])},
        "hatch": str(hatch),
        "cases": {},
    }
    for case in ("existing", "cold"):
        root = workspace / case / "customer"
        materialize(root)
        setup = None
        if case == "existing":
            prefix = workspace / "existing-native"
            config = root / "hatch.toml"
            config.write_text(config.read_text() + f"path = {json.dumps(str(prefix))}\n")
            environment = {
                key: value
                for key, value in os.environ.items()
                if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
                and not key.startswith("HATCH_")
            }
            environment["HATCH_PYTHON"] = str(python)
            process = subprocess.run(
                [str(hatch), "env", "create", "review"],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=180,
            )
            setup = {"exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr}
            assert process.returncode == 0, setup
            selected_python = prefix / "bin/python"
            before_inventory = inventory(selected_python, root)
        else:
            selected_python = python
            before_inventory = None
        before_declarations = declarations(root)
        plan = inspect_project(
            root,
            ProjectSelection(
                environment="review", python=str(selected_python) if case == "cold" else None, hatch=str(hatch)
            ),
        )
        prepared = prepare_project(plan, workspace / case / "invocation")
        assert isinstance(prepared, PreparedProject), prepared
        assert prepared.identity.ownership == ("existing" if case == "existing" else "invocation")
        assert prepared.identity.interpreter.version == (3, 11, 15)
        actual_python = prepared.identity.interpreter.executable
        installed_before_checks = inventory(actual_python, root)
        assert not any(
            name.lower().startswith("specfact") or name.lower() in {"crosshair-tool", "beartype", "icontract"}
            for name, _, _ in installed_before_checks
        )
        commands = {}

        def run(name, argv, expected, prepared=prepared, root=root, commands=commands):
            result = prepared.run(ProjectCommand(tuple(argv), root), timeout=60)
            commands[name] = asdict(result)
            assert result.outcome == "exited" and result.exit_code == expected, (name, result)
            return result

        run(
            "imports",
            [
                "python",
                "-c",
                "import requests,pytest,pytest_asyncio,sys; print(sys.executable); print(sys.prefix); print(requests.Request('GET','https://example.invalid').prepare().method)",
            ],
            0,
        )
        run("dependency_entrypoint", ["pytest", "--version"], 0)
        tests = run("native_async_pytest", ["python", "-m", "pytest", "-p", "no:asyncio", "-v"], 0)
        assert "test_runtime_dependencies PASSED" in tests.stdout and "8 passed" in tests.stdout, tests
        lint = run("enabled_customer_rule", ["ruff", "check", "lint_probe.py"], 1)
        assert "F821" in lint.stdout and "F401" not in lint.stdout
        run("disabled_customer_rule", ["ruff", "check", "lint_probe.py", "--ignore", "F821"], 0)
        seeded = root / "tests/test_seeded_failure.py"
        seeded.write_text("def test_seeded_customer_defect():\n    assert 2 + 2 == 5\n")
        defect = run("seeded_real_failure", ["python", "-m", "pytest", "-p", "no:asyncio", "-v"], 1)
        assert "test_seeded_customer_defect FAILED" in defect.stdout and "1 failed" in defect.stdout
        assert defect.source_identity != tests.source_identity
        seeded.unlink()
        after_inventory = inventory(actual_python, root)
        assert after_inventory == installed_before_checks
        if before_inventory is not None:
            assert after_inventory == before_inventory
        assert declarations(root) == before_declarations
        receipt["cases"][case] = {
            "identity": asdict(prepared.identity),
            "setup": setup,
            "declarations_before": before_declarations,
            "declarations_after": declarations(root),
            "inventory_before": before_inventory or installed_before_checks,
            "inventory_after": after_inventory,
            "commands": commands,
        }
    assert files_identity(ORIGINAL) == original
    receipt["original_fixture_unchanged"] = original
    (workspace / "receipt.json").write_text(json.dumps(receipt, indent=2, default=str))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--hatch", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    arguments = parser.parse_args()
    prove(arguments.workspace, hatch=arguments.hatch, python=arguments.python)
    print(arguments.workspace / "receipt.json")


if __name__ == "__main__":
    main()
