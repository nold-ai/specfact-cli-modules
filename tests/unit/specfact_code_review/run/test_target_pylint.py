"""Real Pylint uses attached namespace roots without replacing native configuration."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pylint
import pytest

from specfact_code_review.run import target_bootstrap


def _runtime(tmp_path: Path, roots: list[str], editable: bool) -> dict[str, Path]:
    paths = {"PROJECT": tmp_path / "runtime", "SNAPSHOT": tmp_path / "snapshot"}
    installed = paths["PROJECT"] / "site-packages"
    installed.mkdir(parents=True)
    files = {
        "src/example/example.py": "LEAF = True\n",
        "src/example/utils/__init__.py": "",
        "src/example/utils/values.py": "VALUE = 1\n",
        "tests/__init__.py": "",
        "tests/test_values.py": "from example.utils.values import VALUE\n",
    }
    for name, content in files.items():
        path = paths["SNAPSHOT"] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    if editable:
        (installed / "example.pth").write_text(str(paths["SNAPSHOT"] / "src") + "\n")
    descriptor = {
        "project": {"source_roots": roots},
        "inventory": {"member_graphs": {"pylint": {"sealed_imports": ["pylint", "astroid"], "installed": []}}},
    }
    (paths["PROJECT"] / "project-runtime.json").write_text(json.dumps(descriptor))
    paths["ANALYZERS"] = Path(pylint.__file__).parent.parent
    paths["BUILTIN"] = Path(target_bootstrap.__file__).parents[2]
    return paths


def _run(paths: dict[str, Path], arguments: list[str]) -> subprocess.CompletedProcess[str]:
    path_values = {name: str(path) for name, path in paths.items()}
    script = f"""
import multiprocessing, runpy, sys
from pathlib import Path
# This fixture has no built interpreter launcher; keep native subprocess startup.
multiprocessing.set_executable(sys.executable)
bootstrap = runpy.run_path({target_bootstrap.__file__!r})
main = bootstrap['main']
main.__globals__.update({{name: Path(value) for name, value in {path_values!r}.items()}})
sys.argv = ['target_bootstrap', 'pylint', *{arguments!r}]
main()
"""
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", script],
        cwd=paths["SNAPSHOT"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _import_findings(paths: dict[str, Path], arguments: list[str]) -> list[dict]:
    result = _run(
        paths,
        [
            "--output-format=json",
            "--persistent=no",
            "--disable=all",
            "--enable=E0401,E0611",
            *arguments,
            "src/example/utils/values.py",
            "tests/test_values.py",
        ],
    )
    assert result.returncode in (0, 2), result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("roots,editable", [([], True), (["src"], False), (["."], True)])
def test_attached_namespace_root_prevents_leaf_shadowing(tmp_path: Path, roots: list[str], editable: bool) -> None:
    paths = _runtime(tmp_path, roots, editable)
    assert _import_findings(paths, []) == []


@pytest.mark.parametrize("configured", ['["src/example"]', "[]"])
def test_native_config_overrides_runtime_fallback(tmp_path: Path, configured: str) -> None:
    paths = _runtime(tmp_path, [], True)
    (paths["SNAPSHOT"] / "pyproject.toml").write_text(f"[tool.pylint.main]\nsource-roots = {configured}\n")
    assert {item["message-id"] for item in _import_findings(paths, [])} == {"E0401", "E0611"}


@pytest.mark.parametrize("arguments", [["--source-roots=src"], ["--source-roots", "src"]])
def test_native_cli_overrides_repository_roots(tmp_path: Path, arguments: list[str]) -> None:
    paths = _runtime(tmp_path, [], True)
    (paths["SNAPSHOT"] / "pyproject.toml").write_text('[tool.pylint.main]\nsource-roots = ["src/example"]\n')
    assert _import_findings(paths, arguments) == []


def test_missing_import_is_preserved_with_attached_roots(tmp_path: Path) -> None:
    paths = _runtime(tmp_path, [], True)
    test = paths["SNAPSHOT"] / "tests/test_values.py"
    test.write_text(test.read_text() + "import genuinely_missing_customer_dependency\n")
    findings = _import_findings(paths, [])
    assert len(findings) == 1
    assert findings[0]["message-id"] == "E0401"
    assert "genuinely_missing_customer_dependency" in findings[0]["message"]


def test_built_runtime_does_not_infer_raw_source_root(tmp_path: Path) -> None:
    paths = _runtime(tmp_path, [], False)
    result = _run(paths, ["--generate-toml-config"])
    assert result.returncode == 0, result.stderr
    assert tomllib.loads(result.stdout)["tool"]["pylint"]["main"].get("source-roots", []) == []


def test_parallel_pylint_retains_runtime_roots(tmp_path: Path) -> None:
    paths = _runtime(tmp_path, [], True)
    assert _import_findings(paths, ["--jobs=2"]) == []
