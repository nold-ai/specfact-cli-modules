"""Manager probe compatibility within the already confined Python worker."""

import io
import sys
import warnings

import pytest

from specfact_code_review.run import native_child_worker as worker


@pytest.mark.parametrize("form", ["command", "module", "script"])
def test_nonisolated_child_imports_sibling_from_execution_directory(tmp_path, monkeypatch, form):
    (tmp_path / "sibling_native.py").write_text("VALUE=7\n")
    (tmp_path / "launch_native.py").write_text("import sibling_native; assert sibling_native.VALUE==7\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", [value for value in sys.path if value and value != str(tmp_path)])
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    monkeypatch.setitem(sys.modules, "__main__", sys.modules["__main__"])
    try:
        arguments = {
            "command": ["-c", "import sibling_native; assert sibling_native.VALUE==7"],
            "module": ["-m", "launch_native"],
            "script": [str(tmp_path / "launch_native.py")],
        }
        assert worker._dispatch(arguments[form]) == 0
    finally:
        sys.modules.pop("sibling_native", None)


def test_hatch_warning_filter_and_stdin_probe(monkeypatch, capsys):
    original_main, original_argv = sys.modules["__main__"], sys.argv
    monkeypatch.setattr(sys, "stdin", io.StringIO("import warnings; warnings.warn('probe'); print('native probe')"))
    try:
        with warnings.catch_warnings(record=True) as observed:
            assert worker._dispatch(["-W", "ignore", "-"]) == 0
            assert not observed
        assert capsys.readouterr().out == "native probe\n"
        assert sys.argv == ["-"]
    finally:
        sys.modules["__main__"] = original_main
        sys.argv = original_argv


def test_missing_warning_filter_is_actionable():
    with pytest.raises(worker.ManagedProcessError, match="warning filter"):
        worker._dispatch(["-W"])


def test_uv_isolated_probe_uses_existing_isolated_bootstrap(capsys):
    original_main, original_argv = sys.modules["__main__"], sys.argv
    try:
        assert worker._dispatch(["-I", "-B", "-c", "print('native query')"]) == 0
        assert capsys.readouterr().out == "native query\n"
    finally:
        sys.modules["__main__"] = original_main
        sys.argv = original_argv


def test_pytest_child_preparation_retains_selected_plugins_and_versions(tmp_path, monkeypatch):
    from _pytest.config import _prepareconfig

    selected = tmp_path / ".specfact-project-runtime/site-packages"
    info = selected / "child_plugin-1.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: child-plugin\nVersion: 1\n")
    (info / "entry_points.txt").write_text("[pytest11]\nchild-plugin = child_plugin\n")
    (selected / "child_plugin.py").write_text(
        "def pytest_addoption(parser): parser.addoption('--child-probe', action='store_true')\n"
    )
    monkeypatch.syspath_prepend(str(selected))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    try:
        with worker.installed_child_pytest_plugins(tmp_path):
            config = _prepareconfig(["--child-probe", "-o", "required_plugins=child-plugin>=1", str(tmp_path)])
            assert config.getoption("child_probe") is True
            assert config.pluginmanager.hasplugin("child-plugin")
            config._ensure_unconfigure()
        assert worker.os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    finally:
        sys.modules.pop("child_plugin", None)


def test_pytest_child_defers_plugin_imports_until_after_channel_bootstrap(tmp_path, monkeypatch, capsys):
    from _pytest.config import _prepareconfig

    site = tmp_path / ".specfact-project-runtime/site-packages"
    info = site / "deferred_plugin-1.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: deferred-plugin\nVersion: 1\n")
    (info / "entry_points.txt").write_text("[pytest11]\ndeferred-plugin = deferred_plugin\n")
    (site / "deferred_plugin.py").write_text("print('plugin-import-output')\n")
    monkeypatch.syspath_prepend(str(site))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    try:
        with worker.installed_child_pytest_plugins(tmp_path):
            assert capsys.readouterr().out == ""
            config = _prepareconfig([str(tmp_path)])
            assert "plugin-import-output" in capsys.readouterr().out
            config._ensure_unconfigure()
    finally:
        sys.modules.pop("deferred_plugin", None)


