from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import sysconfig

import yaml
from specfact_cli.models import module_package

from tests.support.capsule_review_fixtures import (
    create_isolated_reviewer,
    independent_review_job,
    isolated_python_site_packages,
)


SOURCE_PUBLISH_STEP = "Publish installed controller source observation"
SOURCE_INVOCATIONS = ("preparation", "review")
SOURCE_CANARY = "PRIVATE_SOURCE_CANARY:/private/source --private-argument"


def source_unavailable(invocation):
    return {"phase": "installed_controller_source", "invocation": invocation, "status": "unavailable"}


def source_observed(invocation, digests):
    return source_unavailable(invocation) | {
        "status": "observed",
        "identity_kind": "authenticated_source_and_loaded_origins",
        "runner_sha256": digests["runner"],
        "sandbox_sha256": digests["sandbox"],
    }


def run_source_publication(trusted, environment):
    steps = [step for step in independent_review_job()["steps"] if step.get("name") == SOURCE_PUBLISH_STEP]
    if not steps:
        return subprocess.CompletedProcess([], 0, "", "")
    assert len(steps) == 1
    return subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + steps[0]["run"]],
        cwd=trusted.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def run_independent_source_command(trusted, environment):
    step = next(step for step in independent_review_job()["steps"] if step.get("id") == "independent_review")
    return subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=trusted.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


_SYNTHETIC_SOURCE_CASE_CODE = {
    "valid": "",
    "other_version": "",
    "cache_present": (
        "(sources/'__pycache__').mkdir(exist_ok=True)\n(sources/'__pycache__/unrelated.pyc').write_bytes(b'cache')"
    ),
    "verifier_false": "",
    "verifier_exception": "",
    "manifest_drift": "",
    "runner_drift": "",
    "sandbox_drift": "",
    "manifest_replace": "",
    "wrong_name": "",
    "invalid_metadata": "",
    "missing_key": "key.unlink()",
    "oversized_key": "key.write_bytes(b'K'*(64*1024+1))",
    "missing_runner": "sys.modules.pop(runner.__name__)",
    "missing_sandbox": "sys.modules.pop(sandbox.__name__)",
    "missing_spec": "sandbox.__spec__=None",
    "runner_file": "runner.__file__=str(root/'PRIVATE_SOURCE_CANARY.py')",
    "sandbox_file": "sandbox.__file__=runner.__file__",
    "runner_origin": "runner.__spec__.origin=sandbox.__file__",
    "sandbox_origin": "sandbox.__spec__.origin=runner.__file__",
    "relative_origin": "sandbox.__spec__.origin='sandbox.py'",
    "relative_file": "runner.__file__='runner.py'",
    "bytecode_origin": "sandbox.__spec__.origin=str(sources/'__pycache__/sandbox.pyc')",
    "missing_bindings": "del runner.execute_launch_plan\ndel sandbox.execute_launch_plan",
    "noncallable_binding": "runner.execute_launch_plan=sandbox.execute_launch_plan=None",
    "shared_string_binding": "runner.execute_launch_plan=sandbox.execute_launch_plan='PRIVATE_SOURCE_CANARY'",
    "different_binding": "runner.execute_launch_plan=lambda: None",
    "missing_source": "(sources/'sandbox.py').unlink()",
    "directory_source": "(sources/'sandbox.py').unlink()\n(sources/'sandbox.py').mkdir()",
    "fifo_source": "(sources/'sandbox.py').unlink()\nos.mkfifo(sources/'sandbox.py')",
    "oversized_source": "(sources/'sandbox.py').write_bytes(b'x'*(4*1024*1024+1))",
    "oversized_manifest": "manifest.write_bytes(b'x'*(256*1024+1))",
    "symlink_source": (
        "original=sources/'sandbox.py'\n"
        "original.rename(sources/'original.py')\n"
        "original.symlink_to(sources/'original.py')"
    ),
    "symlink_descendant": (
        "original=package/'src'\n"
        "original.rename(package/'original-src')\n"
        "original.symlink_to(package/'original-src',target_is_directory=True)"
    ),
    "symlink_package": (
        "package.rename(package.with_name('original-package'))\n"
        "package.symlink_to(package.with_name('original-package'),target_is_directory=True)"
    ),
    "receipt_write_error": "os.replace=lambda *args,**kwargs: (_ for _ in ()).throw(OSError('PRIVATE_SOURCE_CANARY'))",
    "observer_error": (
        "def broken_key():\n"
        "    raise OSError('PRIVATE_SOURCE_CANARY')\n"
        "module_installer._bundled_public_key_path=broken_key"
    ),
    "distinct_invocations": "",
}


