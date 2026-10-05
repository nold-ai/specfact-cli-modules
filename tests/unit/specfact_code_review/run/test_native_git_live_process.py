"""Opt-in physical SCM proof through the owned native child protocol."""

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run.native_project_runtime import _run_pip_phase


@pytest.mark.skipif(
    platform.system() != "Darwin" or platform.machine() != "arm64" or not os.environ.get("SPECFACT_GIT_PROOF_CAPSULE"),
    reason="explicit private native Git capsule proof",
)
def test_packaged_git_queries_real_tags_and_dirty_state_without_host_path(tmp_path):
    capsule = Path(os.environ["SPECFACT_GIT_PROOF_CAPSULE"]).resolve()
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
        "import os,subprocess,shutil\nfrom pathlib import Path\n"
        "def get_requires_for_build_wheel(config_settings=None):\n"
        "    image=shutil.which('git'); assert image and image.endswith('/tools/git')\n"
        "    assert shutil.which('/usr/bin/git') is None\n"
        "    def query(*args):\n"
        "        return subprocess.run(['git','--git-dir',str(Path.cwd()/'.git'),*args],"
        "capture_output=True,text=True,timeout=5,check=True).stdout.strip()\n"
        "    assert query('--version')=='git version 2.54.0'\n"
        "    clean=query('describe','--dirty','--tags','--long','--match','hatch-v*')\n"
        "    assert clean.startswith('hatch-v1.2.3-0-g') and not clean.endswith('-dirty'),clean\n"
        "    assert len(query('rev-parse','HEAD'))==40\n"
        "    assert query('status','--porcelain','--untracked-files=no')==''\n"
        "    assert query('-c','log.showSignature=false','log','-n','1','HEAD','--format=%cI')\n"
        "    Path('tracked').write_text('dirty')\n"
        "    assert query('describe','--dirty','--tags','--long','--match','hatch-v*')==clean+'-dirty'\n"
        "    assert query('status','--porcelain','--untracked-files=no')=='M tracked'\n"
        "    with subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE) as child:\n"
        "        child.kill(); assert child.wait(timeout=5)==-9\n"
        "    try: subprocess.run(['git','fetch'],capture_output=True,timeout=5)\n"
        "    except OSError: pass\n"
        "    else: raise AssertionError('transport admitted')\n"
        "    try: os.fork()\n"
        "    except OSError: pass\n"
        "    else: os._exit(99)\n"
        "    return []\n"
    )
    (inputs / "tracked").write_text("clean")
    # Maintainer fixture construction uses the candidate itself, outside project
    # execution. Every query above runs through the traced, confined broker.
    environment = {
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_AUTHOR_NAME": "SCM fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "SCM fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }
    for arguments in (
        ("init", "--quiet", "--template="),
        ("add", "tracked", "pyproject.toml", "fixture_backend.py"),
        ("commit", "--quiet", "-m", "fixture"),
        ("tag", "hatch-v1.2.3"),
    ):
        subprocess.run(
            [str(capsule / "tools/git"), *arguments],
            cwd=inputs,
            env=environment,
            check=True,
            capture_output=True,
            timeout=10,
        )
    output = tmp_path / "output"
    try:
        _run_pip_phase(SimpleNamespace(native_lease=lease), "hook", inputs, output)
        assert json.loads((output / "hook-result.json").read_text()) == {"requirements": []}
    finally:
        for descriptor in descriptors.values():
            os.close(descriptor)
