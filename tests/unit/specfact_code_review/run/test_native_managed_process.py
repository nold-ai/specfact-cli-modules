"""Owned managed-process compatibility, with no host process creation."""

import io
import signal
import subprocess
import threading

import pytest

from specfact_code_review.run import native_managed_process as managed


def test_installed_popen_preserves_runtime_generic_annotations(tmp_path, monkeypatch):
    monkeypatch.setattr(managed, "NativeWorkerChannel", Transport)
    roots = [tmp_path / name for name in ("capsule", "project", "output", "temporary")]
    for root in roots:
        root.mkdir(exist_ok=True)
    with managed.installed_subprocess(*roots):
        namespace = {"subprocess": subprocess}
        exec("def consumer(process: subprocess.Popen[bytes]): pass", namespace)
        assert namespace["consumer"].__annotations__["process"] is subprocess.Popen


def test_private_virtualenv_path_overlay_is_validated_then_removed(tmp_path, monkeypatch):
    import plistlib

    interpreter = tmp_path / "capsule/python3"
    interpreter.parent.mkdir()
    interpreter.write_bytes(b"fixed image")
    prefix = tmp_path / "temporary/env"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "bin/python").symlink_to(interpreter)
    (prefix / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    transport = Transport()
    selected = adapter(tmp_path, transport)
    selected.executables[str(interpreter)] = "python"
    environment = {**managed.os.environ, "PATH": str(prefix / "bin") + ":"}
    selected.popen([str(prefix / "bin/python"), "-I", "-c", "print(1)"], env=environment)
    request = plistlib.loads(transport.calls[0][2])
    assert "PATH" not in request["environment"]
    with pytest.raises(managed.ManagedProcessError, match="environment override"):
        selected.popen([str(prefix / "bin/python"), "-c", "pass"], env={**environment, "PATH": "/usr/bin"})


@pytest.fixture(autouse=True)
def confined_cwd(tmp_path, monkeypatch):
    (tmp_path / "project").mkdir()
    monkeypatch.chdir(tmp_path / "project")
    monkeypatch.setattr(managed.os, "environ", {"LANG": "C", "PYTHONHASHSEED": "0"})


def test_poetry_locale_encoding_returns_text_in_communicate(tmp_path):
    transport = Transport()
    transport.running = False
    result = adapter(tmp_path, transport).run(
        ["/capsule/python/bin/python3", "-c", "pass"], text=True, encoding="locale", capture_output=True, check=True
    )
    assert result.stdout == "native child output\n"


def test_invalid_encoding_is_rejected_before_launch(tmp_path):
    transport = Transport()
    with pytest.raises(LookupError):
        adapter(tmp_path, transport).popen(
            ["/capsule/python/bin/python3", "-c", "pass"], text=True, encoding="not-a-real-codec"
        )
    assert not transport.calls


class Transport:
    def __init__(self):
        self.calls = []
        self.running = True
        self.stdout = bytearray(b"native child output\n")
        self.stderr = bytearray(b"native child diagnostic\n")

    def exchange(self, opcode, handle=0, payload=b""):
        self.calls.append((opcode, handle, payload))
        if opcode == managed.LAUNCH:
            return managed.WorkerReply(17, -1, b"")
        if opcode == managed.POLL:
            return managed.WorkerReply(handle, -1 if self.running else 0, b"")
        if opcode in {managed.STDOUT, managed.STDERR}:
            source = self.stdout if opcode == managed.STDOUT else self.stderr
            data = bytes(source)
            source.clear()
            return managed.WorkerReply(handle, -1 if self.running else 0, data)
        if opcode == managed.WRITE_STDIN:
            return managed.WorkerReply(handle, len(payload), b"")
        if opcode == managed.CLOSE_STDIN:
            self.running = False
        if opcode == managed.SIGNAL:
            self.running = False
        return managed.WorkerReply(handle, 0, b"")


def adapter(tmp_path, transport):
    roots = {name: tmp_path / name for name in ("project", "temporary", "output")}
    for root in roots.values():
        root.mkdir(exist_ok=True)
    return managed.ManagedSubprocess(transport, roots=roots, executables={"/capsule/python/bin/python3": "python"})


def test_managed_popen_launches_live_child_and_communicates_without_host_popen(tmp_path, monkeypatch):
    transport = Transport()
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("host Popen used"))
    process = adapter(tmp_path, transport).popen(
        ["/capsule/python/bin/python3", "-c", "print('child')"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.poll() is None
    assert process.communicate("input\n", timeout=1) == ("native child output\n", "native child diagnostic\n")
    assert process.returncode == 0
    assert transport.calls[0][0] == managed.LAUNCH
    assert any(row[0] == managed.WRITE_STDIN for row in transport.calls)


@pytest.mark.parametrize(
    "kwargs", [{"shell": True}, {"preexec_fn": lambda: None}, {"pass_fds": (9,)}, {"cwd": "/private/host"}]
)
def test_unmanaged_launch_options_are_rejected_before_broker_request(tmp_path, kwargs):
    transport = Transport()
    with pytest.raises(managed.ManagedProcessError):
        adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"], **kwargs)
    assert transport.calls == []


def test_unknown_host_executable_never_reaches_the_broker(tmp_path):
    transport = Transport()
    with pytest.raises(managed.ManagedProcessError):
        adapter(tmp_path, transport).popen(["/usr/bin/env", "python"])
    assert transport.calls == []


def test_packaged_uv_launch_preserves_owned_streams_and_private_environment(tmp_path):
    import plistlib

    transport = Transport()
    selected = adapter(tmp_path, transport)
    tool = tmp_path / "capsule/tools/uv"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"verified capsule uv fixture")
    tool.chmod(0o555)
    selected.executables[str(tool)] = "uv"
    wheelhouse = selected.roots["project"] / "wheelhouse"
    wheelhouse.mkdir()
    prefix = selected.roots["temporary"] / "environment"
    (prefix / "bin").mkdir(parents=True)
    python = tool.parent.parent / "python/bin/python3"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"verified capsule Python fixture")
    python.chmod(0o555)
    selected.executables[str(python)] = "python"
    (prefix / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    (prefix / "bin/python").symlink_to(python)
    environment = {
        **managed.os.environ,
        "VIRTUAL_ENV": str(prefix),
        "PATH": str(prefix / "bin") + ":",
        "UV_PYTHON": str(tool.parent.parent / "python/bin/python3"),
        "SPECFACT_MANAGED_UV": "1",
        "private_token": "denied",
    }
    selected.popen([tool, "pip", "install", "--no-index", "example"], env=environment, stdout=subprocess.PIPE)
    request = plistlib.loads(transport.calls[0][2])
    assert request["program"] == "uv"
    assert request["argv"] == ["pip", "install", "--python", str(prefix / "bin/python"), "--no-index", "example"]
    assert request["python_paths"] == [] and request["python_prefix"] == request["python_alias"] == ""
    assert "PATH" not in request["environment"]
    assert "UV_PYTHON" not in request["environment"]
    assert "SPECFACT_MANAGED_UV" not in request["environment"]
    assert "private_token" not in request["environment"]
    assert request["environment"]["UV_OFFLINE"] == request["environment"]["UV_NO_INDEX"] == "1"
    assert request["environment"]["UV_FIND_LINKS"] == str(wheelhouse)


@pytest.mark.parametrize("substitution", ["host", "alias", "symlink", "writable", "outside-env"])
def test_uv_identity_and_environment_substitution_never_reach_broker(tmp_path, substitution):
    transport = Transport()
    selected = adapter(tmp_path, transport)
    tool = tmp_path / "capsule/tools/uv"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"verified capsule uv fixture")
    tool.chmod(0o555)
    selected.executables[str(tool)] = "uv"
    executable = tool
    environment = dict(managed.os.environ)
    if substitution == "host":
        executable = "/usr/bin/uv"
    elif substitution == "alias":
        executable = "uv"
    elif substitution == "symlink":
        tool.unlink()
        tool.symlink_to("another-image")
    elif substitution == "writable":
        tool.chmod(0o755)
    else:
        environment["VIRTUAL_ENV"] = "/host/environment"
    with pytest.raises(managed.ManagedProcessError):
        selected.popen([executable, "venv", "environment"], env=environment)
    assert transport.calls == []