def _synthetic_source_installation(trusted, case):
    interpreter = trusted / "venv/bin/python"
    site = isolated_python_site_packages(interpreter)
    package = trusted / "home/.specfact/modules/specfact-code-review"
    package.mkdir(parents=True)
    (package / "src").mkdir()
    shutil.move(str(site / "specfact_code_review"), str(package / "src/specfact_code_review"))
    (site / "synthetic-dependencies.pth").write_text(str(package / "src") + "\n" + sysconfig.get_path("purelib") + "\n")
    model_dir = site / "specfact_cli/models"
    model_dir.mkdir()
    (model_dir / "__init__.py").write_text("")
    shutil.copyfile(module_package.__file__, model_dir / "module_package.py")
    metadata = {"name": "nold-ai/specfact-code-review", "version": "0.51.2", "commands": ["code"]}
    if case == "other_version":
        metadata["version"] = "0.51.99"
    if case == "wrong_name":
        metadata["name"] = "nold-ai/other-module"
    if case == "invalid_metadata":
        metadata["version"] = None
    (package / "module-package.yaml").write_text(yaml.safe_dump(metadata))
    key = site / "specfact_cli/bundled.pem"
    key.write_text("SYNTHETIC_BUNDLED_PEM\n")
    return site, package


def _synthetic_source_verifier(site, case):
    installer = site / "specfact_cli/registry/module_installer.py"
    installer.write_text(
        "import json,os\nfrom pathlib import Path\n"
        "from specfact_cli.models.module_package import ModulePackageMetadata\n"
        "USER_MODULES_ROOT=Path(os.environ['HOME'])/'.specfact/modules'\n"
        f"CASE={case!r}\n"
        "def _bundled_public_key_path(): return Path(__file__).parents[1]/'bundled.pem'\n"
        "def verify_module_artifact(package,meta,**kwargs):\n"
        "    root=Path(os.environ['HOME']).parent\n"
        "    assert isinstance(meta,ModulePackageMetadata)\n"
        "    with (root/'verifier-calls.jsonl').open('a') as out:\n"
        "        out.write(json.dumps({'package':str(package),'metadata':meta.model_dump(),**kwargs})+'\\n')\n"
        "    if CASE=='verifier_exception': raise ValueError('PRIVATE_SOURCE_CANARY')\n"
        "    targets={'manifest_drift':'module-package.yaml','runner_drift':'src/specfact_code_review/run/runner.py',"
        "'sandbox_drift':'src/specfact_code_review/run/sandbox.py'}\n"
        "    if CASE in targets:\n"
        "        with (package/targets[CASE]).open('a') as out: out.write('\\n# drift\\n')\n"
        "    if CASE=='manifest_replace':\n"
        "        manifest=package/'module-package.yaml'\n"
        "        replacement=package/'replacement.yaml'\n"
        "        replacement.write_bytes(manifest.read_bytes())\n"
        "        replacement.replace(manifest)\n"
        "    return CASE!='verifier_false'\n"
    )


def _synthetic_source_subject_entry(sources, case):
    setup = (
        "import json,os,sys\nfrom pathlib import Path\n"
        "from specfact_cli.registry import module_installer\n"
        "from specfact_code_review.run import runner,sandbox\n"
        "root=Path(os.environ['HOME']).parent\n"
        "package=module_installer.USER_MODULES_ROOT/'specfact-code-review'\n"
        "sources=package/'src/specfact_code_review/run'\n"
        "manifest=package/'module-package.yaml'\n"
        "key=module_installer._bundled_public_key_path()\n" + _SYNTHETIC_SOURCE_CASE_CODE[case] + "\n"
        "original_chdir=os.chdir\n"
        "def subject_entry(path):\n"
        "    invocation='preparation' if sys.argv[2]=='prepare-index' else 'review'\n"
        "    receipt=root/f'controller-source-{invocation}.private.json'\n"
        "    entry={'cwd':str(Path.cwd()),'receipt':receipt.read_text() if receipt.is_file() else None}\n"
        "    (root/f'entry-{invocation}.json').write_text(json.dumps(entry))\n"
        "    original_chdir(path)\n"
        "os.chdir=subject_entry\n"
    )
    scope = sources / "scope.py"
    scope.write_text(scope.read_text() + setup)
    if case == "distinct_invocations":
        scope.write_text(
            scope.read_text() + "original_cleanup=cleanup_scope_resolution\n"
            "def cleanup_scope_resolution(resolution):\n"
            "    original_cleanup(resolution)\n"
            "    with (sources/'sandbox.py').open('a') as out: out.write('# review source\\n')\n"
        )


