"""Bounded native hook transport preserves exact source and developer evidence."""

from __future__ import annotations

import base64
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/native_hook_transport.py"
_ALLOWED = "packages/specfact-code-review/src/specfact_code_review/run/runner.py"


def _transport() -> ModuleType:
    assert _SCRIPT.is_file(), "native hook transport implementation is absent"
    spec = importlib.util.spec_from_file_location("native_hook_transport", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()


@pytest.fixture(name="snapshot")
def snapshot_fixture(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Create a genuine Git patch and expected immutable tree."""
    repo = tmp_path / "repository"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Transport test")
    _git(repo, "config", "user.email", "transport@example.invalid")
    source = repo / _ALLOWED
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
    source.write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    return repo, _request_for_staged_snapshot(repo)


def _request_for_staged_snapshot(repo: Path) -> dict[str, str]:
    base = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "write-tree")
    patch = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--binary"],
        check=True,
        capture_output=True,
        timeout=10,
    ).stdout
    _git(repo, "reset", "--hard", "HEAD")
    return {
        "base": base,
        "tree": tree,
        "sha256": hashlib.sha256(patch).hexdigest(),
        "patch": base64.b64encode(gzip.compress(patch, mtime=0)).decode("ascii"),
    }


def test_exact_tree_is_applied(snapshot: tuple[Path, dict[str, str]]) -> None:
    """A genuine allowlisted patch yields exactly the declared index tree."""
    repo, request = snapshot
    result = _transport().prepare_snapshot(repo, request)
    assert result["tree"] == request["tree"] == _git(repo, "write-tree")
    assert result["paths"] == [_ALLOWED]


@pytest.mark.parametrize("field", ["base", "tree", "sha256"])
def test_identity_mismatch_rejected(snapshot: tuple[Path, dict[str, str]], field: str) -> None:
    """No mismatched caller identity can lead to hook execution."""
    repo, request = snapshot
    request[field] = "0" * len(request[field])
    with pytest.raises(ValueError, match=field):
        _transport().prepare_snapshot(repo, request)


@pytest.mark.parametrize("path", [".pre-commit-config.yaml", ".github/workflows/evil.yml", "../escape.py"])
def test_control_or_escaping_path_rejected(snapshot: tuple[Path, dict[str, str]], path: str) -> None:
    """Forbidden patch paths fail before Git applies customer bytes."""
    repo, request = snapshot
    patch = gzip.decompress(base64.b64decode(request["patch"])).replace(_ALLOWED.encode(), path.encode())
    request["patch"] = base64.b64encode(gzip.compress(patch)).decode()
    request["sha256"] = hashlib.sha256(patch).hexdigest()
    with pytest.raises(ValueError, match="path"):
        _transport().prepare_snapshot(repo, request)
    assert not _git(repo, "status", "--porcelain")


def test_oversized_patch_rejected(snapshot: tuple[Path, dict[str, str]]) -> None:
    """Highly compressed expansion remains bounded before Git is invoked."""
    repo, request = snapshot
    patch = b"x" * 1_000_001
    request["patch"] = base64.b64encode(gzip.compress(patch)).decode()
    request["sha256"] = hashlib.sha256(patch).hexdigest()
    with pytest.raises(ValueError, match="size"):
        _transport().prepare_snapshot(repo, request)


def test_nonregular_mode_rejected(snapshot: tuple[Path, dict[str, str]]) -> None:
    """An allowlisted filename cannot introduce an executable or symlink."""
    repo, request = snapshot
    patch = gzip.decompress(base64.b64decode(request["patch"]))
    patch = patch.replace(b"index ", b"old mode 100644\nnew mode 100755\nindex ", 1)
    request["patch"] = base64.b64encode(gzip.compress(patch)).decode()
    request["sha256"] = hashlib.sha256(patch).hexdigest()
    with pytest.raises(ValueError, match="mode"):
        _transport().prepare_snapshot(repo, request)


def test_dirty_checkout_rejected(snapshot: tuple[Path, dict[str, str]]) -> None:
    """A dirty base cannot silently contribute additional tested content."""
    repo, request = snapshot
    (repo / "unexpected.txt").write_text("not declared", encoding="utf-8")
    with pytest.raises(ValueError, match="clean"):
        _transport().prepare_snapshot(repo, request)


def test_child_environment_excludes_authority_and_credentials() -> None:
    """Child review is local developer evidence with an explicit allowlist."""
    caller = {
        "HOME": "/safe",
        "PATH": "/safe/bin",
        "GITHUB_ACTIONS": "true",
        "GH_TOKEN": "secret",
        "GITHUB_TOKEN": "secret",
        "SPECFACT_CODE_REVIEW_ENFORCEMENT": "none",
        "LD_PRELOAD": "evil",
    }
    child = _transport().hook_environment(caller)
    assert child == {"HOME": "/safe", "PATH": "/safe/bin"}


def test_default_customer_workflow_is_preserved() -> None:
    """Only explicit snapshot mode selects the transport instead of the corpus."""
    workflow = yaml.safe_load((_SCRIPT.parent.parent / ".github/workflows/capsule-customer-execution.yml").read_text())
    assert workflow["jobs"]["customer"]["if"] == "${{ inputs.hook_snapshot == '' }}"
    transport = workflow["jobs"]["native-hooks"]
    assert transport["if"] == "${{ github.event_name == 'workflow_dispatch' && inputs.hook_snapshot != '' }}"
    assert transport["timeout-minutes"] == 90
    assert workflow["permissions"] == {"contents": "read"}


def test_request_round_trip(snapshot: tuple[Path, dict[str, str]]) -> None:
    """Request fields are JSON data, including compressed patch bytes."""
    repo, request = snapshot
    assert _transport().prepare_snapshot(repo, json.loads(json.dumps(request)))["tree"] == request["tree"]


@pytest.mark.parametrize("exit_code", [0, 7])
def test_hook_exit_and_authority_are_preserved(
    snapshot: tuple[Path, dict[str, str]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int,
) -> None:
    """A real child process receives no credential or publisher context."""
    repo, request = snapshot
    transport = _transport()
    receipt = transport.prepare_snapshot(repo, request)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    interpreter = repo / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        '#!/bin/sh\n[ -z "${GH_TOKEN:-}" ] && [ -z "${GITHUB_ACTIONS:-}" ] || exit 99\n'
        f'printf "%s\\n" "$*"\nexit {exit_code}\n',
        encoding="utf-8",
    )
    interpreter.chmod(0o755)
    (repo / ".git/info/exclude").write_text(".venv/\n", encoding="utf-8")
    monkeypatch.setenv("GH_TOKEN", "fixture-secret")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    result = transport.execute_hooks(repo, evidence, receipt)
    assert result == receipt["hook_exit"] == exit_code
    assert "GITHUB_ACTIONS" in receipt["environment_removed"]
    assert (evidence / "hooks.log").read_text().strip() == (
        "-m pre_commit hook-impl --config=.pre-commit-config.yaml --hook-type=pre-commit --hook-dir=.git/hooks"
    )


@pytest.mark.parametrize("target", [_ALLOWED, "new_module.py"])
def test_hook_source_mutation_fails(
    snapshot: tuple[Path, dict[str, str]],
    tmp_path: Path,
    target: str,
) -> None:
    """Even a successful hook cannot authorize a different worktree."""
    repo, request = snapshot
    transport = _transport()
    receipt = transport.prepare_snapshot(repo, request)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    interpreter = repo / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    (repo / ".git/info/exclude").write_text(".venv/\n", encoding="utf-8")
    interpreter.write_text(f'#!/bin/sh\nprintf "VALUE = 3\\n" > "{target}"\n', encoding="utf-8")
    interpreter.chmod(0o755)
    assert transport.execute_hooks(repo, evidence, receipt) == 1
    assert receipt["hook_exit"] == 0
    assert "modified tested source" in receipt["failure"]


def _fake_hatch(root: Path, output: str, monkeypatch: pytest.MonkeyPatch, diagnostic_exit: int = 0) -> None:
    hatch = root / "hatch"
    hatch.write_text(
        f"#!{sys.executable}\nimport sys\n"
        "if any(arg.endswith('native_basedpyright_diagnostic.py') for arg in sys.argv):\n"
        f"    raise SystemExit({diagnostic_exit})\n"
        f"sys.stdout.write({output!r})\n",
        encoding="utf-8",
    )
    hatch.chmod(0o755)
    monkeypatch.setenv("PATH", str(root) + ":" + os.environ["PATH"])


@pytest.mark.parametrize("basedpyright", [False, True])
@pytest.mark.parametrize("outcomes", [(0, 9), (7, 0), (7, 9)])
def test_receipt_binds_actual_outer_identity_and_report(
    snapshot: tuple[Path, dict[str, str]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcomes: tuple[int, int],
    basedpyright: bool,
) -> None:
    """The CLI records actual authority and binds retained review bytes."""
    hook_exit, diagnostic_exit = outcomes
    repo, request = snapshot
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    evidence = tmp_path / "evidence"
    interpreter = repo / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        "#!/bin/sh\nmkdir -p .specfact\nprintf '{}' > .specfact/code-review.json\n"
        f'[ "$2" != "pre_commit" ] || exit {hook_exit}\n'
        f'case "$1" in *native_*diagnostic.py) exit {diagnostic_exit};; esac\n',
        encoding="utf-8",
    )
    interpreter.chmod(0o755)
    # Ordinary bootstrap artifacts are ignored by the real repository too.
    (repo / ".git/info/exclude").write_text(".venv/\n.specfact/\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            str(_SCRIPT),
            "--checkout",
            str(repo),
            "--request",
            str(request_path),
            "--evidence",
            str(evidence),
            *(["--basedpyright-diagnostic"] if basedpyright else []),
        ],
    )
    runtime = {
        "authority": "local_build",
        "identity": "fixture-runtime",
        "descriptor": "/private/runtime.json",
        "project": {"manager": "hatch", "environment": "default"},
    }
    _fake_hatch(tmp_path, json.dumps(runtime), monkeypatch, diagnostic_exit)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_RUN_ID", "fixture-run")
    assert _transport().main() == hook_exit
    receipt = json.loads((evidence / "receipt.json").read_text())
    assert receipt["exit_code"] == receipt["hook_exit"] == hook_exit
    _assert_diagnostic_exits(receipt, outcomes, basedpyright)
    _assert_review_receipt(receipt, evidence, request["tree"])


def _assert_diagnostic_exits(receipt: dict, outcomes: tuple[int, int], basedpyright: bool) -> None:
    hook_exit, diagnostic_exit = outcomes
    if hook_exit:
        assert receipt["semgrep_diagnostic_exit"] == diagnostic_exit
        assert receipt["semgrep_diagnostic_acceptance"] is False
    else:
        assert "semgrep_diagnostic_exit" not in receipt
    if basedpyright and hook_exit:
        assert receipt["basedpyright_diagnostic_exit"] == diagnostic_exit
        assert receipt["basedpyright_diagnostic_acceptance"] is False
    else:
        assert "basedpyright_diagnostic_exit" not in receipt


def _assert_review_receipt(receipt: dict, evidence: Path, tree: str) -> None:
    """Independently bind workflow identity, actual interpreter inventory and review bytes."""
    assert receipt["github"]["GITHUB_RUN_ID"] == "fixture-run"
    assert receipt["github"]["GITHUB_ACTIONS"] == "true"
    assert receipt["authority"] == "local-uncommitted-explicit-files"
    inventory = evidence / "hook-python-freeze.txt"
    assert receipt["hook_inventory_sha256"] == hashlib.sha256(inventory.read_bytes()).hexdigest()
    assert receipt["hook_inventory_command"][1:] == ["-m", "pip", "freeze", "--all"]
    assert receipt["tree_after"] == tree
    assert receipt["review_sha256"] == hashlib.sha256((evidence / "code-review.json").read_bytes()).hexdigest()


def test_bad_request_still_retains_failure_receipt(
    snapshot: tuple[Path, dict[str, str]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preparation failure is explicit evidence, never a missing success receipt."""
    repo, request = snapshot
    request["sha256"] = "0" * 64
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    evidence = tmp_path / "evidence"
    monkeypatch.setattr(
        "sys.argv",
        [
            str(_SCRIPT),
            "--checkout",
            str(repo),
            "--request",
            str(request_path),
            "--evidence",
            str(evidence),
        ],
    )
    assert _transport().main() == 1
    receipt = json.loads((evidence / "receipt.json").read_text())
    assert receipt["exit_code"] == 1
    assert "sha256 mismatch" in receipt["failure"]
    assert "hook_exit" not in receipt


def test_preparation_uses_native_hatch_and_preserves_stdout(
    snapshot: tuple[Path, dict[str, str]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Genuine Hatch invocation resolves selection; CLI decorations remain evidence."""
    repo, request = snapshot
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    evidence = tmp_path / "evidence"
    runtime = {
        "authority": "local_build",
        "identity": "fixture-runtime",
        "descriptor": "/private/runtime.json",
        "project": {"manager": "hatch", "environment": "default"},
    }
    decorated = "SpecFact CLI - test\n" + json.dumps(runtime) + "\nFinished\n"
    _fake_hatch(tmp_path, decorated, monkeypatch)
    interpreter = repo / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    interpreter.chmod(0o755)
    (repo / ".git/info/exclude").write_text(".venv/\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            str(_SCRIPT),
            "--checkout",
            str(repo),
            "--request",
            str(request_path),
            "--evidence",
            str(evidence),
        ],
    )
    assert _transport().main() == 0
    receipt = json.loads((evidence / "receipt.json").read_text())
    assert receipt["runtime_command"][:3] == ["hatch", "run", "python"]
    assert (evidence / "runtime.stdout").read_text().strip() == decorated.strip()
    assert json.loads((evidence / "runtime.json").read_text()) == runtime


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        "{}",
        '{"authority":"local_build","identity":"incomplete"}',
        '{"authority":"local_build","identity":"ok","descriptor":false,"project":{"manager":"hatch"}}',
        '{"authority":"local_build","identity":"ok","descriptor":"/runtime","project":[]}',
        ('{"authority":"local_build","identity":"ok","descriptor":"/runtime","project":{"manager":"hatch"}}\n' * 2),
    ],
)
def test_incomplete_or_ambiguous_runtime_output_is_rejected(output: str) -> None:
    """Decorations cannot convert missing, mistyped or duplicate descriptors into success."""
    with pytest.raises(ValueError, match="exactly one complete typed"):
        _transport().parse_runtime_output(output)


def test_preparation_selects_only_owned_workspace_modules(snapshot: tuple[Path, dict[str, str]]) -> None:
    """The baseline cannot silently replace the workspace runtime implementation."""
    repo, _ = snapshot
    caller = {
        "HOME": "/private/home",
        "PATH": "/bin",
        "PYTHONPATH": "/unrelated/host",
        "SPECFACT_MODULES_ROOTS": "/unrelated/modules",
        "GH_TOKEN": "fixture-secret",
    }
    environment = _transport().runtime_environment(repo, caller)
    assert environment["SPECFACT_MODULES_REPO"] == str(repo.resolve())
    assert environment["SPECFACT_CLI_MODULES_REPO"] == str(repo.resolve())
    assert environment["SPECFACT_MODULES_ROOTS"] == str((repo / "packages").resolve())
    assert environment["PYTHONPATH"] == str((repo / "packages/specfact-code-review/src").resolve())
    assert "GH_TOKEN" not in environment
    assert "/unrelated" not in ":".join(environment.values())


@pytest.mark.parametrize("extra_change", [False, True])
def test_only_reviewed_development_pins_are_admitted(
    snapshot: tuple[Path, dict[str, str]],
    extra_change: bool,
) -> None:
    """The dependency exception cannot carry build, hook or unrelated package changes."""
    repo, _ = snapshot
    config = repo / "pyproject.toml"
    original = (
        '[tool.hatch.envs.default]\ndependencies = [\n    "beartype>=0.22.0", '
        '"pylint>=4.0.2", "basedpyright>=1.32.1"]\n'
    )
    config.write_text(original, encoding="utf-8")
    _git(repo, "add", "pyproject.toml")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-qm", "configuration fixture")
    changed = original.replace("pylint>=4.0.2", "pylint==4.0.7").replace(
        "basedpyright>=1.32.1", "basedpyright==1.39.10"
    )
    changed = changed.replace(
        '"basedpyright==1.39.10"', '"basedpyright==1.39.10",\n    "nodejs-wheel-binaries==24.16.0"'
    )
    changed = changed.replace(
        "[tool.hatch.envs.default]\n",
        '[tool.specfact.code-review]\nnative_tools = ["git", "uname", "sed"]\n\n[tool.hatch.envs.default]\n',
    )
    changed = changed.replace('"beartype>=0.22.0"', '"specfact-cli==0.55.4",\n    "beartype>=0.22.0"')
    config.write_text(changed + ("# unrelated mutation\n" if extra_change else ""), encoding="utf-8")
    _git(repo, "add", "pyproject.toml")
    request = _request_for_staged_snapshot(repo)
    if extra_change:
        with pytest.raises(ValueError, match="development dependency"):
            _transport().prepare_snapshot(repo, request)
    else:
        assert _transport().prepare_snapshot(repo, request)["tree"] == request["tree"]


def test_basedpyright_replay_uses_real_hatch_activation(tmp_path: Path, monkeypatch) -> None:
    """An actual detached Hatch environment supplies verified selection context."""
    assert shutil.which("hatch"), "native Hatch is required for this transport regression"
    repository = tmp_path / "project"
    repository.mkdir()
    (repository / "pyproject.toml").write_text(
        "[tool.hatch.envs.default]\ndetached = true\n"
        f'path = "{tmp_path / "hatch-environment"}"\n'
        "[tool.hatch.envs.hatch-test]\ndetached = true\n"
    )
    controls = tmp_path / "controls"
    controls.mkdir()
    probe = controls / "native_basedpyright_diagnostic.py"
    probe.write_text(
        "import os, json\nprint(json.dumps({'active':os.environ.get('HATCH_ENV_ACTIVE'),"
        "'venv':os.environ.get('VIRTUAL_ENV'),'token':os.environ.get('GH_TOKEN')}))\nraise SystemExit(7)\n"
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    transport = _transport()
    monkeypatch.setattr(transport, "__file__", str(controls / "native_hook_transport.py"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GH_TOKEN", "do-not-forward")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("HATCH_ENV_ACTIVE", raising=False)
    receipt = {"hook_exit": 23}
    transport.diagnose_failed_basedpyright(repository, evidence, receipt)
    assert receipt.get("basedpyright_diagnostic_exit") == 7, (
        receipt,
        (evidence / "basedpyright-diagnostic.log").read_text(),
    )
    assert receipt["hook_exit"] == 23 and receipt["basedpyright_diagnostic_acceptance"] is False
    output = json.loads((evidence / "basedpyright-diagnostic.log").read_text().splitlines()[-1])
    assert (
        output["active"] == "default" and Path(output["venv"]).resolve() == (tmp_path / "hatch-environment").resolve()
    )
    assert output["token"] is None


def _control_request(
    tmp_path: Path, request: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> tuple[ModuleType, Path, dict[str, str]]:
    """Relocate the actual helper's control-owned data beside its fixed module path."""
    transport = _transport()
    controls = tmp_path / "controls/scripts"
    controls.mkdir(parents=True)
    monkeypatch.setattr(transport, "__file__", str(controls / "native_hook_transport.py"))
    payload = controls / "native_hook_snapshot.patch.gz.b64"
    payload.write_text(request["patch"], encoding="ascii")
    return (
        transport,
        payload,
        {**{key: value for key, value in request.items() if key != "patch"}, "patch_source": "control-checkout"},
    )


def test_control_checkout_large_snapshot(tmp_path: Path, snapshot, monkeypatch: pytest.MonkeyPatch) -> None:
    """A real patch beyond workflow input limits is authenticated and staged intact."""
    repo, _ = snapshot
    content = "\n".join(hashlib.sha256(str(index).encode()).hexdigest() for index in range(5000))
    (repo / _ALLOWED).write_text(content + "\n")
    _git(repo, "add", ".")
    request = _request_for_staged_snapshot(repo)
    assert len(request["patch"]) > 65_535
    transport, payload, file_request = _control_request(tmp_path, request, monkeypatch)
    receipt = transport.prepare_snapshot(repo, file_request)
    compressed = base64.b64decode(payload.read_bytes(), validate=True)
    assert receipt["tree"] == request["tree"] == _git(repo, "write-tree")
    assert receipt["patch_transport"] == {
        "mode": "control-checkout",
        "path": "scripts/native_hook_snapshot.patch.gz.b64",
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "compressed_bytes": len(compressed),
        "raw_bytes": len(gzip.decompress(compressed)),
    }


def test_inline_transport_receipt(snapshot) -> None:
    """Legacy payloads retain equivalent storage and size evidence."""
    repo, request = snapshot
    receipt = _transport().prepare_snapshot(repo, request)
    compressed = base64.b64decode(request["patch"])
    assert receipt["patch_transport"] == {
        "mode": "inline-gzip",
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "compressed_bytes": len(compressed),
        "raw_bytes": len(gzip.decompress(compressed)),
    }


@pytest.mark.parametrize("violation", ["symlink", "directory", "fifo", "compressed", "expanded", "corrupt"])
def test_control_payload_refused(tmp_path: Path, snapshot, monkeypatch: pytest.MonkeyPatch, violation: str) -> None:
    """Only a bounded regular compressed file can reach index mutation."""
    repo, request = snapshot
    transport, payload, file_request = _control_request(tmp_path, request, monkeypatch)
    match violation:
        case "symlink":
            target = tmp_path / "elsewhere.gz"
            payload.rename(target)
            payload.symlink_to(target)
        case "directory":
            payload.unlink()
            payload.mkdir()
        case "fifo":
            payload.unlink()
            os.mkfifo(payload)
        case "compressed":
            payload.write_bytes(base64.b64encode(b"x" * 1_000_001))
        case "expanded":
            payload.write_bytes(base64.b64encode(gzip.compress(b"x" * 1_000_001)))
        case "corrupt":
            payload.write_bytes(base64.b64encode(b"not gzip"))
    with pytest.raises((ValueError, OSError)):
        transport.prepare_snapshot(repo, file_request)
    assert not _git(repo, "status", "--porcelain")


@pytest.mark.parametrize("field", ["base", "tree", "sha256"])
def test_control_identity_refused(tmp_path: Path, snapshot, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    """File transport preserves every existing source identity check."""
    repo, request = snapshot
    transport, _, file_request = _control_request(tmp_path, request, monkeypatch)
    file_request[field] = "0" * len(file_request[field])
    with pytest.raises(ValueError, match=field):
        transport.prepare_snapshot(repo, file_request)


@pytest.mark.parametrize("extra", [{"patch": ""}, {"patch_source": "https://example.invalid/data"}, {"path": "/tmp/x"}])
def test_control_selector_refused(
    tmp_path: Path, snapshot, monkeypatch: pytest.MonkeyPatch, extra: dict[str, str]
) -> None:
    """No mixed format or caller-provided path/URL broadens the fixed source."""
    repo, request = snapshot
    transport, _, file_request = _control_request(tmp_path, request, monkeypatch)
    with pytest.raises(ValueError):
        transport.prepare_snapshot(repo, {**file_request, **extra})
    assert not _git(repo, "status", "--porcelain")


def test_control_payload_is_staged_text_safe(tmp_path: Path, snapshot, monkeypatch: pytest.MonkeyPatch) -> None:
    """The unchanged hook's forced text diff can decode the fixed payload as UTF-8."""
    _, request = snapshot
    _, payload, _ = _control_request(tmp_path, request, monkeypatch)
    control_root = payload.parent.parent
    _git(control_root, "init", "-q")
    _git(control_root, "add", ".")
    text_diff = _git(control_root, "diff", "--cached", "--text")
    assert payload.read_text(encoding="ascii") in text_diff
    assert base64.b64decode(payload.read_bytes(), validate=True) == base64.b64decode(request["patch"])


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"A" * 1_333_337, "encoded patch size"),
        (base64.b64encode(b"x" * 1_000_001), "compressed patch size"),
        (b"invalid!", "base64"),
        (b"\xff", "base64"),
        (b"Zh==", "canonical"),
        (b"Zg==\n", "base64"),
    ],
    ids=["encoded-cap", "compressed-cap", "invalid-alphabet", "non-ascii", "padding-bits", "newline"],
)
def test_control_encoded_payload_refused(
    tmp_path: Path, snapshot, monkeypatch: pytest.MonkeyPatch, content: bytes, reason: str
) -> None:
    """Encoded and compressed bounds are independent; encoding must be canonical ASCII."""
    repo, request = snapshot
    transport, payload, file_request = _control_request(tmp_path, request, monkeypatch)
    payload.write_bytes(content)
    with pytest.raises(ValueError, match=reason):
        transport.prepare_snapshot(repo, file_request)
    assert not _git(repo, "status", "--porcelain")