@pytest.mark.parametrize(
    "field",
    [
        "UV_OFFLINE",
        "UV_NO_INDEX",
        "UV_FIND_LINKS",
        "UV_CACHE_DIR",
        "UV_PYTHON_DOWNLOADS",
        "UV_KEYRING_PROVIDER",
        "UV_LINK_MODE",
    ],
)
def test_uv_override_diagnostic_names_only_the_fixed_field(tmp_path, field):
    transport = Transport()
    selected = adapter(tmp_path, transport)
    tool = tmp_path / "capsule/tools/uv"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"verified uv fixture")
    tool.chmod(0o555)
    selected.executables[str(tool)] = "uv"
    (selected.roots["project"] / "wheelhouse").mkdir()
    private_value = str(selected.roots["temporary"] / "source/wheelhouse-secret")
    with pytest.raises(managed.ManagedProcessError) as error:
        selected.popen([tool, "pip", "install", "fixture"], env={**managed.os.environ, field: private_value})
    assert f"uv offline environment override is not admitted:{field}" in str(error.value)
    assert private_value not in str(error.value)
    assert transport.calls == []


@pytest.fixture
def uv_environment_adapter(tmp_path):
    transport = Transport()
    selected = adapter(tmp_path, transport)
    capsule = tmp_path / "capsule"
    uv = capsule / "tools/uv"
    python = capsule / "python/bin/python3"
    for image in (uv, python):
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"verified capsule image")
        image.chmod(0o555)
    selected.executables.update({str(uv): "uv", str(python): "python"})
    (selected.roots["project"] / "wheelhouse").mkdir()
    prefix = selected.roots["temporary"] / "environment"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    alias = prefix / "bin/python"
    alias.symlink_to(python)
    return selected, transport, uv, python, prefix, alias