def test_pytest_origin_child_can_run_without_pytest_installed(tmp_path):
    import subprocess
    from pathlib import Path

    from specfact_code_review.run import native_pytest_plugins

    source = str(Path(native_pytest_plugins.__file__))
    code = (
        "import runpy; from pathlib import Path; "
        f"namespace = runpy.run_path({source!r}); "
        f"context = namespace['installed_child_pytest_plugins'](Path({str(tmp_path)!r})); "
        "context.__enter__(); print('ordinary-child'); context.__exit__(None,None,None)"
    )
    result = subprocess.run([sys.executable, "-S", "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ordinary-child"


@pytest.mark.parametrize("coverage", [False, True])
def test_pytest_child_preserves_explicit_plugin_objects(tmp_path, monkeypatch, coverage):
    import importlib

    import pytest_cov.plugin
    from _pytest.config import _prepareconfig

    site = tmp_path / ".specfact-project-runtime/site-packages"
    info = site / "explicit_plugin-1.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: explicit-plugin\nVersion: 1\n")
    (info / "entry_points.txt").write_text("[pytest11]\nexplicit-plugin = explicit_plugin\n")
    (site / "explicit_plugin.py").write_text("VALUE = 1\n")
    monkeypatch.syspath_prepend(str(site))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    plugin = pytest_cov.plugin if coverage else importlib.import_module("explicit_plugin")
    try:
        with worker.installed_child_pytest_plugins(tmp_path):
            config = _prepareconfig(["-o", "required_plugins=explicit-plugin>=1", str(tmp_path)], plugins=[plugin])
            assert config.pluginmanager.get_plugin(plugin.__name__) is plugin
            config._ensure_unconfigure()
    finally:
        sys.modules.pop("explicit_plugin", None)


def test_confined_rerun_store_preserves_counts_and_rejects_host_tokens(tmp_path):
    from specfact_code_review.run import native_pytest_plugins as plugins

    master = plugins.ConfinedRerunStore(tmp_path)
    child = plugins.ConfinedRerunStore(tmp_path, token=master.sock_port)
    master.set_test_reruns("tests/test_example.py::test_flaky", 2)
    assert child.get_test_reruns("tests/test_example.py::test_flaky") == 2
    child.add_test_failure("tests/test_example.py::test_flaky")
    master.add_test_failure("tests/test_example.py::test_flaky")
    assert child.get_test_failures("tests/test_example.py::test_flaky") == 2
    assert child.get_test_failures("tests/test_example.py::test_other") == 0
    with pytest.raises(plugins.ProjectPytestPluginError, match="rerun_store_token"):
        plugins.ConfinedRerunStore(tmp_path, token="/etc/passwd")


def test_confined_rerun_store_byte_limit_survives_nondefault_pages(tmp_path):
    import sqlite3

    from specfact_code_review.run.native_pytest_plugins import ConfinedRerunStore

    store = ConfinedRerunStore(tmp_path)
    store.path.unlink()
    database = sqlite3.connect(store.path)
    try:
        database.execute("PRAGMA page_size=65536")
        database.execute("CREATE TABLE counts (test TEXT PRIMARY KEY, failures INTEGER, reruns INTEGER)")
        database.commit()
    finally:
        database.close()
    store.path.chmod(0o600)
    with store._database() as database:
        page_size = database.execute("PRAGMA page_size").fetchone()[0]
        max_pages = database.execute("PRAGMA max_page_count").fetchone()[0]
        assert max_pages * page_size <= 4 << 20


def test_confined_rerun_store_concurrent_failure_counts_are_not_lost(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from specfact_code_review.run.native_pytest_plugins import ConfinedRerunStore

    server = ConfinedRerunStore(tmp_path)

    def increment(_index):
        client = ConfinedRerunStore(tmp_path, token=server.sock_port)
        for _attempt in range(10):
            client.add_test_failure("tests/test_flaky.py::test_same_node")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(increment, range(4)))
    assert server.get_test_failures("tests/test_flaky.py::test_same_node") == 40
