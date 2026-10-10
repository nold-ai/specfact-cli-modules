from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import cast

import pytest

from specfact_code_review.run import native_worker


@pytest.fixture(autouse=True)
def _restore_fixture_permissions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> object:  # pyright: ignore[reportUnusedFunction]
    for name in native_worker._UNSAFE_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    yield
    for root, directories, files in os.walk(tmp_path, topdown=False):
        for name in files:
            path = Path(root) / name
            if not path.is_symlink():
                path.chmod(0o600)
        for name in directories:
            (Path(root) / name).chmod(0o700)
    tmp_path.chmod(0o700)


def _roots(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    capsule = tmp_path / "capsule"
    project = tmp_path / "project"
    output = tmp_path / "output"
    temporary = tmp_path / "temporary"
    for root in (capsule, project, output, temporary):
        root.mkdir()
    source = project / "pkg" / "example.py"
    source.parent.mkdir()
    source.write_text("def value():\n    return True\n", encoding="utf-8")
    request = {
        "adapter_argv": [],
        "bug_hunt": False,
        "complete_pytest_inventory": False,
        "member": "ai-bloat-ast",
        "paths": ["pkg/example.py"],
        "schema": "specfact-native-analyzer-request-v1",
    }
    (project / ".specfact-native-request.json").write_text(
        json.dumps(request, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for path in (source, project / ".specfact-native-request.json"):
        path.chmod(0o400)
    source.parent.chmod(0o500)
    project.chmod(0o500)
    capsule.chmod(0o700)
    return capsule, project, output, temporary


def _argv(roots: tuple[Path, Path, Path, Path]) -> list[str]:
    return ["native_worker.py", *(str(root) for root in roots)]


def _set_member(roots: tuple[Path, Path, Path, Path], member: str) -> None:
    project = roots[1]
    request_path = project / ".specfact-native-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["member"] = member
    project.chmod(0o700)
    request_path.chmod(0o600)
    request_path.write_text(json.dumps(request), encoding="utf-8")
    request_path.chmod(0o400)
    project.chmod(0o500)


def _write_replies(roots: tuple[Path, Path, Path, Path], replies: list[dict[str, object]]) -> None:
    project = roots[1]
    reply_path = project / ".specfact-native-replies.json"
    project.chmod(0o700)
    if reply_path.exists():
        reply_path.chmod(0o600)
    reply_path.write_text(
        json.dumps({"replies": replies, "schema": "specfact-native-analyzer-replies-v1"}),
        encoding="utf-8",
    )
    reply_path.chmod(0o400)
    project.chmod(0o500)


def _clear_output(roots: tuple[Path, Path, Path, Path]) -> None:
    for path in roots[2].iterdir():
        path.unlink()


def _fake_external_adapter(tool: str):
    def execute(paths, managed_run, adapter_argv, _bug_hunt, _complete_pytest_inventory):
        result = managed_run(
            [f"capsule-tool:{tool}", "--fixed-scan", str(paths[0]), *adapter_argv],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert isinstance(result, subprocess.CompletedProcess)
        return []

    return execute


def test_native_pytest_policy_binds_cache_to_private_temporary_root(tmp_path: Path) -> None:
    policy = ["-c", "pytest.ini", "--", "tests/test_app.py::test_value"]

    assert native_worker._bind_pytest_private_state(policy, tmp_path) == [
        "-c",
        "pytest.ini",
        "-o",
        f"cache_dir={tmp_path / 'pytest/cache-dir'}",
        "--",
        "tests/test_app.py::test_value",
    ]


@pytest.mark.parametrize("member", ["ai-bloat-ast", "ast-clean-code"])
def test_in_process_members_write_atomic_runner_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, member: str
) -> None:
    roots = _roots(tmp_path)
    project = roots[1]
    request_path = project / ".specfact-native-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["member"] = member
    request_path.chmod(0o600)
    request_path.write_text(json.dumps(request), encoding="utf-8")
    request_path.chmod(0o400)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_COMPLETE

    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert result["member"] == member
    assert result["execution_state"] == "ran"
    assert result["evidence_outcome"] in {"PASS", "FAIL"}
    assert isinstance(result["findings"], list)
    assert result["diagnostic"] == ""
    assert not (roots[2] / ".result.json.tmp").exists()


@pytest.mark.parametrize(
    ("member", "tool"),
    [
        ("ruff", "ruff"),
        ("radon", "radon"),
        ("semgrep-clean", "semgrep"),
        ("basedpyright", "basedpyright"),
        ("pylint", "pylint"),
        ("contracts", "crosshair"),
        ("semgrep-bugs", "semgrep"),
        ("targeted-pytest-coverage", "pytest"),
    ],
)
def test_external_members_emit_closed_replay_request_and_unknown_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    member: str,
    tool: str,
) -> None:
    roots = _roots(tmp_path)
    request_path = roots[1] / ".specfact-native-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["member"] = member
    request_path.chmod(0o600)
    request_path.write_text(json.dumps(request), encoding="utf-8")
    request_path.chmod(0o400)
    monkeypatch.setitem(native_worker.EXTERNAL_ADAPTERS, member, _fake_external_adapter(tool))
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_REPLAY_REQUIRED

    emitted = json.loads(capsys.readouterr().out)
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert emitted == result["managed_launch_request"]
    assert emitted["schema"] == "specfact-managed-launch-request-v1"
    assert emitted["member"] == member
    assert emitted["tool"] == tool
    assert emitted["cwd"] == "project"
    assert emitted["environment"] == {}
    assert emitted["argv"] == [f"capsule-tool:{tool}", "--fixed-scan", "project/pkg/example.py"]
    assert result == {
        "diagnostic": "managed_tool_replay_required",
        "evidence_outcome": "UNKNOWN",
        "execution_state": "error",
        "findings": [],
        "managed_launch_request": emitted,
        "member": member,
    }


@pytest.mark.parametrize(
    ("member", "adapter_argv"),
    [
        ("ruff", ["--isolated", "--no-cache", "--no-force-exclude"]),
        ("radon", ["radon-full-result-v1"]),
        ("semgrep-clean", ["/opt/specfact/config/1"]),
        ("basedpyright", ["--project", "/opt/specfact/config/2/basedpyright.json"]),
        ("pylint", ["--rcfile", "/opt/specfact/config/3/pylintrc", "--jobs=1"]),
        ("contracts", ["contract-inputs-v1", "--test-root", "tests"]),
        (
            "targeted-pytest-coverage",
            [
                "-c",
                "/opt/specfact/config/4/pytest.ini",
                "--rootdir",
                "/opt/specfact/snapshot",
                "--cov-config",
                "/opt/specfact/config/5/coveragerc",
                "--",
                "tests/test_app.py::test_value",
            ],
        ),
    ],
)
def test_external_members_bind_only_fixed_adapter_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    member: str,
    adapter_argv: list[str],
) -> None:
    roots = _roots(tmp_path)
    request_path = roots[1] / ".specfact-native-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request.update({"member": member, "adapter_argv": adapter_argv})
    request_path.chmod(0o600)
    request_path.write_text(json.dumps(request), encoding="utf-8")
    request_path.chmod(0o400)
    monkeypatch.setitem(
        native_worker.EXTERNAL_ADAPTERS,
        member,
        _fake_external_adapter(native_worker._EXTERNAL_TOOLS[member]),
    )
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_REPLAY_REQUIRED
    emitted = json.loads(capsys.readouterr().out)
    transport = native_worker.ReplayTransport(
        member=member,
        tool=native_worker._EXTERNAL_TOOLS[member],
        replies=[],
        capsule=roots[0],
        project=roots[1],
        temporary=roots[3],
    )
    materialized = native_worker._materialized_adapter_argv(adapter_argv, roots[1])
    expected = [transport._logical_path(value) for value in materialized]
    assert emitted["argv"][-len(expected) :] == expected


def test_in_process_tool_error_preserves_unknown_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    source = roots[1] / "pkg" / "example.py"
    roots[1].chmod(0o700)
    source.parent.chmod(0o700)
    source.chmod(0o600)
    source.write_text("def broken(:\n", encoding="utf-8")
    source.chmod(0o400)
    source.parent.chmod(0o500)
    roots[1].chmod(0o500)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_COMPLETE
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert result["execution_state"] == "error"
    assert result["evidence_outcome"] == "UNKNOWN"
    assert result["diagnostic"] == "analyzer_reported_incomplete_execution"
    assert result["findings"][0]["category"] == "tool_error"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda request: request.update({"extra": True}),
        lambda request: request.update({"member": "unknown"}),
        lambda request: request.update({"paths": ["../escape.py"]}),
        lambda request: request.update({"adapter_argv": ["--arbitrary"]}),
        lambda request: request.update({"bug_hunt": "yes"}),
    ],
)
def test_request_rejects_extra_fields_unknown_members_escapes_and_unsafe_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: object,
) -> None:
    roots = _roots(tmp_path)
    request_path = roots[1] / ".specfact-native-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    mutation(request)  # type: ignore[operator]
    request_path.chmod(0o600)
    request_path.write_text(json.dumps(request), encoding="utf-8")
    request_path.chmod(0o400)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_INVALID_REQUEST
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert result["evidence_outcome"] == "UNKNOWN"
    assert result["execution_state"] == "error"
    assert result["findings"] == []
    assert str(result["diagnostic"]).startswith("native_worker_request_invalid:")