@pytest.mark.parametrize("command", ["install", "sync"])
def test_uv_install_selects_verified_private_environment_without_quiet_flag_changes(uv_environment_adapter, command):
    import plistlib

    selected, transport, uv, python, prefix, alias = uv_environment_adapter
    selected.popen(
        [str(uv), "pip", command, "-qq", "example"],
        env={**managed.os.environ, "VIRTUAL_ENV": str(prefix), "UV_PYTHON": str(python)},
    )
    request = plistlib.loads(transport.calls[0][2])
    assert request["argv"] == ["pip", command, "--python", str(alias), "-qq", "example"]
    assert request["program"] == "uv"
    assert "UV_PYTHON" not in request["environment"]
    assert request["environment"]["VIRTUAL_ENV"] == str(prefix)


@pytest.mark.parametrize(
    "fault", ["alias", "configuration", "system-site", "selector", "joined-selector", "short-selector"]
)
def test_uv_install_cannot_select_foreign_or_unverified_environment(uv_environment_adapter, fault):
    selected, transport, uv, python, prefix, alias = uv_environment_adapter
    args = [str(uv), "pip", "install", "example"]
    if fault == "alias":
        alias.unlink()
        alias.write_bytes(b"customer interpreter")
    elif fault == "configuration":
        (prefix / "pyvenv.cfg").unlink()
    elif fault == "system-site":
        (prefix / "pyvenv.cfg").write_text("include-system-site-packages = true\n")
    elif fault == "selector":
        args.extend(["--python", str(python)])
    elif fault == "joined-selector":
        args.append("--python=" + str(python))
    else:
        args.append("-p" + str(python))
    with pytest.raises(managed.ManagedProcessError):
        selected.popen(args, env={**managed.os.environ, "VIRTUAL_ENV": str(prefix)})
    assert transport.calls == []


@pytest.mark.parametrize("form", ["long", "joined", "short", "short-joined"])
def test_uv_install_preserves_an_explicit_verified_private_alias(uv_environment_adapter, form):
    import plistlib

    selected, transport, uv, _python, prefix, alias = uv_environment_adapter
    options = {
        "long": ["--python", str(alias)],
        "joined": ["--python=" + str(alias)],
        "short": ["-p", str(alias)],
        "short-joined": ["-p" + str(alias)],
    }[form]
    args = [str(uv), "pip", "install", *options, "example"]
    selected.popen(args, env={**managed.os.environ, "VIRTUAL_ENV": str(prefix)})
    assert plistlib.loads(transport.calls[0][2])["argv"] == args[1:]


