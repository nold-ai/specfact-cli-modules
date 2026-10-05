"""Opt-in physical tests of managed children in the actual ad-hoc capsule."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run.native_project_runtime import _run_pip_phase


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64" or not os.environ.get("SPECFACT_NATIVE_CAPSULE"),
    reason="explicit native ARM64 capsule proof",
)
def test_build_hook_runs_managed_python_child_and_denies_direct_fork(tmp_path: Path) -> None:
    capsule = Path(os.environ["SPECFACT_NATIVE_CAPSULE"]).resolve()
    names = ("bin/specfact-native-broker", "bin/specfact-native-bootstrap", "bin/specfact-native-verifier")
    descriptors = {name: os.open(capsule / name, os.O_RDONLY) for name in names}
    lease = SimpleNamespace(
        path=capsule,
        identity=hashlib.sha256((capsule / names[0]).read_bytes()).hexdigest(),
        fds=descriptors,
        code_identities={name: (os.fstat(fd).st_dev, os.fstat(fd).st_ino) for name, fd in descriptors.items()},
        evidence={
            "status": "VERIFIED_CACHE_CANDIDATE",
            "native_signing_mode": "adhoc",
            "native_signing_verified": True,
        },
    )
    inputs = tmp_path / "inputs"
    (inputs / ".specfact-build-dependencies/site-packages").mkdir(parents=True)
    (inputs / ".specfact-hook.json").write_text(json.dumps({"operation": "requirements", "extras": []}))
    (inputs / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="fixture_backend"\nbackend-path=["."]\n'
    )
    (inputs / "fixture_backend.py").write_text(
        "import os, subprocess, sys, time, io\nfrom pathlib import Path\nfrom contextlib import redirect_stdout\n"
        "def get_requires_for_build_wheel(config_settings=None):\n"
        "    result=subprocess.run([sys.executable,'-c','import sys; print(sys.stdin.read().upper())'],"
        "input='owned child',capture_output=True,text=True,timeout=5,check=True)\n"
        "    assert result.stdout.strip()=='OWNED CHILD', result\n"
        "    Path('generated.txt').write_text('current source')\n"
        "    os.environ['NATIVE_BUILD_VERSION']='1.2'\n"
        "    result=subprocess.run([sys.executable,'-c',"
        '\'import os; assert os.environ["NATIVE_BUILD_VERSION"]=="1.2"; print(open("generated.txt").read())\'],'
        "capture_output=True,text=True,timeout=5,check=True)\n"
        "    assert result.stdout.strip()=='current source'\n"
        "    Path('sibling_probe.py').write_text('VALUE=73\\n')\n"
        "    Path('entry_probe.py').write_text('import sibling_probe; print(sibling_probe.VALUE)\\n')\n"
        "    for args in (['-c','import sibling_probe; print(sibling_probe.VALUE)'],"
        "['-m','entry_probe'],[str(Path.cwd()/'entry_probe.py')]):\n"
        "        result=subprocess.run([sys.executable,*args],capture_output=True,text=True,timeout=5,check=True)\n"
        "        assert result.stdout.strip()=='73', result\n"
        "    for args in (['-B','-I'],['-W','ignore','-I']):\n"
        "        isolated={**os.environ,'PYTHONPATH':'/unadmitted/ignored/overlay'}\n"
        "        result=subprocess.run([sys.executable,*args,'-c',"
        "'import importlib.util; assert importlib.util.find_spec(\"sibling_probe\") is None'],"
        "env=isolated,capture_output=True,text=True,timeout=5,check=True)\n"
        "    for index in range(12):\n"
        "        plain=subprocess.Popen([sys.executable,'-c','print(71)'],stdout=subprocess.PIPE)\n"
        "        assert plain.wait(timeout=5)==0\n"
        "        assert plain.stdout.read().strip()==b'71'\n"
        "    capture=io.StringIO()\n"
        "    with redirect_stdout(capture): subprocess.check_call([sys.executable,'-c','print(72)'])\n"
        "    assert capture.getvalue().strip()=='72'\n"
        "    with subprocess.Popen([sys.executable,'-u','-c','import time; print(\"READY\"); time.sleep(0.8)'],"
        "stdout=subprocess.PIPE,text=True) as child:\n"
        "        started=time.monotonic()\n"
        "        assert child.stdout.readline().strip()=='READY'\n"
        "        assert time.monotonic()-started<0.5\n"
        "    with subprocess.Popen([sys.executable,'-c',"
        '\'import time; from pathlib import Path; time.sleep(0.1); Path("completed.txt").write_text("done")\']): pass\n'
        "    assert Path('completed.txt').read_text()=='done'\n"
        "    result=subprocess.run([sys.executable,'-c','import sys; sys.exit(7)'],capture_output=True,timeout=5)\n"
        "    assert result.returncode==7, result\n"
        "    try: subprocess.run([sys.executable,'-c','import time; time.sleep(60)'],capture_output=True,timeout=0.1)\n"
        "    except subprocess.TimeoutExpired: pass\n"
        "    else: raise AssertionError('managed timeout was ignored')\n"
        "    with subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],stdout=subprocess.PIPE) as child:\n"
        "        assert child.poll() is None\n"
        "        child.kill()\n"
        "        assert child.wait(timeout=5)==-9\n"
        "    try: pid=os.fork()\n"
        "    except OSError: pass\n"
        "    else:\n"
        "        if pid==0: os._exit(90)\n"
        "        raise AssertionError('direct fork was admitted')\n"
        "    return []\n"
    )
    output = tmp_path / "output"
    try:
        _run_pip_phase(SimpleNamespace(native_lease=lease), "hook", inputs, output)
        assert json.loads((output / "hook-result.json").read_text()) == {"requirements": []}
    finally:
        for descriptor in descriptors.values():
            os.close(descriptor)


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64" or not os.environ.get("SPECFACT_NATIVE_CAPSULE"),
    reason="explicit native ARM64 capsule proof",
)
def test_authentic_hatch_creates_and_installs_private_environment(tmp_path: Path) -> None:
    """Exercise pinned Hatch, virtualenv and offline pip; no host manager."""
    import shutil

    from specfact_code_review.run.native_project_runtime import _prepare_build_dependencies

    capsule = Path(os.environ["SPECFACT_NATIVE_CAPSULE"]).resolve()
    names = ("bin/specfact-native-broker", "bin/specfact-native-bootstrap", "bin/specfact-native-verifier")
    descriptors = {name: os.open(capsule / name, os.O_RDONLY) for name in names}
    lease = SimpleNamespace(
        path=capsule,
        identity=hashlib.sha256((capsule / names[0]).read_bytes()).hexdigest(),
        fds=descriptors,
        code_identities={name: (os.fstat(fd).st_dev, os.fstat(fd).st_ino) for name, fd in descriptors.items()},
        evidence={
            "status": "VERIFIED_CACHE_CANDIDATE",
            "native_signing_mode": "adhoc",
            "native_signing_verified": True,
        },
    )
    runtime = SimpleNamespace(native_lease=lease)
    try:
        dependencies = _prepare_build_dependencies(runtime, ["hatch==1.18.0", "uv==0.12.13"], tmp_path, "hatch-manager")
        wheels = tmp_path / "requirements"
        wheels.mkdir()
        (wheels / "request.json").write_text(
            json.dumps({"schema": "specfact-native-pip-request-v1", "requirements": ["idna==3.10"], "constraints": []})
        )
        acquired = tmp_path / "acquired"
        _run_pip_phase(runtime, "acquire", wheels, acquired)
        inputs = tmp_path / "inputs"
        inputs.mkdir()
        shutil.copytree(dependencies, inputs / ".specfact-build-dependencies")
        shutil.copytree(acquired / "wheels", inputs / "wheelhouse")
        (inputs / ".specfact-hook.json").write_text(json.dumps({"operation": "requirements", "extras": []}))
        (inputs / "pyproject.toml").write_text(
            '[build-system]\nrequires=[]\nbuild-backend="fixture_backend"\nbackend-path=["."]\n'
            '[project]\nname="managed-hatch-fixture"\nversion="1.0"\n'
            '[tool.hatch.envs.review]\nskip-install=true\ndependencies=["idna==3.10"]\n'
        )
        (inputs / "fixture_backend.py").write_text(
            "import os,sys\nfrom pathlib import Path\n"
            "def get_requires_for_build_wheel(config_settings=None):\n"
            "    from hatch.cli import hatch\n"
            "    import io\n    from contextlib import redirect_stderr\n"
            "    from hatch._version import __version__\n"
            "    assert __version__=='1.18.0'\n"
            "    os.environ.update(PIP_NO_INDEX='1', PIP_FIND_LINKS=str(Path.cwd()/'wheelhouse'),"
            "PIP_DISABLE_PIP_VERSION_CHECK='1')\n"
            "    data=Path(os.environ['TMPDIR'])/'hatch-data'\n"
            "    diagnostic=io.StringIO()\n"
            "    try:\n"
            "        with redirect_stderr(diagnostic):\n"
            "            hatch.main(args=['-q','--data-dir',str(data),'--cache-dir',str(data/'cache'),"
            "'--env','review','env','create','review'],standalone_mode=False)\n"
            "    except BaseException as error: raise ValueError(str(error)+': '+diagnostic.getvalue()) from error\n"
            "    environments=list(data.rglob('pyvenv.cfg')); assert len(environments)==1, environments\n"
            "    import subprocess\n"
            "    result=subprocess.run([str(environments[0].parent/'bin/python'),'-c','import idna; print(idna.__version__)'],"
            "capture_output=True,timeout=5,check=True)\n"
            "    assert result.stdout.strip()==b'3.10', result\n"
            "    return []\n"
        )
        output = tmp_path / "output"
        _run_pip_phase(runtime, "hook", inputs, output)
        assert json.loads((output / "hook-result.json").read_text()) == {"requirements": []}
        (inputs / ".specfact-hatch.json").write_text(
            json.dumps({"schema": "native-hatch-request-v1", "environment": "review", "groups": [], "extras": []})
        )
        (inputs / ".specfact-hook.json").write_text(json.dumps({"operation": "hatch.describe", "extras": []}))
        described = tmp_path / "hatch-described"
        _run_pip_phase(runtime, "hook", inputs, described)
        description = json.loads((described / "hook-result.json").read_text())
        assert description["requirements"] == ["idna==3.10"]
        assert description["skip_install"] is True
        (inputs / ".specfact-hook.json").write_text(json.dumps({"operation": "hatch.install", "extras": []}))
        installed = tmp_path / "hatch-installed"
        _run_pip_phase(runtime, "hook", inputs, installed)
        assert (installed / "site-packages/idna/__init__.py").is_file()
        assert json.loads((installed / "hook-result.json").read_text())["manager"] == {
            "name": "hatch",
            "version": "1.18.0",
        }
    finally:
        for descriptor in descriptors.values():
            os.close(descriptor)


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64" or not os.environ.get("SPECFACT_NATIVE_CAPSULE"),
    reason="explicit native ARM64 capsule proof",
)
def test_native_project_hook_reads_only_admitted_cpu_topology(tmp_path):
    capsule = Path(os.environ["SPECFACT_NATIVE_CAPSULE"]).resolve()
    names = ("bin/specfact-native-broker", "bin/specfact-native-bootstrap", "bin/specfact-native-verifier")
    fds = {name: os.open(capsule / name, os.O_RDONLY) for name in names}
    lease = SimpleNamespace(
        path=capsule,
        identity="a" * 64,
        fds=fds,
        code_identities={name: (os.fstat(fd).st_dev, os.fstat(fd).st_ino) for name, fd in fds.items()},
        evidence={
            "status": "VERIFIED_CACHE_CANDIDATE",
            "native_signing_mode": "adhoc",
            "native_signing_verified": True,
        },
    )
    inputs, output = tmp_path / "inputs", tmp_path / "output"
    inputs.mkdir()
    (inputs / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="fixture_backend"\nbackend-path=["."]\n'
    )
    (inputs / "fixture_backend.py").write_text(
        "def get_requires_for_build_wheel(config_settings=None):\n"
        "    import ctypes\n"
        "    from ctypes import byref, c_int, c_size_t\n"
        "    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)\n"
        "    for name in ('hw.logicalcpu', 'hw.physicalcpu'):\n"
        "        result = c_int(); size = c_size_t(ctypes.sizeof(result))\n"
        "        assert library.sysctlbyname(name.encode(), byref(result), byref(size), None, 0) == 0\n"
        "        assert result.value > 0\n"
        "    result = c_int(); size = c_size_t(ctypes.sizeof(result))\n"
        "    assert library.sysctlbyname(b'hw.memsize', byref(result), byref(size), None, 0) != 0\n"
        "    assert ctypes.get_errno() == 1\n"
        "    return []\n"
    )
    (inputs / ".specfact-hook.json").write_text(json.dumps({"operation": "requirements", "extras": []}))
    try:
        _run_pip_phase(SimpleNamespace(native_lease=lease), "hook", inputs, output)
        assert json.loads((output / "hook-result.json").read_text())["requirements"] == []
    finally:
        for fd in fds.values():
            os.close(fd)