def test_worker_rejects_symlink_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    project = roots[1]
    source = project / "pkg" / "example.py"
    project.chmod(0o700)
    source.parent.chmod(0o700)
    source.chmod(0o600)
    source.unlink()
    source.symlink_to(tmp_path / "outside.py")
    (tmp_path / "outside.py").write_text("value = 1\n", encoding="utf-8")
    source.parent.chmod(0o500)
    project.chmod(0o500)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    try:
        assert native_worker.main() == native_worker.EXIT_INVALID_REQUEST
        result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
        assert result["evidence_outcome"] == "UNKNOWN"
    finally:
        project.chmod(0o700)
        source.parent.chmod(0o700)


def test_worker_rejects_unsafe_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    monkeypatch.setenv("DYLD_INSERT_LIBRARIES", "/tmp/injected.dylib")
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_INVALID_REQUEST
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert result["evidence_outcome"] == "UNKNOWN"


def test_worker_rejects_output_collision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    (roots[2] / "result.json").write_text("existing\n", encoding="utf-8")
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_OUTPUT_COLLISION
    assert (roots[2] / "result.json").read_text(encoding="utf-8") == "existing\n"


def test_worker_accepts_only_broker_created_stream_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    for name in ("managed-stdout.bin", "managed-stderr.bin"):
        (roots[2] / name).write_bytes(b"")
        (roots[2] / name).chmod(0o600)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_COMPLETE
    assert (roots[2] / "result.json").is_file()