def test_hatch_pathlike_arguments_keep_normal_subprocess_compatibility(tmp_path):
    import plistlib
    from pathlib import Path

    transport = Transport()
    selected = adapter(tmp_path, transport)
    requirements = selected.roots["temporary"] / "requirements.txt"
    selected.popen([Path("/capsule/python/bin/python3"), "-m", "pip", "install", "-r", requirements])
    assert plistlib.loads(transport.calls[0][2])["argv"][-1] == str(requirements)


def test_managed_signal_uses_handle_not_host_pid(tmp_path):
    transport = Transport()
    process = adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"])
    process.send_signal(signal.SIGTERM)
    assert transport.calls[-1][0:2] == (managed.SIGNAL, 17)
    with pytest.raises(managed.ManagedProcessError):
        _ = process.pid


def test_communicate_timeout_includes_stalled_standard_input(tmp_path):
    class StalledInput(Transport):
        def exchange(self, opcode, handle=0, payload=b""):
            if opcode == managed.WRITE_STDIN:
                return managed.WorkerReply(handle, 0, b"")
            return super().exchange(opcode, handle, payload)

    with pytest.raises(subprocess.TimeoutExpired):
        adapter(tmp_path, StalledInput()).run(
            ["/capsule/python/bin/python3", "-c", "pass"], input=b"blocked", capture_output=True, timeout=0.02
        )


def test_launch_document_contains_only_inherited_project_paths(tmp_path, monkeypatch):
    import plistlib
    import sys

    transport = Transport()
    selected = adapter(tmp_path, transport)
    monkeypatch.setattr(sys, "path", ["/host/environment", str(selected.roots["project"])])
    selected.popen(["/capsule/python/bin/python3", "-c", "pass"])
    document = plistlib.loads(transport.calls[0][2])
    assert document["python_paths"] == [str(selected.roots["project"])]


def test_uv_isolated_probe_excludes_inherited_project_imports(tmp_path, monkeypatch):
    import plistlib
    import sys

    transport = Transport()
    selected = adapter(tmp_path, transport)
    monkeypatch.setattr(sys, "path", [str(selected.roots["project"])])
    selected.popen(["/capsule/python/bin/python3", "-I", "-B", "-c", "print('query')"])
    request = plistlib.loads(transport.calls[0][2])
    assert request["argv"][:2] == ["-I", "-B"]
    assert request["python_paths"] == []


def test_default_and_relative_cwd_follow_the_confined_caller(tmp_path, monkeypatch):
    selected = adapter(tmp_path, Transport())
    source = selected.roots["temporary"] / "source"
    (source / "generated").mkdir(parents=True)
    monkeypatch.chdir(source)
    assert selected._cwd(None) == "temporary/source"
    assert selected._cwd("generated") == "temporary/source/generated"


def test_omitted_environment_retains_permitted_build_variables(tmp_path, monkeypatch):
    import plistlib

    transport = Transport()
    monkeypatch.setenv("NATIVE_BUILD_VERSION", "1.2")
    adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"])
    assert plistlib.loads(transport.calls[0][2])["environment"]["NATIVE_BUILD_VERSION"] == "1.2"


def test_pep517_overlay_preserves_only_inherited_private_paths(tmp_path, monkeypatch):
    import plistlib

    transport = Transport()
    selected = adapter(tmp_path, transport)
    site = selected.roots["temporary"] / "build-env" / "site"
    site.mkdir(parents=True)
    monkeypatch.setenv("PYTHONPATH", str(site))
    selected.popen(["/capsule/python/bin/python3", "-c", "pass"])
    request = plistlib.loads(transport.calls[0][2])
    assert request["environment"]["PYTHONPATH"] == str(site)
    assert request["python_paths"][0] == str(site)


@pytest.mark.parametrize("options", [["-B", "-I"], ["-W", "ignore", "-I"]])
def test_isolation_after_other_options_removes_python_overlays(tmp_path, monkeypatch, options):
    import plistlib

    transport = Transport()
    selected = adapter(tmp_path, transport)
    site = selected.roots["temporary"] / "build-site"
    site.mkdir()
    monkeypatch.setenv("PYTHONPATH", str(site))
    selected.popen(["/capsule/python/bin/python3", *options, "-c", "pass"])
    request = plistlib.loads(transport.calls[0][2])
    assert "PYTHONPATH" not in request["environment"]
    assert request["python_paths"] == []