def synthetic_installed_source_reviewer(tmp_path, case="valid", review_case=(0, "PASS", "")):
    trusted, environment = create_isolated_reviewer(tmp_path, review_case)
    site, package = _synthetic_source_installation(trusted, case)
    _synthetic_source_verifier(site, case)
    sources = package / "src/specfact_code_review/run"
    (sources / "sandbox.py").write_text("def execute_launch_plan(): return None\n")
    runner = sources / "runner.py"
    runner.write_text(runner.read_text() + "from .sandbox import execute_launch_plan\n")
    _synthetic_source_subject_entry(sources, case)
    expected = {
        name: hashlib.sha256((sources / f"{name}.py").read_bytes()).hexdigest() for name in ("runner", "sandbox")
    }
    (trusted / "subject/module-package.yaml").write_text("PRIVATE_SOURCE_CANARY")
    (trusted / "subject/tempting.pem").write_text("PRIVATE_SOURCE_CANARY")
    environment["SPECFACT_MODULE_PUBLIC_KEY"] = str(trusted / "subject/tempting.pem")
    environment["CONTROLLER_SOURCE_RECEIPT"] = str(trusted / "subject/tempting.json")
    return trusted, environment, expected


def run_complete_source_bootstrap(trusted, invocation):
    recipe = next(step["run"] for step in independent_review_job()["steps"] if step.get("id") == "independent_review")
    program = recipe.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    reviewer = trusted / "reviewer.py"
    reviewer.write_text(program)
    args = ["prepare-index", str(trusted / "project.toml")] if invocation == "preparation" else ["code", "review"]
    isolated = {
        "HOME": str(trusted / "home"),
        "TMPDIR": str(trusted / "tmp"),
        "PATH": str(trusted / "venv/bin") + ":/usr/bin:/bin",
        "SPECFACT_MODULES_BRANCH": "main",
        "SPECFACT_CODE_REVIEW_CAPSULE_CACHE": str(trusted / "cache"),
    }
    result = subprocess.run(
        [str(trusted / "venv/bin/python"), "-I", str(reviewer), str(trusted / "subject"), *args],
        cwd=trusted,
        env=isolated,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (trusted / "preloaded").exists()
    entry = json.loads((trusted / f"entry-{invocation}.json").read_text())
    assert entry["cwd"] == str(trusted)
    if invocation == "preparation":
        assert (trusted / "cleaned").exists()
        assert (trusted / "prepared").read_text().splitlines() == ["base", "head"]
    else:
        assert json.loads((trusted / "argv.json").read_text()) == ["code", "review"]
    return entry


def source_publisher_environment(tmp_path):
    trusted = tmp_path / "trusted"
    (trusted / "venv/bin").mkdir(parents=True)
    (trusted / "venv/bin/python").symlink_to(sys.executable)
    return trusted, dict(os.environ, TRUSTED_ROOT=str(trusted))


def _malformed_source_receipt(case):
    observed = source_observed("preparation", {"runner": "a" * 64, "sandbox": "b" * 64})
    variants = {
        "invalid_utf8": b"\xffPRIVATE_SOURCE_CANARY",
        "invalid_json": b"{PRIVATE_SOURCE_CANARY",
        "trailing_json": json.dumps(observed).encode() + b' "PRIVATE_SOURCE_CANARY"',
        "duplicate_key": b'{"phase":"PRIVATE_SOURCE_CANARY",' + json.dumps(observed).encode()[1:],
        "nonobject": b'["PRIVATE_SOURCE_CANARY"]',
        "oversized": b" " * 4097,
        "oversized_unicode": ("é" * 2049).encode(),
    }
    updates = {
        "extra_key": {"PRIVATE_SOURCE_CANARY": "PRIVATE_SOURCE_CANARY"},
        "wrong_phase": {"phase": "PRIVATE_SOURCE_CANARY"},
        "wrong_invocation": {"invocation": "review"},
        "wrong_status": {"status": "verified"},
        "wrong_identity": {"identity_kind": "PRIVATE_SOURCE_CANARY"},
        "null_digest": {"runner_sha256": None},
        "uppercase_digest": {"runner_sha256": "A" * 64},
        "nonhex_digest": {"sandbox_sha256": "g" * 64},
        "short_digest": {"runner_sha256": "a" * 63},
        "long_digest": {"sandbox_sha256": "b" * 65},
    }
    if case in variants:
        return variants[case]
    if case in updates:
        return json.dumps(observed | updates[case]).encode()
    if case == "missing_digest":
        del observed["runner_sha256"]
        return json.dumps(observed).encode()
    unavailable = source_unavailable("preparation")
    return json.dumps(unavailable | {case: "PRIVATE_SOURCE_CANARY"}).encode()


def write_source_receipt_case(receipt, case):
    if case == "symlink":
        target = receipt.parent / "PRIVATE_SOURCE_CANARY.json"
        target.write_text(json.dumps(source_unavailable("preparation")))
        receipt.symlink_to(target)
        return
    if case == "directory":
        receipt.mkdir()
        return
    if case == "fifo":
        os.mkfifo(receipt)
        return
    if case == "unreadable":
        receipt.write_text("PRIVATE_SOURCE_CANARY")
        receipt.chmod(0)
        return
    if case != "missing":
        receipt.write_bytes(_malformed_source_receipt(case))