def test_worker_rejects_malformed_adapter_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))
    monkeypatch.setitem(native_worker.IN_PROCESS_ADAPTERS, "ai-bloat-ast", lambda _paths: [object()])

    assert native_worker.main() == native_worker.EXIT_INVALID_RESULT
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert result["evidence_outcome"] == "UNKNOWN"
    assert str(result["diagnostic"]).startswith("native_worker_result_invalid:")


def test_worker_rejects_extra_argv_and_non_absolute_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    monkeypatch.setattr(native_worker.sys, "argv", [*_argv(roots), "extra"])
    assert native_worker.main() == native_worker.EXIT_INVALID_REQUEST

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(native_worker.sys, "argv", ["native_worker.py", "capsule", "project", "output", "temporary"])
    assert native_worker.main() == native_worker.EXIT_INVALID_REQUEST


@pytest.mark.parametrize("member", sorted(native_worker._EXTERNAL_TOOLS))
def test_controller_reply_completes_each_external_member_without_spawning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    member: str,
) -> None:
    roots = _roots(tmp_path)
    tool = native_worker._EXTERNAL_TOOLS[member]
    _set_member(roots, member)
    monkeypatch.setitem(native_worker.EXTERNAL_ADAPTERS, member, _fake_external_adapter(tool))
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_REPLAY_REQUIRED
    pending = json.loads(capsys.readouterr().out)
    assert pending == {
        "argv": [f"capsule-tool:{tool}", "--fixed-scan", "project/pkg/example.py"],
        "capture_output": True,
        "cwd": "project",
        "environment": {},
        "member": member,
        "schema": "specfact-managed-launch-request-v1",
        "sequence": 0,
        "text": True,
        "timeout_ms": 30_000,
        "tool": tool,
    }

    _clear_output(roots)
    _write_replies(
        roots,
        [{"request": pending, "result": {"returncode": 0, "stderr": "", "stdout": "[]"}}],
    )
    assert native_worker.main() == native_worker.EXIT_COMPLETE
    assert capsys.readouterr().out == ""
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert result == {
        "diagnostic": "",
        "evidence_outcome": "PASS",
        "execution_state": "ran",
        "findings": [],
        "member": member,
    }