@pytest.mark.parametrize("value", ["/host/environment", ":", "/host/../environment"])
def test_isolated_launch_ignores_unadmitted_python_path(tmp_path, monkeypatch, value):
    import plistlib

    transport = Transport()
    monkeypatch.setenv("PYTHONPATH", value)
    adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-B", "-I", "-c", "pass"])
    request = plistlib.loads(transport.calls[0][2])
    assert "PYTHONPATH" not in request["environment"]
    assert request["python_paths"] == []


@pytest.mark.parametrize("value", ["/host/environment", ":", "/host/../environment"])
def test_pep517_overlay_cannot_add_host_or_empty_paths(tmp_path, monkeypatch, value):
    transport = Transport()
    monkeypatch.setenv("PYTHONPATH", value)
    with pytest.raises(managed.ManagedProcessError, match="Python path"):
        adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"])
    assert not transport.calls


def test_wait_releases_the_handle_and_preserves_unread_capture(tmp_path):
    transport = Transport()
    transport.running = False
    process = adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"], stdout=subprocess.PIPE)
    assert process.wait(timeout=1) == 0
    assert any(row[0] == managed.RELEASE for row in transport.calls)
    assert process.stdout is not None
    assert process.stdout.read() == b"native child output\n"


def test_sized_stream_read_returns_partial_data_before_child_exit(tmp_path):
    transport = Transport()
    process = adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"], stdout=subprocess.PIPE)
    results = []
    done = threading.Event()

    def read():
        assert process.stdout is not None
        results.append(process.stdout.read(4096))
        done.set()

    thread = threading.Thread(target=read)
    thread.start()
    returned_while_running = done.wait(0.1)
    transport.running = False
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert returned_while_running
    assert results == [b"native child output\n"]


def test_normal_context_exit_waits_without_cancelling(tmp_path):
    class CompletesNormally(Transport):
        def exchange(self, opcode, handle=0, payload=b""):
            if opcode == managed.POLL and sum(row[0] == managed.POLL for row in self.calls) > 0:
                self.running = False
            return super().exchange(opcode, handle, payload)

    transport = CompletesNormally()
    with adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"]):
        pass
    assert not any(row[0] == managed.SIGNAL for row in transport.calls)


def test_wait_forwards_inherited_output(tmp_path, capsys):
    transport = Transport()
    transport.running = False
    process = adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"])
    assert process.wait(timeout=1) == 0
    captured = capsys.readouterr()
    assert captured.out == "native child output\n"
    assert captured.err == "native child diagnostic\n"


def test_private_virtualenv_alias_selects_own_prefix(tmp_path, monkeypatch):
    import plistlib
    import sys

    selected = adapter(tmp_path, Transport())
    capsule_python = tmp_path / "capsule/python/bin/python3"
    capsule_python.parent.mkdir(parents=True)
    capsule_python.write_bytes(b"verified capsule Python")
    selected.executables[str(capsule_python)] = "python"
    venv = selected.roots["temporary"] / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    (venv / "bin/python").symlink_to(capsule_python)
    # A nested venv worker already registers its sys.executable; that registration
    # must not turn the next launch back into a capsule-prefix process.
    selected.executables[str(venv / "bin/python")] = "python"
    site = venv / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    site.mkdir(parents=True)
    selected.popen([str(venv / "bin/python"), "-c", "print('own environment')"])
    document = plistlib.loads(selected.transport.calls[0][2])
    assert document["python_prefix"] == str(venv)
    assert document["python_paths"] == [str(site)]


def test_private_environment_preserves_python3_alias(tmp_path):
    import plistlib

    selected = adapter(tmp_path, Transport())
    image = tmp_path / "capsule/python/bin/python3"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"capsule Python")
    selected.executables[str(image)] = "python"
    venv = selected.roots["temporary"] / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("include-system-site-packages=false\n")
    (venv / "bin/python3").symlink_to(image)
    selected.popen([str(venv / "bin/python3"), "-c", "pass"])
    assert plistlib.loads(selected.transport.calls[0][2])["python_alias"] == "python3"


def test_virtualenv_alias_cannot_select_an_unverified_image(tmp_path):
    selected = adapter(tmp_path, Transport())
    venv = selected.roots["temporary"] / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    (venv / "bin/python").write_bytes(b"customer image")
    with pytest.raises(managed.ManagedProcessError, match="executable identity"):
        selected.popen([str(venv / "bin/python"), "-c", "pass"])
    assert not selected.transport.calls