@pytest.mark.parametrize(
    "tamper",
    ["reordered", "extra", "duplicate", "oversized", "path", "environment", "argv"],
)
def test_controller_replies_reject_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tamper: str,
) -> None:
    roots = _roots(tmp_path)
    _set_member(roots, "ruff")
    monkeypatch.setitem(native_worker.EXTERNAL_ADAPTERS, "ruff", _fake_external_adapter("ruff"))
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))
    assert native_worker.main() == native_worker.EXIT_REPLAY_REQUIRED
    pending = json.loads(capsys.readouterr().out)
    result: dict[str, object] = {"returncode": 0, "stderr": "", "stdout": "[]"}
    reply: dict[str, object] = {"request": json.loads(json.dumps(pending)), "result": result}
    reply_request = cast(dict[str, object], reply["request"])
    reply_argv = cast(list[str], reply_request["argv"])
    replies = [reply]
    mutations = {
        "reordered": lambda: replies.insert(0, _sequenced_reply(reply)),
        "extra": lambda: replies.append(_sequenced_reply(reply)),
        "duplicate": lambda: replies.append(json.loads(json.dumps(reply))),
        "oversized": lambda: result.update(stdout="x" * ((4 << 20) + 1)),
        "path": lambda: reply_argv.__setitem__(-1, "project/../escape.py"),
        "environment": lambda: reply_request.update(environment={"HOME": "/tmp/substituted"}),
        "argv": lambda: reply_argv.__setitem__(1, "--substituted"),
    }
    mutations[tamper]()
    _clear_output(roots)
    _write_replies(roots, replies)

    assert native_worker.main() == native_worker.EXIT_INVALID_REQUEST
    invalid = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert invalid["evidence_outcome"] == "UNKNOWN"
    assert str(invalid["diagnostic"]).startswith("native_worker_request_invalid:")


def _sequenced_reply(reply):
    changed = json.loads(json.dumps(reply))
    changed["request"]["sequence"] = 1
    return changed


def test_controller_replay_relaunches_until_all_requests_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    roots = _roots(tmp_path)
    _set_member(roots, "ruff")

    def two_runs(paths, managed_run, _adapter_argv, _bug_hunt, _complete_pytest_inventory):
        for phase in ("first", "second"):
            managed_run(
                ["capsule-tool:ruff", f"--{phase}", str(paths[0])],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        return []

    monkeypatch.setitem(native_worker.EXTERNAL_ADAPTERS, "ruff", two_runs)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))

    assert native_worker.main() == native_worker.EXIT_REPLAY_REQUIRED
    first = json.loads(capsys.readouterr().out)
    assert first["sequence"] == 0
    replies = [{"request": first, "result": {"returncode": 0, "stderr": "", "stdout": "first"}}]

    _clear_output(roots)
    _write_replies(roots, replies)
    assert native_worker.main() == native_worker.EXIT_REPLAY_REQUIRED
    second = json.loads(capsys.readouterr().out)
    assert second["sequence"] == 1
    replies.append({"request": second, "result": {"returncode": 0, "stderr": "", "stdout": "second"}})

    _clear_output(roots)
    _write_replies(roots, replies)
    assert native_worker.main() == native_worker.EXIT_COMPLETE
    assert capsys.readouterr().out == ""
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert result["evidence_outcome"] == "PASS"


def test_native_policy_paths_materialize_only_inside_immutable_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    assert native_worker._materialized_adapter_argv(
        [
            "--config",
            "/opt/specfact/config/1/ruff.toml",
            "/opt/specfact/snapshot",
            "/opt/specfact/snapshot/pkg/example.py",
        ],
        project,
    ) == [
        "--config",
        str(project / ".specfact-native-config/1/ruff.toml"),
        str(project),
        str(project / "pkg/example.py"),
    ]
    with pytest.raises(native_worker.WorkerContractError, match="escapes"):
        native_worker._materialized_adapter_argv(
            ["/opt/specfact/config/../escape"],
            project,
        )


@pytest.mark.parametrize("kind", ["writable", "symlink"])
def test_reply_document_must_be_immutable_regular_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    roots = _roots(tmp_path)
    _set_member(roots, "ruff")
    monkeypatch.setitem(native_worker.EXTERNAL_ADAPTERS, "ruff", _fake_external_adapter("ruff"))
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))
    _write_replies(roots, [])
    reply_path = roots[1] / ".specfact-native-replies.json"
    roots[1].chmod(0o700)
    if kind == "writable":
        reply_path.chmod(0o600)
    else:
        reply_path.unlink()
        outside = tmp_path / "outside-replies.json"
        outside.write_text('{"replies":[],"schema":"specfact-native-analyzer-replies-v1"}', encoding="utf-8")
        reply_path.symlink_to(outside)
    roots[1].chmod(0o500)

    assert native_worker.main() == native_worker.EXIT_INVALID_REQUEST
    result = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert str(result["diagnostic"]).startswith("native_worker_request_invalid:")