def test_replacing_a_registered_private_alias_fails_admission(tmp_path):
    selected = adapter(tmp_path, Transport())
    image = tmp_path / "capsule/python/bin/python3"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"fixed capsule image")
    selected.executables[str(image)] = "python"
    venv = selected.roots["temporary"] / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("include-system-site-packages=false\n")
    alias = venv / "bin/python"
    alias.symlink_to(image)
    selected.executables[str(alias)] = "python"
    alias.unlink()
    alias.write_bytes(b"substituted executable")
    with pytest.raises(managed.ManagedProcessError, match="executable identity"):
        selected.popen([str(alias), "-c", "pass"])
    assert not selected.transport.calls


def test_utf8_probe_override_is_narrowly_admitted(tmp_path):
    import plistlib

    selected = adapter(tmp_path, Transport())
    selected.popen(["/capsule/python/bin/python3", "-c", "pass"], env={"PYTHONUTF8": "1"})
    assert plistlib.loads(selected.transport.calls[0][2])["environment"] == {"PYTHONUTF8": "1"}
    with pytest.raises(managed.ManagedProcessError, match="environment override"):
        selected.popen(["/capsule/python/bin/python3", "-c", "pass"], env={"PYTHONUTF8": "0"})


def test_context_exit_closes_stdin_before_waiting(tmp_path):
    class RequiresEof(Transport):
        def exchange(self, opcode, handle=0, payload=b""):
            if opcode == managed.POLL and self.running:
                raise AssertionError("waited before stdin EOF")
            return super().exchange(opcode, handle, payload)

    transport = RequiresEof()
    with adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-"], stdin=subprocess.PIPE) as child:
        assert isinstance(child.stdin, io.RawIOBase)
        child.stdin.write(b"print('complete')")
    assert any(row[0] == managed.RELEASE for row in transport.calls)


def test_inherited_binary_output_is_forwarded_and_handle_released(tmp_path, monkeypatch):
    import io
    import sys

    raw = io.BytesIO()
    output = io.TextIOWrapper(raw, encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", output)
    transport = Transport()
    transport.running = False
    transport.stdout[:] = b"\xff\x00native"
    child = adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"], stderr=subprocess.DEVNULL)
    assert child.wait() == 0
    output.flush()
    assert raw.getvalue() == b"\xff\x00native"
    assert any(row[0] == managed.RELEASE for row in transport.calls)


def test_managed_python_omits_missing_import_paths_without_broadening_grants(tmp_path, monkeypatch):
    import plistlib

    transport = Transport()
    selected = adapter(tmp_path, transport)
    site = tmp_path / "project/site-packages"
    site.mkdir()
    missing = tmp_path / "project/project/.specfact-native-analyzers"
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(managed.sys, "path", [str(site), str(missing), str(outside)])
    selected.popen(["/capsule/python/bin/python3", "-u", "-c", "pass"], stdin=subprocess.PIPE)
    request = plistlib.loads(transport.calls[0][2])
    assert request["python_paths"] == [str(site.resolve())]


def test_managed_binary_stream_supports_execnet_byte_channel_selection(tmp_path):
    transport = Transport()
    transport.running = False
    process = adapter(tmp_path, transport).popen(["/capsule/python/bin/python3", "-c", "pass"], stdout=subprocess.PIPE)
    assert process.stdout is not None
    channel = getattr(process.stdout, "buffer", process.stdout)
    assert channel.read() == b"native child output\n"


def test_managed_uv_discovery_never_uses_host_path(tmp_path, monkeypatch):
    import shutil

    monkeypatch.setattr(managed, "NativeWorkerChannel", Transport)
    capsule = tmp_path / "capsule"
    image = capsule / "tools/uv"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"verified native uv fixture")
    image.chmod(0o555)
    roots = [tmp_path / name for name in ("project", "output", "temporary")]
    for root in roots:
        root.mkdir(exist_ok=True)
    with managed.installed_subprocess(capsule, *roots):
        assert shutil.which("uv", path="/host/bin") == str(image)
        assert shutil.which("/usr/bin/uv") is None
        image.chmod(0o755)
        assert shutil.which("uv") is None