def test_real_ruff_adapter_uses_managed_surface_without_host_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    roots = _roots(tmp_path)
    _set_member(roots, "ruff")
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))
    monkeypatch.setattr(
        native_worker.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("host subprocess executed")),
    )

    assert native_worker.main() == native_worker.EXIT_REPLAY_REQUIRED
    pending = json.loads(capsys.readouterr().out)
    assert pending["tool"] == "ruff"
    assert pending["argv"][0] == "capsule-tool:ruff"
    assert pending["argv"][-1] == "project/pkg/example.py"


def test_native_worker_and_retained_proofs_have_no_complexity_warning():
    from radon.complexity import cc_visit

    from specfact_code_review.tools.radon_runner import _allowed_paths, _map_radon_complexity_findings

    root = Path(__file__).resolve().parents[4]
    files = [
        Path(native_worker.__file__),
        Path(__file__),
        Path(__file__).with_name("test_native_project_runtime.py"),
        root / "tests/unit/test_capsule_proof_contexts.py",
    ]
    payload = {
        str(path): [
            {"name": block.name, "lineno": block.lineno, "complexity": block.complexity}
            for block in cc_visit(path.read_text(encoding="utf-8"))
        ]
        for path in files
    }
    findings = _map_radon_complexity_findings(payload, _allowed_paths(files))
    assert findings == [], [(finding.file, finding.rule, finding.message) for finding in findings]


def test_scoped_native_and_scheduling_entry_points_have_contracts():
    from specfact_code_review.tools.contract_runner import _scan_file

    root = Path(__file__).resolve().parents[4]
    files = [
        Path(native_worker.__file__),
        root / "scripts/check_capsule_deferral.py",
        root / "tools/smart_test_coverage.py",
    ]
    findings = [finding for path in files for finding in _scan_file(path)]
    assert findings == [], [(finding.file, finding.message) for finding in findings]


def test_controller_tamper_proof_has_no_blocking_nesting():
    from specfact_code_review.tools.radon_runner import _kiss_metric_findings

    findings = [finding for finding in _kiss_metric_findings(Path(__file__)) if finding.severity == "error"]
    assert findings == [], [(finding.file, finding.rule, finding.message) for finding in findings]


def _assert_native_semgrep_request_argv(request: dict[str, object], config_name: str) -> None:
    """Verify the exact capsule tool and policy source binding."""
    assert isinstance(request["argv"], list) and isinstance(request["environment"], dict)
    managed_argv = cast(list[str], request["argv"])
    assert managed_argv[0] == "capsule-tool:semgrep"
    assert managed_argv[-1] == "project/pkg/example.py"
    assert (
        managed_argv[managed_argv.index("--config") + 1]
        == f"project/.specfact-native-config/semgrep/.semgrep/{config_name}"
    )
    assert "--disable-nosem" in managed_argv


def _assert_native_semgrep_request_environment(request: dict[str, object]) -> None:
    """Verify private settings, disabled metrics and the existing launch budget."""
    environment = cast(dict[str, str], request["environment"])
    assert environment["HOME"] == "temporary/semgrep-home"
    assert environment["SEMGREP_SETTINGS_FILE"] == "temporary/semgrep-home/.semgrep/settings.yml"
    assert environment["SEMGREP_SEND_METRICS"] == "off"
    assert request["cwd"] == "project" and request["timeout_ms"] == 90000


@pytest.mark.parametrize("member,config_name", [("semgrep-clean", "clean_code.yaml"), ("semgrep-bugs", "bugs.yaml")])
def test_real_semgrep_adapter_replays_owned_policy_without_host_spawn(tmp_path, monkeypatch, member, config_name):
    from specfact_code_review.tools import semgrep_runner

    capsule, project, output, temporary = _roots(tmp_path)
    project.chmod(0o700)
    policy = project / ".specfact-native-config" / "semgrep"
    (policy / ".semgrep").mkdir(parents=True)
    (policy / ".semgrep" / config_name).write_text("rules: []\n", encoding="utf-8")
    source = project / "pkg/example.py"
    transport = native_worker.ReplayTransport(
        member=member, tool="semgrep", replies=[], capsule=capsule, project=project, temporary=temporary
    )
    original_process = semgrep_runner.subprocess
    original_temporary = semgrep_runner.tempfile
    original_command = semgrep_runner.analyzer_command
    monkeypatch.setattr(native_worker.subprocess, "run", lambda *args, **kwargs: pytest.fail("host process executed"))
    monkeypatch.delenv("SEMGREP_SEND_METRICS", raising=False)
    with pytest.raises(native_worker.RequestPending) as pending:
        native_worker._semgrep_external_adapter(member, [source], transport.run, [str(policy)], False, False)
    request = pending.value.request
    _assert_native_semgrep_request_argv(request, config_name)
    _assert_native_semgrep_request_environment(request)
    transport.replies.append(
        {
            "request": request,
            "result": {
                "returncode": 0,
                "stdout": json.dumps({"results": [], "paths": {"scanned": [str(source)], "skipped": []}}),
                "stderr": "",
            },
        }
    )
    assert native_worker._semgrep_external_adapter(member, [source], transport.run, [str(policy)], False, False) == []
    transport.verify_complete()
    assert semgrep_runner.subprocess is original_process
    assert semgrep_runner.tempfile is original_temporary
    assert semgrep_runner.analyzer_command is original_command
    assert (temporary / "semgrep-home").stat().st_mode & 0o777 == 0o700
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("policy_case", ["multiple", "outside", "default_outside"])
def test_native_semgrep_rejects_unbound_policies_before_launch(tmp_path, policy_case):
    capsule, project, _output, temporary = _roots(tmp_path)
    transport = native_worker.ReplayTransport(
        member="semgrep-clean", tool="semgrep", replies=[], capsule=capsule, project=project, temporary=temporary
    )
    policies = {"multiple": [str(project), str(project)], "outside": [str(capsule)], "default_outside": []}
    with pytest.raises(native_worker.ReplayContractViolation):
        native_worker._semgrep_external_adapter(
            "semgrep-clean", [project / "pkg/example.py"], transport.run, policies[policy_case], False, False
        )
    assert transport.consumed == 0
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("roots", [None, "tests", [True], ["."], ["../outside"], ["/outside"], ["a" * 241]])
def test_native_contract_inventory_rejects_invalid_root_identity(roots):
    with pytest.raises(native_worker.WorkerContractError, match="inventory paths"):
        native_worker._validated_contract_roots(roots)


@pytest.mark.parametrize(
    "document",
    [[], {}, {"schema": "wrong", "test_roots": []}, {"schema": "contract-inputs-v2", "test_roots": [], "extra": 1}],
)
def test_native_contract_inventory_rejects_invalid_schema(tmp_path, document):
    policy = tmp_path / ".specfact-native-config/contracts.json"
    policy.parent.mkdir()
    policy.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(native_worker.WorkerContractError, match="inventory schema"):
        native_worker._native_contract_roots(["contract-inputs-v2", str(policy)], tmp_path)


def test_native_contract_inventory_preserves_valid_and_legacy_roots(tmp_path):
    policy = tmp_path / ".specfact-native-config/contracts.json"
    policy.parent.mkdir()
    policy.write_text(
        json.dumps({"schema": "contract-inputs-v2", "test_roots": ["tests", "checks/unit"]}), encoding="utf-8"
    )
    assert native_worker._native_contract_roots(["contract-inputs-v2", str(policy)], tmp_path) == (
        Path("tests"),
        Path("checks/unit"),
    )
    assert native_worker._native_contract_roots(["contract-inputs-v1", "--test-root", "tests"], tmp_path) == (
        Path("tests"),
    )


def test_native_contract_inventory_rejects_symlink_and_outside_grant(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"schema": "contract-inputs-v2", "test_roots": []}), encoding="utf-8")
    link = tmp_path / ".specfact-native-config/contracts.json"
    link.parent.mkdir()
    link.symlink_to(outside)
    for policy in (link, outside):
        with pytest.raises(native_worker.WorkerContractError, match="sealed config grant"):
            native_worker._native_contract_roots(["contract-inputs-v2", str(policy)], tmp_path)
    with pytest.raises(native_worker.WorkerContractError, match="manifest request"):
        native_worker._native_contract_roots(["contract-inputs-v2"], tmp_path)
